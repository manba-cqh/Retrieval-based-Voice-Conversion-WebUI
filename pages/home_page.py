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
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread, QUrl, QMetaObject, Q_ARG, QSize
from PyQt6.QtGui import QFont, QPixmap, QIcon, QMovie
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput

from .base_page import BasePage
from api.models import models_api
from api.async_utils import run_async
from api.auth import auth_api


class ModelCard(QFrame):
    """模型卡片组件"""
    detail_clicked = pyqtSignal(str)  # 发送模型ID
    
    def __init__(self, model_data, parent=None, load_online=False):
        super().__init__(parent)
        self.model_id = model_data.get("id", "")
        self.model_name = model_data.get("name", "未知")
        self.model_image = model_data.get("image", "")
        self.model_category = model_data.get("category", "全部")
        self.model_data = model_data  # 保存完整的模型数据，用于获取UUID
        self.load_online = load_online  # 是否优先从服务端加载图片（主页使用）
        
        # 图片下载线程相关（仅用于在线加载）
        self.image_download_thread = None
        self.image_download_worker = None
        
        # 保存图片对象引用，用于传递给详情页
        self.original_pixmap = None  # 静态图片的原始 pixmap
        self.movie = None  # GIF 动图的 movie 对象
        
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
        
        # 保存 image_label 引用，用于后续更新
        self.image_label = image_label
        
        # 根据 load_online 标志决定加载方式
        if self.load_online:
            # 主页使用：优先从服务端下载图片
            self._load_online_image()
        else:
            # 管理页面使用：读取本地路径
            self._load_local_image()
        
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
    
    def _load_local_image(self):
        """加载本地图片（管理页面使用）"""
        if self.model_image and os.path.exists(self.model_image):
            try:
                # 检查是否为 GIF 动图
                file_ext = os.path.splitext(self.model_image)[1].lower()
                if file_ext == '.gif':
                    # 使用 QMovie 加载 GIF 动图
                    movie = QMovie(self.model_image)
                    movie.setScaledSize(self.image_label.size())
                    self.image_label.setMovie(movie)
                    movie.start()
                    # 保存 movie 引用，防止被垃圾回收
                    self.movie = movie
                elif file_ext == '.png' or file_ext == '.jpg' or file_ext == '.jpeg' or file_ext == '.bmp' or file_ext == '.webp':
                    # 使用 QPixmap 加载静态图片（PNG、JPG等）
                    pixmap = QPixmap(self.model_image)
                    if not pixmap.isNull():
                        # 保存原始 pixmap，用于传递给详情页
                        self.original_pixmap = pixmap
                        # 缩放图片以适应标签大小，保持宽高比
                        scaled_pixmap = pixmap.scaled(
                            180, 180, 
                            Qt.AspectRatioMode.KeepAspectRatio, 
                            Qt.TransformationMode.SmoothTransformation
                        )
                        self.image_label.setPixmap(scaled_pixmap)
                else:
                    # 图片加载失败，显示占位符
                    placeholder = self.model_name[0] if self.model_name else "?"
                    self.image_label.setText(f"<div style='font-size: 48px; color: #8b5cf6;'>{placeholder}</div>")
            except Exception as e:
                # 图片加载出错，显示占位符
                print(f"加载图片失败 {self.model_image}: {e}")
                placeholder = self.model_name[0] if self.model_name else "?"
                self.image_label.setText(f"<div style='font-size: 48px; color: #8b5cf6;'>{placeholder}</div>")
        else:
            # 根据名称生成占位符
            placeholder = self.model_name[0] if self.model_name else "?"
            self.image_label.setText(f"<div style='font-size: 48px; color: #8b5cf6;'>{placeholder}</div>")
    
    def _load_online_image(self):
        """从服务端下载并显示图片（主页使用，优先从服务端获取）"""
        # 先尝试加载本地图片（如果存在）
        if self.model_image and os.path.exists(self.model_image):
            self._load_local_image()
            return  # 本地图片存在，直接使用
        
        # 显示占位符
        placeholder = self.model_name[0] if self.model_name else "?"
        self.image_label.setText(f"<div style='font-size: 48px; color: #8b5cf6;'>{placeholder}</div>")
        
        # 获取模型UUID
        model_uid = self.model_data.get("uid")
        if not model_uid:
            # 如果没有UUID，无法下载，显示占位符
            return
        
        # 异步下载图片
        async def download_image():
            try:
                # 创建临时目录保存图片
                temp_dir = os.path.join(tempfile.gettempdir(), "rvc_model_images")
                os.makedirs(temp_dir, exist_ok=True)
                
                result = await models_api.download_model_image(model_uid, temp_dir)
                if result.get("success"):
                    downloaded_path = result.get("file_path")
                    if downloaded_path and os.path.exists(downloaded_path):
                        # 下载成功，更新图片路径并加载
                        self.model_image = downloaded_path
                        # 使用QTimer在主线程中更新UI
                        QTimer.singleShot(0, lambda: self._load_local_image())
                        return {"success": True}
                    else:
                        return {"success": False, "message": "图片文件下载失败"}
                else:
                    return result
            except Exception as e:
                return {"success": False, "message": f"下载失败: {str(e)}"}
        
        # 使用异步工具运行
        # 如果已有下载线程在运行，先清理
        if self.image_download_thread and self.image_download_thread.isRunning():
            try:
                if self.image_download_worker:
                    self.image_download_worker.finished.disconnect()
                    self.image_download_worker.error.disconnect()
                self.image_download_thread.quit()
                self.image_download_thread.wait(1000)  # 等待最多1秒
                if self.image_download_thread.isRunning():
                    self.image_download_thread.terminate()
                    self.image_download_thread.wait()
            except Exception as e:
                print(f"清理图片下载线程时出错: {e}")
            finally:
                if self.image_download_thread:
                    self.image_download_thread.deleteLater()
                if self.image_download_worker:
                    self.image_download_worker.deleteLater()
                self.image_download_thread = None
                self.image_download_worker = None
        
        # 创建新的下载线程
        self.image_download_thread, self.image_download_worker = run_async(download_image())
        self.image_download_worker.finished.connect(lambda result: None)  # 静默处理完成
        self.image_download_worker.error.connect(lambda error: None)  # 静默处理错误
        self.image_download_thread.start()
    
    def cleanup(self):
        """清理资源，包括停止下载线程"""
        if self.image_download_thread and self.image_download_thread.isRunning():
            try:
                if self.image_download_worker:
                    self.image_download_worker.finished.disconnect()
                    self.image_download_worker.error.disconnect()
                self.image_download_thread.quit()
                self.image_download_thread.wait(1000)  # 等待最多1秒
                if self.image_download_thread.isRunning():
                    self.image_download_thread.terminate()
                    self.image_download_thread.wait()
            except Exception as e:
                print(f"清理图片下载线程时出错: {e}")
            finally:
                if self.image_download_thread:
                    self.image_download_thread.deleteLater()
                if self.image_download_worker:
                    self.image_download_worker.deleteLater()
                self.image_download_thread = None
                self.image_download_worker = None


class ModelDetailPage(QWidget):
    """模型详情页面"""
    back_clicked = pyqtSignal()  # 返回信号
    progress_updated = pyqtSignal(int, int, str)  # 进度更新信号 (downloaded, total, status_text)
    
    def __init__(self, model_data, parent=None, is_purchased=False, home_page=None, main_window=None, model_image=None):
        super().__init__(parent)
        self.model_data = model_data
        self.is_purchased = is_purchased  # 是否已购买/已下载
        self.home_page = home_page  # 主页引用，用于更新本地模型uid列表
        self.main_window = main_window  # 主窗口引用，用于刷新管理页面
        self.model_image = model_image  # 模型图片（QPixmap 或 QMovie），由调用者传递
        self.trial_timer = QTimer()
        self.trial_timer.timeout.connect(self.update_trial_time)
        self.trial_seconds = 0
        self.trial_active = False
        
        # 试用线程相关
        self.trial_thread = None
        self.trial_worker = None
        self.check_status_thread = None
        self.check_status_worker = None
        self.sync_status_thread = None
        self.sync_status_worker = None
        self.trial_sync_timer = None  # 定期同步服务器状态的定时器
        
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
        self.right_panel = None  # 保存右侧面板的引用，用于动态添加下载区块
        
        # 音频下载相关
        self.need_download_audio = False
        self.audio_download_thread = None
        self.audio_download_worker = None
        
        # 收藏线程相关
        self.favorite_thread = None
        self.favorite_worker = None
        
        # 查找音频文件
        self.find_audio_file()
        
        self.setup_ui()
        
        # 页面加载后检查试用状态（延迟一点，确保UI元素已创建）
        # 只有在已登录时才检查试用状态
        if auth_api.is_logged_in():
            QTimer.singleShot(100, self._check_trial_status)
    
    def on_back_clicked(self):
        """返回按钮点击"""
        # 清理所有线程
        self._cleanup_download_thread()
        self._cleanup_audio_download_thread()
        self._cleanup_trial_thread()
        self._cleanup_check_status_thread()
        self._cleanup_sync_status_thread()
        # 停止定时器
        if hasattr(self, 'trial_sync_timer') and self.trial_sync_timer:
            self.trial_sync_timer.stop()
            self.trial_sync_timer = None
        if hasattr(self, 'trial_timer') and self.trial_timer:
            self.trial_timer.stop()
        self.back_clicked.emit()
    
    def _cleanup_download_thread(self):
        """清理下载线程资源"""
        if hasattr(self, 'download_thread') and self.download_thread:
            try:
                if hasattr(self, 'download_worker') and self.download_worker:
                    try:
                        self.download_worker.finished.disconnect()
                        self.download_worker.error.disconnect()
                    except:
                        pass
                
                if hasattr(self.download_thread, 'isRunning') and self.download_thread.isRunning():
                    self.download_thread.quit()
                    if not self.download_thread.wait(3000):  # 等待最多3秒
                        if hasattr(self.download_thread, 'isRunning') and self.download_thread.isRunning():
                            self.download_thread.terminate()
                            self.download_thread.wait()
            except RuntimeError:
                # 对象已被删除
                pass
            except Exception as e:
                print(f"清理下载线程时出错: {e}")
            finally:
                if hasattr(self, 'download_thread') and self.download_thread:
                    try:
                        self.download_thread.deleteLater()
                    except:
                        pass
                if hasattr(self, 'download_worker') and self.download_worker:
                    try:
                        self.download_worker.deleteLater()
                    except:
                        pass
                self.download_thread = None
                self.download_worker = None
    
    def _cleanup_audio_download_thread(self):
        """清理音频下载线程资源"""
        if hasattr(self, 'audio_download_thread') and self.audio_download_thread:
            try:
                if hasattr(self, 'audio_download_worker') and self.audio_download_worker:
                    try:
                        self.audio_download_worker.finished.disconnect()
                        self.audio_download_worker.error.disconnect()
                    except:
                        pass
                
                if hasattr(self.audio_download_thread, 'isRunning') and self.audio_download_thread.isRunning():
                    self.audio_download_thread.quit()
                    if not self.audio_download_thread.wait(3000):  # 等待最多3秒
                        if hasattr(self.audio_download_thread, 'isRunning') and self.audio_download_thread.isRunning():
                            self.audio_download_thread.terminate()
                            self.audio_download_thread.wait()
            except RuntimeError:
                # 对象已被删除
                pass
            except Exception as e:
                print(f"清理音频下载线程时出错: {e}")
            finally:
                if hasattr(self, 'audio_download_thread') and self.audio_download_thread:
                    try:
                        self.audio_download_thread.deleteLater()
                    except:
                        pass
                if hasattr(self, 'audio_download_worker') and self.audio_download_worker:
                    try:
                        self.audio_download_worker.deleteLater()
                    except:
                        pass
                self.audio_download_thread = None
                self.audio_download_worker = None
    
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
        image_label.setScaledContents(False)  # 不使用自动缩放，手动控制以保持宽高比
        
        # 保存原始pixmap或movie，用于在resize时重新缩放
        self.original_pixmap = None
        self.movie = None
        self.is_gif = False
        self.movie_original_size = None  # 保存 QMovie 的原始尺寸
        
        # 加载模型图片：优先使用调用者传递的图片对象
        if self.model_image:
            # 如果传递的是 QMovie（GIF）
            if isinstance(self.model_image, QMovie):
                self.is_gif = True
                self.movie = self.model_image
                image_label.setMovie(self.movie)
                
                # 获取 QMovie 的原始尺寸
                # 先启动 movie 以确保可以获取帧信息
                if not self.movie.state() == QMovie.MovieState.Running:
                    self.movie.start()
                
                # 尝试获取原始尺寸
                if self.movie.frameCount() > 0:
                    # 跳转到第一帧并获取尺寸
                    current_frame = self.movie.currentFrameNumber()
                    self.movie.jumpToFrame(0)
                    pixmap = self.movie.currentPixmap()
                    if not pixmap.isNull():
                        self.movie_original_size = pixmap.size()
                        # 恢复原来的帧
                        if current_frame >= 0:
                            self.movie.jumpToFrame(current_frame)
                    else:
                        # 如果获取失败，尝试等待一帧
                        from PyQt6.QtCore import QTimer
                        def get_movie_size():
                            if self.movie and self.movie.frameCount() > 0:
                                pixmap = self.movie.currentPixmap()
                                if not pixmap.isNull():
                                    self.movie_original_size = pixmap.size()
                                    self._update_movie_display(image_label)
                        QTimer.singleShot(100, get_movie_size)
                else:
                    # 如果无法获取帧数，等待一帧后获取尺寸
                    from PyQt6.QtCore import QTimer
                    def get_movie_size():
                        if self.movie and self.movie.frameCount() > 0:
                            pixmap = self.movie.currentPixmap()
                            if not pixmap.isNull():
                                self.movie_original_size = pixmap.size()
                                self._update_movie_display(image_label)
                    QTimer.singleShot(100, get_movie_size)
                
                # 设置 GIF 动图大小策略，保持宽高比
                # 如果已经获取到原始尺寸，立即更新显示
                if self.movie_original_size:
                    self._update_movie_display(image_label)
            # 如果传递的是 QPixmap（静态图片）
            elif isinstance(self.model_image, QPixmap) and not self.model_image.isNull():
                self.is_gif = False
                self.original_pixmap = self.model_image
                # 初始设置图片
                self._update_image_display(image_label)
            else:
                # 图片对象无效，显示占位符
                image_label.setText("🖼️")
        else:
            # 没有传递图片对象，尝试从 model_data 获取图片路径（向后兼容）
            model_image_path = self.model_data.get("image", "")
            if model_image_path and os.path.exists(model_image_path):
                try:
                    # 检查是否为 GIF 动图
                    file_ext = os.path.splitext(model_image_path)[1].lower()
                    if file_ext == '.gif':
                        # 使用 QMovie 加载 GIF 动图
                        self.is_gif = True
                        movie = QMovie(model_image_path)
                        self.movie = movie
                        # 获取 QMovie 的原始尺寸
                        movie.start()
                        from PyQt6.QtCore import QTimer
                        def get_movie_size():
                            if movie.frameCount() > 0:
                                self.movie_original_size = movie.currentPixmap().size()
                                self._update_movie_display(image_label)
                        QTimer.singleShot(100, get_movie_size)
                        
                        image_label.setMovie(movie)
                        # 设置 GIF 动图大小策略，保持宽高比
                        self._update_movie_display(image_label)
                    elif file_ext == '.png' or file_ext == '.jpg' or file_ext == '.jpeg' or file_ext == '.bmp' or file_ext == '.webp':
                        # 使用 QPixmap 加载静态图片（PNG、JPG等）
                        self.is_gif = False
                        pixmap = QPixmap(model_image_path)
                        if not pixmap.isNull():
                            self.original_pixmap = pixmap
                            # 初始设置图片
                            self._update_image_display(image_label)
                        else:
                            image_label.setText("🖼️")
                    else:
                        # 图片加载失败，显示占位符
                        image_label.setText("🖼️")
                except Exception as e:
                    # 图片加载出错，显示占位符
                    print(f"加载详情图片失败 {model_image_path}: {e}")
                    image_label.setText("🖼️")
            else:
                # 没有图片，显示占位符
                image_label.setText("🖼️")
        
        # 保存image_label引用，用于resize时更新
        self.image_label = image_label
        
        # 重写resizeEvent以在窗口大小改变时更新图片
        original_resize = image_label.resizeEvent
        def resizeEvent(event):
            if self.is_gif and self.movie:
                # GIF 动图：更新 movie 的缩放大小，保持宽高比
                self._update_movie_display(image_label)
            elif hasattr(self, 'original_pixmap') and self.original_pixmap and not self.original_pixmap.isNull():
                # 静态图片：更新显示
                self._update_image_display(image_label)
            original_resize(event)
        image_label.resizeEvent = resizeEvent
        
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
        
        # 获取模型信息
        category = self.model_data.get("category", "")
        category_name = self.model_data.get("category_name", "")
        if not category_name and category:
            # 如果没有category_name，从category字段判断
            categories = [cat.strip() for cat in category.split(";")]
            if "官方音色" in categories:
                category_name = "官方音色"
            elif "免费音色" in categories:
                category_name = "免费音色"
            else:
                category_name = category.split(";")[0].strip() if category else "未知"
        
        price = self.model_data.get("price", 0.0)
        if not isinstance(price, (int, float)):
            try:
                price = float(price)
            except (ValueError, TypeError):
                price = 0.0
        
        version = self.model_data.get("version", "V1")
        sample_rate = self.model_data.get("sample_rate", "48K")
        
        info_text = QLabel(f"""
种类: {category_name}<br>
价格: {price}<br>
版本: {version}<br>
采样率: {sample_rate}
        """)
        info_text.setStyleSheet("color: #cccccc; font-size: 14px;")
        info_row.addWidget(info_text)
        info_row.addStretch()
        info_layout.addLayout(info_row)
        
        layout.addWidget(info_panel, 1)
        
        return panel
    
    def _update_image_display(self, image_label):
        """更新图片显示，保持原始宽高比"""
        if not self.original_pixmap or self.original_pixmap.isNull():
            return
        
        # 获取label的可用大小
        label_size = image_label.size()
        if label_size.width() <= 0 or label_size.height() <= 0:
            return
        
        # 直接使用pixmap.scaled()方法，传入宽度和高度
        scaled_pixmap = self.original_pixmap.scaled(
            label_size.width(),
            label_size.height(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        
        # 设置pixmap
        image_label.setPixmap(scaled_pixmap)
    
    def _update_movie_display(self, image_label):
        """更新 GIF 动图显示，保持原始宽高比"""
        if not self.movie:
            return
        
        # 获取label的可用大小
        label_size = image_label.size()
        if label_size.width() <= 0 or label_size.height() <= 0:
            return
        
        # 获取原始尺寸
        if not self.movie_original_size:
            # 如果还没有获取到原始尺寸，尝试获取
            if self.movie.frameCount() > 0:
                self.movie_original_size = self.movie.currentPixmap().size()
            else:
                # 如果无法获取，使用 label 的尺寸（不缩放）
                self.movie.setScaledSize(label_size)
                return
        
        # 计算保持宽高比的缩放尺寸
        original_width = self.movie_original_size.width()
        original_height = self.movie_original_size.height()
        
        if original_width <= 0 or original_height <= 0:
            self.movie.setScaledSize(label_size)
            return
        
        # 计算缩放比例
        width_ratio = label_size.width() / original_width
        height_ratio = label_size.height() / original_height
        scale_ratio = min(width_ratio, height_ratio)  # 使用较小的比例以保持宽高比
        
        # 计算缩放后的尺寸
        scaled_width = int(original_width * scale_ratio)
        scaled_height = int(original_height * scale_ratio)
        
        # 设置缩放尺寸
        self.movie.setScaledSize(QSize(scaled_width, scaled_height))
    
    def create_right_panel(self):
        """创建右侧面板"""
        panel = QWidget()
        self.right_panel = panel  # 保存右侧面板的引用
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
            # 检查是否为免费模型
            category = self.model_data.get("category", "")
            price = self.model_data.get("price", 0) or 0
            is_free_model = False
            if category:
                categories = [cat.strip() for cat in category.split(";")]
                is_free_model = "免费音色" in categories
            
            # 判断是否为官方模型
            is_official_model = category and "官方音色" in [cat.strip() for cat in category.split(";")]
            
            # 判断是否为收费模型（价格大于0或不是免费音色）
            is_paid_model = price > 0 or (not is_free_model and is_official_model)
            
            # 检查模型是否在用户的可用模型列表中
            model_uid = self.model_data.get("uid")
            is_in_available_list = False
            if model_uid:
                available_uids = self._get_user_available_model_uids()
                if available_uids and model_uid in available_uids:
                    is_in_available_list = True
            
            # 检查是否有正在进行的试用
            has_active_trial = False
            if self.home_page and hasattr(self.home_page, 'user_trials'):
                if model_uid:
                    trial_data = self.home_page.user_trials.get(model_uid)
                    if trial_data and trial_data.get("is_active", False):
                        remaining_seconds = trial_data.get("remaining_seconds", 0)
                        if remaining_seconds > 0:
                            has_active_trial = True
            
            # 如果是官方模型、未下载、且在用户可用列表中，显示下载按钮而不是试用按钮
            if is_official_model and is_in_available_list:
                # 显示下载区块，不显示试用区块
                self.download_section = self.create_download_section()
                layout.addWidget(self.download_section, 5)
            else:
                # 如果不是免费模型，显示试用区块
                if not is_free_model:
                    trial_section = self.create_trial_section()
                    layout.addWidget(trial_section, 5)
                
                # 下载按钮：免费模型始终显示，收费模型只在试用中显示
                if not is_paid_model or has_active_trial:
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
        """查找模型目录下的音频文件（支持本地和在线模型）"""
        model_name = self.model_data.get("name", "")
        if not model_name:
            return
        
        # 支持的音频格式
        audio_extensions = (".wav", ".mp3", ".flac", ".m4a", ".ogg", ".aac")
        
        # 首先尝试从本地查找（已下载的模型）
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
        
        # 如果本地找不到，尝试从服务端下载（在线模型）
        # 标记需要从服务端下载
        self.audio_file_path = None
        self.need_download_audio = True
    
    def on_play_clicked(self):
        """播放按钮点击"""
        # 如果需要从服务端下载音频
        if self.need_download_audio and not self.audio_file_path:
            self._download_audio_for_preview()
            return
        
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
    
    def _download_audio_for_preview(self):
        """从服务端下载音频文件用于试听"""
        model_uid = self.model_data.get("uid")
        if not model_uid:
            QMessageBox.warning(self, "错误", "模型UUID不存在")
            return
        
        # 禁用播放按钮
        if self.play_btn:
            self.play_btn.setEnabled(False)
            self.play_btn.setText("下载中...")
        
        # 创建临时目录保存音频文件
        temp_dir = os.path.join(tempfile.gettempdir(), "rvc_audio_preview")
        os.makedirs(temp_dir, exist_ok=True)
        
        # 异步下载音频
        async def download_audio():
            try:
                result = await models_api.download_model_audio(model_uid, temp_dir)
                if result.get("success"):
                    # 下载成功，更新音频文件路径
                    downloaded_path = result.get("file_path")
                    if downloaded_path and os.path.exists(downloaded_path):
                        self.audio_file_path = downloaded_path
                        self.need_download_audio = False
                        # 下载完成后自动播放
                        return {"success": True, "auto_play": True}
                    else:
                        return {"success": False, "message": "音频文件下载失败"}
                else:
                    return result
            except Exception as e:
                return {"success": False, "message": f"下载失败: {str(e)}"}
        
        # 使用异步工具运行
        self.audio_download_thread, self.audio_download_worker = run_async(download_audio())
        self.audio_download_worker.finished.connect(self._on_audio_download_finished)
        self.audio_download_worker.error.connect(self._on_audio_download_error)
        self.audio_download_thread.start()
    
    def _on_audio_download_finished(self, result):
        """音频下载完成"""
        # 清理线程
        if self.audio_download_thread:
            self.audio_download_thread.quit()
            self.audio_download_thread.wait()
            self.audio_download_thread = None
            self.audio_download_worker = None
        
        # 恢复播放按钮
        if self.play_btn:
            self.play_btn.setEnabled(True)
            self.play_btn.setText("▶")
        
        if result.get("success"):
            # 如果设置了自动播放，开始播放
            if result.get("auto_play"):
                QTimer.singleShot(100, self.on_play_clicked)
        else:
            QMessageBox.warning(self, "错误", result.get("message", "音频下载失败"))
    
    def _on_audio_download_error(self, error_msg):
        """音频下载出错"""
        # 清理线程
        if self.audio_download_thread:
            self.audio_download_thread.quit()
            self.audio_download_thread.wait()
            self.audio_download_thread = None
            self.audio_download_worker = None
        
        # 恢复播放按钮
        if self.play_btn:
            self.play_btn.setEnabled(True)
            self.play_btn.setText("▶")
        
        QMessageBox.warning(self, "错误", f"音频下载失败: {error_msg}")
    
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
        # 禁用按钮，显示"启动中..."
        self.trial_btn.setEnabled(False)
        self.trial_btn.setText("启动中...")
        
        # 获取模型UUID
        model_uuid = self.model_data.get("uid")
        if not model_uuid:
            QMessageBox.warning(self, "错误", "无法获取模型UUID")
            self.trial_btn.setEnabled(True)
            self.trial_btn.setText("开始试用")
            return
        
        # 异步调用服务器API
        async def start_trial():
            return await models_api.start_trial(model_uuid)
        
        # 使用异步工具运行
        self.trial_thread, self.trial_worker = run_async(start_trial())
        
        # 连接信号
        self.trial_worker.finished.connect(self._on_trial_started)
        self.trial_worker.error.connect(self._on_trial_error)
        
        # 启动线程
        self.trial_thread.start()
    
    def _on_trial_started(self, result):
        """试用开始成功回调"""
        # 清理线程
        self._cleanup_trial_thread()
        
        if result.get("success"):
            data = result.get("data", {})
            remaining_seconds = data.get("remaining_seconds", 3600)
            
            # 更新状态
            self.trial_active = True
            self.trial_seconds = remaining_seconds
            
            # 更新主页的试用记录（如果可用）
            if self.home_page and hasattr(self.home_page, 'user_trials'):
                model_uid = self.model_data.get("uid")
                if model_uid:
                    # 更新或添加试用记录
                    self.home_page.user_trials[model_uid] = {
                        "model_uid": model_uid,
                        "model_name": self.model_data.get("name", ""),
                        "is_active": True,
                        "remaining_seconds": remaining_seconds,
                        "start_time": data.get("start_time"),
                        "end_time": data.get("end_time")
                    }
            
            # 启动本地倒计时
            self.trial_timer.start(1000)  # 每秒更新
            
            # 启动服务器同步定时器（每30秒同步一次）
            if not self.trial_sync_timer:
                self.trial_sync_timer = QTimer()
                self.trial_sync_timer.timeout.connect(self._sync_trial_status)
            self.trial_sync_timer.start(30000)  # 30秒
            
            # 更新UI
            self.trial_btn.setText("试用中...")
            self.trial_btn.setEnabled(False)
            self.trial_time_label.setVisible(True)
            self.update_trial_time()
            
            # 如果是收费模型，显示下载按钮
            category = self.model_data.get("category", "")
            price = self.model_data.get("price", 0) or 0
            is_free_model = "免费音色" in (category.split(";") if category else [])
            is_paid_model = price > 0 or (not is_free_model and category and "官方音色" in (category.split(";") if category else []))
            
            if is_paid_model:
                # 检查下载按钮是否已存在
                if not hasattr(self, 'download_section') or not self.download_section:
                    # 使用保存的右侧面板引用
                    if self.right_panel and hasattr(self.right_panel, 'layout'):
                        right_layout = self.right_panel.layout()
                        if right_layout:
                            self.download_section = self.create_download_section()
                            # 找到试用区块的位置，在其后插入
                            trial_index = -1
                            # 试用按钮的层级：trial_btn -> trial_layout -> trial_section
                            if hasattr(self, 'trial_btn') and self.trial_btn:
                                try:
                                    trial_section = self.trial_btn.parent().parent()
                                    if trial_section:
                                        for i in range(right_layout.count()):
                                            item = right_layout.itemAt(i)
                                            if item and item.widget() == trial_section:
                                                trial_index = i
                                                break
                                except (AttributeError, RuntimeError):
                                    pass
                            
                            if trial_index >= 0:
                                # 在试用区块后插入下载区块
                                right_layout.insertWidget(trial_index + 1, self.download_section, 5)
                            else:
                                # 如果找不到试用区块，添加到布局末尾（在stretch之前）
                                # 先移除stretch（如果存在）
                                stretch_index = -1
                                for i in range(right_layout.count()):
                                    item = right_layout.itemAt(i)
                                    if item and item.spacerItem():
                                        stretch_index = i
                                        break
                                if stretch_index >= 0:
                                    right_layout.insertWidget(stretch_index, self.download_section, 5)
                                else:
                                    right_layout.addWidget(self.download_section, 5)
                else:
                    # 下载按钮已存在，确保可见
                    self.download_section.setVisible(True)
        else:
            # 显示错误信息
            error_msg = result.get("message", "启动试用失败")
            QMessageBox.warning(self, "错误", error_msg)
            self.trial_btn.setEnabled(True)
            self.trial_btn.setText("开始试用")
    
    def _on_trial_error(self, error_msg):
        """试用启动错误回调"""
        QMessageBox.warning(self, "错误", f"启动试用失败: {error_msg}")
        self.trial_btn.setEnabled(True)
        self.trial_btn.setText("开始试用")
        self._cleanup_trial_thread()
    
    def _get_user_available_model_uids(self):
        """
        获取用户可用的模型UUID列表
        
        Returns:
            可用模型UUID的集合（set），如果用户未登录或没有可用模型列表则返回None
        """
        try:
            # 尝试从auth_api获取用户信息
            user_info = auth_api.user_info
            if not user_info:
                # 如果auth_api中没有，尝试从存储中加载
                from api.storage import token_storage
                user_info = token_storage.load_user_info()
            
            if not user_info:
                # 用户未登录，返回None
                return None
            
            # 获取available_models字段
            available_models = user_info.get("available_models")
            if not available_models:
                # 如果没有available_models字段或为空，返回None
                return None
            
            # 解析分号分隔的UUID列表
            uids = [uid.strip() for uid in available_models.split(";") if uid.strip()]
            if not uids:
                # 如果解析后列表为空，返回None
                return None
            return set(uids)  # 返回集合以便快速查找
            
        except Exception as e:
            print(f"获取用户可用模型列表失败: {e}")
            # 出错时返回None
            return None
    
    def _check_trial_status(self):
        """检查试用状态（页面加载时）"""
        # 检查登录状态，未登录时不检查试用状态
        if not auth_api.is_logged_in():
            print("未登录，跳过试用状态检查")
            return
        
        # 先清理之前的检查线程（如果存在）
        self._cleanup_check_status_thread()
        
        # 获取模型UUID
        model_uuid = self.model_data.get("uid")
        if not model_uuid:
            return
        
        # 优先使用主页已加载的试用记录（如果可用）
        if self.home_page and hasattr(self.home_page, 'user_trials'):
            trial_data = self.home_page.user_trials.get(model_uuid)
            if trial_data:
                # 使用本地已加载的数据
                is_active = trial_data.get("is_active", False)
                remaining_seconds = trial_data.get("remaining_seconds", 0)
                
                # 构造与API返回格式一致的数据结构
                result = {
                    "success": True,
                    "data": {
                        "has_trialed": True,
                        "is_active": is_active,
                        "remaining_seconds": remaining_seconds
                    }
                }
                
                # 直接调用回调处理
                self._on_trial_status_checked(result)
                
                # 如果数据已过期，仍然同步一次服务器状态
                if is_active and remaining_seconds > 0:
                    return  # 使用本地数据，不需要再调用API
                # 如果数据已过期或不存在，继续调用API更新
        
        # 如果没有本地数据或需要更新，异步检查试用状态
        async def check():
            return await models_api.get_trial_status(model_uuid)
        
        # 使用异步工具运行
        self.check_status_thread, self.check_status_worker = run_async(check())
        
        # 连接信号
        self.check_status_worker.finished.connect(self._on_trial_status_checked)
        self.check_status_worker.error.connect(lambda e: print(f"检查试用状态失败: {e}"))
        
        # 启动线程
        self.check_status_thread.start()
    
    def _on_trial_status_checked(self, result):
        """试用状态检查回调"""
        # 清理检查线程
        self._cleanup_check_status_thread()
        
        if result.get("success"):
            data = result.get("data", {})
            has_trialed = data.get("has_trialed", False)
            is_active = data.get("is_active", False)
            remaining_seconds = data.get("remaining_seconds", 0)
            
            if is_active:
                # 有正在进行的试用
                self.trial_active = True
                self.trial_seconds = remaining_seconds
                
                # 启动本地倒计时
                self.trial_timer.start(1000)
                
                # 启动服务器同步定时器
                if not self.trial_sync_timer:
                    self.trial_sync_timer = QTimer()
                    self.trial_sync_timer.timeout.connect(self._sync_trial_status)
                self.trial_sync_timer.start(30000)
                
                # 更新UI（确保UI元素已创建）
                def update_ui():
                    if hasattr(self, 'trial_btn') and self.trial_btn:
                        self.trial_btn.setText("试用中...")
                        self.trial_btn.setEnabled(False)
                    if hasattr(self, 'trial_time_label') and self.trial_time_label:
                        self.trial_time_label.setVisible(True)
                    self.update_trial_time()
                    
                    # 如果试用中且是收费模型，显示下载按钮（如果之前没有显示）
                    if not hasattr(self, 'download_section') or not self.download_section:
                        # 检查是否为收费模型
                        category = self.model_data.get("category", "")
                        price = self.model_data.get("price", 0) or 0
                        is_free_model = "免费音色" in (category.split(";") if category else [])
                        is_paid_model = price > 0 or (not is_free_model and category and "官方音色" in category.split(";"))
                        
                        if is_paid_model:
                            # 收费模型试用中，显示下载按钮
                            # 使用保存的右侧面板引用
                            if not hasattr(self, 'download_section') or not self.download_section:
                                if self.right_panel and hasattr(self.right_panel, 'layout'):
                                    right_layout = self.right_panel.layout()
                                    if right_layout:
                                        self.download_section = self.create_download_section()
                                        # 找到试用区块的位置，在其后插入
                                        trial_index = -1
                                        if hasattr(self, 'trial_btn') and self.trial_btn:
                                            try:
                                                trial_section = self.trial_btn.parent().parent()
                                                if trial_section:
                                                    for i in range(right_layout.count()):
                                                        item = right_layout.itemAt(i)
                                                        if item and item.widget() == trial_section:
                                                            trial_index = i
                                                            break
                                            except (AttributeError, RuntimeError):
                                                pass
                                        
                                        if trial_index >= 0:
                                            # 在试用区块后插入下载区块
                                            right_layout.insertWidget(trial_index + 1, self.download_section, 5)
                                        else:
                                            # 如果找不到试用区块，添加到布局末尾（在stretch之前）
                                            stretch_index = -1
                                            for i in range(right_layout.count()):
                                                item = right_layout.itemAt(i)
                                                if item and item.spacerItem():
                                                    stretch_index = i
                                                    break
                                            if stretch_index >= 0:
                                                right_layout.insertWidget(stretch_index, self.download_section, 5)
                                            else:
                                                right_layout.addWidget(self.download_section, 5)
                            else:
                                # 下载区块已存在，确保可见
                                if self.download_section:
                                    self.download_section.setVisible(True)
                
                # 如果UI元素还没创建，延迟更新
                if hasattr(self, 'trial_btn') and self.trial_btn:
                    update_ui()
                else:
                    # UI元素可能还没创建，延迟100ms再更新
                    QTimer.singleShot(100, update_ui)
            elif has_trialed:
                # 已试用过，禁用按钮
                def update_ui_disabled():
                    if hasattr(self, 'trial_btn') and self.trial_btn:
                        self.trial_btn.setText("已试用")
                        self.trial_btn.setEnabled(False)
                    if hasattr(self, 'trial_time_label') and self.trial_time_label:
                        self.trial_time_label.setVisible(False)
                
                if hasattr(self, 'trial_btn') and self.trial_btn:
                    update_ui_disabled()
                else:
                    QTimer.singleShot(100, update_ui_disabled)
    
    def _sync_trial_status(self):
        """同步服务器试用状态"""
        # 检查登录状态，未登录时不同步试用状态
        if not auth_api.is_logged_in():
            print("未登录，跳过试用状态同步")
            return
        
        # 先清理之前的同步线程（如果存在）
        self._cleanup_sync_status_thread()
        
        # 获取模型UUID
        model_uuid = self.model_data.get("uid")
        if not model_uuid:
            return
        
        # 异步同步状态
        async def sync():
            return await models_api.get_trial_status(model_uuid)
        
        # 使用异步工具运行
        self.sync_status_thread, self.sync_status_worker = run_async(sync())
        
        # 连接信号
        self.sync_status_worker.finished.connect(self._on_trial_status_synced)
        self.sync_status_worker.error.connect(lambda e: print(f"同步试用状态失败: {e}"))
        
        # 启动线程
        self.sync_status_thread.start()
    
    def _on_trial_status_synced(self, result):
        """同步状态回调"""
        # 清理同步线程
        self._cleanup_sync_status_thread()
        
        if result.get("success"):
            data = result.get("data", {})
            if data.get("is_active"):
                # 更新剩余时间
                remaining = data.get("remaining_seconds", 0)
                self.trial_seconds = remaining
                self.update_trial_time()
            else:
                # 试用已过期
                self._end_trial()
    
    def _end_trial(self):
        """结束试用"""
        # 停止定时器
        if self.trial_timer:
            self.trial_timer.stop()
        if self.trial_sync_timer:
            self.trial_sync_timer.stop()
        
        # 更新状态
        self.trial_active = False
        self.trial_seconds = 0
        
        # 更新UI
        if hasattr(self, 'trial_btn') and self.trial_btn:
            self.trial_btn.setText("已试用")
            self.trial_btn.setEnabled(False)
        if hasattr(self, 'trial_time_label') and self.trial_time_label:
            self.trial_time_label.setVisible(False)
    
    def update_trial_time(self):
        """更新试用时间"""
        if self.trial_seconds > 0:
            minutes = self.trial_seconds // 60
            seconds = self.trial_seconds % 60
            if hasattr(self, 'trial_time_label') and self.trial_time_label:
                self.trial_time_label.setText(f"剩余时间: {minutes:02d}:{seconds:02d}")
                self.trial_time_label.setVisible(True)
            self.trial_seconds -= 1
        else:
            # 时间到了
            self._end_trial()
            QMessageBox.information(self, "提示", "试用时间已到")
    
    def _cleanup_trial_thread(self):
        """清理试用相关线程"""
        if self.trial_thread:
            try:
                if self.trial_worker:
                    try:
                        self.trial_worker.finished.disconnect()
                        self.trial_worker.error.disconnect()
                    except:
                        pass
                
                if hasattr(self.trial_thread, 'isRunning') and self.trial_thread.isRunning():
                    self.trial_thread.quit()
                    if not self.trial_thread.wait(3000):
                        self.trial_thread.terminate()
                        self.trial_thread.wait()
            except RuntimeError:
                # 对象已被删除
                pass
            except Exception as e:
                print(f"清理试用线程时出错: {e}")
            finally:
                if self.trial_thread:
                    try:
                        self.trial_thread.deleteLater()
                    except:
                        pass
                if self.trial_worker:
                    try:
                        self.trial_worker.deleteLater()
                    except:
                        pass
                self.trial_thread = None
                self.trial_worker = None
    
    def _cleanup_check_status_thread(self):
        """清理检查状态线程"""
        if self.check_status_thread:
            try:
                if self.check_status_worker:
                    try:
                        self.check_status_worker.finished.disconnect()
                        self.check_status_worker.error.disconnect()
                    except:
                        pass
                
                if hasattr(self.check_status_thread, 'isRunning') and self.check_status_thread.isRunning():
                    self.check_status_thread.quit()
                    if not self.check_status_thread.wait(3000):
                        self.check_status_thread.terminate()
                        self.check_status_thread.wait()
            except RuntimeError:
                # 对象已被删除
                pass
            except Exception as e:
                print(f"清理检查状态线程时出错: {e}")
            finally:
                if self.check_status_thread:
                    try:
                        self.check_status_thread.deleteLater()
                    except:
                        pass
                if self.check_status_worker:
                    try:
                        self.check_status_worker.deleteLater()
                    except:
                        pass
                self.check_status_thread = None
                self.check_status_worker = None
    
    def _cleanup_sync_status_thread(self):
        """清理同步状态线程"""
        if self.sync_status_thread:
            try:
                if self.sync_status_worker:
                    try:
                        self.sync_status_worker.finished.disconnect()
                        self.sync_status_worker.error.disconnect()
                    except:
                        pass
                
                if hasattr(self.sync_status_thread, 'isRunning') and self.sync_status_thread.isRunning():
                    self.sync_status_thread.quit()
                    if not self.sync_status_thread.wait(3000):
                        self.sync_status_thread.terminate()
                        self.sync_status_thread.wait()
            except RuntimeError:
                # 对象已被删除
                pass
            except Exception as e:
                print(f"清理同步状态线程时出错: {e}")
            finally:
                if self.sync_status_thread:
                    try:
                        self.sync_status_thread.deleteLater()
                    except:
                        pass
                if self.sync_status_worker:
                    try:
                        self.sync_status_worker.deleteLater()
                    except:
                        pass
                self.sync_status_thread = None
                self.sync_status_worker = None
    
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
        
        # 删除和收藏按钮
        action_layout = QHBoxLayout()
        action_layout.setSpacing(10)
        
        # 收藏按钮
        favorite_btn = QPushButton()
        # 检查当前是否已收藏
        category = self.model_data.get("category", "")
        categories = [cat.strip() for cat in category.split(";") if cat.strip()]
        is_favorite = "收藏" in categories
        if is_favorite:
            favorite_btn.setText("★ 已收藏")
            favorite_btn.setStyleSheet("""
                QPushButton {
                    background-color: #ff9800;
                    color: #ffffff;
                    border: none;
                    border-radius: 6px;
                    padding: 8px 16px;
                    font-size: 14px;
                }
                QPushButton:hover {
                    background-color: #f57c00;
                }
            """)
        else:
            favorite_btn.setText("☆ 收藏")
            favorite_btn.setStyleSheet("""
                QPushButton {
                    background-color: #4caf50;
                    color: #ffffff;
                    border: none;
                    border-radius: 6px;
                    padding: 8px 16px;
                    font-size: 14px;
                }
                QPushButton:hover {
                    background-color: #45a049;
                }
            """)
        favorite_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        favorite_btn.clicked.connect(self.on_favorite_clicked)
        self.favorite_btn = favorite_btn  # 保存引用以便更新文本
        action_layout.addWidget(favorite_btn)
        
        # 删除按钮
        delete_btn = QPushButton("删除")
        delete_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: #ffffff;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #da190b;
            }
        """)
        delete_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        delete_btn.clicked.connect(self.on_delete_clicked)
        action_layout.addWidget(delete_btn)
        
        action_layout.addStretch()
        layout.addLayout(action_layout)
        
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
    
    def on_favorite_clicked(self):
        """收藏/取消收藏按钮点击"""
        # 获取模型UUID
        model_uid = self.model_data.get("uid")
        if not model_uid:
            QMessageBox.warning(self, "错误", "模型UUID不存在")
            return
        
        # 检查是否已登录
        if not auth_api.is_logged_in():
            QMessageBox.warning(self, "提示", "请先登录后再使用收藏功能")
            return
        
        # 异步切换收藏状态
        async def toggle_favorite():
            try:
                result = await models_api.toggle_favorite(model_uid)
                return result
            except Exception as e:
                return {"success": False, "message": f"收藏操作失败: {str(e)}"}
        
        # 使用异步工具运行
        self.favorite_thread, self.favorite_worker = run_async(toggle_favorite())
        self.favorite_worker.finished.connect(self._on_favorite_finished)
        self.favorite_worker.error.connect(self._on_favorite_error)
        self.favorite_thread.start()
        
        # 禁用按钮，防止重复点击
        if self.favorite_btn:
            self.favorite_btn.setEnabled(False)
            self.favorite_btn.setText("处理中...")
    
    def _on_favorite_finished(self, result):
        """收藏操作完成"""
        # 清理线程
        if self.favorite_thread:
            self.favorite_thread.quit()
            self.favorite_thread.wait()
            self.favorite_thread = None
            self.favorite_worker = None
        
        if not result.get("success"):
            # 恢复按钮状态
            if self.favorite_btn:
                self.favorite_btn.setEnabled(True)
                # 恢复按钮文本（根据当前状态）
                category = self.model_data.get("category", "")
                categories = [cat.strip() for cat in category.split(";") if cat.strip()]
                is_favorite = "收藏" in categories
                if is_favorite:
                    self.favorite_btn.setText("★ 已收藏")
                else:
                    self.favorite_btn.setText("☆ 收藏")
            QMessageBox.warning(self, "错误", result.get("message", "收藏操作失败"))
            return
        
        # 获取新的收藏状态
        data = result.get("data", {})
        is_favorite = data.get("is_favorite", False)
        message = result.get("message", "操作成功")
        
        # 更新本地JSON文件（如果模型已下载）
        pth_path = self.model_data.get("pth_path", "")
        if pth_path:
            try:
                models_base_path = os.path.join(os.getcwd(), "models")
                if not os.path.isabs(pth_path):
                    model_dir_path = os.path.join(models_base_path, os.path.dirname(pth_path))
                else:
                    model_dir_path = os.path.dirname(pth_path)
                
                # 查找JSON文件
                if os.path.exists(model_dir_path):
                    json_files = [f for f in os.listdir(model_dir_path) if f.endswith(".json")]
                    if json_files:
                        json_path = os.path.join(model_dir_path, json_files[0])
                        
                        # 读取并更新JSON文件
                        try:
                            with open(json_path, 'r', encoding='utf-8') as f:
                                model_info = json.load(f)
                            
                            # 更新分类
                            category = model_info.get("category", "免费音色")
                            categories = [cat.strip() for cat in category.split(";") if cat.strip()]
                            
                            if is_favorite:
                                if "收藏" not in categories:
                                    categories.append("收藏")
                            else:
                                if "收藏" in categories:
                                    categories.remove("收藏")
                            
                            model_info["category"] = ";".join(categories)
                            
                            # 保存JSON文件
                            with open(json_path, 'w', encoding='utf-8') as f:
                                json.dump(model_info, f, indent=2, ensure_ascii=False)
                            
                            # 更新model_data
                            self.model_data["category"] = model_info["category"]
                        except Exception as e:
                            print(f"更新本地JSON文件失败: {str(e)}")
            except Exception as e:
                print(f"更新本地JSON文件时出错: {str(e)}")
        
        # 更新按钮文本和样式
        if self.favorite_btn:
            self.favorite_btn.setEnabled(True)
            if is_favorite:
                self.favorite_btn.setText("★ 已收藏")
                self.favorite_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #ff9800;
                        color: #ffffff;
                        border: none;
                        border-radius: 6px;
                        padding: 8px 16px;
                        font-size: 14px;
                    }
                    QPushButton:hover {
                        background-color: #f57c00;
                    }
                """)
            else:
                self.favorite_btn.setText("☆ 收藏")
                self.favorite_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #4caf50;
                        color: #ffffff;
                        border: none;
                        border-radius: 6px;
                        padding: 8px 16px;
                        font-size: 14px;
                    }
                    QPushButton:hover {
                        background-color: #45a049;
                    }
                """)
        
        # 刷新相关页面
        if self.main_window:
            # 刷新管理页面
            if hasattr(self.main_window, 'pages') and 'management' in self.main_window.pages:
                management_page = self.main_window.pages['management']
                if hasattr(management_page, '_refresh_models_with_filter'):
                    management_page._refresh_models_with_filter()
                elif hasattr(management_page, 'load_models'):
                    management_page.load_models()
        
        QMessageBox.information(self, "提示", message)
    
    def _on_favorite_error(self, error_msg):
        """收藏操作出错"""
        # 清理线程
        if self.favorite_thread:
            self.favorite_thread.quit()
            self.favorite_thread.wait()
            self.favorite_thread = None
            self.favorite_worker = None
        
        # 恢复按钮状态
        if self.favorite_btn:
            self.favorite_btn.setEnabled(True)
            # 恢复按钮文本（根据当前状态）
            category = self.model_data.get("category", "")
            categories = [cat.strip() for cat in category.split(";") if cat.strip()]
            is_favorite = "收藏" in categories
            if is_favorite:
                self.favorite_btn.setText("★ 已收藏")
            else:
                self.favorite_btn.setText("☆ 收藏")
        
        QMessageBox.warning(self, "错误", f"收藏操作失败: {error_msg}")
    
    def on_delete_clicked(self):
        """删除按钮点击"""
        # 确认删除
        reply = QMessageBox.question(
            self,
            "确认删除",
            "确定要删除该模型吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        # 获取模型文件路径
        pth_path = self.model_data.get("pth_path", "")
        
        if not pth_path:
            QMessageBox.warning(self, "错误", "模型文件路径不存在")
            return
        
        # 获取模型目录
        models_base_path = os.path.join(os.getcwd(), "models")
        if not os.path.isabs(pth_path):
            model_dir_path = os.path.join(models_base_path, os.path.dirname(pth_path))
        else:
            model_dir_path = os.path.dirname(pth_path)
        
        # 确认目录是否存在
        if not os.path.exists(model_dir_path):
            QMessageBox.warning(self, "错误", "模型目录不存在")
            return
        
        # 删除整个模型目录及其所有内容
        errors = []
        model_dir_name = os.path.basename(model_dir_path)
        
        try:
            # 使用shutil.rmtree递归删除整个目录及其所有内容
            import shutil
            shutil.rmtree(model_dir_path)
        except Exception as e:
            errors.append(f"删除模型目录失败: {str(e)}")
        
        # 显示删除结果
        if errors:
            error_msg = "删除失败：\n" + "\n".join(errors)
            QMessageBox.warning(self, "删除失败", error_msg)
        else:
            QMessageBox.information(self, "删除成功", f"已成功删除模型")
        
        # 无论是否有错误，都刷新相关页面（因为可能部分文件已删除）
        if self.main_window:
            # 刷新管理页面
            if hasattr(self.main_window, 'pages') and 'management' in self.main_window.pages:
                management_page = self.main_window.pages['management']
                if hasattr(management_page, '_refresh_models_with_filter'):
                    management_page._refresh_models_with_filter()
                elif hasattr(management_page, 'load_models'):
                    management_page.load_models()
            
            # 刷新主页
            if hasattr(self.main_window, 'pages') and 'home' in self.main_window.pages:
                home_page = self.main_window.pages['home']
                if hasattr(home_page, 'load_models'):
                    home_page.load_models()
        
        # 如果删除成功（没有错误），返回上一页
        if not errors:
            self.back_clicked.emit()
    
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
            
            # 刷新管理页面（如果主窗口可用）
            self._refresh_management_page()
            # 刷新推理页面（如果主窗口可用）
            self._refresh_inference_page()
            
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
    
    def _refresh_management_page(self):
        """刷新管理页面（保持当前筛选条件）"""
        try:
            # 如果直接有主窗口引用，使用它
            if self.main_window and hasattr(self.main_window, 'pages'):
                management_page = self.main_window.pages.get("management")
                if management_page:
                    # 重新加载模型数据，但保持当前的筛选条件
                    management_page._refresh_models_with_filter()
                    return
            
            # 否则，尝试向上查找主窗口
            parent = self.parent()
            while parent:
                if hasattr(parent, 'pages'):
                    management_page = parent.pages.get("management")
                    if management_page:
                        # 重新加载模型数据，但保持当前的筛选条件
                        management_page._refresh_models_with_filter()
                        return
                parent = parent.parent()
        except Exception as e:
            print(f"刷新管理页面失败: {e}")

    def _refresh_inference_page(self):
        """刷新推理页面模型列表"""
        try:
            # 优先通过main_window引用
            if self.main_window and hasattr(self.main_window, 'pages'):
                inference_page = self.main_window.pages.get("inference")
                if inference_page:
                    inference_page.load_models()
                    return

            # 向上查找主窗口
            parent = self.parent()
            while parent:
                if hasattr(parent, 'pages'):
                    inference_page = parent.pages.get("inference")
                    if inference_page:
                        inference_page.load_models()
                        return
                parent = parent.parent()
        except Exception as e:
            print(f"刷新推理页面失败: {e}")
    
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
        self.user_trials = {}  # 用户的试用记录 {model_uid: trial_data}
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
        list_layout.addWidget(self.scroll_area, stretch=1)
        self.scroll_area.hide()
        
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

        list_layout.addStretch()
        
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
        categories = ["全部", "免费音色", "官方音色"]
        
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
        
        # 登录成功后，加载用户的试用记录（再次确认登录状态）
        if auth_api.is_logged_in():
            self._load_user_trials()
        else:
            print("登录状态异常，跳过加载试用记录")
        
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
            # 按模型名称排序
            self.models_data.sort(key=lambda x: x.get("name", "").lower())
            self.filtered_models = self.models_data.copy()
            
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
    
    def _load_user_trials(self):
        """加载用户的试用记录"""
        if not auth_api.is_logged_in():
            return
        
        # 异步加载试用记录
        async def fetch_trials():
            return await models_api.get_user_trials()
        
        # 使用异步工具运行
        self.trials_thread, self.trials_worker = run_async(fetch_trials())
        self.trials_worker.finished.connect(self._on_trials_loaded)
        self.trials_worker.error.connect(lambda e: print(f"加载试用记录失败: {e}"))
        self.trials_thread.start()
    
    def _on_trials_loaded(self, result):
        """试用记录加载完成"""
        if result.get("success"):
            # API客户端会将服务器返回的JSON包装在data中
            # 服务器返回格式: {"success": True, "data": {"trials": [...]}}
            # 客户端包装后: {"success": True, "data": {"success": True, "data": {"trials": [...]}}}
            data = result.get("data", {})
            
            # 如果data中还有success字段，说明是服务器返回的完整响应，需要再取一次data
            if isinstance(data, dict) and "success" in data and "data" in data:
                data = data.get("data", {})
            
            trials = data.get("trials", [])
            
            # 将试用记录存储到字典中，以model_uid为key
            self.user_trials = {}
            for trial in trials:
                model_uid = trial.get("model_uid")
                if model_uid:
                    self.user_trials[model_uid] = trial
            
            print(f"已加载 {len(self.user_trials)} 条试用记录")
            if len(trials) > 0:
                print(f"试用记录详情: {trials}")
        else:
            print(f"加载试用记录失败: {result.get('message', '未知错误')}")
            print(f"完整响应: {result}")
        
        # 清理线程
        if hasattr(self, 'trials_thread') and self.trials_thread:
            try:
                if hasattr(self.trials_thread, 'isRunning') and self.trials_thread.isRunning():
                    self.trials_thread.quit()
                    self.trials_thread.wait(3000)
            except:
                pass
            try:
                self.trials_thread.deleteLater()
            except:
                pass
            self.trials_thread = None
            self.trials_worker = None
    
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
            "price": api_model.get("price", 0.0),  # 价格
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
        # 清除现有卡片（先清理资源）
        while self.grid_layout.count():
            child = self.grid_layout.takeAt(0)
            if child.widget():
                widget = child.widget()
                # 如果是ModelCard且使用了在线加载，先清理其资源
                if isinstance(widget, ModelCard) and widget.load_online:
                    widget.cleanup()
                widget.deleteLater()
        
        # 添加模型卡片（主页使用，优先从服务端获取图片）
        columns = 5  # 每行5个
        for i, model_data in enumerate(self.filtered_models):
            card = ModelCard(model_data, load_online=True)  # 主页使用在线加载
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
        
        # 查找对应的 ModelCard，获取图片对象
        model_image = None
        for i in range(self.grid_layout.count()):
            item = self.grid_layout.itemAt(i)
            if item and item.widget():
                widget = item.widget()
                if isinstance(widget, ModelCard) and widget.model_id == model_id:
                    # 优先使用 movie（GIF），否则使用 original_pixmap
                    if hasattr(widget, 'movie') and widget.movie:
                        # 创建新的 QMovie 实例（因为 QMovie 不能直接复制）
                        # 如果 ModelCard 有图片路径，使用路径创建新的 QMovie
                        if widget.model_image and os.path.exists(widget.model_image):
                            model_image = QMovie(widget.model_image)
                            model_image.start()
                    elif hasattr(widget, 'original_pixmap') and widget.original_pixmap and not widget.original_pixmap.isNull():
                        # 复制 QPixmap
                        model_image = QPixmap(widget.original_pixmap)
                    elif hasattr(widget, 'image_label') and widget.image_label:
                        # 尝试从 image_label 获取 pixmap（备用方案）
                        pixmap = widget.image_label.pixmap()
                        if pixmap and not pixmap.isNull():
                            model_image = QPixmap(pixmap)
                    break
        
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
        
        # 根据category字段判断音色类型
        category = detail_data.get("category", "")
        category_name = "免费音色"  # 默认值
        if category:
            # category可能包含多个分类，用分号分隔
            categories = [cat.strip() for cat in category.split(";")]
            if "官方音色" in categories:
                category_name = "官方音色"
            elif "免费音色" in categories:
                category_name = "免费音色"
        
        # 从模型数据中获取价格，如果没有则默认为0
        price = detail_data.get("price", 0.0)
        if not isinstance(price, (int, float)):
            try:
                price = float(price)
            except (ValueError, TypeError):
                price = 0.0
        
        detail_data.update({
            "price": price,
            "version": "V1",
            "sample_rate": "48K",
            "category_name": category_name,
            "description": detail_data.get("description", "茶韵悠悠可音袅袅少御音介于少女与御姐之间既有少女清脆又具御姐沉稳圆润柔和年龄感适中清嗓咳嗽呢喃细语悄悄话 笑声 自带情绪感")
        })
        
        # 如果本地已下载，显示已下载样式
        # 尝试获取主窗口引用
        main_window = None
        parent = self.parent()
        while parent:
            if hasattr(parent, 'pages'):
                main_window = parent
                break
            parent = parent.parent()
        
        self.detail_page = ModelDetailPage(detail_data, is_purchased=is_downloaded, home_page=self, main_window=main_window, model_image=model_image)
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

