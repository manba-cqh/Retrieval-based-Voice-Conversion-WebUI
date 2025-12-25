import sys
import os

# 将项目根目录添加到 Python 路径中，以便能够导入 pages 模块
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFrame, QStackedWidget
)
from PyQt6.QtCore import Qt, QSize, QPoint
from PyQt6.QtGui import QFont, QIcon, QMouseEvent, QPixmap, QPainter, QBrush, QLinearGradient, QMovie, QPaintEvent

# 导入页面类
from pages import (
    HomePage,
    InferencePage,
    ManagementPage,
    SettingsPage,
    SupportPage,
    AuthPage,
    AgreementPage
)

class BackgroundWidget(QWidget):
    """带背景图片的Widget"""
    def __init__(self, background_path, parent=None):
        super().__init__(parent)
        self.background_path = background_path
        self.background_pixmap = None
        if os.path.exists(background_path):
            self.background_pixmap = QPixmap(background_path)
    
    def paintEvent(self, event: QPaintEvent):
        """绘制背景图片"""
        if self.background_pixmap:
            painter = QPainter(self)
            # 缩放图片以适应窗口大小，保持宽高比
            scaled_pixmap = self.background_pixmap.scaled(
                self.size(), 
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation
            )
            # 居中绘制
            x = (self.width() - scaled_pixmap.width()) // 2
            y = (self.height() - scaled_pixmap.height()) // 2
            painter.drawPixmap(x, y, scaled_pixmap)
        super().paintEvent(event)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.current_page = "home"  # 当前选中的页面
        self.drag_position = QPoint()  # 拖动位置
        self.dragging = False  # 是否正在拖动
        self.is_logged_in = False  # 登录状态
        self.current_username = None  # 当前登录用户名
        self.init_ui()
    
    def init_ui(self):
        """初始化用户界面"""
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setWindowTitle("娱音")
        self.setFixedSize(1200, 800)
        
        # 创建主堆叠窗口（用于切换登录/主界面）
        self.main_stack = QStackedWidget()
        self.main_stack.setStyleSheet("background: transparent;")
        self.setCentralWidget(self.main_stack)
        
        # 登录/注册容器
        self.auth_container = QLabel()
        self.main_stack.addWidget(self.auth_container)
        movie = QMovie("res/background.gif")
        movie.setScaledSize(self.size())
        self.auth_container.setMovie(movie)
        movie.start()
        auth_layout = QVBoxLayout(self.auth_container)
        auth_layout.setContentsMargins(0, 0, 0, 0)
        
        # 创建认证页面堆叠（用于切换登录/注册和协议页面）
        self.auth_stack = QStackedWidget()
        self.auth_stack.setStyleSheet("background: transparent;")
        
        # 创建统一的认证页面（包含登录和注册）
        self.auth_page = AuthPage()
        self.auth_page.main_window = self
        self.auth_page.login_success.connect(self.on_login_success)
        self.auth_page.register_success.connect(self.on_register_success)
        self.auth_stack.addWidget(self.auth_page)
        
        # 创建协议页面
        self.agreement_page = AgreementPage()
        self.agreement_page.closed.connect(self.show_auth_page)
        self.auth_stack.addWidget(self.agreement_page)
        
        auth_layout.addWidget(self.auth_stack)

        self.auth_close_btn = QPushButton("", self.auth_container)
        self.auth_close_btn.setFixedSize(30, 30)
        self.auth_close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.auth_close_btn.setStyleSheet("""
            QPushButton {
                border-image: url("res/关闭.png");
            }
        """)
        self.auth_close_btn.clicked.connect(self.close)
        
        # 主页面容器（带背景图片）
        self.app_container = BackgroundWidget("")
        self.main_stack.addWidget(self.app_container)
        app_layout = QVBoxLayout(self.app_container)
        app_layout.setContentsMargins(0, 0, 0, 0)
        app_layout.setSpacing(0)
        
        self.create_top_bar(app_layout)
        self.create_content_area(app_layout)
        
        # 默认显示登录页面
        self.main_stack.setCurrentWidget(self.auth_container)
    
    def create_top_bar(self, parent_layout):
        """创建顶部导航栏"""
        top_bar = QFrame()
        top_bar.setFixedHeight(60)
        # 保存顶部栏引用，用于拖动检测
        self.top_bar = top_bar
        top_bar.setStyleSheet("""
            QFrame {
                background-color: #252525;
                border-bottom: 1px solid #3d3d3d;
            }
        """)
        
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(20, 0, 20, 0)
        top_layout.setSpacing(20)
        
        # 左侧：Logo
        logo_label = QLabel("")
        logo_font = QFont()
        logo_font.setPointSize(18)
        logo_font.setBold(True)
        logo_label.setFont(logo_font)
        logo_label.setPixmap(QPixmap("res/logo.png").scaled(128, 37))
        top_layout.addWidget(logo_label)
        
        top_layout.addStretch()
        
        # 中间：导航链接（图标+文本）
        nav_buttons = [
            (" 主  页", "home", "res/主页.png"),
            (" 推  理", "inference", "res/推理.png"),
            (" 管  理", "management", "res/管理.png"),
            (" 设  置", "settings", "res/设置.png"),
            (" 联系客服", "support", "res/客服.png")
        ]
        
        self.nav_buttons = {}
        for text, key, icon_path in nav_buttons:
            # 创建带图标的按钮
            icon = QIcon(icon_path)
            btn = QPushButton(icon, text)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFixedSize(120, 42)
            btn.setStyleSheet("""
                QPushButton {
                    font-size: 42px;
                }
                text-align: center;
            """)
            
            # 设置图标大小
            btn.setIconSize(QSize(32, 32))
            
            btn.clicked.connect(lambda checked, k=key: self.on_nav_clicked(k))
            self.nav_buttons[key] = btn
            top_layout.addWidget(btn)
        
        # 设置默认选中"主页"
        self.update_nav_button_style("home")
        
        top_layout.addSpacing(36)
        
        # 右侧：用户操作按钮
        logout_btn = QPushButton("退出登录")
        logout_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        logout_btn.clicked.connect(self.on_logout_clicked)
        top_layout.addWidget(logout_btn)
        
        # 窗口控制按钮（最小化、最大化、关闭）
        window_controls = QHBoxLayout()
        window_controls.setSpacing(12)
        
        minimize_btn = QPushButton("")
        minimize_btn.setFixedSize(30, 30)
        minimize_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        minimize_btn.setStyleSheet("""
            QPushButton {
                border-image: url("res/最小化.png");
            }
        """)
        minimize_btn.clicked.connect(self.showMinimized)
        
        close_btn = QPushButton("")
        close_btn.setFixedSize(30, 30)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setStyleSheet("""
            QPushButton {
                border-image: url("res/关闭.png");
            }
        """)
        close_btn.clicked.connect(self.close)
        
        window_controls.addWidget(minimize_btn)
        window_controls.addWidget(close_btn)
        
        top_layout.addLayout(window_controls)
        
        parent_layout.addWidget(top_bar)
    
    def create_content_area(self, parent_layout):
        """创建内容区域"""
        # 使用 QStackedWidget 管理多个页面
        self.stacked_widget = QStackedWidget()
        
        # 创建5个主界面页面
        self.pages = {
            "home": HomePage(),
            "inference": InferencePage(),
            "management": ManagementPage(),
            "settings": SettingsPage(),
            "support": SupportPage()
        }
        
        # 将所有页面添加到堆叠窗口
        for page in self.pages.values():
            self.stacked_widget.addWidget(page)
        
        # 设置默认显示主页
        self.stacked_widget.setCurrentWidget(self.pages["home"])
        
        parent_layout.addWidget(self.stacked_widget)
    
    
    def toggle_maximize(self):
        """切换最大化/还原窗口"""
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()
    
    def update_nav_button_style(self, selected_key):
        """更新导航按钮样式"""
        for btn_key, btn in self.nav_buttons.items():
            if btn_key == selected_key:
                # 选中状态：特殊背景色
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: #8b5cf6;
                        text-align: left;
                    }
                    QPushButton:hover {
                        background-color: #7c3aed;
                    }
                    QPushButton:pressed {
                        background-color: #6d28d9;
                    }
                """)
            else:
                # 未选中状态：使用全局样式，只设置特殊属性
                btn.setStyleSheet("text-align: left;")
    
    def on_nav_clicked(self, key):
        """导航按钮点击事件"""
        # 更新当前页面
        if key in self.pages:
            self.stacked_widget.setCurrentWidget(self.pages[key])
            self.current_page = key
            
            # 更新导航按钮样式
            self.update_nav_button_style(key)
    
    def show_login(self):
        """显示登录页面"""
        if hasattr(self, 'auth_page'):
            self.auth_page.show_login()
    
    def show_register(self):
        """显示注册页面"""
        if hasattr(self, 'auth_page'):
            self.auth_page.show_register()
    
    def show_agreement(self):
        """显示用户协议页面"""
        if hasattr(self, 'auth_stack'):
            self.auth_stack.setCurrentWidget(self.agreement_page)
    
    def show_auth_page(self):
        """显示认证页面（登录/注册）"""
        if hasattr(self, 'auth_stack'):
            self.auth_stack.setCurrentWidget(self.auth_page)
    
    def on_login_success(self, username, password):
        """登录成功"""
        from api.auth import auth_api
        
        # 检查是否真的登录成功（token已保存）
        if auth_api.is_logged_in():
            print(f"登录成功: {username}")
            self.is_logged_in = True
            # 保存用户信息（可选：保存到配置文件）
            self.current_username = username
            # 切换到主应用界面
            self.main_stack.setCurrentWidget(self.app_container)
            # 登录成功后，加载主页和管理页面的模型数据
            if "home" in self.pages:
                print("登录成功，开始加载主页模型列表...")
                self.pages["home"].load_models()
            if "management" in self.pages:
                print("登录成功，开始加载管理页面模型列表...")
                self.pages["management"].load_models()
        else:
            # 如果API调用失败，这里不应该被调用
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "错误", "登录状态异常，请重新登录")
    
    def on_register_success(self, username, password, phone, activation_code):
        """注册成功"""
        from PyQt6.QtWidgets import QMessageBox
        
        # 注册成功后，总是返回到登录页面
        print(f"注册成功: {username}, {phone}")
        QMessageBox.information(self, "提示", "注册成功！请登录")
        # 切换到登录页面
        self.show_login()
    
    def on_logout_clicked(self):
        """退出登录按钮点击事件"""
        from api.auth import auth_api
        
        # 清除登录状态
        auth_api.logout()
        self.is_logged_in = False
        self.current_username = None
        
        # 切换到登录页面
        self.main_stack.setCurrentWidget(self.auth_container)
        self.show_login()
    
    def on_search_clicked(self):
        """搜索按钮点击事件"""
        print("搜索")
        # TODO: 实现搜索逻辑
    
    def mousePressEvent(self, event: QMouseEvent):
        """鼠标按下事件"""
        # 检查是否在顶部栏区域（前60像素高度）
        if event.position().y() <= 60:
            if event.button() == Qt.MouseButton.LeftButton:
                # 检查点击的是否是按钮
                widget = self.childAt(event.position().toPoint())
                # 如果点击的不是按钮，则允许拖动
                if widget is None or not isinstance(widget, QPushButton):
                    # 向上查找父控件，确保不是按钮的子控件
                    parent = widget
                    is_button = False
                    while parent:
                        if isinstance(parent, QPushButton):
                            is_button = True
                            break
                        parent = parent.parent()
                    
                    if not is_button:
                        self.dragging = True
                        self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
                        event.accept()
                        return
        super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event: QMouseEvent):
        """鼠标移动事件"""
        if self.dragging and event.buttons() == Qt.MouseButton.LeftButton:
            # 移动窗口
            self.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()
        super().mouseMoveEvent(event)
    
    def mouseReleaseEvent(self, event: QMouseEvent):
        """鼠标释放事件"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = False
            event.accept()
        super().mouseReleaseEvent(event)

    def resizeEvent(self, event):
        """窗口大小改变事件"""
        super().resizeEvent(event)
        self.auth_close_btn.move(self.width() - self.auth_close_btn.width() * 3 / 2 , self.auth_close_btn.height() / 2)
        self.auth_container.raise_()


def load_stylesheet(file_path):
    """加载样式表文件"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        print(f"警告: 找不到样式表文件 {file_path}")
        return ""
    except Exception as e:
        print(f"加载样式表失败: {e}")
        return ""


def main():
    try:
        # 添加异常捕获，确保错误能被看到
        import traceback
        
        app = QApplication(sys.argv)
        
        # 设置应用程序样式
        app.setStyle('Fusion')
        
        # 从文件加载全局样式表
        stylesheet = load_stylesheet("res/style.qss")
        if stylesheet:
            app.setStyleSheet(stylesheet)
        
        window = MainWindow()
        window.show()
        
        sys.exit(app.exec())
    except Exception as e:
        # 打印详细错误信息
        import traceback
        error_msg = traceback.format_exc()
        print("=" * 50)
        print("程序启动失败！")
        print("=" * 50)
        print(error_msg)
        print("=" * 50)
        input("按回车键退出...")  # 暂停，让用户看到错误信息
        sys.exit(1)


if __name__ == "__main__":
    main()
