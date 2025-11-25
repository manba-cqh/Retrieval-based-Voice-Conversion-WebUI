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
    QFileDialog, QMessageBox, QSizePolicy
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QResizeEvent

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
        self.setStyleSheet("background-color: #1e1e1e;")
        
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
        
        # 初始化设备列表
        self.update_devices()
        
        # 加载配置
        self.load_config()
        
        # 初始化UI
        self.init_ui()
        
        # 定时器更新推理时间
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_inference_time)
        self.inference_start_time = 0
    
    def init_ui(self):
        """初始化UI"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)
        
        # 上侧区域
        top_layout = QHBoxLayout()
        top_layout.setSpacing(20)
        
        # 左上：大预览区域
        large_preview = self.create_preview_area("布丁", size="large")
        top_layout.addWidget(large_preview, 1)
        
        # 右下：音频设备和控制
        control_panel = self.create_audio_device_panel()
        top_layout.addWidget(control_panel, 1)
        
        main_layout.addLayout(top_layout, 3)  # 上侧占3/4
        
        # 下侧区域：音频控制
        bottom_panel = self.create_control_panel()
        main_layout.addWidget(bottom_panel, 1)  # 下侧占1/4
    
    def create_preview_area(self, text, size="large"):
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
        
        layout = QVBoxLayout(preview)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 使用自适应字体大小的Label
        label = AdaptiveLabel(text)
        # 根据size设置字体大小比例
        if size == "large":
            label._base_font_size = 0.4  # 大预览区域使用更大的字体比例
        else:
            label._base_font_size = 0.35  # 小预览区域使用稍小的字体比例
        
        label.setStyleSheet("color: #ffffff; border: none; background-color: transparent;")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(label)
        
        return preview
    
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
        
        # 左侧：小预览
        small_preview = self.create_preview_area("布丁", size="small")
        layout.addWidget(small_preview)
        
        # 右侧：滑块和控制
        controls_layout = QVBoxLayout()
        controls_layout.setSpacing(15)
        
        # 音调滑块
        pitch_container, self.pitch_slider, pitch_value_label = self.create_slider(
            "音调", self.gui_config.pitch, -12, 12, self.gui_config.pitch
        )
        self.pitch_slider.valueChanged.connect(
            lambda val: self.on_pitch_changed(val, pitch_value_label)
        )
        controls_layout.addWidget(pitch_container)
        
        # 声音粗细滑块
        formant_container, self.formant_slider, formant_value_label = self.create_slider(
            "声音粗细", self.gui_config.formant, -2.0, 2.0, self.gui_config.formant, step=0.05
        )
        self.formant_slider.valueChanged.connect(
            lambda val: self.on_formant_changed(val, formant_value_label)
        )
        controls_layout.addWidget(formant_container)
        
        # 声音延迟滑块（对应block_time）
        delay_container, self.delay_slider, delay_value_label = self.create_slider(
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
        
        refresh_btn = QPushButton("🔄")
        refresh_btn.setFixedSize(40, 40)
        refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #2d2d2d;
                border: none;
                border-radius: 20px;
            }
            QPushButton:hover {
                background-color: #3d3d3d;
            }
        """)
        refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        refresh_btn.clicked.connect(self.on_refresh_devices)
        
        button_layout.addStretch()
        button_layout.addWidget(save_btn)
        button_layout.addWidget(refresh_btn)
        
        controls_layout.addLayout(button_layout)
        controls_layout.addStretch()
        
        layout.addLayout(controls_layout)
        
        return panel
    
    def create_slider(self, label_text, value, min_val, max_val, default_val, step=1):
        """创建滑块控件，返回容器、滑块和值标签"""
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        container.setStyleSheet("background-color: transparent;")
        
        # 标签和值
        label_layout = QHBoxLayout()
        label = QLabel(label_text)
        label.setStyleSheet("color: #ffffff; font-size: 14px; border: none; background-color: transparent;")
        value_label = QLabel(str(value))
        value_label.setStyleSheet("color: #8b5cf6; font-size: 14px; font-weight: bold; border: none; background-color: transparent;")
        value_label.setMinimumWidth(50)
        value_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        
        label_layout.addWidget(label)
        label_layout.addWidget(value_label)
        layout.addLayout(label_layout)
        
        # 滑块
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setMinimum(int(min_val / step))
        slider.setMaximum(int(max_val / step))
        slider.setValue(int(default_val / step))
        slider.setStyleSheet("""
            QSlider::groove:horizontal {
                background-color: #2d2d2d;
                height: 6px;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background-color: #8b5cf6;
                width: 18px;
                height: 18px;
                margin: -6px 0;
                border-radius: 9px;
            }
            QSlider::handle:horizontal:hover {
                background-color: #7c3aed;
            }
            QSlider::sub-page:horizontal {
                background-color: #8b5cf6;
                border-radius: 3px;
            }
        """)
        
        # 连接信号更新值显示
        def update_value(val):
            actual_val = val * step
            value_label.setText(f"{actual_val:.2f}" if step < 1 else str(actual_val))
        
        slider.valueChanged.connect(update_value)
        slider.setCursor(Qt.CursorShape.PointingHandCursor)
        
        layout.addWidget(slider)
        
        return container, slider, value_label
    
    def create_algorithm_group(self):
        """创建音高算法选择组"""
        group = QGroupBox("音高算法:")
        group.setStyleSheet("""
            QGroupBox {
                color: #ffffff;
                font-size: 14px;
                border: 1px solid #3d3d3d;
                border-radius: 6px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        
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
            radio.setStyleSheet("""
                QRadioButton {
                    color: #ffffff;
                    font-size: 13px;
                }
                QRadioButton::indicator {
                    width: 16px;
                    height: 16px;
                }
                QRadioButton::indicator:unchecked {
                    border: 2px solid #3d3d3d;
                    border-radius: 8px;
                    background-color: #2d2d2d;
                }
                QRadioButton::indicator:checked {
                    border: 2px solid #8b5cf6;
                    border-radius: 8px;
                    background-color: #8b5cf6;
                }
            """)
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
        layout.setSpacing(20)
        
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
        self.stop_btn.setStyleSheet("""
            QPushButton {
                background-color: #2d2d2d;
                color: #ffffff;
                border: none;
                border-radius: 8px;
                padding: 15px 30px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #3d3d3d;
            }
            QPushButton:pressed {
                background-color: #1d1d1d;
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
        container = QWidget()
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
        combo.setStyleSheet("""
            QComboBox {
                background-color: #2d2d2d;
                border: 1px solid #3d3d3d;
                border-radius: 6px;
                padding: 8px;
                color: #ffffff;
                font-size: 13px;
            }
            QComboBox:hover {
                border: 1px solid #8b5cf6;
            }
            QComboBox::drop-down {
                border: none;
                width: 30px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid #ffffff;
                margin-right: 10px;
            }
            QComboBox QAbstractItemView {
                background-color: #2d2d2d;
                border: 1px solid #3d3d3d;
                selection-background-color: #8b5cf6;
                color: #ffffff;
            }
        """)
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
