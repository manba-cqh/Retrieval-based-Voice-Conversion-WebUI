"""注册页面"""
import re
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QFrame, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont


class RegisterPage(QWidget):
    """注册页面"""
    register_success = pyqtSignal(str, str, str, str)  # 发送用户名、密码、手机号、激活码
    
    def __init__(self):
        super().__init__()
        self.init_ui()
    
    def init_ui(self):
        """初始化UI"""
        # 设置页面背景透明，让主窗口背景显示
        self.setStyleSheet("background: transparent;")
        
        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 创建注册对话框容器
        dialog_frame = QFrame()
        dialog_frame.setStyleSheet("""
            QFrame {
                background-color: rgba(40, 40, 40, 240);
                border-radius: 12px;
            }
        """)
        dialog_frame.setFixedSize(400, 550)
        
        dialog_layout = QVBoxLayout(dialog_frame)
        dialog_layout.setContentsMargins(40, 40, 40, 40)
        dialog_layout.setSpacing(20)
        
        # 标题
        title_label = QLabel("Welcome to 布丁!")
        title_font = QFont()
        title_font.setPointSize(24)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setStyleSheet("color: #8b5cf6;")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        dialog_layout.addWidget(title_label)
        
        dialog_layout.addSpacing(10)
        
        # 用户名输入框
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("用户名")
        self.username_input.setStyleSheet("""
            QLineEdit {
                background-color: white;
                border: 1px solid #cccccc;
                border-radius: 6px;
                padding: 12px;
                font-size: 14px;
            }
            QLineEdit:focus {
                border: 2px solid #8b5cf6;
            }
        """)
        dialog_layout.addWidget(self.username_input)
        
        # 密码输入框容器
        password_container = QHBoxLayout()
        password_container.setSpacing(0)
        
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("密码")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setStyleSheet("""
            QLineEdit {
                background-color: white;
                border: 1px solid #cccccc;
                border-radius: 6px;
                padding: 12px;
                font-size: 14px;
            }
            QLineEdit:focus {
                border: 2px solid #8b5cf6;
            }
        """)
        password_container.addWidget(self.password_input)
        
        # 密码显示/隐藏按钮
        self.password_toggle_btn = QPushButton()
        self.password_toggle_btn.setFixedSize(30, 30)
        self.password_toggle_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                color: #8b5cf6;
                font-size: 18px;
            }
            QPushButton:hover {
                color: #7c3aed;
            }
        """)
        self.password_toggle_btn.setText("👁")
        self.password_toggle_btn.clicked.connect(self.toggle_password_visibility)
        password_container.addWidget(self.password_toggle_btn)
        
        dialog_layout.addLayout(password_container)
        
        # 手机号码输入框
        self.phone_input = QLineEdit()
        self.phone_input.setPlaceholderText("手机号码")
        self.phone_input.setStyleSheet("""
            QLineEdit {
                background-color: white;
                border: 1px solid #cccccc;
                border-radius: 6px;
                padding: 12px;
                font-size: 14px;
            }
            QLineEdit:focus {
                border: 2px solid #8b5cf6;
            }
        """)
        dialog_layout.addWidget(self.phone_input)
        
        # 激活码输入框
        self.activation_input = QLineEdit()
        self.activation_input.setPlaceholderText("激活码 (请联系客服人员获取)")
        self.activation_input.setStyleSheet("""
            QLineEdit {
                background-color: white;
                border: 1px solid #cccccc;
                border-radius: 6px;
                padding: 12px;
                font-size: 14px;
            }
            QLineEdit:focus {
                border: 2px solid #8b5cf6;
            }
        """)
        dialog_layout.addWidget(self.activation_input)
        
        # 注册按钮
        register_btn = QPushButton("注册")
        register_btn.setStyleSheet("""
            QPushButton {
                background-color: #8b5cf6;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 12px;
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
        register_btn.clicked.connect(self.on_register)
        dialog_layout.addWidget(register_btn)
        
        # 登录链接
        login_layout = QHBoxLayout()
        login_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        login_text = QLabel("已有账号?")
        login_text.setStyleSheet("color: #cccccc; font-size: 12px;")
        login_layout.addWidget(login_text)
        
        login_link = QLabel("立即登录")
        login_link.setStyleSheet("""
            QLabel {
                color: #8b5cf6;
                font-size: 12px;
                text-decoration: underline;
            }
        """)
        login_link.setCursor(Qt.CursorShape.PointingHandCursor)
        login_link.mousePressEvent = lambda e: self.on_login_clicked()
        login_layout.addWidget(login_link)
        
        dialog_layout.addLayout(login_layout)
        
        # 将对话框居中
        main_layout.addStretch()
        main_layout.addWidget(dialog_frame, alignment=Qt.AlignmentFlag.AlignCenter)
        main_layout.addStretch()
    
    def toggle_password_visibility(self):
        """切换密码显示/隐藏"""
        if self.password_input.echoMode() == QLineEdit.EchoMode.Password:
            self.password_input.setEchoMode(QLineEdit.EchoMode.Normal)
            self.password_toggle_btn.setText("🙈")
        else:
            self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
            self.password_toggle_btn.setText("👁")
    
    def validate_phone(self, phone):
        """验证手机号格式"""
        pattern = r'^1[3-9]\d{9}$'
        return re.match(pattern, phone) is not None
    
    def on_register(self):
        """注册按钮点击"""
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()
        phone = self.phone_input.text().strip()
        activation_code = self.activation_input.text().strip()
        
        if not username:
            QMessageBox.warning(self, "提示", "请输入用户名")
            return
        
        if len(username) < 3:
            QMessageBox.warning(self, "提示", "用户名至少3个字符")
            return
        
        if not password:
            QMessageBox.warning(self, "提示", "请输入密码")
            return
        
        if len(password) < 6:
            QMessageBox.warning(self, "提示", "密码至少6个字符")
            return
        
        if not phone:
            QMessageBox.warning(self, "提示", "请输入手机号码")
            return
        
        if not self.validate_phone(phone):
            QMessageBox.warning(self, "提示", "请输入正确的手机号码格式")
            return
        
        if not activation_code:
            QMessageBox.warning(self, "提示", "请输入激活码")
            return
        
        # 发送注册成功信号
        self.register_success.emit(username, password, phone, activation_code)
    
    def on_login_clicked(self):
        """登录链接点击"""
        if hasattr(self, 'main_window'):
            self.main_window.show_login()

