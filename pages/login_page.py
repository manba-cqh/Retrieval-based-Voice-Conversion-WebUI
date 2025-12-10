"""登录页面"""
import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QCheckBox, QFrame, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QPixmap, QIcon


class LoginPage(QWidget):
    """登录页面"""
    login_success = pyqtSignal(str, str)  # 发送用户名和密码
    
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
        
        # 创建登录对话框容器
        dialog_frame = QFrame()
        dialog_frame.setStyleSheet("""
            QFrame {
                background-color: rgba(40, 40, 40, 240);
                border-radius: 12px;
            }
        """)
        dialog_frame.setFixedSize(400, 500)
        
        dialog_layout = QVBoxLayout(dialog_frame)
        dialog_layout.setContentsMargins(40, 40, 40, 40)
        dialog_layout.setSpacing(20)
        
        # 标题
        title_label = QLabel("欢迎来到娱音Ai!")
        title_font = QFont()
        title_font.setPointSize(24)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setStyleSheet("color: #8b5cf6;")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        dialog_layout.addWidget(title_label)
        
        dialog_layout.addSpacing(20)
        
        # 账号输入框
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("账号")
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
        
        # 选项行
        options_layout = QHBoxLayout()
        options_layout.setContentsMargins(0, 0, 0, 0)
        
        # 保存密码复选框
        self.remember_checkbox = QCheckBox("保存密码")
        self.remember_checkbox.setStyleSheet("""
            QCheckBox {
                color: #cccccc;
                font-size: 12px;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border: 1px solid #cccccc;
                border-radius: 3px;
                background-color: white;
            }
            QCheckBox::indicator:checked {
                background-color: #8b5cf6;
                border: 1px solid #8b5cf6;
            }
        """)
        options_layout.addWidget(self.remember_checkbox)
        
        options_layout.addStretch()
        
        # 忘记密码链接
        forgot_password_label = QLabel("忘记密码?")
        forgot_password_label.setStyleSheet("""
            QLabel {
                color: #8b5cf6;
                font-size: 12px;
            }
        """)
        forgot_password_label.setCursor(Qt.CursorShape.PointingHandCursor)
        forgot_password_label.mousePressEvent = lambda e: self.on_forgot_password()
        options_layout.addWidget(forgot_password_label)
        
        dialog_layout.addLayout(options_layout)
        
        # 登录按钮
        login_btn = QPushButton("登录")
        login_btn.setStyleSheet("""
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
        login_btn.clicked.connect(self.on_login)
        dialog_layout.addWidget(login_btn)
        
        # 注册链接
        register_layout = QHBoxLayout()
        register_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        register_text = QLabel("没有账号?")
        register_text.setStyleSheet("color: #cccccc; font-size: 12px;")
        register_layout.addWidget(register_text)
        
        register_link = QLabel("立即注册")
        register_link.setStyleSheet("""
            QLabel {
                color: #8b5cf6;
                font-size: 12px;
                text-decoration: underline;
            }
        """)
        register_link.setCursor(Qt.CursorShape.PointingHandCursor)
        register_link.mousePressEvent = lambda e: self.on_register_clicked()
        register_layout.addWidget(register_link)
        
        dialog_layout.addLayout(register_layout)
        
        # 用户协议复选框
        self.agreement_checkbox = QCheckBox("我已详细阅读并同意《用户协议》")
        self.agreement_checkbox.setStyleSheet("""
            QCheckBox {
                color: #cccccc;
                font-size: 11px;
            }
            QCheckBox::indicator {
                width: 14px;
                height: 14px;
                border: 1px solid #cccccc;
                border-radius: 3px;
                background-color: white;
            }
            QCheckBox::indicator:checked {
                background-color: #8b5cf6;
                border: 1px solid #8b5cf6;
            }
        """)
        # 创建可点击的用户协议文本
        agreement_text = self.agreement_checkbox.text()
        self.agreement_checkbox.setText("我已详细阅读并同意")
        
        agreement_link_layout = QHBoxLayout()
        agreement_link_layout.setContentsMargins(0, 0, 0, 0)
        agreement_link_layout.addWidget(self.agreement_checkbox)
        
        agreement_link = QLabel("《用户协议》")
        agreement_link.setStyleSheet("""
            QLabel {
                color: #8b5cf6;
                font-size: 11px;
                text-decoration: underline;
            }
        """)
        agreement_link.setCursor(Qt.CursorShape.PointingHandCursor)
        agreement_link.mousePressEvent = lambda e: self.on_agreement_clicked()
        agreement_link_layout.addWidget(agreement_link)
        agreement_link_layout.addStretch()
        
        dialog_layout.addLayout(agreement_link_layout)
        
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
    
    def on_login(self):
        """登录按钮点击"""
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()
        
        if not username:
            QMessageBox.warning(self, "提示", "请输入账号")
            return
        
        if not password:
            QMessageBox.warning(self, "提示", "请输入密码")
            return
        
        if not self.agreement_checkbox.isChecked():
            QMessageBox.warning(self, "提示", "请先同意用户协议")
            return
        
        # 发送登录成功信号
        self.login_success.emit(username, password)
    
    def on_forgot_password(self):
        """忘记密码"""
        QMessageBox.information(self, "提示", "请联系客服找回密码")
    
    def on_register_clicked(self):
        """注册链接点击"""
        if hasattr(self, 'main_window'):
            self.main_window.show_register()
    
    def on_agreement_clicked(self):
        """用户协议链接点击"""
        if hasattr(self, 'main_window'):
            self.main_window.show_agreement()

