"""基础页面类"""
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont


class BasePage(QWidget):
    """所有页面的基类"""
    
    def __init__(self, page_name):
        super().__init__()
        self.page_name = page_name
        self.init_ui()
    
    def init_ui(self):
        """初始化UI（子类可重写）"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # 页面标题
        title_label = QLabel(self.page_name)
        title_font = QFont()
        title_font.setPointSize(24)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setStyleSheet("color: #8b5cf6; padding: 20px 0;")
        layout.addWidget(title_label)
        
        # 占位内容区域
        content_area = QWidget()
        content_area.setStyleSheet("""
            QWidget {
                background-color: #252525;
                border-radius: 8px;
            }
        """)
        content_area.setMinimumHeight(600)
        layout.addWidget(content_area)
        
        layout.addStretch()

