import sys
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFrame, QStackedWidget
)
from PyQt6.QtCore import Qt, QSize, QPoint
from PyQt6.QtGui import QFont, QIcon, QMouseEvent, QPixmap

# 导入页面类
from pages import (
    HomePage,
    InferencePage,
    ManagementPage,
    SettingsPage,
    SupportPage
)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.current_page = "home"  # 当前选中的页面
        self.drag_position = QPoint()  # 拖动位置
        self.dragging = False  # 是否正在拖动
        self.init_ui()
    
    def init_ui(self):
        """初始化用户界面"""
        # 隐藏标题栏（无边框窗口）
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        
        self.setWindowTitle("娱音")
        self.setFixedSize(1200, 800)
        
        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 顶部导航栏
        self.create_top_bar(main_layout)
        
        # 内容区域
        self.create_content_area(main_layout)
    
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
        logo_label.setPixmap(QPixmap("res/logo.png").scaled(82, 32))
        top_layout.addWidget(logo_label)
        
        top_layout.addStretch()
        
        # 中间：导航链接（图标+文本）
        nav_buttons = [
            ("主页", "home", "res/主页.png"),
            ("推理", "inference", "res/推理.png"),
            ("管理", "management", "res/管理.png"),
            ("设置", "settings", "res/设置.png"),
            ("联系客服", "support", "res/客服.png")
        ]
        
        self.nav_buttons = {}
        for text, key, icon_path in nav_buttons:
            # 创建带图标的按钮
            icon = QIcon(icon_path)
            btn = QPushButton(icon, text)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            
            # 设置图标大小
            btn.setIconSize(QSize(20, 20))
            
            # 基础样式由全局样式表提供，只设置特殊样式
            btn.setStyleSheet("text-align: left;")
            
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
    
    def on_logout_clicked(self):
        """退出登录按钮点击事件"""
        print("退出登录")
        # TODO: 实现退出登录逻辑
    
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


if __name__ == "__main__":
    main()

