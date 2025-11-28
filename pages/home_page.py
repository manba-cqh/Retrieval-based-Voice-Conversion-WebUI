"""主页"""
import json
import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QScrollArea, QGridLayout, QFrame, QStackedWidget,
    QProgressBar, QMessageBox, QSizePolicy, QSlider
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread, QUrl
from PyQt6.QtGui import QFont, QPixmap, QIcon
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput

from .base_page import BasePage


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
    
    def __init__(self, model_data, parent=None):
        super().__init__(parent)
        self.model_data = model_data
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
        
        # 查找音频文件
        self.find_audio_file()
        
        self.setup_ui()
    
    def on_back_clicked(self):
        """返回按钮点击"""
        self.back_clicked.emit()
    
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
        
        # 立即购买按钮
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
        
        # 试用
        trial_section = self.create_trial_section()
        layout.addWidget(trial_section, 5)
        
        # 下载
        download_section = self.create_download_section()
        layout.addWidget(download_section, 5)
        
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
        
        # 先尝试从 net_models 目录查找（主页使用）
        net_models_dir = os.path.join(os.getcwd(), "net_models")
        if os.path.exists(net_models_dir):
            for item in os.listdir(net_models_dir):
                model_dir_path = os.path.join(net_models_dir, item)
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
        
        # 再尝试从 models 目录查找（管理页使用）
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
        
        # 下载按钮
        download_layout = QHBoxLayout()
        
        download_btn = QPushButton("点击按钮即可开始下载")
        download_btn.setFixedSize(164, 36)
        download_btn.setStyleSheet("""
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
        """)
        download_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        download_btn.clicked.connect(self.on_download_clicked)
        download_layout.addWidget(download_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        
        alt_download_btn = QPushButton("备用下载通道")
        alt_download_btn.setFixedSize(164, 36)
        alt_download_btn.setStyleSheet("""
            QPushButton {
                background-color: #3d3d3d;
                color: #ffffff;
                border: none;
                border-radius: 6px;
                font-size: 14px;
                padding: 0px;
            }
            QPushButton:hover {
                background-color: #4d4d4d;
            }
        """)
        alt_download_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        download_layout.addWidget(alt_download_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        download_layout.addStretch()
        
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
    
    def on_download_clicked(self):
        """下载按钮点击"""
        QMessageBox.information(self, "提示", "开始下载音色模型...")


class HomePage(BasePage):
    """主页"""
    
    def __init__(self):
        super().__init__("主页")
        self.models_data = []  # 存储所有模型数据
        self.filtered_models = []  # 过滤后的模型
        self.current_category = "全部"  # 当前选中的分类
        self.current_model = None  # 当前查看的模型
        self.setup_content()
        self.load_models()  # 加载模型数据
    
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
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        # 基础样式由全局样式表提供，只设置特殊样式
        scroll_area.setStyleSheet("""
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
        scroll_area.setWidget(grid_widget)
        list_layout.addWidget(scroll_area)
        
        self.stacked_widget.addWidget(self.list_page)
        
        # 详情页面（初始为空，点击详情时创建）
        self.detail_page = None
    
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
        categories = ["全部", "入门", "真人拟声"]
        
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
        
        return toolbar
    
    def load_models(self):
        """从net_models目录加载模型数据"""
        self.models_data = self.fetch_models_from_net_models_dir()
        self.filtered_models = self.models_data.copy()
        self.update_model_grid()
    
    def fetch_models_from_net_models_dir(self):
        """从net_models目录获取模型数据"""
        net_models_dir = os.path.join(os.getcwd(), "net_models")
        models_data = []
        
        # 如果net_models目录不存在，返回空列表
        if not os.path.exists(net_models_dir):
            return models_data
        
        # 扫描net_models目录下的所有子目录
        model_id = 1
        for item in os.listdir(net_models_dir):
            model_dir_path = os.path.join(net_models_dir, item)
            
            # 只处理目录
            if not os.path.isdir(model_dir_path):
                continue
            
            # 查找.pth文件（文件名可以是任意的，只要扩展名是.pth即可）
            pth_files = [f for f in os.listdir(model_dir_path) if f.endswith(".pth")]
            if not pth_files:
                continue  # 如果没有.pth文件，跳过这个目录
            
            # 查找index文件（文件名可以是任意的，只要扩展名是.index即可）
            index_files = [f for f in os.listdir(model_dir_path) if f.endswith(".index")]
            
            # 查找json信息文件
            json_files = [f for f in os.listdir(model_dir_path) if f.endswith(".json")]
            
            # 查找图片文件（支持常见图片格式）
            image_extensions = (".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp")
            image_files = [f for f in os.listdir(model_dir_path) 
                          if f.lower().endswith(image_extensions)]
            
            # 使用第一个找到的.pth文件
            pth_path = os.path.join(model_dir_path, pth_files[0])
            
            # 使用第一个找到的index文件，如果没有则设为空字符串
            index_path = os.path.join(model_dir_path, index_files[0]) if index_files else ""
            
            # 读取json信息文件（如果存在）
            model_info = {}
            if json_files:
                json_path = os.path.join(model_dir_path, json_files[0])
                try:
                    with open(json_path, 'r', encoding='utf-8') as f:
                        model_info = json.load(f)
                except Exception as e:
                    print(f"读取模型信息文件失败 {json_path}: {e}")
            
            # 构建模型数据
            model_name = model_info.get("name", item)  # 如果json中没有name，使用目录名
            
            # 确定模型图片路径（优先级：json中的image > 目录下的图片文件）
            model_image = model_info.get("image", "")
            if model_image:
                # 如果json中指定了图片路径
                if not os.path.isabs(model_image):
                    # 如果是相对路径，转换为相对于模型目录的路径
                    model_image = os.path.join(model_dir_path, model_image)
            elif image_files:
                # 如果json中没有指定，但目录下有图片文件，使用第一个找到的图片
                model_image = os.path.join(model_dir_path, image_files[0])
            else:
                # 没有图片
                model_image = ""
            
            # 获取分类信息（从json中读取，默认为"入门"）
            category = model_info.get("category", "入门")
            
            # 构建模型数据（兼容主页的数据结构）
            model_data = {
                "id": str(model_id),
                "name": model_name,
                "image": model_image,
                "description": model_info.get("description", ""),
                "category": category,
                "version": model_info.get("version", "V1"),
                "sample_rate": model_info.get("sample_rate", "48K"),
                "pth_path": pth_path,
                "index_path": index_path,
            }
            
            # 添加json中的其他信息（如果有）
            for key in ["price", "category_name"]:
                if key in model_info:
                    model_data[key] = model_info[key]
            
            models_data.append(model_data)
            model_id += 1
        
        return models_data
    
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
        
        self.detail_page = ModelDetailPage(detail_data)
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

