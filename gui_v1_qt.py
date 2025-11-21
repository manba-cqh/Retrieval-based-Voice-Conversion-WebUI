import sys
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFrame, QStackedWidget
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

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
        self.init_ui()
    
    def init_ui(self):
        """初始化用户界面"""
        self.setWindowTitle("布TAI")
        self.setMinimumSize(1200, 800)
        
        # 设置深色主题样式
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1e1e1e;
            }
            QWidget {
                background-color: #1e1e1e;
                color: #ffffff;
            }
            QPushButton {
                background-color: #2d2d2d;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                color: #ffffff;
            }
            QPushButton:hover {
                background-color: #3d3d3d;
            }
            QPushButton:pressed {
                background-color: #1d1d1d;
            }
            QTabWidget::pane {
                border: none;
                background-color: #1e1e1e;
            }
            QTabBar::tab {
                background-color: #2d2d2d;
                color: #ffffff;
                padding: 10px 20px;
                border: none;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background-color: #8b5cf6;
                color: #ffffff;
            }
            QTabBar::tab:hover {
                background-color: #3d3d3d;
            }
            QLineEdit {
                background-color: #2d2d2d;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                padding: 8px;
                color: #ffffff;
            }
            QLineEdit:focus {
                border: 1px solid #8b5cf6;
            }
        """)
        
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
        logo_label = QLabel("布TAI")
        logo_font = QFont()
        logo_font.setPointSize(18)
        logo_font.setBold(True)
        logo_label.setFont(logo_font)
        logo_label.setStyleSheet("color: #8b5cf6;")
        top_layout.addWidget(logo_label)
        
        top_layout.addStretch()
        
        # 中间：导航链接
        nav_buttons = [
            ("主页", "home"),
            ("推理", "inference"),
            ("管理", "management"),
            ("设置", "settings"),
            ("联系客服", "support")
        ]
        
        self.nav_buttons = {}
        for text, key in nav_buttons:
            btn = QPushButton(text)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda checked, k=key: self.on_nav_clicked(k))
            self.nav_buttons[key] = btn
            top_layout.addWidget(btn)
        
        # 设置默认选中"主页"
        self.update_nav_button_style("home")
        
        top_layout.addStretch()
        
        # 右侧：用户操作按钮
        logout_btn = QPushButton("退出登录")
        logout_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        logout_btn.clicked.connect(self.on_logout_clicked)
        top_layout.addWidget(logout_btn)
        
        pudding_btn = QPushButton("布丁")
        pudding_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        pudding_btn.clicked.connect(self.on_pudding_clicked)
        top_layout.addWidget(pudding_btn)
        
        # 窗口控制按钮（最小化、最大化、关闭）
        window_controls = QHBoxLayout()
        window_controls.setSpacing(5)
        
        minimize_btn = QPushButton("—")
        minimize_btn.setFixedSize(30, 30)
        minimize_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        minimize_btn.clicked.connect(self.showMinimized)
        
        maximize_btn = QPushButton("□")
        maximize_btn.setFixedSize(30, 30)
        maximize_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        maximize_btn.clicked.connect(self.toggle_maximize)
        
        close_btn = QPushButton("×")
        close_btn.setFixedSize(30, 30)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
        """)
        close_btn.clicked.connect(self.close)
        
        window_controls.addWidget(minimize_btn)
        window_controls.addWidget(maximize_btn)
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
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: #8b5cf6;
                        border: none;
                        padding: 8px 16px;
                        border-radius: 4px;
                        color: #ffffff;
                    }
                    QPushButton:hover {
                        background-color: #7c3aed;
                    }
                    QPushButton:pressed {
                        background-color: #6d28d9;
                    }
                """)
            else:
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: #2d2d2d;
                        border: none;
                        padding: 8px 16px;
                        border-radius: 4px;
                        color: #ffffff;
                    }
                    QPushButton:hover {
                        background-color: #3d3d3d;
                    }
                    QPushButton:pressed {
                        background-color: #1d1d1d;
                    }
                """)
    
    def on_nav_clicked(self, key):
        """导航按钮点击事件"""
        # 更新当前页面
        if key in self.pages:
            self.stacked_widget.setCurrentWidget(self.pages[key])
            self.current_page = key
            
            # 更新导航按钮样式
            self.update_nav_button_style(key)
            
            print(f"切换到页面: {key}")
    
    def on_logout_clicked(self):
        """退出登录按钮点击事件"""
        print("退出登录")
        # TODO: 实现退出登录逻辑
    
    def on_pudding_clicked(self):
        """布丁按钮点击事件"""
        print("布丁")
        # TODO: 实现布丁功能
    
    def on_search_clicked(self):
        """搜索按钮点击事件"""
        print("搜索")
        # TODO: 实现搜索逻辑


def main():
    app = QApplication(sys.argv)
    
    # 设置应用程序样式
    app.setStyle('Fusion')
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

