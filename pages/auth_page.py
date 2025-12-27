"""登录和注册页面（统一页面类）"""
import os
import re
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QCheckBox, QFrame, QMessageBox, QStackedWidget
)
from PyQt6.QtCore import Qt, pyqtSignal
from api.auth import auth_api
from api.async_utils import AsyncTaskManager
from api.storage import token_storage
from utils.mac_address import get_mac_address


class PasswordWidget(QLineEdit):
    """密码输入框容器（按钮在输入框内部）"""
    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 12, 0)
        layout.setSpacing(0)
        
        self.toggle_btn = QPushButton(self)
        self.toggle_btn.setFixedSize(24, 24)
        self.toggle_btn.setProperty("auth_password_hide", True)
        self.toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setEchoMode(QLineEdit.EchoMode.Password)
        self.toggle_btn.clicked.connect(self.on_toggle_btn_clicked)
        layout.addStretch()
        layout.addWidget(self.toggle_btn)
        
        # 设置默认光标
        self._default_cursor = self.cursor()

    def on_toggle_btn_clicked(self):
        if self.toggle_btn.property("auth_password_hide"):
            self.toggle_btn.setProperty("auth_password_show", True)
            self.toggle_btn.setProperty("auth_password_hide", False)
        else:
            self.toggle_btn.setProperty("auth_password_hide", True)
            self.toggle_btn.setProperty("auth_password_show", False)
        self.setEchoMode(QLineEdit.EchoMode.Password if self.toggle_btn.property("auth_password_hide") else QLineEdit.EchoMode.Normal)
        self.toggle_btn.style().polish(self.toggle_btn)
    
    def mouseMoveEvent(self, event):
        """鼠标移动时检查是否在按钮区域内"""
        super().mouseMoveEvent(event)
        # 获取按钮的几何位置（相对于输入框）
        btn_rect = self.toggle_btn.geometry()
        
        # 检查鼠标是否在按钮区域内
        if btn_rect.contains(event.pos()):
            # 在按钮区域内，设置为手型光标
            self.setCursor(Qt.CursorShape.PointingHandCursor)
        else:
            # 不在按钮区域内，恢复默认光标（文本输入光标）
            self.setCursor(self._default_cursor)
    
    def enterEvent(self, event):
        """鼠标进入时保持默认光标"""
        super().enterEvent(event)
        # 鼠标刚进入时保持默认光标，等待 mouseMoveEvent 来检测按钮区域
        self.setCursor(self._default_cursor)
    
    def leaveEvent(self, event):
        """鼠标离开时恢复默认光标"""
        super().leaveEvent(event)
        self.setCursor(self._default_cursor)

class AuthPage(QWidget):
    """登录和注册统一页面"""
    login_success = pyqtSignal(str, str)  # 发送用户名和密码
    register_success = pyqtSignal(str, str, str, str)  # 发送用户名、密码、手机号、激活码
    
    def __init__(self):
        super().__init__()
        self.task_manager = AsyncTaskManager()  # 异步任务管理器
        self.init_ui()
        # 加载保存的凭据
        self.load_saved_credentials()
    
    def init_ui(self):
        """初始化UI"""
        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 使用堆叠窗口切换登录和注册视图
        self.stack = QStackedWidget()
        self.stack.setStyleSheet("background: transparent;")
        
        # 创建登录视图
        self.login_view = self.create_login_view()
        self.stack.addWidget(self.login_view)
        
        # 创建注册视图
        self.register_view = self.create_register_view()
        self.stack.addWidget(self.register_view)
        
        # 默认显示登录视图
        self.stack.setCurrentIndex(0)
        
        main_layout.addStretch()
        main_layout.addWidget(self.stack, alignment=Qt.AlignmentFlag.AlignCenter)
        main_layout.addStretch()
    
    def create_login_view(self):
        """创建登录视图"""
        view = QWidget()
        view.setStyleSheet("background: transparent;")
        
        main_layout = QVBoxLayout(view)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 创建登录对话框容器
        dialog_frame = QFrame()
        dialog_frame.setProperty("login_bg", True)
        dialog_frame.setFixedSize(400, 500)
        
        dialog_layout = QVBoxLayout(dialog_frame)
        dialog_layout.setContentsMargins(40, 40, 40, 40)
        dialog_layout.setSpacing(20)
        
        # 标题
        title_label = QLabel("欢迎来到娱音Ai!")
        title_label.setProperty("auth_title", True)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        dialog_layout.addWidget(title_label)
        
        dialog_layout.addSpacing(20)
        
        # 账号输入框
        self.login_username_input = QLineEdit()
        self.login_username_input.setPlaceholderText("账号")
        self.login_username_input.setProperty("auth_input", True)
        self.login_username_input.setStyleSheet("background-color: white;")
        dialog_layout.addWidget(self.login_username_input)
        
        # 密码输入框容器（用于将按钮放在输入框内部）
        self.login_password_input = PasswordWidget()
        self.login_password_input.setPlaceholderText("密码")
        self.login_password_input.setProperty("auth_input", True)
        self.login_password_input.setStyleSheet("background-color: white;")
        dialog_layout.addWidget(self.login_password_input)
        
        # 选项行
        options_layout = QHBoxLayout()
        options_layout.setContentsMargins(0, 0, 0, 0)
        
        # 保存密码复选框
        self.remember_checkbox = QCheckBox("保存密码")
        self.remember_checkbox.setProperty("auth_checkbox", True)
        # 连接信号：当用户取消勾选时，清除保存的密码
        self.remember_checkbox.stateChanged.connect(self.on_remember_checkbox_changed)
        options_layout.addWidget(self.remember_checkbox)
        
        options_layout.addStretch()
        
        # 忘记密码链接
        forgot_password_label = QLabel("忘记密码?")
        forgot_password_label.setProperty("auth_link", True)
        forgot_password_label.setCursor(Qt.CursorShape.PointingHandCursor)
        forgot_password_label.mousePressEvent = lambda e: self.on_forgot_password()
        options_layout.addWidget(forgot_password_label)
        
        dialog_layout.addLayout(options_layout)
        
        # 登录按钮
        self.login_btn = QPushButton("登录")
        self.login_btn.setProperty("auth_primary", True)
        self.login_btn.setStyleSheet("background-color: #0068B7;")   # 不知为啥在style.qss中设置背景颜色无效
        self.login_btn.clicked.connect(self.on_login)
        dialog_layout.addWidget(self.login_btn)
        
        # 注册链接
        register_layout = QHBoxLayout()
        register_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        register_text = QLabel("没有账号?")
        register_text.setProperty("auth_text_secondary", True)
        register_layout.addWidget(register_text)
        
        register_link = QLabel("立即注册")
        register_link.setProperty("auth_link", True)
        register_link.setCursor(Qt.CursorShape.PointingHandCursor)
        register_link.mousePressEvent = lambda e: self.show_register()
        register_layout.addWidget(register_link)
        
        dialog_layout.addLayout(register_layout)
        
        # 用户协议
        agreement_link_layout = QHBoxLayout()
        agreement_link_layout.setContentsMargins(0, 0, 0, 0)

        self.agreement_checkbox = QCheckBox("")
        self.agreement_checkbox.setProperty("auth_checkbox_small", True)
        self.agreement_checkbox.setText("我已详细阅读并同意")
        agreement_link_layout.addWidget(self.agreement_checkbox)
        
        agreement_link = QLabel("《用户协议》")
        agreement_link.setProperty("auth_link_small", True)
        agreement_link.setCursor(Qt.CursorShape.PointingHandCursor)
        agreement_link.mousePressEvent = lambda e: self.on_agreement_clicked()
        agreement_link_layout.addWidget(agreement_link)
        agreement_link_layout.addStretch()
        
        dialog_layout.addLayout(agreement_link_layout)
        
        main_layout.addStretch()
        main_layout.addWidget(dialog_frame, alignment=Qt.AlignmentFlag.AlignCenter)
        main_layout.addStretch()
        
        return view
    
    def create_register_view(self):
        """创建注册视图"""
        view = QWidget()
        view.setStyleSheet("background: transparent;")
        
        main_layout = QVBoxLayout(view)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 创建注册对话框容器
        dialog_frame = QFrame()
        dialog_frame.setProperty("login_bg", True)
        dialog_frame.setFixedSize(400, 550)
        
        dialog_layout = QVBoxLayout(dialog_frame)
        dialog_layout.setContentsMargins(40, 40, 40, 40)
        dialog_layout.setSpacing(20)
        
        # 标题
        title_label = QLabel("Welcome to 布丁!")
        title_label.setProperty("auth_title", True)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        dialog_layout.addWidget(title_label)
        
        dialog_layout.addSpacing(10)
        
        # 用户名输入框
        self.register_username_input = QLineEdit()
        self.register_username_input.setPlaceholderText("用户名")
        self.register_username_input.setProperty("auth_input", True)
        self.register_username_input.setStyleSheet("background-color: white;")
        dialog_layout.addWidget(self.register_username_input)
        
        # 密码输入框容器（用于将按钮放在输入框内部）
        self.register_password_input = PasswordWidget()
        self.register_password_input.setPlaceholderText("密码")
        self.register_password_input.setProperty("auth_input", True)
        self.register_password_input.setStyleSheet("background-color: white;")
        dialog_layout.addWidget(self.register_password_input)
        
        # 手机号码输入框
        self.phone_input = QLineEdit()
        self.phone_input.setPlaceholderText("手机号码")
        self.phone_input.setProperty("auth_input", True)
        self.phone_input.setStyleSheet("background-color: white;")
        dialog_layout.addWidget(self.phone_input)
        
        # 激活码输入框
        self.activation_input = QLineEdit()
        self.activation_input.setPlaceholderText("激活码 (请联系客服人员获取)")
        self.activation_input.setProperty("auth_input", True)
        self.activation_input.setStyleSheet("background-color: white;")
        dialog_layout.addWidget(self.activation_input)
        
        # 注册按钮
        self.register_btn = QPushButton("注册")
        self.register_btn.setProperty("auth_primary", True)
        self.register_btn.setStyleSheet("background-color: #0068B7;")   # 不知为啥在style.qss中设置背景颜色无效
        self.register_btn.clicked.connect(self.on_register)
        dialog_layout.addWidget(self.register_btn)
        
        # 登录链接
        login_layout = QHBoxLayout()
        login_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        login_text = QLabel("已有账号?")
        login_text.setProperty("auth_text_secondary", True)
        login_layout.addWidget(login_text)
        
        login_link = QLabel("立即登录")
        login_link.setProperty("auth_link", True)
        login_link.setCursor(Qt.CursorShape.PointingHandCursor)
        login_link.mousePressEvent = lambda e: self.show_login()
        login_layout.addWidget(login_link)
        
        dialog_layout.addLayout(login_layout)
        
        main_layout.addStretch()
        main_layout.addWidget(dialog_frame, alignment=Qt.AlignmentFlag.AlignCenter)
        main_layout.addStretch()
        
        return view
    
    def toggle_password_visibility(self, password_input, toggle_btn):
        """切换密码显示/隐藏"""
        if password_input.echoMode() == QLineEdit.EchoMode.Password:
            password_input.setEchoMode(QLineEdit.EchoMode.Normal)
            toggle_btn.setText("🙈")
        else:
            password_input.setEchoMode(QLineEdit.EchoMode.Password)
            toggle_btn.setText("👁")
    
    def show_login(self):
        """显示登录视图"""
        self.stack.setCurrentIndex(0)
    
    def show_register(self):
        """显示注册视图"""
        self.stack.setCurrentIndex(1)
    
    def on_login(self):
        """登录按钮点击"""
        username = self.login_username_input.text().strip()
        password = self.login_password_input.text().strip()
        
        if not username:
            QMessageBox.warning(self, "提示", "请输入账号")
            return
        
        if not password:
            QMessageBox.warning(self, "提示", "请输入密码")
            return
        
        if not self.agreement_checkbox.isChecked():
            QMessageBox.warning(self, "提示", "请先同意用户协议")
            return
        
        # 禁用登录按钮
        self.login_btn.setEnabled(False)
        self.login_btn.setText("登录中...")
        
        # 获取MAC地址
        try:
            mac = get_mac_address()
        except Exception as e:
            QMessageBox.warning(self, "错误", f"获取设备信息失败: {e}")
            self.login_btn.setEnabled(True)
            self.login_btn.setText("登录")
            return
        
        # 异步调用登录API
        thread, worker = self.task_manager.run_task(
            "login",
            auth_api.login(username, password, mac)
        )
        
        # 连接信号
        worker.finished.connect(
            lambda result: self._on_login_result(username, password, result)
        )
        worker.error.connect(
            lambda error: self._on_login_error(error)
        )
        
        # 启动线程
        thread.start()
    
    def _on_login_result(self, username: str, password: str, result: dict):
        """登录结果处理"""
        # 恢复登录按钮
        self.login_btn.setEnabled(True)
        self.login_btn.setText("登录")
        
        if result.get("success"):
            # 如果勾选了"保存密码"，保存用户名和密码
            if self.remember_checkbox.isChecked():
                token_storage.save_credentials(username, password)
            else:
                # 如果未勾选，清除之前保存的凭据
                token_storage.clear_credentials()
            
            # 登录成功，发送信号
            self.login_success.emit(username, password)
        else:
            # 登录失败，显示错误信息
            error_message = result.get("message", "登录失败，请检查用户名和密码")
            
            # 检查是否是MAC地址相关的错误
            if "设备" in error_message or "mac" in error_message.lower() or "其他设备" in error_message:
                QMessageBox.warning(self, "登录失败", error_message)
            else:
                QMessageBox.warning(self, "登录失败", error_message)
    
    def _on_login_error(self, error: str):
        """登录错误处理"""
        # 恢复登录按钮
        self.login_btn.setEnabled(True)
        self.login_btn.setText("登录")
        
        # 检查是否是MAC地址相关的错误
        if "设备" in error or "mac" in error.lower() or "其他设备" in error:
            QMessageBox.warning(self, "登录失败", f"设备验证失败: {error}")
        else:
            QMessageBox.warning(self, "登录错误", f"登录过程中发生错误: {error}")
    
    def on_forgot_password(self):
        """忘记密码"""
        QMessageBox.information(self, "提示", "请联系客服找回密码")
    
    def validate_phone(self, phone):
        """验证手机号格式"""
        pattern = r'^1[3-9]\d{9}$'
        return re.match(pattern, phone) is not None
    
    def on_register(self):
        """注册按钮点击"""
        username = self.register_username_input.text().strip()
        password = self.register_password_input.text().strip()
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
        
        # 禁用注册按钮
        self.register_btn.setEnabled(False)
        self.register_btn.setText("注册中...")
        
        # 获取MAC地址
        try:
            mac = get_mac_address()
        except Exception as e:
            QMessageBox.warning(self, "错误", f"获取设备信息失败: {e}")
            self.register_btn.setEnabled(True)
            self.register_btn.setText("注册")
            return
        
        # 异步调用注册API
        thread, worker = self.task_manager.run_task(
            "register",
            auth_api.register(
                username=username,
                password=password,
                mac=mac,
                phone=phone,
                invitation_code=activation_code
            )
        )
        
        # 连接信号
        worker.finished.connect(
            lambda result: self._on_register_result(username, password, phone, activation_code, result)
        )
        worker.error.connect(
            lambda error: self._on_register_error(error)
        )
        
        # 启动线程
        thread.start()
    
    def _on_register_result(self, username: str, password: str, phone: str, activation_code: str, result: dict):
        """注册结果处理"""
        # 恢复注册按钮
        self.register_btn.setEnabled(True)
        self.register_btn.setText("注册")
        
        if result.get("success"):
            # 注册成功，发送信号
            self.register_success.emit(username, password, phone, activation_code)
        else:
            # 注册失败，显示错误信息
            error_message = result.get("message", "注册失败，请重试")
            
            # 检查是否是邀请码相关的错误
            if "邀请码" in error_message or "invitation" in error_message.lower():
                if "不存在" in error_message:
                    QMessageBox.warning(self, "邀请码错误", "邀请码不存在，请检查后重试")
                elif "已被使用" in error_message or "已使用" in error_message:
                    QMessageBox.warning(self, "邀请码错误", "该邀请码已被使用，请使用其他邀请码")
                else:
                    QMessageBox.warning(self, "邀请码错误", error_message)
            else:
                QMessageBox.warning(self, "注册失败", error_message)
    
    def _on_register_error(self, error: str):
        """注册错误处理"""
        # 恢复注册按钮
        self.register_btn.setEnabled(True)
        self.register_btn.setText("注册")
        
        # 检查是否是邀请码相关的错误
        if "邀请码" in error or "invitation" in error.lower():
            if "不存在" in error:
                QMessageBox.warning(self, "邀请码错误", "邀请码不存在，请检查后重试")
            elif "已被使用" in error or "已使用" in error:
                QMessageBox.warning(self, "邀请码错误", "该邀请码已被使用，请使用其他邀请码")
            else:
                QMessageBox.warning(self, "邀请码错误", f"邀请码验证失败: {error}")
        else:
            QMessageBox.warning(self, "注册错误", f"注册过程中发生错误: {error}")
    
    def load_saved_credentials(self):
        """加载保存的用户名和密码"""
        credentials = token_storage.load_credentials()
        if credentials:
            username, password = credentials
            # 填充用户名和密码
            self.login_username_input.setText(username)
            self.login_password_input.setText(password)
            # 勾选"保存密码"复选框
            self.remember_checkbox.setChecked(True)
    
    def on_remember_checkbox_changed(self, state):
        """记住密码复选框状态改变"""
        # 如果用户取消勾选，清除保存的密码
        # state: 0=未选中, 2=选中
        if state == 0:  # Qt.CheckState.Unchecked
            token_storage.clear_credentials()
            # 清除密码输入框（保留用户名）
            self.login_password_input.setText("")
    
    def on_agreement_clicked(self):
        """用户协议链接点击"""
        if hasattr(self, 'main_window'):
            self.main_window.show_agreement()

