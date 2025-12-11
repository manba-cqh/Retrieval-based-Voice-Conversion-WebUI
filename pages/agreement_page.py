"""用户协议页面"""
import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QFrame
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont


class AgreementPage(QWidget):
    """用户协议页面"""
    closed = pyqtSignal()  # 关闭信号
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
    
    def init_ui(self):
        """初始化UI"""
        # 设置页面背景透明
        self.setStyleSheet("background: transparent;")
        
        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        main_layout.addStretch()
        
        # 创建对话框容器
        dialog_frame = QFrame()
        dialog_frame.setProperty("login_bg", True)
        dialog_frame.setFixedSize(600, 500)
        
        dialog_layout = QVBoxLayout(dialog_frame)
        dialog_layout.setContentsMargins(30, 30, 30, 30)
        dialog_layout.setSpacing(20)
        
        # 标题
        title_label = QLabel("使用协议")
        title_label.setProperty("auth_title", True)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        dialog_layout.addWidget(title_label)
        
        # 协议内容
        agreement_text = QTextEdit()
        agreement_text.setReadOnly(True)
        agreement_text.setStyleSheet("""
            QTextEdit {
                background-color: rgba(30, 30, 30, 200);
                border: 1px solid #3d3d3d;
                border-radius: 12px;
                color: #cccccc;
                font-size: 12px;
                padding: 10px;
                line-height: 1.3;
            }
        """)
        
        # 从 agreement.html 文件加载 HTML 内容
        html_content = self.load_agreement_html()
        if html_content:
            agreement_text.setHtml(html_content)
        else:
            # 如果文件读取失败，显示默认文本
            agreement_text.setPlainText("无法加载协议内容，请稍后重试。")
        
        dialog_layout.addWidget(agreement_text)
        
        # 关闭按钮
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.close_btn = QPushButton("关闭")
        self.close_btn.setProperty("auth_primary", True)
        self.close_btn.setStyleSheet("background-color: #3d3d3d;")
        self.close_btn.setFixedSize(92, 32)
        self.close_btn.clicked.connect(self.on_close)
        button_layout.addWidget(self.close_btn)
        button_layout.addStretch()
        
        dialog_layout.addLayout(button_layout)
        
        main_layout.addWidget(dialog_frame, alignment=Qt.AlignmentFlag.AlignCenter)
        main_layout.addStretch()
    
    def load_agreement_html(self):
        """从 agreement.html 文件加载 HTML 内容"""
        try:
            # 获取项目根目录
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            html_path = os.path.join(project_root, "agreement.html")
            
            # 读取 HTML 文件
            with open(html_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            return html_content
        except FileNotFoundError:
            print(f"协议文件未找到: {html_path}")
            return None
        except Exception as e:
            print(f"读取协议文件时出错: {e}")
            return None
    
    def on_close(self):
        """关闭页面"""
        self.closed.emit()