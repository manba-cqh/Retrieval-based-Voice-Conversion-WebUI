"""联系客服页面"""
import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSizePolicy
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap, QFont
from .base_page import BasePage


class SupportPage(BasePage):
    """联系客服页面"""
    
    def __init__(self):
        super().__init__("联系客服")
        self.setup_content()
    
    def setup_content(self):
        """设置联系客服页面内容"""
        # 获取或使用现有的布局
        main_layout = self.layout()
        if not main_layout:
            main_layout = QVBoxLayout(self)
            main_layout.setContentsMargins(0, 20, 0, 0)
            main_layout.setSpacing(10)
            main_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # 清除基类创建的默认内容
        while main_layout.count():
            child = main_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        # 页面标题
        title_label = QLabel("联系客服")
        title_font = QFont()
        title_font.setPointSize(24)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setStyleSheet("color: #8b5cf6; padding: 20px 0;")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title_label)
        
        # 提示文字
        tip_label = QLabel("扫描下方二维码添加客服QQ")
        tip_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        tip_label.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-size: 16px;
                padding: 10px 0;
                border: none;
                background-color: transparent;
            }
        """)
        main_layout.addWidget(tip_label)
        
        # QQ二维码容器
        qq_container = QWidget()
        qq_layout = QHBoxLayout(qq_container)
        qq_layout.setContentsMargins(40, 20, 40, 60)
        qq_layout.setSpacing(60)
        qq_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # QQ1 二维码
        qq1_widget = self.create_qq_card("res/qq1.png", "123777788")
        qq_layout.addWidget(qq1_widget, 1)  # 添加拉伸因子，允许扩展
        
        # QQ2 二维码
        qq2_widget = self.create_qq_card("res/qq2.jpg", "757249211")
        qq_layout.addWidget(qq2_widget, 1)  # 添加拉伸因子，允许扩展
        
        # 让容器能够扩展
        qq_container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        main_layout.addWidget(qq_container, 1)  # 添加拉伸因子
    
    def create_qq_card(self, image_path, qq_number):
        """创建QQ二维码卡片"""
        card = QWidget()
        card.setStyleSheet("""
            QWidget {
                background-color: #252525;
                border-radius: 12px;
                padding: 20px;
            }
        """)
        
        layout = QVBoxLayout(card)
        layout.setSpacing(15)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # 让卡片能够扩展
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        # 二维码图片
        qr_label = QLabel()
        qr_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        qr_label.setStyleSheet("""
            QLabel {
                background-color: #ffffff;
                border-radius: 8px;
                padding: 10px;
            }
        """)
        
        # 加载图片并保存原始pixmap
        original_pixmap = None
        if os.path.exists(image_path):
            pixmap = QPixmap(image_path)
            if not pixmap.isNull():
                original_pixmap = pixmap
                # 初始设置图片
                qr_label.setPixmap(pixmap)
            else:
                qr_label.setText("图片加载失败")
                qr_label.setStyleSheet("color: #ff0000;")
        else:
            qr_label.setText(f"图片不存在\n{image_path}")
            qr_label.setStyleSheet("color: #ff0000;")
        
        # 设置最小大小，但允许扩展
        if original_pixmap:
            qr_label.setMinimumSize(200, 200)
        # 使用大小策略让标签能够扩展
        qr_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        # 保存原始pixmap引用，用于后续缩放
        if original_pixmap:
            qr_label.original_pixmap = original_pixmap
            
            # 重写resizeEvent来保持宽高比缩放
            def resize_event(event):
                if hasattr(qr_label, 'original_pixmap') and qr_label.original_pixmap:
                    # 获取可用大小（减去padding）
                    available_size = event.size()
                    available_size.setWidth(available_size.width() - 20)  # 减去padding
                    available_size.setHeight(available_size.height() - 20)
                    
                    # 计算保持宽高比的缩放大小
                    scaled_pixmap = qr_label.original_pixmap.scaled(
                        available_size,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation
                    )
                    qr_label.setPixmap(scaled_pixmap)
                QLabel.resizeEvent(qr_label, event)
            
            qr_label.resizeEvent = resize_event
        
        layout.addWidget(qr_label, alignment=Qt.AlignmentFlag.AlignCenter)
        
        # QQ号标签
        qq_label = QLabel(f"QQ: {qq_number}")
        qq_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        qq_label.setStyleSheet("""
            QLabel {
                color: #8b5cf6;
                font-size: 18px;
                font-weight: bold;
                padding: 5px 0;
                border: none;
                background-color: transparent;
            }
        """)
        layout.addWidget(qq_label)
        
        return card

