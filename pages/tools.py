"""GUI工具函数"""
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSlider
from PyQt6.QtCore import Qt


def create_slider(label_text, value, min_val, max_val, default_val, step=1):
    """创建滑块控件，返回容器、滑块和值标签
    
    Args:
        label_text: 标签文本
        value: 当前值
        min_val: 最小值
        max_val: 最大值
        default_val: 默认值
        step: 步长，默认为1
    
    Returns:
        tuple: (container, slider, value_label)
            - container: 容器Widget
            - slider: QSlider对象
            - value_label: 值标签QLabel对象
    """
    container = QWidget()
    layout = QVBoxLayout(container)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(6)
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
    slider.setFixedHeight(18)
    # 样式由全局样式表提供
    
    # 连接信号更新值显示
    def update_value(val):
        actual_val = val * step
        value_label.setText(f"{actual_val:.2f}" if step < 1 else str(actual_val))
    
    slider.valueChanged.connect(update_value)
    slider.setCursor(Qt.CursorShape.PointingHandCursor)
    
    layout.addWidget(slider)
    
    return container, slider, value_label

