"""设置页面"""
import os
import sys
import json
import shutil
from multiprocessing import cpu_count

import sounddevice as sd
import torch

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton,
    QSlider, QComboBox, QFrame, QScrollArea, QGroupBox, QMessageBox
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QPixmap

from .base_page import BasePage
from .tools import create_slider


class SettingsPage(BasePage):
    """设置页面"""
    
    def __init__(self):
        super().__init__("设置")
        
        # 配置数据
        self.config_data = {}
        self.load_config()
        
        # 音频设备相关（需要在 setup_content 之前初始化）
        self.hostapis = None
        self.input_devices = None
        self.output_devices = None
        self.input_devices_indices = None
        self.output_devices_indices = None
        
        # GPU信息
        self.gpu_devices = []
        
        # 初始化设备列表
        self.update_devices()
        self.detect_gpu()
        
        # 设置页面内容（需要在设备初始化之后）
        self.setup_content()
    
    def setup_content(self):
        """设置设置页面内容"""
        # 获取或使用现有的布局（基类已创建）
        main_layout = self.layout()
        if not main_layout:
            main_layout = QVBoxLayout(self)
        
        # 清除基类创建的默认内容
        while main_layout.count():
            child = main_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        # 创建滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        # 样式由全局样式表提供
        
        # 创建内容widget
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(20, 20, 20, 20)
        content_layout.setSpacing(20)
        
        # 性能设备部分
        performance_group = self.create_performance_group()
        content_layout.addWidget(performance_group)
        
        # 设备检查部分
        device_check_group = self.create_device_check_group()
        content_layout.addWidget(device_check_group)
        
        content_layout.addStretch()
        
        scroll.setWidget(content_widget)
        
        # 使用现有布局，设置边距和间距
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        main_layout.addWidget(scroll)
    
    def create_performance_group(self):
        """创建性能设备组"""
        group = QGroupBox("性能设备")
        
        layout = QGridLayout(group)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 30, 20, 20)
        
        # 从配置加载默认值
        volume_val = self.config_data.get("rms_mix_rate", 0.5)
        fade_val = self.config_data.get("crossfade_length", 0.15)
        harvest_val = int(self.config_data.get("n_cpu", 4))
        extra_val = self.config_data.get("extra_time", 2.99)
        
        # 音量大小 (使用 rms_mix_rate) - 第0行第0列
        volume_container, self.volume_slider, volume_label = create_slider(
            "音量大小", volume_val, 0.0, 1.0, volume_val, step=0.01
        )
        self.volume_slider.valueChanged.connect(
            lambda val: self.on_volume_changed(val, volume_label)
        )
        layout.addWidget(volume_container, 0, 0)
        
        # 淡入淡出长度 - 第0行第1列
        fade_container, self.fade_slider, fade_label = create_slider(
            "淡入淡出长度", fade_val, 0.01, 0.5, fade_val, step=0.01
        )
        self.fade_slider.valueChanged.connect(
            lambda val: self.on_fade_changed(val, fade_label)
        )
        layout.addWidget(fade_container, 0, 1)
        
        # harvest进程数 - 第1行第0列
        harvest_container, self.harvest_slider, harvest_label = create_slider(
            "harvest进程数", harvest_val, 1, min(cpu_count(), 8), harvest_val, step=1
        )
        self.harvest_slider.valueChanged.connect(
            lambda val: self.on_harvest_changed(val, harvest_label)
        )
        layout.addWidget(harvest_container, 1, 0)
        
        # 额外推理时长 - 第1行第1列
        extra_container, self.extra_slider, extra_label = create_slider(
            "额外推理时长", extra_val, 0.05, 5.0, extra_val, step=0.01
        )
        self.extra_slider.valueChanged.connect(
            lambda val: self.on_extra_changed(val, extra_label)
        )
        layout.addWidget(extra_container, 1, 1)
        
        return group
    
    def create_device_check_group(self):
        """创建设备检查组"""
        group = QGroupBox("设备检查")
        
        layout = QGridLayout(group)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 30, 20, 20)
        
        # 麦克风 - 第0行第0列
        mic_layout = QVBoxLayout()
        mic_layout.setContentsMargins(0, 0, 0, 0)
        mic_layout.setSpacing(9)
        mic_label = QLabel("麦克风")
        # 基础样式由全局样式表提供，只设置特殊字体大小
        mic_label.setStyleSheet("font-size: 14px;")
        self.mic_combo = QComboBox()
        if self.input_devices:
            self.mic_combo.addItems(self.input_devices)
            # 加载保存的输入设备
            saved_input = self.config_data.get("sg_input_device", "")
            if saved_input and saved_input in self.input_devices:
                self.mic_combo.setCurrentText(saved_input)
        else:
            self.mic_combo.addItem("未找到设备")
        # 样式由全局样式表提供
        self.mic_combo.currentTextChanged.connect(self.on_mic_device_changed)
        mic_layout.addWidget(mic_label)
        mic_layout.addWidget(self.mic_combo)
        layout.addLayout(mic_layout, 0, 0)
        
        # 显卡 - 第0行第1列
        gpu_layout = QVBoxLayout()
        gpu_layout.setContentsMargins(0, 0, 0, 0)
        gpu_layout.setSpacing(9)
        gpu_label = QLabel("显卡")
        # 基础样式由全局样式表提供，只设置特殊字体大小
        gpu_label.setStyleSheet("font-size: 14px;")
        self.gpu_combo = QComboBox()
        if self.gpu_devices:
            self.gpu_combo.addItems(self.gpu_devices)
        else:
            self.gpu_combo.addItem("未检测到显卡")
        # 样式由全局样式表提供
        gpu_layout.addWidget(gpu_label)
        gpu_layout.addWidget(self.gpu_combo)
        layout.addLayout(gpu_layout, 0, 1)
        
        # 扬声器 - 第1行第0列
        speaker_layout = QVBoxLayout()
        speaker_layout.setContentsMargins(0, 0, 0, 0)
        speaker_layout.setSpacing(9)
        speaker_label = QLabel("扬声器")
        # 基础样式由全局样式表提供，只设置特殊字体大小
        speaker_label.setStyleSheet("font-size: 14px;")
        self.speaker_combo = QComboBox()
        if self.output_devices:
            self.speaker_combo.addItems(self.output_devices)
            # 加载保存的输出设备
            saved_output = self.config_data.get("sg_output_device", "")
            if saved_output and saved_output in self.output_devices:
                self.speaker_combo.setCurrentText(saved_output)
        else:
            self.speaker_combo.addItem("未找到设备")
        # 样式由全局样式表提供
        self.speaker_combo.currentTextChanged.connect(self.on_speaker_device_changed)
        speaker_layout.addWidget(speaker_label)
        speaker_layout.addWidget(self.speaker_combo)
        layout.addLayout(speaker_layout, 1, 0)

        # 系统扬声器音量 (使用 threhold 的绝对值，范围通常是 -60 到 0)
        threshold_val = abs(int(self.config_data.get("threhold", -60)))
        # 将阈值转换为0-100的范围显示
        system_volume_val = max(0, min(100, int((threshold_val + 60) * 100 / 60)))
        volume_container, self.system_volume_slider, system_volume_label = create_slider(
            "系统扬声器音量", system_volume_val, 0, 100, system_volume_val, step=1
        )
        self.system_volume_slider.valueChanged.connect(
            lambda val: self.on_system_volume_changed(val, system_volume_label)
        )
        layout.addWidget(volume_container, 1, 1)
        
        # 设备检测状态 - 第1行第1列
        status_layout = QHBoxLayout()
        status_layout.setContentsMargins(0, 0, 0, 0)
        status_icon = QLabel("")
        status_icon.setPixmap(QPixmap("res/注意安全.png").scaled(24, 24))
        status_text = QLabel("无法检测到设备?")
        # 基础样式由全局样式表提供，只设置特殊字体大小
        status_text.setStyleSheet("font-size: 13px;")
        
        reload_btn = QPushButton("重新加载设备")
        reload_btn.setStyleSheet("""
            QPushButton {
                background-color: #8b5cf6;
                color: #ffffff;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #7c3aed;
            }
        """)
        reload_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        reload_btn.clicked.connect(self.on_reload_devices)
        
        detect_btn = QPushButton("检测")
        detect_btn.setStyleSheet("""
            QPushButton {
                background-color: #8b5cf6;
                color: #ffffff;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #7c3aed;
            }
        """)
        detect_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        detect_btn.clicked.connect(self.on_detect_devices)
        
        feedback_link = QLabel('<a href="#" style="color: #8b5cf6; text-decoration: none;">反馈</a>')
        feedback_link.setOpenExternalLinks(False)
        feedback_link.linkActivated.connect(self.on_feedback)
        
        status_layout.addWidget(status_icon)
        status_layout.addWidget(status_text)
        status_layout.addWidget(reload_btn)
        status_layout.addWidget(detect_btn)
        status_layout.addWidget(QLabel("或"))
        status_layout.addWidget(feedback_link)
        status_layout.addStretch()
        layout.addLayout(status_layout, 2, 0)
        
        # 音频电平指示器（占位）
        level_indicator = QWidget()
        level_indicator.setFixedHeight(8)
        level_indicator.setStyleSheet("""
            QWidget {
                background-color: #2d2d2d;
                border-radius: 4px;
            }
        """)
        layout.addWidget(level_indicator, 2, 1)
        
        return group
    
    def load_config(self):
        """加载配置"""
        try:
            if os.path.exists("configs/inuse/config.json"):
                with open("configs/inuse/config.json", "r", encoding="utf-8") as f:
                    self.config_data = json.load(f)
        except Exception as e:
            print(f"加载配置失败: {e}")
            self.config_data = {}
    
    def save_config(self):
        """保存配置"""
        try:
            os.makedirs("configs/inuse", exist_ok=True)
            # 读取现有配置，保留未修改的配置项
            existing_config = {}
            if os.path.exists("configs/inuse/config.json"):
                try:
                    with open("configs/inuse/config.json", "r", encoding="utf-8") as f:
                        existing_config = json.load(f)
                except:
                    pass
            
            # 合并配置：先使用现有配置，然后用新配置覆盖
            merged_config = {**existing_config, **self.config_data}
            
            with open("configs/inuse/config.json", "w", encoding="utf-8") as f:
                json.dump(merged_config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"保存配置失败: {e}")
    
    def update_devices(self, hostapi_name=None):
        """更新音频设备列表"""
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
            self.hostapis = []
    
    def detect_gpu(self):
        """检测GPU设备"""
        self.gpu_devices = []
        try:
            if torch.cuda.is_available():
                for i in range(torch.cuda.device_count()):
                    gpu_name = torch.cuda.get_device_name(i)
                    self.gpu_devices.append(gpu_name)
        except Exception as e:
            print(f"检测GPU失败: {e}")
    
    def on_volume_changed(self, value, value_label):
        """音量大小改变"""
        actual_val = value * 0.01
        value_label.setText(f"{actual_val:.2f}")
        self.config_data["rms_mix_rate"] = actual_val
        self.save_config()
    
    def on_fade_changed(self, value, value_label):
        """淡入淡出长度改变"""
        actual_val = value * 0.01
        value_label.setText(f"{actual_val:.2f}")
        self.config_data["crossfade_length"] = actual_val
        self.save_config()
    
    def on_harvest_changed(self, value, value_label):
        """harvest进程数改变"""
        value_label.setText(str(value))
        self.config_data["n_cpu"] = float(value)
        self.save_config()
    
    def on_extra_changed(self, value, value_label):
        """额外推理时长改变"""
        actual_val = value * 0.01
        value_label.setText(f"{actual_val:.2f}")
        self.config_data["extra_time"] = actual_val
        self.save_config()
    
    def on_system_volume_changed(self, value, value_label):
        """系统扬声器音量改变（实际是阈值设置）"""
        value_label.setText(str(value))
        # 将0-100转换为-60到0的阈值范围
        threshold_val = -60 + (value * 60 / 100)
        self.config_data["threhold"] = float(threshold_val)
        self.save_config()
    
    def on_protocol_changed(self, protocol):
        """设备协议改变"""
        self.config_data["sg_hostapi"] = protocol
        self.update_devices(protocol)
        # 更新设备下拉框
        if hasattr(self, "mic_combo"):
            self.mic_combo.clear()
            if self.input_devices:
                self.mic_combo.addItems(self.input_devices)
        if hasattr(self, "speaker_combo"):
            self.speaker_combo.clear()
            if self.output_devices:
                self.speaker_combo.addItems(self.output_devices)
        self.save_config()
    
    def on_reload_devices(self):
        """重新加载设备"""
        self.update_devices()
        self.detect_gpu()
        
        # 更新所有下拉框
        if hasattr(self, "mic_combo"):
            self.mic_combo.clear()
            if self.input_devices:
                self.mic_combo.addItems(self.input_devices)
        if hasattr(self, "speaker_combo"):
            self.speaker_combo.clear()
            if self.output_devices:
                self.speaker_combo.addItems(self.output_devices)
        if hasattr(self, "gpu_combo"):
            self.gpu_combo.clear()
            if self.gpu_devices:
                self.gpu_combo.addItems(self.gpu_devices)
            else:
                self.gpu_combo.addItem("未检测到显卡")
        if hasattr(self, "protocol_combo") and self.hostapis:
            self.protocol_combo.clear()
            self.protocol_combo.addItems(self.hostapis)
        
        QMessageBox.information(self, "提示", "设备列表已重新加载")
    
    def on_detect_devices(self):
        """检测设备"""
        self.on_reload_devices()
        QMessageBox.information(self, "提示", "设备检测完成")
    
    def on_feedback(self):
        """反馈链接点击"""
        QMessageBox.information(self, "反馈", "反馈功能待实现")
    
    def on_mic_device_changed(self, device_name):
        """麦克风设备改变（设备检查组）"""
        if device_name and device_name != "未找到设备":
            self.config_data["sg_input_device"] = device_name
            self.save_config()
    
    def on_speaker_device_changed(self, device_name):
        """扬声器设备改变（设备检查组）"""
        if device_name and device_name != "未找到设备":
            self.config_data["sg_output_device"] = device_name
            self.save_config()
    
