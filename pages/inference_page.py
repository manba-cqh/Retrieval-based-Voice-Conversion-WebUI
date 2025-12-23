"""推理页面（实时变声界面）"""
import os
import sys
import json
import shutil
import time
import threading
from multiprocessing import Queue, cpu_count

import numpy as np
import librosa
import sounddevice as sd
import torch
import torch.nn.functional as F
import torchaudio.transforms as tat

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QSlider, QComboBox, QRadioButton, QButtonGroup, QGroupBox, QFrame,
    QFileDialog, QMessageBox, QSizePolicy, QScrollArea
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont, QResizeEvent, QPixmap

# 导入工具函数
from .tools import create_slider
from api.auth import auth_api

# 导入项目模块（延迟导入，避免阻塞）
sys.path.append(os.getcwd())
# 注意：rtrvc 模块会在需要时动态导入，避免 multiprocessing.Manager 在导入时的阻塞


# 全局变量
flag_vc = False


class AdaptiveLabel(QLabel):
    """自适应字体大小的QLabel"""
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self._base_font_size = 0.4  # 字体大小相对于高度的比例
        self._min_font_size = 12
        self._max_font_size = 200
        # 延迟更新字体大小，等待widget显示后
        QTimer.singleShot(0, self.update_font_size)
    
    def resizeEvent(self, event: QResizeEvent):
        """重写resizeEvent，根据大小调整字体"""
        super().resizeEvent(event)
        self.update_font_size()
    
    def showEvent(self, event):
        """显示时更新字体大小"""
        super().showEvent(event)
        self.update_font_size()
    
    def update_font_size(self):
        """根据当前大小更新字体大小"""
        size = self.size()
        if size.width() <= 0 or size.height() <= 0:
            return
        
        # 使用高度和宽度中的较小值来计算字体大小
        min_dimension = min(size.width(), size.height())
        font_size = int(min_dimension * self._base_font_size)
        font_size = max(self._min_font_size, min(font_size, self._max_font_size))
        
        font = self.font()
        font.setPointSize(font_size)
        font.setBold(True)
        self.setFont(font)


class SquareFrame(QFrame):
    """保持正方形比例的QFrame，高度占满，宽度等于高度"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self._updating_size = False
        self._last_height = 0
    
    def resizeEvent(self, event: QResizeEvent):
        """重写resizeEvent，使宽度等于高度（保持正方形）"""
        if self._updating_size:
            return super().resizeEvent(event)
        
        size = event.size()
        height = size.height()
        
        # 如果高度变化了，更新宽度限制
        if height != self._last_height:
            self._updating_size = True
            # 设置最大和最小宽度为高度值，这样布局管理器会将宽度设置为高度
            self.setMaximumWidth(height)
            self.setMinimumWidth(height)
            self._last_height = height
            self._updating_size = False
        
        super().resizeEvent(event)


def phase_vocoder(a, b, fade_out, fade_in):
    """相位声码器"""
    window = torch.sqrt(fade_out * fade_in)
    fa = torch.fft.rfft(a * window)
    fb = torch.fft.rfft(b * window)
    absab = torch.abs(fa) + torch.abs(fb)
    n = a.shape[0]
    if n % 2 == 0:
        absab[1:-1] *= 2
    else:
        absab[1:] *= 2
    phia = torch.angle(fa)
    phib = torch.angle(fb)
    deltaphase = phib - phia
    deltaphase = deltaphase - 2 * np.pi * torch.floor(deltaphase / 2 / np.pi + 0.5)
    w = 2 * np.pi * torch.arange(n // 2 + 1).to(a) + deltaphase
    t = torch.arange(n).unsqueeze(-1).to(a) / n
    result = (
        a * (fade_out**2)
        + b * (fade_in**2)
        + torch.sum(absab * torch.cos(w * t + phia), -1) * window / n
    )
    return result


class ModelCard(QFrame):
    """模型卡片组件（用于推理页面）"""
    clicked = pyqtSignal(dict)  # 发送模型数据
    
    def __init__(self, model_data, parent=None):
        super().__init__(parent)
        self.model_data = model_data
        self.model_name = model_data.get("name", "未知")
        self.model_image = model_data.get("image", "")
        self.is_selected = False
        
        self.setup_ui()
    
    def setup_ui(self):
        """设置UI"""
        self.setStyleSheet("""
            QFrame {
                background-color: #252525;
                border: 1px solid #3d3d3d;
                border-radius: 1px;
            }
            QFrame:hover {
                border: 2px solid #8b5cf6;
                background-color: #2d2d2d;
            }
        """)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        
        # 头像区域
        image_label = QLabel()
        image_label.setFixedSize(100, 100)
        image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        image_label.setStyleSheet("""
            QLabel {
                background-color: #1e1e1e;
                border-radius: 0px;
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
                        100, 100, 
                        Qt.AspectRatioMode.KeepAspectRatio, 
                        Qt.TransformationMode.SmoothTransformation
                    )
                    image_label.setPixmap(scaled_pixmap)
                else:
                    # 图片加载失败，显示占位符
                    placeholder = self.model_name[0] if self.model_name else "?"
                    image_label.setText(f"<div style='font-size: 64px; color: #8b5cf6;'>{placeholder}</div>")
            except Exception as e:
                # 图片加载出错，显示占位符
                print(f"加载图片失败 {self.model_image}: {e}")
                placeholder = self.model_name[0] if self.model_name else "?"
                image_label.setText(f"<div style='font-size: 64px; color: #8b5cf6;'>{placeholder}</div>")
        else:
            # 根据名称生成占位符
            placeholder = self.model_name[0] if self.model_name else "?"
            image_label.setText(f"<div style='font-size: 64px; color: #8b5cf6;'>{placeholder}</div>")
        
        image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(image_label)
        
        right_layout = QVBoxLayout()
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)
        # 名称
        name_label = QLabel(self.model_name)
        name_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        name_label.setStyleSheet("font-size: 26px; font-weight: bold; padding: 0px 3px; border: none; background-color: transparent;")
        right_layout.addWidget(name_label)
        content_label = QLabel(self.model_data.get("description", ""))
        content_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        content_label.setWordWrap(True)
        content_label.setStyleSheet("font-size: 12px; padding: 0px; border: none; background-color: transparent; padding: 0px 5px;")
        right_layout.addWidget(content_label)
        layout.addLayout(right_layout)
    
    def mousePressEvent(self, event):
        """鼠标点击事件"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.model_data)
        super().mousePressEvent(event)
    
    def set_selected(self, selected):
        """设置选中状态"""
        self.is_selected = selected
        if selected:
            self.setStyleSheet("""
                QFrame {
                    background-color: #2d2d2d;
                    border: 2px solid #8b5cf6;
                    border-radius: 8px;
                }
            """)
        else:
            self.setStyleSheet("""
                QFrame {
                    background-color: #252525;
                    border: 2px solid #3d3d3d;
                    border-radius: 8px;
                }
                QFrame:hover {
                    border: 2px solid #8b5cf6;
                    background-color: #2d2d2d;
                }
            """)


class GUIConfig:
    """GUI配置类"""
    def __init__(self, n_cpu=4):
        self.pth_path: str = ""
        self.index_path: str = ""
        self.pitch: int = 0
        self.formant: float = 0.0
        self.sr_type: str = "sr_model"
        self.block_time: float = 0.25
        self.threhold: int = -60
        self.crossfade_time: float = 0.05
        self.extra_time: float = 2.5
        self.I_noise_reduce: bool = False
        self.O_noise_reduce: bool = False
        self.use_pv: bool = False
        self.rms_mix_rate: float = 0.0
        self.index_rate: float = 0.0
        self.n_cpu: int = min(n_cpu, 4)
        self.f0method: str = "fcpe"
        self.sg_hostapi: str = ""
        self.wasapi_exclusive: bool = False
        self.sg_input_device: str = ""
        self.sg_output_device: str = ""
        self.samplerate: int = 40000
        self.channels: int = 1


class InferencePage(QWidget):
    """推理页面"""
    
    def __init__(self):
        super().__init__()
        # 样式由全局样式表提供
        
        # 延迟导入项目模块（避免阻塞）
        from configs.config import Config
        
        # 初始化配置
        self.n_cpu = min(cpu_count(), 8)
        self.gui_config = GUIConfig(self.n_cpu)
        self.config = Config()
        
        # 延迟导入 rtrvc（避免 multiprocessing.Manager 阻塞）
        self.rvc_module = None
        self.function = "vc"
        self.delay_time = 0
        
        # 音频设备相关
        self.hostapis = None
        self.input_devices = None
        self.output_devices = None
        self.input_devices_indices = None
        self.output_devices_indices = None
        
        # RVC相关
        self.rvc = None
        self.rvc_module = None  # 延迟导入的模块
        self.stream = None
        self.flag_vc = False
        
        # 音频处理相关
        self.zc = 0
        self.block_frame = 0
        self.block_frame_16k = 0
        self.crossfade_frame = 0
        self.sola_buffer_frame = 0
        self.sola_search_frame = 0
        self.extra_frame = 0
        self.input_wav = None
        self.input_wav_denoise = None
        self.input_wav_res = None
        self.rms_buffer = None
        self.sola_buffer = None
        self.nr_buffer = None
        self.output_buffer = None
        self.skip_head = 0
        self.return_length = 0
        self.fade_in_window = None
        self.fade_out_window = None
        self.resampler = None
        self.resampler2 = None
        self.tg = None
        
        # 控件引用
        self.pitch_slider = None
        self.formant_slider = None
        self.delay_slider = None
        self.input_device_combo = None
        self.output_device_combo = None
        
        # 模型列表相关
        self.models_data = []
        self.current_model = None
        self.model_cards = []
        self.preview_image_label = None
        self.preview_overlay = None  # 预览区域底部蒙层
        
        # 初始化设备列表
        self.update_devices()
        
        # 加载配置
        self.load_config()
        
        # 初始化UI
        self.init_ui()
        
        # 加载模型列表
        self.load_models()

        # 如果有模型，自动选中第一个，显示蒙层
        if self.models_data:
            self.on_model_selected(self.models_data[0])
        
        # 定时器更新推理时间
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_inference_time)
        self.inference_start_time = 0
    
    def init_ui(self):
        """初始化UI"""
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)

        # 左侧：模型列表
        model_list_panel = self.create_model_list_panel()

        right_layout = QVBoxLayout()
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(12)

        main_layout.addWidget(model_list_panel, 1)
        main_layout.addLayout(right_layout, 2)
        
        # 右侧区域
        # 上侧区域
        top_container = QWidget()
        top_layout = QHBoxLayout(top_container)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(12)
        # 左上：大预览区域
        large_preview = self.create_preview_area()
        top_layout.addWidget(large_preview, 1)
        # 右上：音频设备和控制
        control_panel = self.create_audio_device_panel()
        top_layout.addWidget(control_panel, 1)
        right_layout.addWidget(top_container, 2)
        
        # 下侧区域：音频控制
        bottom_panel = self.create_control_panel()
        right_layout.addWidget(bottom_panel, 1)
    
    def create_preview_area(self):
        """创建预览区域（高度占满，宽度等于高度，保持正方形）"""
        preview = SquareFrame()
        preview.setStyleSheet("""
            QFrame {
                background-color: #000000;
                border: 2px solid #3d3d3d;
                border-radius: 12px;
            }
        """)
        
        # 设置大小策略，让高度可以扩展，宽度根据高度调整
        preview.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
        
        # 使用相对定位的布局，以便蒙层可以覆盖在内容上方
        preview.setLayout(QVBoxLayout())
        preview.layout().setContentsMargins(0, 0, 0, 0)
        preview.layout().setSpacing(0)
        
        # 内容区域（图片或文本）
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        
        # 图片标签（用于显示模型图片）
        image_layout = QVBoxLayout()
        image_layout.setContentsMargins(0, 0, 0, 0)
        image_layout.setSpacing(0)
        image_label = AdaptiveLabel()
        image_label.setLayout(image_layout)
        image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        image_label.setStyleSheet("""
            QLabel {
                background-color: transparent;
                border: none;
            }
        """)
        image_label.setScaledContents(True)  # 允许自动缩放，保持宽高比
        content_layout.addWidget(image_label)
        self.preview_image_label = image_label
        
        preview.layout().addWidget(content_widget)
        
        # 底部蒙层（显示模型信息）
        overlay = QWidget(preview)
        overlay.setStyleSheet("""
            QWidget {
                background-color: rgba(0, 0, 0, 0.7);
                border: none;
                margin: 0;
                padding: 2px;
            }
        """)
        
        overlay_layout = QVBoxLayout(overlay)
        overlay_layout.setContentsMargins(0, 0, 0, 0)
        overlay_layout.setSpacing(6)
        
        # 模型名称
        name_label = QLabel()
        name_label.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-size: 18px;
                font-weight: bold;
                border: none;
                background-color: transparent;
            }
        """)
        name_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        overlay_layout.addWidget(name_label)
        
        # 介绍/描述
        desc_label = QLabel()
        desc_label.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-size: 12px;
                border: none;
                background-color: transparent;
            }
        """)
        desc_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        desc_label.setWordWrap(True)
        overlay_layout.addWidget(desc_label)
        
        # 信息行（版本、采样率、类别）
        info_layout = QHBoxLayout()
        info_layout.setSpacing(12)
        
        version_label = QLabel()
        version_label.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-size: 11px;
                border: none;
                background-color: transparent;
            }
        """)
        info_layout.addWidget(version_label)
        
        sample_rate_label = QLabel()
        sample_rate_label.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-size: 11px;
                border: none;
                background-color: transparent;
            }
        """)
        info_layout.addWidget(sample_rate_label)
        
        category_label = QLabel()
        category_label.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-size: 11px;
                border: none;
                background-color: transparent;
            }
        """)
        info_layout.addWidget(category_label)
        
        info_layout.addStretch()
        overlay_layout.addLayout(info_layout)
        
        overlay_layout.addStretch()

        image_layout.addStretch()
        overlay.setFixedHeight(96)
        image_layout.addWidget(overlay)
        
        # 保存标签引用
        self.preview_overlay = overlay
        self.preview_overlay_name = name_label
        self.preview_overlay_desc = desc_label
        self.preview_overlay_version = version_label
        self.preview_overlay_sample_rate = sample_rate_label
        self.preview_overlay_category = category_label
        
        return preview
    
    def create_model_list_panel(self):
        """创建模型列表面板"""
        panel = QFrame()
        panel.setStyleSheet("""
            QFrame {
                background-color: #252525;
                border: 2px solid #3d3d3d;
                border-radius: 12px;
            }
        """)
        
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(12)
        
        # 标题
        title = QLabel("模型列表")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setStyleSheet("color: #ffffff; border: none; background-color: transparent;")
        layout.addWidget(title)
        
        # 滚动区域
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)  # 禁用水平滚动条
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: 2px solid #3d3d3d;
                border-radius: 4px;
                background-color: transparent;
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
        
        # 模型列表容器
        self.model_list_widget = QWidget()
        self.model_list_layout = QVBoxLayout(self.model_list_widget)
        self.model_list_layout.setContentsMargins(0, 0, 0, 0)
        self.model_list_layout.setSpacing(6)
        self.model_list_layout.addStretch()
        
        scroll_area.setWidget(self.model_list_widget)
        layout.addWidget(scroll_area)
        
        return panel
    
    def load_models(self):
        """从models目录加载模型列表（只返回用户可用的模型）"""
        models_dir = os.path.join(os.getcwd(), "models")
        self.models_data = []
        
        # 如果models目录不存在，创建它
        if not os.path.exists(models_dir):
            os.makedirs(models_dir, exist_ok=True)
            self.update_model_list()
            return
        
        # 获取用户可用的模型UUID列表
        available_model_uids = self._get_user_available_model_uids()
        
        # 扫描models目录下的所有子目录
        model_id = 1
        for item in os.listdir(models_dir):
            model_dir_path = os.path.join(models_dir, item)
            
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
            
            # 使用第一个找到的.pth文件（如果目录中有多个.pth文件，使用第一个）
            pth_path = os.path.join(model_dir_path, pth_files[0])
            
            # 使用第一个找到的index文件，如果没有则设为空字符串（如果目录中有多个.index文件，使用第一个）
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
            
            # 读取uid（支持uuid或uid字段）
            model_uid = model_info.get("uuid") or model_info.get("uid")
            
            # 获取分类信息（从json中读取，默认为"免费音色"，支持多个分类用分号分隔）
            category = model_info.get("category", "免费音色")
            categories = [cat.strip() for cat in category.split(";")]
            # 判断是否为免费音色
            is_free_model = "免费音色" in categories
            
            # 对于免费音色，只要本地存在就显示，不需要在用户的可用列表中
            # 对于非免费音色（官方音色等），必须同时在用户的可用列表中
            if not is_free_model:
                # 非免费音色，需要检查用户的可用模型列表
                if available_model_uids is None:
                    # 用户未登录或没有可用模型列表，不显示非免费音色
                    continue
                elif not model_uid or model_uid not in available_model_uids:
                    # 模型不在用户的可用列表中，跳过
                    continue
            
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
            
            model_data = {
                "id": str(model_id),
                "name": model_name,
                "image": model_image,
                "pth_path": pth_path,
                "index_path": index_path,
                "uid": model_uid,  # 添加uid字段
            }
            
            # 添加json中的其他信息（如果有）
            for key in ["description", "category", "version", "sample_rate"]:
                if key in model_info:
                    model_data[key] = model_info[key]
            
            self.models_data.append(model_data)
            model_id += 1
        
        # 按模型名称排序
        self.models_data.sort(key=lambda x: x.get("name", "").lower())
        
        self.update_model_list()
    
    def _get_user_available_model_uids(self):
        """
        获取用户可用的模型UUID列表
        
        Returns:
            可用模型UUID的集合（set），如果用户未登录或没有可用模型列表则返回None（不显示任何模型）
        """
        try:
            # 尝试从auth_api获取用户信息
            user_info = auth_api.user_info
            if not user_info:
                # 如果auth_api中没有，尝试从存储中加载
                from api.storage import token_storage
                user_info = token_storage.load_user_info()
            
            if not user_info:
                # 用户未登录，返回None表示不显示任何模型
                return None
            
            # 获取available_models字段
            available_models = user_info.get("available_models")
            if not available_models:
                # 如果没有available_models字段或为空，返回None表示不显示任何模型
                return None
            
            # 解析分号分隔的UUID列表
            uids = [uid.strip() for uid in available_models.split(";") if uid.strip()]
            if not uids:
                # 如果解析后列表为空，返回None表示不显示任何模型
                return None
            return set(uids)  # 返回集合以便快速查找
            
        except Exception as e:
            print(f"获取用户可用模型列表失败: {e}")
            # 出错时返回None，不显示任何模型
            return None
    
    def update_model_list(self):
        """更新模型列表显示"""
        # 清除现有卡片
        while self.model_list_layout.count():
            child = self.model_list_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        self.model_cards = []
        
        # 添加模型卡片
        for model_data in self.models_data:
            card = ModelCard(model_data)
            card.clicked.connect(self.on_model_selected)
            self.model_cards.append(card)
            self.model_list_layout.addWidget(card)
        self.model_list_layout.addStretch()
    
    def on_model_selected(self, model_data):
        """模型被选中"""
        # 更新选中状态
        for card in self.model_cards:
            card.set_selected(card.model_data["id"] == model_data["id"])
        
        # 更新当前模型
        self.current_model = model_data
        
        # 更新预览区域
        model_image = model_data.get("image", "")
        
        # 如果有图片，显示图片；否则显示文本
        if model_image and os.path.exists(model_image):
            pixmap = QPixmap(model_image)
            self.preview_image_label.setPixmap(pixmap)
        else:
            # 图片加载失败，显示文本
            self.preview_image_label.setText(model_data["name"])
        
        # 更新底部蒙层信息
        if self.preview_overlay:
            # 更新模型名称
            if self.preview_overlay_name:
                self.preview_overlay_name.setText(model_data.get("name", "未知"))
            
            # 更新介绍/描述
            if self.preview_overlay_desc:
                description = model_data.get("description", "")
                if description:
                    self.preview_overlay_desc.setText(f"介绍: {description}")
                else:
                    self.preview_overlay_desc.setText("")
            
            # 更新版本
            if self.preview_overlay_version:
                version = model_data.get("version", "V1")
                self.preview_overlay_version.setText(f"版本: {version}")
            
            # 更新采样率
            if self.preview_overlay_sample_rate:
                sample_rate = model_data.get("sample_rate", "48K")
                self.preview_overlay_sample_rate.setText(f"采样率: {sample_rate}")
            
            # 更新类别（如果包含多个分类，只显示第一个）
            if self.preview_overlay_category:
                category = model_data.get("category", "免费音色")
                # 如果包含多个分类（用分号分隔），只显示第一个
                if ";" in category:
                    category = category.split(";")[0].strip()
                self.preview_overlay_category.setText(f"类别: {category}")
        
        # 更新模型路径（如果存在）
        if "pth_path" in model_data and os.path.exists(model_data["pth_path"]):
            self.gui_config.pth_path = model_data["pth_path"]
        if "index_path" in model_data and os.path.exists(model_data["index_path"]):
            self.gui_config.index_path = model_data["index_path"]
        
        # 保存配置
        self.save_config()
    
    def create_control_panel(self):
        """创建控制面板"""
        panel = QFrame()
        panel.setStyleSheet("""
            QFrame {
                background-color: #252525;
                border: 2px solid #3d3d3d;
                border-radius: 12px;
            }
        """)
        
        layout = QHBoxLayout(panel)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(20)
        
        # 滑块和控制
        controls_layout = QVBoxLayout()
        controls_layout.setSpacing(8)
        
        # 音调滑块
        pitch_container, self.pitch_slider, pitch_value_label = create_slider(
            "音调", self.gui_config.pitch, -12, 12, self.gui_config.pitch
        )
        self.pitch_slider.valueChanged.connect(
            lambda val: self.on_pitch_changed(val, pitch_value_label)
        )
        controls_layout.addWidget(pitch_container)
        
        # 声音粗细滑块
        formant_container, self.formant_slider, formant_value_label = create_slider(
            "声音粗细", self.gui_config.formant, -2.0, 2.0, self.gui_config.formant, step=0.05
        )
        self.formant_slider.valueChanged.connect(
            lambda val: self.on_formant_changed(val, formant_value_label)
        )
        controls_layout.addWidget(formant_container)
        
        # 声音延迟滑块（对应block_time）
        delay_container, self.delay_slider, delay_value_label = create_slider(
            "声音延迟", self.gui_config.block_time, 0.02, 1.5, self.gui_config.block_time, step=0.01
        )
        self.delay_slider.valueChanged.connect(
            lambda val: self.on_delay_changed(val, delay_value_label)
        )
        controls_layout.addWidget(delay_container)
        
        # 音高算法选择
        algorithm_group = self.create_algorithm_group()
        controls_layout.addWidget(algorithm_group)
        
        # 保存预设按钮和刷新
        button_layout = QHBoxLayout()
        save_btn = QPushButton("保存预设")
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #8b5cf6;
                color: #ffffff;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #7c3aed;
            }
            QPushButton:pressed {
                background-color: #6d28d9;
            }
        """)
        save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        save_btn.clicked.connect(self.on_save_preset)
        
        refresh_btn = QPushButton("")
        refresh_btn.setFixedSize(40, 40)
        refresh_btn.setStyleSheet("border-image: url('res/刷新图标.png');")
        refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        refresh_btn.clicked.connect(self.on_refresh_devices)
        
        button_layout.addStretch()
        button_layout.addWidget(save_btn)
        button_layout.addWidget(refresh_btn)
        
        controls_layout.addLayout(button_layout)
        controls_layout.addStretch()
        
        layout.addLayout(controls_layout)
        
        return panel
    
    
    def create_algorithm_group(self):
        """创建音高算法选择组"""
        group = QGroupBox("音高算法:")
        # 样式由全局样式表提供
        
        layout = QHBoxLayout(group)
        layout.setSpacing(8)
        
        self.algorithm_group = QButtonGroup()
        # 算法映射：显示文本 -> (实际值, 中文描述)
        algorithms = [
            ("pm", "pm", "速度快，效果一般"),
            ("harvest", "harvest", "速度慢，效果好"),
            ("crepe", "crepe", "占用高，效果好"),
            ("rmvpe", "rmvpe", "占用适中，效果好"),
            ("fcpe (推荐)", "fcpe", "占用低，效果好")
        ]
        
        # 创建反向映射：中文描述 -> 实际值（用于保存配置）
        self.algorithm_value_map = {}
        for text, value, desc in algorithms:
            self.algorithm_value_map[desc] = value
        
        for i, (text, value, desc) in enumerate(algorithms):
            # 显示文本使用中文描述
            radio = QRadioButton(desc)
            # 样式由全局样式表提供
            if value == self.gui_config.f0method:  # 根据配置设置默认选中
                radio.setChecked(True)
            elif value == "fcpe" and self.gui_config.f0method not in ["pm", "harvest", "crepe", "rmvpe"]:
                radio.setChecked(True)
            self.algorithm_group.addButton(radio, i)
            # 传递实际值（value）给回调函数
            radio.clicked.connect(lambda checked, v=value: self.on_algorithm_changed(v))
            layout.addWidget(radio)
        
        return group
    
    def create_audio_device_panel(self):
        """创建音频设备面板"""
        panel = QFrame()
        panel.setStyleSheet("""
            QFrame {
                background-color: #252525;
                border: 2px solid #3d3d3d;
                border-radius: 12px;
            }
        """)
        
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)
        
        # 标题和推理时间
        header_layout = QHBoxLayout()
        title = QLabel("音频设备")
        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setStyleSheet("color: #ffffff; border: none; background-color: transparent;")
        
        time_label = QLabel("推理时间(ms):")
        time_label.setStyleSheet("color: #ffffff; font-size: 12px; border: none; background-color: transparent;")
        self.time_value = QLabel("0")
        self.time_value.setStyleSheet("color: #8b5cf6; font-size: 12px; font-weight: bold; border: none; background-color: transparent;")
        
        header_layout.addWidget(title)
        header_layout.addStretch()
        header_layout.addWidget(time_label)
        header_layout.addWidget(self.time_value)
        
        layout.addLayout(header_layout)

        # 设备协议
        protocol_group, self.protocol_combo = self.create_device_group(
            "设备协议", self.hostapis, self.gui_config.sg_hostapi
        )
        layout.addWidget(protocol_group)
        
        # 输入设备
        input_group, self.input_device_combo = self.create_device_group(
            "输入设备", self.input_devices, self.gui_config.sg_input_device
        )
        layout.addWidget(input_group)
        
        # 输出设备
        output_group, self.output_device_combo = self.create_device_group(
            "输出设备", self.output_devices, self.gui_config.sg_output_device
        )
        layout.addWidget(output_group)
        
        layout.addStretch()
        
        # 控制按钮
        button_layout = QHBoxLayout()
        button_layout.setSpacing(15)
        
        self.start_btn = QPushButton("开始变声")
        self.start_btn.setStyleSheet("""
            QPushButton {
                background-color: #8b5cf6;
                color: #ffffff;
                border: none;
                border-radius: 8px;
                padding: 15px 30px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #7c3aed;
            }
            QPushButton:pressed {
                background-color: #6d28d9;
            }
        """)
        self.start_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.start_btn.clicked.connect(self.on_start_vc)
        
        self.stop_btn = QPushButton("停止变声")
        # 基础样式由全局样式表提供，只设置特殊样式
        self.stop_btn.setStyleSheet("""
            QPushButton {
                border-radius: 8px;
                padding: 15px 30px;
                font-size: 16px;
                font-weight: bold;
            }
        """)
        self.stop_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.stop_btn.clicked.connect(self.on_stop_vc)
        self.stop_btn.setEnabled(False)
        
        button_layout.addWidget(self.start_btn)
        button_layout.addWidget(self.stop_btn)
        
        layout.addLayout(button_layout)
        
        return panel
    
    def create_device_group(self, label_text, device_list, default_device):
        """创建设备选择组，返回容器和下拉框"""
        container = QFrame()
        container.setStyleSheet("QFrame { background-color: #252525; border: none; }")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        label = QLabel(label_text)
        label.setStyleSheet("color: #ffffff; font-size: 14px; border: none; background-color: transparent;")
        layout.addWidget(label)
        
        combo = QComboBox()
        if device_list:
            combo.addItems(device_list)
            if default_device in device_list:
                combo.setCurrentText(default_device)
        else:
            combo.addItem("未找到设备")
        # 样式由全局样式表提供
        combo.setCursor(Qt.CursorShape.PointingHandCursor)
        layout.addWidget(combo)
        
        return container, combo
    
    def load_config(self):
        """加载配置文件"""
        try:
            if not os.path.exists("configs/inuse/config.json"):
                if os.path.exists("configs/config.json"):
                    shutil.copy("configs/config.json", "configs/inuse/config.json")
                else:
                    return
            
            with open("configs/inuse/config.json", "r", encoding="utf-8") as f:
                data = json.load(f)
                
            # 更新配置
            self.gui_config.pth_path = data.get("pth_path", "")
            self.gui_config.index_path = data.get("index_path", "")
            self.gui_config.pitch = data.get("pitch", 0)
            self.gui_config.formant = data.get("formant", 0.0)
            self.gui_config.block_time = data.get("block_time", 0.25)
            self.gui_config.f0method = data.get("f0method", "fcpe")
            self.gui_config.sg_input_device = data.get("sg_input_device", "")
            self.gui_config.sg_output_device = data.get("sg_output_device", "")
            
        except Exception as e:
            print(f"加载配置失败: {e}")
    
    def save_config(self):
        """保存配置文件"""
        try:
            os.makedirs("configs/inuse", exist_ok=True)
            data = {
                "pth_path": self.gui_config.pth_path,
                "index_path": self.gui_config.index_path,
                "pitch": self.gui_config.pitch,
                "formant": self.gui_config.formant,
                "block_time": self.gui_config.block_time,
                "f0method": self.gui_config.f0method,
                "sg_input_device": self.gui_config.sg_input_device,
                "sg_output_device": self.gui_config.sg_output_device,
            }
            with open("configs/inuse/config.json", "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"保存配置失败: {e}")
    
    def update_devices(self, hostapi_name=None):
        """更新音频设备列表"""
        global flag_vc
        flag_vc = False
        try:
            sd._terminate()
            sd._initialize()
            devices = sd.query_devices()
            hostapis = sd.query_hostapis()
            
            for hostapi in hostapis:
                for device_idx in hostapi["devices"]:
                    devices[device_idx]["hostapi_name"] = hostapi["name"]
            
            self.hostapis = [hostapi["name"] for hostapi in hostapis]
            
            if hostapi_name and hostapi_name in self.hostapis:
                selected_hostapi = hostapi_name
            else:
                selected_hostapi = self.hostapis[0] if self.hostapis else None
            
            if selected_hostapi:
                self.input_devices = [
                    d["name"]
                    for d in devices
                    if d["max_input_channels"] > 0 and d["hostapi_name"] == selected_hostapi
                ]
                self.output_devices = [
                    d["name"]
                    for d in devices
                    if d["max_output_channels"] > 0 and d["hostapi_name"] == selected_hostapi
                ]
                self.input_devices_indices = [
                    d["index"] if "index" in d else d["name"]
                    for d in devices
                    if d["max_input_channels"] > 0 and d["hostapi_name"] == selected_hostapi
                ]
                self.output_devices_indices = [
                    d["index"] if "index" in d else d["name"]
                    for d in devices
                    if d["max_output_channels"] > 0 and d["hostapi_name"] == selected_hostapi
                ]
        except Exception as e:
            print(f"更新设备列表失败: {e}")
            self.input_devices = []
            self.output_devices = []
    
    def set_devices(self, input_device, output_device):
        """设置音频设备"""
        try:
            if input_device in self.input_devices:
                input_idx = self.input_devices.index(input_device)
                sd.default.device[0] = self.input_devices_indices[input_idx]
            
            if output_device in self.output_devices:
                output_idx = self.output_devices.index(output_device)
                sd.default.device[1] = self.output_devices_indices[output_idx]
            
            print(f"输入设备: {sd.default.device[0]} - {input_device}")
            print(f"输出设备: {sd.default.device[1]} - {output_device}")
        except Exception as e:
            print(f"设置设备失败: {e}")
    
    def get_device_samplerate(self):
        """获取设备采样率"""
        try:
            return int(sd.query_devices(device=sd.default.device[0])["default_samplerate"])
        except:
            return 40000
    
    def get_device_channels(self):
        """获取设备通道数"""
        try:
            max_input_channels = sd.query_devices(device=sd.default.device[0])["max_input_channels"]
            max_output_channels = sd.query_devices(device=sd.default.device[1])["max_output_channels"]
            return min(max_input_channels, max_output_channels, 2)
        except:
            return 1
    
    def on_pitch_changed(self, value, value_label):
        """音调改变事件"""
        self.gui_config.pitch = value
        value_label.setText(str(value))
        if hasattr(self, "rvc") and self.rvc is not None:
            self.rvc.change_key(value)
    
    def on_formant_changed(self, value, value_label):
        """声音粗细改变事件"""
        actual_val = value * 0.05
        self.gui_config.formant = actual_val
        value_label.setText(f"{actual_val:.2f}")
        if hasattr(self, "rvc") and self.rvc is not None:
            self.rvc.change_formant(actual_val)
    
    def on_delay_changed(self, value, value_label):
        """延迟改变事件"""
        actual_val = value * 0.01
        self.gui_config.block_time = actual_val
        value_label.setText(f"{actual_val:.2f}")
    
    def on_algorithm_changed(self, algorithm):
        """音高算法改变事件"""
        self.gui_config.f0method = algorithm
    
    def on_save_preset(self):
        """保存预设"""
        self.save_config()
        QMessageBox.information(self, "提示", "预设已保存")
    
    def on_refresh_devices(self):
        """刷新设备列表"""
        self.update_devices()
        if self.input_device_combo:
            self.input_device_combo.clear()
            if self.input_devices:
                self.input_device_combo.addItems(self.input_devices)
                if self.gui_config.sg_input_device in self.input_devices:
                    self.input_device_combo.setCurrentText(self.gui_config.sg_input_device)
        if self.output_device_combo:
            self.output_device_combo.clear()
            if self.output_devices:
                self.output_device_combo.addItems(self.output_devices)
                if self.gui_config.sg_output_device in self.output_devices:
                    self.output_device_combo.setCurrentText(self.gui_config.sg_output_device)
        QMessageBox.information(self, "提示", "设备列表已刷新")
    
    def on_start_vc(self):
        """开始变声"""
        global flag_vc
        
        # 检查模型文件
        if not self.gui_config.pth_path or not os.path.exists(self.gui_config.pth_path):
            QMessageBox.warning(self, "警告", "请先选择.pth模型文件")
            # 打开文件选择对话框
            file_path, _ = QFileDialog.getOpenFileName(
                self, "选择.pth文件", "assets/weights", "PTH Files (*.pth)"
            )
            if file_path:
                self.gui_config.pth_path = file_path
            else:
                return
        
        if not self.gui_config.index_path or not os.path.exists(self.gui_config.index_path):
            QMessageBox.warning(self, "警告", "请先选择.index索引文件")
            # 打开文件选择对话框
            file_path, _ = QFileDialog.getOpenFileName(
                self, "选择.index文件", "logs", "Index Files (*.index)"
            )
            if file_path:
                self.gui_config.index_path = file_path
            else:
                return
        
        # 检查路径中是否有中文
        import re
        pattern = re.compile("[^\x00-\x7F]+")
        if pattern.findall(self.gui_config.pth_path):
            QMessageBox.warning(self, "警告", "pth文件路径不可包含中文")
            return
        if pattern.findall(self.gui_config.index_path):
            QMessageBox.warning(self, "警告", "index文件路径不可包含中文")
            return
        
        if flag_vc:
            return
        
        try:
            # 设置设备
            if self.input_device_combo and self.output_device_combo:
                input_device = self.input_device_combo.currentText()
                output_device = self.output_device_combo.currentText()
                self.set_devices(input_device, output_device)
                self.gui_config.sg_input_device = input_device
                self.gui_config.sg_output_device = output_device
            
            # 延迟导入 rtrvc 模块（避免导入时阻塞）
            if self.rvc_module is None:
                from infer.lib import rtrvc as rvc_for_realtime
                self.rvc_module = rvc_for_realtime
            else:
                rvc_for_realtime = self.rvc_module
            
            # 初始化RVC
            torch.cuda.empty_cache()
            # 创建队列（如果需要多进程处理）
            inp_q = Queue()
            opt_q = Queue()
            self.rvc = rvc_for_realtime.RVC(
                self.gui_config.pitch,
                self.gui_config.formant,
                self.gui_config.pth_path,
                self.gui_config.index_path,
                self.gui_config.index_rate,
                self.gui_config.n_cpu,
                inp_q,
                opt_q,
                self.config,
                self.rvc if hasattr(self, "rvc") and self.rvc is not None else None,
            )
            
            # 设置采样率
            self.gui_config.samplerate = (
                self.rvc.tgt_sr
                if self.gui_config.sr_type == "sr_model"
                else self.get_device_samplerate()
            )
            self.gui_config.channels = self.get_device_channels()
            
            # 初始化音频处理参数
            self.zc = self.gui_config.samplerate // 100
            self.block_frame = int(
                np.round(self.gui_config.block_time * self.gui_config.samplerate / self.zc)
            ) * self.zc
            self.block_frame_16k = 160 * self.block_frame // self.zc
            self.crossfade_frame = int(
                np.round(self.gui_config.crossfade_time * self.gui_config.samplerate / self.zc)
            ) * self.zc
            self.sola_buffer_frame = min(self.crossfade_frame, 4 * self.zc)
            self.sola_search_frame = self.zc
            self.extra_frame = int(
                np.round(self.gui_config.extra_time * self.gui_config.samplerate / self.zc)
            ) * self.zc
            
            # 初始化音频缓冲区
            self.input_wav = torch.zeros(
                self.extra_frame + self.crossfade_frame + self.sola_search_frame + self.block_frame,
                device=self.config.device,
                dtype=torch.float32,
            )
            self.input_wav_denoise = self.input_wav.clone()
            self.input_wav_res = torch.zeros(
                160 * self.input_wav.shape[0] // self.zc,
                device=self.config.device,
                dtype=torch.float32,
            )
            self.rms_buffer = np.zeros(4 * self.zc, dtype="float32")
            self.sola_buffer = torch.zeros(
                self.sola_buffer_frame, device=self.config.device, dtype=torch.float32
            )
            self.nr_buffer = self.sola_buffer.clone()
            self.output_buffer = self.input_wav.clone()
            self.skip_head = self.extra_frame // self.zc
            self.return_length = (
                self.block_frame + self.sola_buffer_frame + self.sola_search_frame
            ) // self.zc
            
            # 初始化淡入淡出窗口
            self.fade_in_window = (
                torch.sin(
                    0.5 * np.pi * torch.linspace(
                        0.0, 1.0, steps=self.sola_buffer_frame, device=self.config.device, dtype=torch.float32
                    )
                ) ** 2
            )
            self.fade_out_window = 1 - self.fade_in_window
            
            # 初始化重采样器
            self.resampler = tat.Resample(
                orig_freq=self.gui_config.samplerate,
                new_freq=16000,
                dtype=torch.float32,
            ).to(self.config.device)
            
            if self.rvc.tgt_sr != self.gui_config.samplerate:
                self.resampler2 = tat.Resample(
                    orig_freq=self.rvc.tgt_sr,
                    new_freq=self.gui_config.samplerate,
                    dtype=torch.float32,
                ).to(self.config.device)
            else:
                self.resampler2 = None
            
            # 初始化降噪器（延迟导入）
            from tools.torchgate import TorchGate
            self.tg = TorchGate(
                sr=self.gui_config.samplerate, n_fft=4 * self.zc, prop_decrease=0.9
            ).to(self.config.device)
            
            # 启动音频流
            self.start_stream()
            
            # 更新UI状态
            self.start_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)
            flag_vc = True
            self.flag_vc = True
            self.inference_start_time = time.perf_counter()
            self.timer.start(100)  # 每100ms更新一次
            
            # 保存配置
            self.save_config()
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"启动变声失败: {str(e)}")
            import traceback
            traceback.print_exc()
    
    def on_stop_vc(self):
        """停止变声"""
        global flag_vc
        self.stop_stream()
        flag_vc = False
        self.flag_vc = False
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.timer.stop()
        self.time_value.setText("0")
    
    def start_stream(self):
        """启动音频流"""
        global flag_vc
        if not flag_vc:
            flag_vc = True
            extra_settings = None
            if "WASAPI" in self.gui_config.sg_hostapi and self.gui_config.wasapi_exclusive:
                extra_settings = sd.WasapiSettings(exclusive=True)
            
            self.stream = sd.Stream(
                callback=self.audio_callback,
                blocksize=self.block_frame,
                samplerate=self.gui_config.samplerate,
                channels=self.gui_config.channels,
                dtype="float32",
                extra_settings=extra_settings,
            )
            self.stream.start()
    
    def stop_stream(self):
        """停止音频流"""
        global flag_vc
        if flag_vc:
            flag_vc = False
            if self.stream is not None:
                try:
                    self.stream.abort()
                    self.stream.close()
                except:
                    pass
                self.stream = None
    
    def audio_callback(self, indata, outdata, frames, time_info, status):
        """音频处理回调函数"""
        global flag_vc
        if not flag_vc:
            return
        
        start_time = time.perf_counter()
        
        try:
            # 转换为单声道
            indata_mono = librosa.to_mono(indata.T)
            
            # 响应阈值处理
            if self.gui_config.threhold > -60:
                indata_mono = np.append(self.rms_buffer, indata_mono)
                rms = librosa.feature.rms(
                    y=indata_mono, frame_length=4 * self.zc, hop_length=self.zc
                )[:, 2:]
                self.rms_buffer[:] = indata_mono[-4 * self.zc:]
                indata_mono = indata_mono[2 * self.zc - self.zc // 2:]
                db_threhold = (
                    librosa.amplitude_to_db(rms, ref=1.0)[0] < self.gui_config.threhold
                )
                for i in range(db_threhold.shape[0]):
                    if db_threhold[i]:
                        indata_mono[i * self.zc : (i + 1) * self.zc] = 0
                indata_mono = indata_mono[self.zc // 2:]
            
            # 更新输入缓冲区
            self.input_wav[:-self.block_frame] = self.input_wav[self.block_frame:].clone()
            self.input_wav[-indata_mono.shape[0]:] = torch.from_numpy(indata_mono).to(
                self.config.device
            )
            
            # 更新重采样缓冲区
            self.input_wav_res[:-self.block_frame_16k] = self.input_wav_res[
                self.block_frame_16k:
            ].clone()
            
            # 输入降噪和重采样
            if self.gui_config.I_noise_reduce:
                self.input_wav_denoise[:-self.block_frame] = self.input_wav_denoise[
                    self.block_frame:
                ].clone()
                input_wav = self.input_wav[-self.sola_buffer_frame - self.block_frame:]
                input_wav = self.tg(input_wav.unsqueeze(0), self.input_wav.unsqueeze(0)).squeeze(0)
                input_wav[:self.sola_buffer_frame] *= self.fade_in_window
                input_wav[:self.sola_buffer_frame] += self.nr_buffer * self.fade_out_window
                self.input_wav_denoise[-self.block_frame:] = input_wav[:self.block_frame]
                self.nr_buffer[:] = input_wav[self.block_frame:]
                self.input_wav_res[-self.block_frame_16k - 160:] = self.resampler(
                    self.input_wav_denoise[-self.block_frame - 2 * self.zc:]
                )[160:]
            else:
                self.input_wav_res[-160 * (indata_mono.shape[0] // self.zc + 1):] = (
                    self.resampler(self.input_wav[-indata_mono.shape[0] - 2 * self.zc:])[160:]
                )
            
            # 推理
            if self.function == "vc" and self.rvc is not None:
                infer_wav = self.rvc.infer(
                    self.input_wav_res,
                    self.block_frame_16k,
                    self.skip_head,
                    self.return_length,
                    self.gui_config.f0method,
                )
                if self.resampler2 is not None:
                    infer_wav = self.resampler2(infer_wav)
            elif self.gui_config.I_noise_reduce:
                infer_wav = self.input_wav_denoise[self.extra_frame:].clone()
            else:
                infer_wav = self.input_wav[self.extra_frame:].clone()
            
            # 输出降噪
            if self.gui_config.O_noise_reduce and self.function == "vc":
                self.output_buffer[:-self.block_frame] = self.output_buffer[
                    self.block_frame:
                ].clone()
                self.output_buffer[-self.block_frame:] = infer_wav[-self.block_frame:]
                infer_wav = self.tg(
                    infer_wav.unsqueeze(0), self.output_buffer.unsqueeze(0)
                ).squeeze(0)
            
            # 响度混合
            if self.gui_config.rms_mix_rate < 1 and self.function == "vc":
                if self.gui_config.I_noise_reduce:
                    input_wav = self.input_wav_denoise[self.extra_frame:]
                else:
                    input_wav = self.input_wav[self.extra_frame:]
                rms1 = librosa.feature.rms(
                    y=input_wav[:infer_wav.shape[0]].cpu().numpy(),
                    frame_length=4 * self.zc,
                    hop_length=self.zc,
                )
                rms1 = torch.from_numpy(rms1).to(self.config.device)
                rms1 = F.interpolate(
                    rms1.unsqueeze(0),
                    size=infer_wav.shape[0] + 1,
                    mode="linear",
                    align_corners=True,
                )[0, 0, :-1]
                rms2 = librosa.feature.rms(
                    y=infer_wav[:].cpu().numpy(),
                    frame_length=4 * self.zc,
                    hop_length=self.zc,
                )
                rms2 = torch.from_numpy(rms2).to(self.config.device)
                rms2 = F.interpolate(
                    rms2.unsqueeze(0),
                    size=infer_wav.shape[0] + 1,
                    mode="linear",
                    align_corners=True,
                )[0, 0, :-1]
                rms2 = torch.max(rms2, torch.zeros_like(rms2) + 1e-3)
                infer_wav *= torch.pow(
                    rms1 / rms2, torch.tensor(1 - self.gui_config.rms_mix_rate)
                )
            
            # SOLA算法
            conv_input = infer_wav[
                None, None, :self.sola_buffer_frame + self.sola_search_frame
            ]
            cor_nom = F.conv1d(conv_input, self.sola_buffer[None, None, :])
            cor_den = torch.sqrt(
                F.conv1d(
                    conv_input**2,
                    torch.ones(1, 1, self.sola_buffer_frame, device=self.config.device),
                ) + 1e-8
            )
            if sys.platform == "darwin":
                _, sola_offset = torch.max(cor_nom[0, 0] / cor_den[0, 0])
                sola_offset = sola_offset.item()
            else:
                sola_offset = torch.argmax(cor_nom[0, 0] / cor_den[0, 0])
            
            infer_wav = infer_wav[sola_offset:]
            
            # 淡入淡出处理
            if "privateuseone" in str(self.config.device) or not self.gui_config.use_pv:
                infer_wav[:self.sola_buffer_frame] *= self.fade_in_window
                infer_wav[:self.sola_buffer_frame] += self.sola_buffer * self.fade_out_window
            else:
                # 使用相位声码器
                infer_wav[:self.sola_buffer_frame] = phase_vocoder(
                    self.sola_buffer,
                    infer_wav[:self.sola_buffer_frame],
                    self.fade_out_window,
                    self.fade_in_window,
                )
            
            self.sola_buffer[:] = infer_wav[
                self.block_frame : self.block_frame + self.sola_buffer_frame
            ]
            
            # 输出
            outdata[:] = (
                infer_wav[:self.block_frame]
                .repeat(self.gui_config.channels, 1)
                .t()
                .cpu()
                .numpy()
            )
            
            # 更新推理时间
            total_time = time.perf_counter() - start_time
            if flag_vc:
                self.time_value.setText(f"{int(total_time * 1000)}")
        
        except Exception as e:
            print(f"音频处理错误: {e}")
            import traceback
            traceback.print_exc()
            outdata[:] = 0
    
    def update_inference_time(self):
        """更新推理时间显示"""
        if self.flag_vc:
            elapsed = time.perf_counter() - self.inference_start_time
            # 这里可以显示总运行时间，如果需要的话
            pass
