"""主页"""
import json
import os
import tempfile
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QScrollArea, QGridLayout, QFrame, QStackedWidget,
    QProgressBar, QMessageBox, QSizePolicy, QSlider
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread, QUrl, QMetaObject, Q_ARG
from PyQt6.QtGui import QFont, QPixmap, QIcon
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput

from .base_page import BasePage
from api.models import models_api
from api.async_utils import run_async
from api.auth import auth_api


class ModelCard(QFrame):
    """模型卡片组件"""
    detail_clicked = pyqtSignal(str)  # 发送模型ID
    
    def __init__(self, model_data, parent=None):
        super().__init__(parent)
        self.model_id = model_data.get("id", "")
        self.model_name = model_data.get("name", "未知")
        self.model_image = model_data.get("image", "")
        self.model_category = model_data.get("category", "全部")
        
        self.setup_ui()
    
    def setup_ui(self):
        """设置UI"""
        self.setFixedSize(200, 280)
        self.setStyleSheet("""
            QFrame {
                background-color: #252525;
                border: 2px solid #3d3d3d;
                border-radius: 12px;
            }
            QFrame:hover {
                border: 2px solid #8b5cf6;
                background-color: #2d2d2d;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # 头像区域
        image_label = QLabel()
        image_label.setFixedSize(180, 180)
        image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        image_label.setStyleSheet("""
            QLabel {
                background-color: #1e1e1e;
                border-radius: 8px;
                border: 1px solid #3d3d3d;
            }
        """)
        
        # 如果有图片路径，尝试加载图片
        if self.model_image and os.path.exists(self.model_image):
            try:
                pixmap = QPixmap(self.model_image)
                if not pixmap.isNull():
                    # 缩放图片以适应标签大小，保持宽高比
                    scaled_pixmap = pixmap.scaled(
                        180, 180, 
                        Qt.AspectRatioMode.KeepAspectRatio, 
                        Qt.TransformationMode.SmoothTransformation
                    )
                    image_label.setPixmap(scaled_pixmap)
                else:
                    # 图片加载失败，显示占位符
                    placeholder = self.model_name[0] if self.model_name else "?"
                    image_label.setText(f"<div style='font-size: 48px; color: #8b5cf6;'>{placeholder}</div>")
            except Exception as e:
                # 图片加载出错，显示占位符
                print(f"加载图片失败 {self.model_image}: {e}")
                placeholder = self.model_name[0] if self.model_name else "?"
                image_label.setText(f"<div style='font-size: 48px; color: #8b5cf6;'>{placeholder}</div>")
        else:
            # 根据名称生成占位符
            placeholder = self.model_name[0] if self.model_name else "?"
            image_label.setText(f"<div style='font-size: 48px; color: #8b5cf6;'>{placeholder}</div>")
        
        image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(image_label)
        
        # 名称
        name_label = QLabel(self.model_name)
        name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # 基础样式由全局样式表提供，只设置特殊样式
        name_label.setStyleSheet("font-size: 16px; font-weight: bold; padding: 5px; border: none; background-color: transparent;")
        layout.addWidget(name_label)
        
        # 详情按钮
        detail_btn = QPushButton("音色详情")
        detail_btn.setStyleSheet("""
            QPushButton {
                background-color: #8b5cf6;
                color: #ffffff;
                border: none;
                border-radius: 6px;
                padding: 8px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #7c3aed;
            }
            QPushButton:pressed {
                background-color: #6d28d9;
            }
        """)
        detail_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        detail_btn.clicked.connect(lambda: self.detail_clicked.emit(self.model_id))
        layout.addWidget(detail_btn)
        
        layout.addStretch()


class ModelDetailPage(QWidget):
    """模型详情页面"""
    back_clicked = pyqtSignal()  # 返回信号
    progress_updated = pyqtSignal(int, int, str)  # 进度更新信号 (downloaded, total, status_text)
    
    def __init__(self, model_data, parent=None, is_purchased=False, home_page=None):
        super().__init__(parent)
        self.model_data = model_data
        self.is_purchased = is_purchased  # 是否已购买/已下载
        self.home_page = home_page  # 主页引用，用于更新本地模型uid列表
        self.trial_timer = QTimer()
        self.trial_timer.timeout.connect(self.update_trial_time)
        self.trial_seconds = 0
        self.trial_active = False
        
        # 音频播放相关
        self.audio_player = None
        self.audio_output = None
        self.audio_file_path = None
        self.is_playing = False
        self.play_btn = None
        self.time_label = None
        self.progress_slider = None
        self.is_slider_dragging = False  # 标记是否正在拖拽滑块
        
        # 下载线程相关
        self.download_thread = None
        self.download_worker = None
        
        # 保存下载区块和使用区块的引用，用于动态切换
        self.download_section = None
        self.use_section = None
        
        # 查找音频文件
        self.find_audio_file()
        
        self.setup_ui()
    
    def on_back_clicked(self):
        """返回按钮点击"""
        # 清理下载线程（如果存在）
        self._cleanup_download_thread()
        self.back_clicked.emit()
    
    def _cleanup_download_thread(self):
        """清理下载线程资源"""
        if self.download_thread and self.download_thread.isRunning():
            try:
                if self.download_worker:
                    self.download_worker.finished.disconnect()
                    self.download_worker.error.disconnect()
                self.download_thread.quit()
                self.download_thread.wait(3000)  # 等待最多3秒
                if self.download_thread.isRunning():
                    self.download_thread.terminate()
                    self.download_thread.wait()
            except Exception as e:
                print(f"清理下载线程时出错: {e}")
            finally:
                if self.download_thread:
                    self.download_thread.deleteLater()
                if self.download_worker:
                    self.download_worker.deleteLater()
                self.download_thread = None
                self.download_worker = None
    
    def setup_ui(self):
        """设置详情页面UI"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)
        
        # 面包屑导航和返回按钮
        nav_layout = QHBoxLayout()
        
        back_btn = QPushButton("← 返回")
        # 基础样式由全局样式表提供，只设置特殊样式
        back_btn.setStyleSheet("""
            QPushButton {
                border-radius: 6px;
                padding: 8px 15px;
                font-size: 14px;
            }
        """)
        back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        back_btn.clicked.connect(self.on_back_clicked)
        nav_layout.addWidget(back_btn)
        
        breadcrumb = QLabel(f"首页 / 音色详情")
        breadcrumb.setStyleSheet("color: #8b5cf6; font-size: 14px;")
        nav_layout.addWidget(breadcrumb)
        nav_layout.addStretch()
        
        main_layout.addLayout(nav_layout)
        
        # 主要内容区域（左右分栏）
        content_layout = QHBoxLayout()
        content_layout.setSpacing(20)
        
        # 左侧：大图和基本信息
        left_panel = self.create_left_panel()
        left_panel.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        content_layout.addWidget(left_panel, 1)
        
        # 右侧：详细信息
        right_panel = self.create_right_panel()
        right_panel.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        content_layout.addWidget(right_panel, 1)
        
        main_layout.addLayout(content_layout)
    
    def create_left_panel(self):
        """创建左侧面板"""
        panel = QWidget()
        panel.setStyleSheet("background-color: #25252E; border-radius: 4px;")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # 显示模型图片
        image_label = QLabel()
        image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        image_label.setStyleSheet("""
            QLabel {
                background-color: rgba(0, 0, 0, 0.3);
                border-radius: 8px;
                color: #ffffff;
                font-size: 48px;
            }
        """)
        image_label.setScaledContents(True)  # 允许自动缩放，保持宽高比
        
        # 加载模型图片
        model_image = self.model_data.get("image", "")
        if model_image and os.path.exists(model_image):
            try:
                pixmap = QPixmap(model_image)
                if not pixmap.isNull():
                    image_label.setPixmap(pixmap)
                else:
                    # 图片加载失败，显示占位符
                    image_label.setText("🖼️")
            except Exception as e:
                # 图片加载出错，显示占位符
                print(f"加载详情图片失败 {model_image}: {e}")
                image_label.setText("🖼️")
        else:
            # 没有图片，显示占位符
            image_label.setText("🖼️")
        
        layout.addWidget(image_label, 4)
        
        # 底部信息面板
        info_panel = QWidget()
        info_layout = QVBoxLayout(info_panel)
        info_layout.setContentsMargins(20, 20, 20, 20)
        info_layout.setSpacing(15)
        
        # 模型名称
        name_label = QLabel(self.model_data.get("name", "未知"))
        name_label.setStyleSheet("color: #ffffff; font-size: 24px; font-weight: bold;")
        info_layout.addWidget(name_label)
        
        # 信息行
        info_row = QHBoxLayout()
        
        info_text = QLabel(f"""
价格: {self.model_data.get("price", 0)}<br>
版本: {self.model_data.get("version", "V1")}<br>
采样率: {self.model_data.get("sample_rate", "48K")}<br>
类别: {self.model_data.get("category_name", "免费音色")}
        """)
        # 基础样式由全局样式表提供，只设置特殊字体大小
        info_text.setStyleSheet("font-size: 14px;")
        info_row.addWidget(info_text)
        info_row.addStretch()
        
        # 立即购买按钮（如果已购买则显示"已购买"）
        if self.is_purchased:
            buy_btn = QPushButton("已购买")
            buy_btn.setStyleSheet("""
                QPushButton {
                    background-color: #4caf50;
                    color: #ffffff;
                    border: none;
                    border-radius: 6px;
                    padding: 10px 30px;
                    font-size: 14px;
                    font-weight: bold;
                }
            """)
            buy_btn.setEnabled(False)
        else:
            buy_btn = QPushButton("立即购买")
            buy_btn.setStyleSheet("""
                QPushButton {
                    background-color: #8b5cf6;
                    color: #ffffff;
                    border: none;
                    border-radius: 6px;
                    padding: 10px 30px;
                    font-size: 14px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #7c3aed;
                }
            """)
            buy_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        info_row.addWidget(buy_btn)
        
        info_layout.addLayout(info_row)
        layout.addWidget(info_panel, 1)
        
        return panel
    
    def create_right_panel(self):
        """创建右侧面板"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setSpacing(20)
        
        # 音色介绍
        intro_section = self.create_section("音色介绍", self.model_data.get("description", "茶韵悠悠可音袅袅少御音介于少女与御姐之间既有少女清脆又具御姐沉稳圆润柔和年龄感适中清嗓咳嗽呢喃细语悄悄话 笑声 自带情绪感"))
        layout.addWidget(intro_section, 4)
        
        # 试听
        audition_section = self.create_audition_section()
        layout.addWidget(audition_section, 3)
        
        # 如果已购买/已下载，不显示试用区块，显示使用按钮
        if self.is_purchased:
            # 使用按钮（已下载，直接使用）
            self.use_section = self.create_use_section()
            layout.addWidget(self.use_section, 5)
        else:
            # 试用
            trial_section = self.create_trial_section()
            layout.addWidget(trial_section, 5)
            
            # 下载
            self.download_section = self.create_download_section()
            layout.addWidget(self.download_section, 5)
        
        layout.addStretch()
        return panel
    
    def create_section(self, title, content):
        """创建通用信息区块"""
        section = QWidget()
        section.setStyleSheet("""
            QWidget {
                background-color: #252525;
                border-radius: 8px;
                padding: 20px;
            }
        """)
        layout = QVBoxLayout(section)
        layout.setSpacing(10)
        
        title_label = QLabel(title)
        # 基础样式由全局样式表提供，只设置特殊样式
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; border: none; background-color: transparent; padding: 0px;")
        layout.addWidget(title_label)
        
        content_label = QLabel(content)
        content_label.setWordWrap(True)
        # 基础样式由全局样式表提供，只设置特殊样式
        content_label.setStyleSheet("font-size: 14px; line-height: 1.6; border: none; background-color: transparent; padding: 0px;")
        layout.addWidget(content_label)
        
        return section
    
    def create_audition_section(self):
        """创建试听区块"""
        section = QWidget()
        section.setStyleSheet("""
            QWidget {
                background-color: #252525;
                border-radius: 8px;
                padding: 20px;
            }
        """)
        layout = QVBoxLayout(section)
        layout.setSpacing(15)
        
        title_label = QLabel("试听")
        # 基础样式由全局样式表提供，只设置特殊样式
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; border: none; background-color: transparent; padding: 0px;")
        layout.addWidget(title_label)
        
        # 播放器控件
        player_layout = QHBoxLayout()
        player_layout.setContentsMargins(0, 0, 0, 0)
        player_layout.setSpacing(12)
        
        play_btn = QPushButton("▶")
        play_btn.setFixedSize(40, 40)
        play_btn.setStyleSheet("""
            QPushButton {
                background-color: #8b5cf6;
                color: #ffffff;
                border: none;
                border-radius: 20px;
                font-size: 16px;
                padding: 0px;
            }
            QPushButton:hover {
                background-color: #7c3aed;
            }
        """)
        play_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        play_btn.clicked.connect(self.on_play_clicked)
        self.play_btn = play_btn
        player_layout.addWidget(play_btn)
        
        # 进度条
        progress_slider = QSlider(Qt.Orientation.Horizontal)
        progress_slider.setMinimum(0)
        progress_slider.setMaximum(1000)  # 使用1000作为最大值，便于精确控制
        progress_slider.setValue(0)
        progress_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                background-color: #3d3d3d;
                height: 4px;
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                background-color: #8b5cf6;
                width: 12px;
                height: 12px;
                border-radius: 6px;
                margin: -4px 0;
            }
            QSlider::handle:horizontal:hover {
                background-color: #7c3aed;
                width: 14px;
                height: 14px;
                border-radius: 7px;
            }
            QSlider::sub-page:horizontal {
                background-color: #8b5cf6;
                border-radius: 2px;
            }
        """)
        progress_slider.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        progress_slider.sliderPressed.connect(self.on_slider_pressed)
        progress_slider.sliderReleased.connect(self.on_slider_released)
        progress_slider.valueChanged.connect(self.on_slider_value_changed)
        self.progress_slider = progress_slider
        player_layout.addWidget(progress_slider)
        
        # 时间显示
        time_label = QLabel("0:00 / 0:00")
        # 基础样式由全局样式表提供，只设置特殊字体大小
        time_label.setStyleSheet("font-size: 14px;")
        self.time_label = time_label
        player_layout.addWidget(time_label)
        
        layout.addLayout(player_layout)
        return section
    
    def find_audio_file(self):
        """查找模型目录下的音频文件"""
        model_name = self.model_data.get("name", "")
        if not model_name:
            return
        
        # 支持的音频格式
        audio_extensions = (".wav", ".mp3", ".flac", ".m4a", ".ogg", ".aac")
        
        # 从服务端的models目录查找（使用file_path）
        file_path = self.model_data.get("pth_path", "")
        if file_path:
            # file_path是相对路径，需要拼接models目录
            models_base_path = os.path.join(os.getcwd(), "models")
            full_file_path = os.path.join(models_base_path, file_path)
            file_dir = os.path.dirname(full_file_path)
            
            if os.path.exists(file_dir):
                                # 查找音频文件
                audio_files = [f for f in os.listdir(file_dir) 
                    if f.lower().endswith(audio_extensions)]
                if audio_files:
                    self.audio_file_path = os.path.join(file_dir, audio_files[0])
                    return
        
        # 如果file_path不可用，尝试从 models 目录查找（通过模型名称匹配）
        models_dir = os.path.join(os.getcwd(), "models")
        if os.path.exists(models_dir):
            for item in os.listdir(models_dir):
                model_dir_path = os.path.join(models_dir, item)
                if os.path.isdir(model_dir_path):
                    # 检查目录名或json中的name是否匹配
                    json_files = [f for f in os.listdir(model_dir_path) if f.endswith(".json")]
                    if json_files:
                        try:
                            json_path = os.path.join(model_dir_path, json_files[0])
                            with open(json_path, 'r', encoding='utf-8') as f:
                                model_info = json.load(f)
                            if model_info.get("name", item) == model_name:
                                # 查找音频文件
                                audio_files = [f for f in os.listdir(model_dir_path) 
                                             if f.lower().endswith(audio_extensions)]
                                if audio_files:
                                    self.audio_file_path = os.path.join(model_dir_path, audio_files[0])
                                    return
                        except:
                            pass
                    # 如果目录名匹配
                    if item == model_name:
                        audio_files = [f for f in os.listdir(model_dir_path) 
                                     if f.lower().endswith(audio_extensions)]
                        if audio_files:
                            self.audio_file_path = os.path.join(model_dir_path, audio_files[0])
                            return
    
    def on_play_clicked(self):
        """播放按钮点击"""
        if not self.audio_file_path or not os.path.exists(self.audio_file_path):
            QMessageBox.warning(self, "提示", "未找到音频文件")
            return
        
        if not self.audio_player:
            # 初始化音频播放器
            self.audio_output = QAudioOutput()
            self.audio_player = QMediaPlayer()
            self.audio_player.setAudioOutput(self.audio_output)
            self.audio_player.mediaStatusChanged.connect(self.on_media_status_changed)
            self.audio_player.positionChanged.connect(self.on_position_changed)
            self.audio_player.durationChanged.connect(self.on_duration_changed)
            self.audio_player.playbackStateChanged.connect(self.on_playback_state_changed)
        
        if self.is_playing:
            # 暂停播放
            self.audio_player.pause()
            self.is_playing = False
            if self.play_btn:
                self.play_btn.setText("▶")
        else:
            # 开始播放
            if self.audio_player.source() != QUrl.fromLocalFile(self.audio_file_path):
                self.audio_player.setSource(QUrl.fromLocalFile(self.audio_file_path))
            self.audio_player.play()
            self.is_playing = True
            if self.play_btn:
                self.play_btn.setText("⏸")
    
    def on_media_status_changed(self, status):
        """媒体状态改变"""
        from PyQt6.QtMultimedia import QMediaPlayer
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            self.is_playing = False
            if self.play_btn:
                self.play_btn.setText("▶")
            if self.time_label:
                self.time_label.setText("0:00 / 0:00")
    
    def on_position_changed(self, position):
        """播放位置改变"""
        if self.audio_player and self.time_label:
            duration = self.audio_player.duration()
            if duration > 0:
                pos_min = position // 60000
                pos_sec = (position % 60000) // 1000
                dur_min = duration // 60000
                dur_sec = (duration % 60000) // 1000
                self.time_label.setText(f"{pos_min}:{pos_sec:02d} / {dur_min}:{dur_sec:02d}")
                
                # 更新进度条（如果不在拖拽状态）
                if not self.is_slider_dragging and self.progress_slider:
                    progress_value = int((position / duration) * 1000)
                    self.progress_slider.setValue(progress_value)
    
    def on_duration_changed(self, duration):
        """总时长改变"""
        if self.time_label and duration > 0:
            dur_min = duration // 60000
            dur_sec = (duration % 60000) // 1000
            self.time_label.setText(f"0:00 / {dur_min}:{dur_sec:02d}")
    
    def on_slider_pressed(self):
        """滑块按下"""
        self.is_slider_dragging = True
    
    def on_slider_released(self):
        """滑块释放"""
        self.is_slider_dragging = False
        if self.audio_player and self.progress_slider:
            duration = self.audio_player.duration()
            if duration > 0:
                # 根据滑块位置跳转到对应时间
                position = int((self.progress_slider.value() / 1000.0) * duration)
                self.audio_player.setPosition(position)
    
    def on_slider_value_changed(self, value):
        """滑块值改变（仅在拖拽时更新显示，不跳转）"""
        if self.is_slider_dragging and self.audio_player and self.time_label:
            duration = self.audio_player.duration()
            if duration > 0:
                position = int((value / 1000.0) * duration)
                pos_min = position // 60000
                pos_sec = (position % 60000) // 1000
                dur_min = duration // 60000
                dur_sec = (duration % 60000) // 1000
                self.time_label.setText(f"{pos_min}:{pos_sec:02d} / {dur_min}:{dur_sec:02d}")
    
    def on_playback_state_changed(self, state):
        """播放状态改变"""
        from PyQt6.QtMultimedia import QMediaPlayer
        if state == QMediaPlayer.PlaybackState.StoppedState:
            self.is_playing = False
            if self.play_btn:
                self.play_btn.setText("▶")
            if self.progress_slider:
                self.progress_slider.setValue(0)
    
    def create_trial_section(self):
        """创建试用区块"""
        section = QWidget()
        section.setStyleSheet("""
            QWidget {
                background-color: #252525;
                border-radius: 8px;
                padding: 20px;
            }
        """)
        layout = QVBoxLayout(section)
        layout.setSpacing(15)
        
        title_label = QLabel("试用")
        # 基础样式由全局样式表提供，只设置特殊样式
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; border: none; background-color: transparent; padding: 0px;")
        layout.addWidget(title_label)
        
        info_label = QLabel("在这里可以进行音色的试用!所有的音色均可试用60分钟,点击按钮后开始计时。")
        info_label.setWordWrap(True)
        # 基础样式由全局样式表提供，只设置特殊字体大小
        info_label.setStyleSheet("font-size: 14px; border: none; background-color: transparent; padding: 0px;")
        layout.addWidget(info_label)
        
        # 试用按钮和时间显示
        trial_layout = QHBoxLayout()
        
        self.trial_btn = QPushButton("开始试用")
        self.trial_btn.setFixedSize(120, 40)
        self.trial_btn.setStyleSheet("""
            QPushButton {
                background-color: #8b5cf6;
                color: #ffffff;
                border: none;
                border-radius: 6px;
                font-size: 16px;
                font-weight: bold;
                padding: 0px;
            }
            QPushButton:hover {
                background-color: #7c3aed;
            }
        """)
        self.trial_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.trial_btn.clicked.connect(self.on_trial_clicked)
        trial_layout.addWidget(self.trial_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        
        self.trial_time_label = QLabel("剩余时间: 60:00")
        self.trial_time_label.setStyleSheet("color: #8b5cf6; font-size: 16px; font-weight: bold; border: none; background-color: transparent; padding: 0px;")
        self.trial_time_label.setVisible(False)
        trial_layout.addWidget(self.trial_time_label, alignment=Qt.AlignmentFlag.AlignCenter)
        trial_layout.addStretch()
        
        layout.addLayout(trial_layout)
        return section
    
    def create_download_section(self):
        """创建下载区块"""
        section = QWidget()
        section.setStyleSheet("""
            QWidget {
                background-color: #252525;
                border-radius: 8px;
                padding: 20px;
            }
        """)
        layout = QVBoxLayout(section)
        layout.setSpacing(15)
        
        title_label = QLabel("下载")
        # 基础样式由全局样式表提供，只设置特殊样式
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; border: none; background-color: transparent; padding: 0px;")
        layout.addWidget(title_label)
        
        info_label = QLabel("在这里可以直接下载音色!下载完毕后点击使用。如果有任何问题点击联系客服界面,联系客服。")
        info_label.setWordWrap(True)
        # 基础样式由全局样式表提供，只设置特殊字体大小
        info_label.setStyleSheet("font-size: 14px; border: none; background-color: transparent; padding: 0px;")
        layout.addWidget(info_label)
        
        # 下载按钮和进度条
        download_layout = QVBoxLayout()
        download_layout.setContentsMargins(0, 0, 24, 0)
        download_layout.setSpacing(10)
        
        btn_layout = QHBoxLayout()
        
        self.download_btn = QPushButton("开始下载")
        self.download_btn.setFixedSize(96, 36)
        self.download_btn.setStyleSheet("""
            QPushButton {
                background-color: #8b5cf6;
                color: #ffffff;
                border: none;
                border-radius: 6px;
                font-size: 14px;
                font-weight: bold;
                padding: 0px;
            }
            QPushButton:hover {
                background-color: #7c3aed;
            }
            QPushButton:disabled {
                background-color: #555555;
                color: #888888;
            }
        """)
        self.download_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.download_btn.clicked.connect(self.on_download_clicked)
        
        # 进度条
        self.download_progress = QProgressBar()
        self.download_progress.setVisible(False)
        self.download_progress.setStyleSheet("""
            QProgressBar {
                border: 1px solid #555555;
                border-radius: 4px;
                text-align: center;
                background-color: #1a1a1a;
                color: #ffffff;
            }
            QProgressBar::chunk {
                background-color: #8b5cf6;
                border-radius: 3px;
            }
        """)
        self.download_status_label = QLabel("")
        self.download_status_label.setVisible(False)
        self.download_status_label.setStyleSheet("color: #888888; font-size: 12px; border: none; background-color: transparent; padding: 0px;")
        
        btn_layout.addStretch()
        btn_layout.addWidget(self.download_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        btn_layout.addStretch()
        
        download_layout.addLayout(btn_layout)
        download_layout.addWidget(self.download_progress)
        download_layout.addWidget(self.download_status_label)
        
        layout.addLayout(download_layout)
        return section
    
    def on_trial_clicked(self):
        """试用按钮点击"""
        if not self.trial_active:
            self.trial_active = True
            self.trial_seconds = 3600  # 60分钟
            self.trial_timer.start(1000)  # 每秒更新
            self.trial_btn.setText("试用中...")
            self.trial_btn.setEnabled(False)
            self.trial_time_label.setVisible(True)
            self.update_trial_time()
        else:
            QMessageBox.information(self, "提示", "试用已在进行中")
    
    def update_trial_time(self):
        """更新试用时间"""
        if self.trial_seconds > 0:
            minutes = self.trial_seconds // 60
            seconds = self.trial_seconds % 60
            self.trial_time_label.setText(f"剩余时间: {minutes:02d}:{seconds:02d}")
            self.trial_seconds -= 1
        else:
            self.trial_timer.stop()
            self.trial_active = False
            self.trial_btn.setText("开始试用")
            self.trial_btn.setEnabled(True)
            self.trial_time_label.setVisible(False)
            QMessageBox.information(self, "提示", "试用时间已到")
    
    def create_use_section(self):
        """创建使用区块（已购买/已下载）"""
        section = QWidget()
        section.setStyleSheet("""
            QWidget {
                background-color: #252525;
                border-radius: 8px;
                padding: 20px;
            }
        """)
        layout = QVBoxLayout(section)
        layout.setSpacing(15)
        
        title_label = QLabel("使用")
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; border: none; background-color: transparent; padding: 0px;")
        layout.addWidget(title_label)
        
        # 状态提示
        status_label = QLabel("✓ 已下载，可直接使用")
        status_label.setStyleSheet("color: #4caf50; font-size: 14px; border: none; background-color: transparent; padding: 0px;")
        layout.addWidget(status_label)
        
        # 使用按钮
        use_layout = QHBoxLayout()
        use_btn = QPushButton("前往推理页面使用")
        use_btn.setFixedSize(200, 40)
        use_btn.setStyleSheet("""
            QPushButton {
                background-color: #8b5cf6;
                color: #ffffff;
                border: none;
                border-radius: 6px;
                padding: 10px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #7c3aed;
            }
        """)
        use_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        use_btn.clicked.connect(self.on_use_clicked)
        use_layout.addWidget(use_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        use_layout.addStretch()
        
        layout.addLayout(use_layout)
        
        # 显示模型文件路径信息
        pth_path = self.model_data.get("pth_path", "")
        index_path = self.model_data.get("index_path", "")
        if pth_path:
            path_info = QLabel(f"模型文件: {pth_path}")
            path_info.setStyleSheet("color: #888888; font-size: 12px; border: none; background-color: transparent; padding: 5px 0px;")
            path_info.setWordWrap(True)
            layout.addWidget(path_info)
        
        layout.addStretch()
        return section
    
    def on_use_clicked(self):
        """使用按钮点击"""
        QMessageBox.information(self, "提示", "请前往推理页面使用该模型")
    
    def on_download_clicked(self):
        """下载按钮点击"""
        model_uuid = self.model_data.get("uid")
        if not model_uuid:
            QMessageBox.warning(self, "错误", "模型UUID不存在")
            return
        
        # 如果已有下载线程在运行，先停止并清理
        self._cleanup_download_thread()
        
        # 禁用下载按钮
        self.download_btn.setEnabled(False)
        self.download_btn.setText("下载中...")
        
        # 显示进度条
        self.download_progress.setVisible(True)
        self.download_progress.setValue(0)
        self.download_status_label.setVisible(True)
        self.download_status_label.setText("准备下载...")
        
        # 连接进度更新信号
        self.progress_updated.connect(self._update_download_progress)
        
        # 创建异步下载任务
        async def download_and_extract():
            try:
                # 客户端models目录
                client_models_dir = os.path.join(os.getcwd(), "models")
                os.makedirs(client_models_dir, exist_ok=True)
                
                # 下载进度回调（使用信号安全更新UI）
                def progress_callback(downloaded, total):
                    if total > 0:
                        percent = int((downloaded / total) * 100)
                        status_text = f"下载中: {downloaded // 1024 // 1024}MB / {total // 1024 // 1024}MB"
                        # 使用信号在主线程中更新UI
                        self.progress_updated.emit(percent, total, status_text)
                
                # 下载压缩包（使用服务端原始文件名）
                self.progress_updated.emit(0, 0, "正在下载压缩包...")
                result = await models_api.download_model_package(
                    model_uuid,
                    client_models_dir,  # 只传目录，不传文件名
                    progress_callback=progress_callback
                )
                
                if not result.get("success"):
                    return {
                        "success": False,
                        "message": result.get("message", "下载失败")
                    }
                
                # 获取服务端返回的文件名和完整路径
                package_path = result.get("file_path")
                
                # 解压压缩包
                self.progress_updated.emit(50, 100, "正在解压...")
                
                # 解压到models目录
                try:
                    import py7zr
                    with py7zr.SevenZipFile(package_path, mode='r') as archive:
                        archive.extractall(path=client_models_dir)
                except ImportError:
                    # 如果没有py7zr，尝试使用7z命令行工具
                    import subprocess
                    result = subprocess.run(
                        ['7z', 'x', package_path, f'-o{client_models_dir}', '-y'],
                        capture_output=True,
                        text=True
                    )
                    if result.returncode != 0:
                        return {
                            "success": False,
                            "message": f"解压失败: {result.stderr}"
                        }
                except Exception as e:
                    return {
                        "success": False,
                        "message": f"解压失败: {str(e)}"
                    }
                
                # 解压完成后删除7z压缩包
                try:
                    if os.path.exists(package_path):
                        os.remove(package_path)
                        print(f"已删除压缩包: {package_path}")
                except Exception as e:
                    print(f"删除压缩包失败: {e}")
                
                self.progress_updated.emit(100, 100, "下载完成！")
                
                return {
                    "success": True,
                    "message": "模型下载并解压完成",
                    "path": client_models_dir
                }
                
            except Exception as e:
                return {
                    "success": False,
                    "message": f"下载失败: {str(e)}"
                }
        
        # 使用异步工具运行
        self.download_thread, self.download_worker = run_async(download_and_extract())
        self.download_worker.finished.connect(self.on_download_finished)
        self.download_worker.error.connect(self.on_download_error)
        self.download_thread.start()
    
    def on_download_finished(self, result):
        """下载完成"""
        # 清理线程资源
        self._cleanup_download_thread()
        
        # 恢复下载按钮
        self.download_btn.setEnabled(True)
        self.download_btn.setText("开始下载")
        
        if result.get("success"):
            QMessageBox.information(self, "成功", "模型下载并解压完成！")
            self.download_status_label.setText("下载完成！")
            
            # 重新加载本地模型uid列表
            if self.home_page:
                self.home_page._load_local_model_uids()
            
            # 检查当前模型是否已下载（通过uuid对比）
            model_uid = self.model_data.get("uid")
            if model_uid and self.home_page and model_uid in self.home_page.local_model_uids:
                # 更新页面状态：从下载状态切换到已下载状态
                self._update_to_downloaded_state()
            else:
                # 3秒后隐藏进度条（如果未检测到已下载）
                QTimer.singleShot(3000, lambda: (
                    self.download_progress.setVisible(False),
                    self.download_status_label.setVisible(False)
                ))
        else:
            QMessageBox.warning(self, "错误", result.get("message", "下载失败"))
            self.download_progress.setVisible(False)
            self.download_status_label.setVisible(False)
    
    def _update_to_downloaded_state(self):
        """更新页面状态为已下载状态"""
        if self.is_purchased:
            return  # 已经是已下载状态，不需要更新
        
        # 更新标志
        self.is_purchased = True
        
        # 隐藏进度条
        if self.download_progress:
            self.download_progress.setVisible(False)
        if self.download_status_label:
            self.download_status_label.setVisible(False)
        
        # 如果下载区块存在，替换为使用区块
        if self.download_section:
            # 获取下载区块的父widget和布局
            parent_widget = self.download_section.parent()
            if parent_widget:
                parent_layout = parent_widget.layout()
                if parent_layout:
                    # 找到下载区块在布局中的位置
                    index = parent_layout.indexOf(self.download_section)
                    if index >= 0:
                        # 移除下载区块
                        parent_layout.removeWidget(self.download_section)
                        self.download_section.setParent(None)
                        self.download_section.deleteLater()
                        self.download_section = None
                        
                        # 创建使用区块
                        self.use_section = self.create_use_section()
                        parent_layout.insertWidget(index, self.use_section)
    
    def _update_download_progress(self, percent, total, status_text):
        """更新下载进度（在主线程中调用）"""
        if percent >= 0:
            self.download_progress.setValue(percent)
        if status_text:
            self.download_status_label.setText(status_text)
    
    def on_download_error(self, error_msg):
        """下载出错"""
        # 清理线程资源
        self._cleanup_download_thread()
        
        self.download_btn.setEnabled(True)
        self.download_btn.setText("开始下载")
        self.download_progress.setVisible(False)
        self.download_status_label.setVisible(False)
        QMessageBox.warning(self, "错误", f"下载失败: {error_msg}")


class HomePage(BasePage):
    """主页"""
    
    def __init__(self):
        super().__init__("主页")
        self.models_data = []  # 存储所有模型数据
        self.filtered_models = []  # 过滤后的模型
        self.current_category = "全部"  # 当前选中的分类
        self.current_model = None  # 当前查看的模型
        self.local_model_uids = set()  # 本地模型的uid集合（用于快速查找）
        self.setup_content()
        # 不在初始化时加载模型，等待登录成功后再加载
        # self.load_models()  # 加载模型数据
    
    def setup_content(self):
        """设置主页内容"""
        # 获取或使用现有的布局
        main_layout = self.layout()
        if not main_layout:
            main_layout = QVBoxLayout(self)
        
        # 清除基类创建的默认内容
        while main_layout.count():
            child = main_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        # 使用堆叠窗口在列表和详情之间切换
        self.stacked_widget = QStackedWidget()
        main_layout.addWidget(self.stacked_widget)
        
        # 列表页面
        self.list_page = QWidget()
        list_layout = QVBoxLayout(self.list_page)
        list_layout.setContentsMargins(0, 0, 0, 0)
        list_layout.setSpacing(24)
        
        # 顶部工具栏
        toolbar = self.create_toolbar()
        list_layout.addWidget(toolbar)
        
        # 模型网格区域
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        # 基础样式由全局样式表提供，只设置特殊样式
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
            }
            QScrollBar:vertical {
                background-color: #2d2d2d;
                width: 8px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background-color: #8b5cf6;
                border-radius: 6px;
                min-height: 30px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #7c3aed;
            }
        """)
        
        # 网格容器
        grid_widget = QWidget()
        grid_container = QHBoxLayout()
        grid_container.setContentsMargins(12, 0, 0, 0)  # 左边距 12px，避免被遮挡
        grid_container.setSpacing(0)
        
        self.grid_layout = QGridLayout()
        self.grid_layout.setSpacing(20)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        
        grid_container.addLayout(self.grid_layout)
        grid_container.addStretch()  # 添加右侧拉伸，使卡片靠左对齐
        
        grid_widget.setLayout(grid_container)
        self.scroll_area.setWidget(grid_widget)
        list_layout.addWidget(self.scroll_area)
        
        self.stacked_widget.addWidget(self.list_page)
        
        # 详情页面（初始为空，点击详情时创建）
        self.detail_page = None
        
        # 加载状态标签
        self.loading_label = QLabel("正在加载模型数据...")
        self.loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.loading_label.setStyleSheet("""
            QLabel {
                color: #8b5cf6;
                font-size: 16px;
                padding: 20px;
            }
        """)
        list_layout.addWidget(self.loading_label)
        self.loading_label.hide()
        
        # 异步任务线程
        self.load_thread = None
        self.load_worker = None
    
    def create_toolbar(self):
        """创建顶部工具栏"""
        toolbar = QWidget()
        toolbar.setStyleSheet("background-color: transparent;")
        
        layout = QVBoxLayout(toolbar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # 分类标签栏
        categories_layout = QHBoxLayout()
        categories_layout.setSpacing(10)
        
        self.category_buttons = {}
        # 默认分类，加载数据后会更新
        categories = ["全部", "天籁Lite", "天籁Ultra"]
        
        for category in categories:
            btn = QPushButton(category)
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda checked, cat=category: self.on_category_changed(cat))
            
            if category == "全部":
                btn.setChecked(True)
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: #e74c3c;
                        color: #ffffff;
                        border: none;
                        border-radius: 6px;
                        padding: 8px 20px;
                        font-size: 14px;
                        font-weight: bold;
                    }
                """)
            else:
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: #2d2d2d;
                        color: #ffffff;
                        border: none;
                        border-radius: 6px;
                        padding: 8px 20px;
                        font-size: 14px;
                    }
                    QPushButton:hover {
                        background-color: #3d3d3d;
                    }
                    QPushButton:checked {
                        background-color: #8b5cf6;
                    }
                """)
            
            self.category_buttons[category] = btn
            categories_layout.addWidget(btn)

        categories_layout.addStretch()
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("请输入你想要的声音")
        # 基础样式由全局样式表提供，只设置特殊样式
        self.search_input.setStyleSheet("""
            QLineEdit {
                background-color: #1e1e1e;
                border: 2px solid #3d3d3d;
                border-radius: 8px;
                padding: 2px 15px;
                font-size: 14px;
            }
            QLineEdit:focus {
                border: 2px solid #8b5cf6;
            }
        """)
        self.search_input.textChanged.connect(self.on_search_changed)
        categories_layout.addWidget(self.search_input)

        layout.addLayout(categories_layout)
        
        # 保存工具栏和分类布局的引用，以便后续更新
        self.toolbar_widget = toolbar
        self.categories_layout = categories_layout
        
        return toolbar
    
    def load_models(self):
        """从服务端API加载模型数据"""
        # 先加载本地模型uid列表
        self._load_local_model_uids()
        
        # 检查登录状态
        if not auth_api.is_logged_in():
            print("未登录，无法加载模型数据")
            self.loading_label.hide()
            if hasattr(self, 'scroll_area'):
                self.scroll_area.show()
            # 显示空列表
            self.models_data = []
            self.filtered_models = []
            self.update_model_grid()
            return
        
        # 显示加载提示，隐藏网格区域
        self.loading_label.show()
        if hasattr(self, 'scroll_area'):
            self.scroll_area.hide()
        
        # 创建异步任务
        async def fetch_models():
            """异步获取模型列表（分页获取所有模型）"""
            all_models = []
            skip = 0
            limit = 100  # 每次获取100条
            total = None
            
            while True:
                # 获取当前页的模型
                result = await models_api.get_models(skip=skip, limit=limit)
                
                if not result.get("success"):
                    # 如果请求失败，返回已获取的数据
                    break
                
                # 获取总数（只在第一次获取）
                if total is None:
                    total = result.get("total", 0)
                
                # 获取当前页的模型列表
                models = result.get("models", [])
                if not models:
                    break
                
                all_models.extend(models)
                
                # 如果已经获取了所有模型，退出循环
                if len(all_models) >= total:
                    break
                
                # 准备获取下一页
                skip += limit
            
            # 返回合并后的结果
            return {
                "success": True,
                "models": all_models,
                "total": len(all_models)
            }
        
        # 使用异步工具运行
        self.load_thread, self.load_worker = run_async(fetch_models())
            
        # 连接信号
        self.load_worker.finished.connect(self.on_models_loaded)
        self.load_worker.error.connect(self.on_models_load_error)
        
        # 启动线程
        self.load_thread.start()
    
    def on_models_loaded(self, result):
        """模型数据加载完成"""
        # 隐藏加载提示，显示网格区域
        self.loading_label.hide()
        if hasattr(self, 'scroll_area'):
            self.scroll_area.show()
        
        # 检查结果
        if result.get("success"):
            models = result.get("models", [])
            # 转换数据格式
            self.models_data = [self._convert_api_model_to_local(model) for model in models]
            self.filtered_models = self.models_data.copy()
            
            # 更新分类按钮（从实际数据中提取分类）
            self._update_category_buttons()
            
            # 更新模型网格
            self.update_model_grid()
        else:
            error_msg = result.get("message", "加载模型数据失败")
            QMessageBox.warning(self, "错误", f"加载模型数据失败：{error_msg}")
            # 如果API加载失败，显示空列表
            self.models_data = []
            self.filtered_models = []
            self.update_model_grid()
    
        # 清理线程
        if self.load_thread:
            self.load_thread.quit()
            self.load_thread.wait()
            self.load_thread = None
            self.load_worker = None
    
    def _load_local_model_uids(self):
        """加载本地模型的uid列表"""
        self.local_model_uids.clear()
        models_dir = os.path.join(os.getcwd(), "models")
        
        if not os.path.exists(models_dir):
            return
        
        # 扫描models目录下的所有子目录
        for item in os.listdir(models_dir):
            model_dir_path = os.path.join(models_dir, item)
            
            # 只处理目录
            if not os.path.isdir(model_dir_path):
                continue
            
            # 查找json信息文件（通常是info.json）
            json_files = [f for f in os.listdir(model_dir_path) if f.endswith(".json")]
            
            if json_files:
                json_path = os.path.join(model_dir_path, json_files[0])
                try:
                    with open(json_path, 'r', encoding='utf-8') as f:
                        model_info = json.load(f)
                    
                    # 读取uid（支持uuid或uid字段）
                    model_uid = model_info.get("uuid") or model_info.get("uid")
                    if model_uid:
                        self.local_model_uids.add(model_uid)
                except Exception as e:
                    print(f"读取本地模型信息文件失败 {json_path}: {e}")
    
    def on_models_load_error(self, error_msg):
        """模型数据加载出错"""
        # 隐藏加载提示，显示网格区域
        self.loading_label.hide()
        if hasattr(self, 'scroll_area'):
            self.scroll_area.show()
        
        QMessageBox.warning(self, "错误", f"加载模型数据时发生错误：{error_msg}")
        # 如果API加载失败，显示空列表
        self.models_data = []
        self.filtered_models = []
        self.update_model_grid()
        
        # 清理线程
        if self.load_thread:
            self.load_thread.quit()
            self.load_thread.wait()
            self.load_thread = None
            self.load_worker = None
    
    def _convert_api_model_to_local(self, api_model):
        """
        将API返回的模型数据转换为主页需要的格式
        
        Args:
            api_model: API返回的模型字典（ModelResponse格式）
        
        Returns:
            转换后的模型字典
        """
        # API返回的模型数据格式（ModelResponse）：
        # {
        #   "id": int,
        #   "name": str,
        #   "description": str,
        #   "version": str,
        #   "category": str,
        #   "tags": str,
        #   "file_name": str,
        #   "file_size": int,
        #   "download_count": int,
        #   "is_public": bool,
        #   "is_active": bool,
        #   "user_id": int,
        #   "created_at": datetime,
        #   "updated_at": datetime
        # }
        # 注意：API返回的ModelResponse中没有file_path字段，只有file_name
        
        # 主页需要的格式：
        # {
        #   "id": str,
        #   "name": str,
        #   "image": str,
        #   "description": str,
        #   "category": str,
        #   "version": str,
        #   "sample_rate": str,
        #   "pth_path": str,
        #   "index_path": str,
        #   ...
        # }
        
        # 尝试从file_path或file_name构建图片路径
        # 假设图片文件与模型文件在同一目录，文件名相同但扩展名不同
        image_path = ""
        if isinstance(api_model, dict):
            file_path = api_model.get("file_path", "")
            file_name = api_model.get("file_name", "")
            
            # 优先使用file_path查找图片
            if file_path:
                file_dir = os.path.dirname(file_path)
                file_name_without_ext = os.path.splitext(os.path.basename(file_path))[0]
                image_extensions = [".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp"]
                for ext in image_extensions:
                    potential_image = os.path.join(file_dir, file_name_without_ext + ext)
                    if os.path.exists(potential_image):
                        image_path = potential_image
                        break
                
                # 如果没找到，尝试查找目录下的任何图片文件
                if not image_path and os.path.exists(file_dir):
                    for f in os.listdir(file_dir):
                        if f.lower().endswith((".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp")):
                            image_path = os.path.join(file_dir, f)
                            break
            
            # 如果file_path不可用，尝试在服务端的models目录中查找
            if not image_path and file_path:
                # file_path是相对路径，需要拼接models目录
                models_base_path = os.path.join(os.getcwd(), "models")
                full_file_path = os.path.join(models_base_path, file_path)
                file_dir = os.path.dirname(full_file_path)
                
                if os.path.exists(file_dir):
                    file_name_without_ext = os.path.splitext(os.path.basename(file_path))[0]
                    image_extensions = [".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp"]
                    for ext in image_extensions:
                        potential_image = os.path.join(file_dir, file_name_without_ext + ext)
                        if os.path.exists(potential_image):
                            image_path = potential_image
                            break
                    
                    # 如果没找到，尝试查找目录下的任何图片文件
                    if not image_path:
                        for f in os.listdir(file_dir):
                            if f.lower().endswith((".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp")):
                                image_path = os.path.join(file_dir, f)
                                break
        
        # 构建转换后的数据
        converted_model = {
            "id": str(api_model.get("id", "")),
            "uid": api_model.get("uid", ""),  # 模型的UUID
            "name": api_model.get("name", "未知模型"),
            "image": image_path,
            "description": api_model.get("description", ""),
            "category": api_model.get("category", "全部") or "全部",  # 确保category不为None
            "version": api_model.get("version", "V1"),
            "sample_rate": "48K",  # API中没有sample_rate字段，使用默认值
            "pth_path": api_model.get("file_path", ""),  # 使用file_path作为pth_path
            "index_path": "",  # API中没有index_path信息，需要从file_path推断或通过其他方式获取
            "file_name": api_model.get("file_name", ""),
            "file_size": api_model.get("file_size", 0),
            "download_count": api_model.get("download_count", 0),
            "is_public": api_model.get("is_public", True),
            "user_id": api_model.get("user_id"),
            "created_at": api_model.get("created_at"),
            "updated_at": api_model.get("updated_at"),
            "model_id": api_model.get("id"),  # 保存原始ID用于下载等操作
            }
            
        # 保留tags等其他字段
        if "tags" in api_model:
            converted_model["tags"] = api_model["tags"]
        
        return converted_model
    
    def _update_category_buttons(self):
        """根据实际模型数据更新分类按钮"""
        # 从模型数据中提取所有分类
        categories = set()
        for model in self.models_data:
            category = model.get("category", "")
            if category:
                # 支持多个分类用分号分隔
                for cat in category.split(";"):
                    cat = cat.strip()
                    if cat:
                        categories.add(cat)
        
        # 如果没有任何分类，使用默认分类
        if not categories:
            categories = {"天籁Lite", "天籁Ultra"}
        
        # 排序分类列表
        sorted_categories = sorted(categories)
        
        # 更新分类按钮
        # 先清除旧的按钮（除了搜索框）
        if hasattr(self, 'categories_layout'):
            # 保存搜索框
            search_widget = None
            stretch_index = None
            for i in range(self.categories_layout.count()):
                item = self.categories_layout.itemAt(i)
                if item:
                    widget = item.widget()
                    if widget == self.search_input:
                        search_widget = widget
                        stretch_index = i
                    elif widget and widget in self.category_buttons.values():
                        widget.deleteLater()
            
            # 清除所有项
            while self.categories_layout.count():
                item = self.categories_layout.takeAt(0)
                if item and item.widget() and item.widget() != self.search_input:
                    item.widget().deleteLater()
            
            self.category_buttons.clear()
            
            # 添加"全部"按钮
            categories_list = ["全部"] + sorted_categories
            
            # 重新创建分类按钮
            for category in categories_list:
                btn = QPushButton(category)
                btn.setCheckable(True)
                btn.setCursor(Qt.CursorShape.PointingHandCursor)
                btn.clicked.connect(lambda checked, cat=category: self.on_category_changed(cat))
                
                if category == "全部":
                    btn.setChecked(True)
                    btn.setStyleSheet("""
                        QPushButton {
                            background-color: #e74c3c;
                            color: #ffffff;
                            border: none;
                            border-radius: 6px;
                            padding: 8px 20px;
                            font-size: 14px;
                            font-weight: bold;
                        }
                    """)
                else:
                    btn.setStyleSheet("""
                        QPushButton {
                            background-color: #2d2d2d;
                            color: #ffffff;
                            border: none;
                            border-radius: 6px;
                            padding: 8px 20px;
                            font-size: 14px;
                        }
                        QPushButton:hover {
                            background-color: #3d3d3d;
                        }
                        QPushButton:checked {
                            background-color: #8b5cf6;
                        }
                    """)
                
                self.category_buttons[category] = btn
                self.categories_layout.addWidget(btn)
            
            # 添加拉伸和搜索框
            self.categories_layout.addStretch()
            if search_widget:
                self.categories_layout.addWidget(search_widget)
    
    
    def on_category_changed(self, category):
        """分类改变"""
        self.current_category = category
        
        # 更新按钮样式
        for cat, btn in self.category_buttons.items():
            if cat == category:
                if category == "全部":
                    btn.setStyleSheet("""
                        QPushButton {
                            background-color: #e74c3c;
                            color: #ffffff;
                            border: none;
                            border-radius: 6px;
                            padding: 8px 20px;
                            font-size: 14px;
                            font-weight: bold;
                        }
                    """)
                else:
                    btn.setStyleSheet("""
                        QPushButton {
                            background-color: #8b5cf6;
                            color: #ffffff;
                            border: none;
                            border-radius: 6px;
                            padding: 8px 20px;
                            font-size: 14px;
                            font-weight: bold;
                        }
                    """)
            else:
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: #2d2d2d;
                        color: #ffffff;
                        border: none;
                        border-radius: 6px;
                        padding: 8px 20px;
                        font-size: 14px;
                    }
                    QPushButton:hover {
                        background-color: #3d3d3d;
                    }
                """)
        
        # 过滤模型
        self.filter_models()
    
    def on_search_changed(self, text):
        """搜索文本改变"""
        self.filter_models()
    
    def filter_models(self):
        """过滤模型"""
        search_text = self.search_input.text().strip().lower()
        
        self.filtered_models = []
        for model in self.models_data:
            # 分类过滤（支持多个分类，用分号分隔）
            if self.current_category != "全部":
                model_categories = [cat.strip() for cat in model.get("category", "").split(";")]
                if self.current_category not in model_categories:
                    continue
            
            # 搜索过滤
            if search_text and search_text not in model["name"].lower():
                continue
            
            self.filtered_models.append(model)
        
        self.update_model_grid()
    
    def update_model_grid(self):
        """更新模型网格"""
        # 清除现有卡片
        while self.grid_layout.count():
            child = self.grid_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        # 添加模型卡片
        columns = 5  # 每行5个
        for i, model_data in enumerate(self.filtered_models):
            card = ModelCard(model_data)
            card.detail_clicked.connect(self.on_model_detail_clicked)
            
            row = i // columns
            col = i % columns
            self.grid_layout.addWidget(card, row, col)
        
        # 设置列的对齐方式，使卡片靠左对齐
        for col in range(columns):
            self.grid_layout.setColumnStretch(col, 0)  # 不拉伸列，让卡片靠左
        
        # 添加弹性空间（只在最后一行）
        self.grid_layout.setRowStretch(self.grid_layout.rowCount(), 1)
    
    def on_model_detail_clicked(self, model_id):
        """模型详情按钮点击"""
        # 查找模型数据
        model_data = None
        for model in self.models_data:
            if model["id"] == model_id:
                model_data = model
                break
        
        if not model_data:
            QMessageBox.warning(self, "错误", "未找到模型信息")
            return
        
        # 检查本地是否有相同uid的模型
        model_uid = model_data.get("uid")
        is_downloaded = False
        if model_uid and model_uid in self.local_model_uids:
            is_downloaded = True
        
        # 创建或更新详情页面
        if self.detail_page:
            self.detail_page.deleteLater()
        
        # 添加更多详情数据
        detail_data = model_data.copy()
        detail_data.update({
            "price": 0,
            "version": "V1",
            "sample_rate": "48K",
            "category_name": "免费音色",
            "description": detail_data.get("description", "茶韵悠悠可音袅袅少御音介于少女与御姐之间既有少女清脆又具御姐沉稳圆润柔和年龄感适中清嗓咳嗽呢喃细语悄悄话 笑声 自带情绪感")
        })
        
        # 如果本地已下载，显示已下载样式
        self.detail_page = ModelDetailPage(detail_data, is_purchased=is_downloaded, home_page=self)
        self.detail_page.back_clicked.connect(self.show_list_page)
        self.detail_page.setParent(self.stacked_widget)
        
        # 如果详情页面不在堆叠中，添加它
        if self.stacked_widget.indexOf(self.detail_page) == -1:
            self.stacked_widget.addWidget(self.detail_page)
        
        # 切换到详情页面
        self.stacked_widget.setCurrentWidget(self.detail_page)
        self.current_model = model_data
    
    def show_list_page(self):
        """显示列表页面"""
        self.stacked_widget.setCurrentWidget(self.list_page)

