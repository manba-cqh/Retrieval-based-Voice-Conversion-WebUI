"""管理页面"""
import json
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QScrollArea, QGridLayout, QFrame, QStackedWidget,
    QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QFont, QIcon

from .base_page import BasePage
from .home_page import ModelCard, ModelDetailPage


class ManagementPage(BasePage):
    """管理页面"""
    
    def __init__(self):
        super().__init__("管理")
        self.models_data = []  # 存储所有模型数据
        self.filtered_models = []  # 过滤后的模型
        self.current_category = "全部音色"  # 当前选中的分类
        self.current_model = None  # 当前查看的模型
        self.setup_content()
        self.load_models()  # 加载模型数据
    
    def setup_content(self):
        """设置管理页面内容"""
        # 获取或使用现有的布局
        main_layout = self.layout()
        if not main_layout:
            main_layout = QVBoxLayout(self)
        
        # 清除基类创建的默认内容
        while main_layout.count():
            child = main_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        # 使用堆叠窗口在列表和详情之间切换
        self.stacked_widget = QStackedWidget()
        main_layout.addWidget(self.stacked_widget)
        
        # 列表页面
        self.list_page = QWidget()
        list_layout = QVBoxLayout(self.list_page)
        list_layout.setContentsMargins(0, 0, 0, 0)
        list_layout.setSpacing(24)
        
        # 顶部工具栏
        toolbar = self.create_toolbar()
        list_layout.addWidget(toolbar)
        
        # 模型网格区域
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        # 基础样式由全局样式表提供，只设置特殊样式
        scroll_area.setStyleSheet("""
            QScrollArea {
                padding-left: -12px;
            }
            QScrollBar:vertical {
                background-color: #2d2d2d;
                width: 8px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background-color: #8b5cf6;
                border-radius: 6px;
                min-height: 30px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #7c3aed;
            }
        """)
        
        # 网格容器
        grid_widget = QWidget()
        self.grid_layout = QGridLayout(grid_widget)
        self.grid_layout.setSpacing(20)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        
        scroll_area.setWidget(grid_widget)
        list_layout.addWidget(scroll_area)
        
        self.stacked_widget.addWidget(self.list_page)
        
        # 详情页面（初始为空，点击详情时创建）
        self.detail_page = None
    
    def create_toolbar(self):
        """创建顶部工具栏"""
        toolbar = QWidget()
        toolbar.setStyleSheet("background-color: transparent;")
        
        layout = QVBoxLayout(toolbar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # 分类标签栏
        categories_layout = QHBoxLayout()
        categories_layout.setSpacing(10)
        
        self.category_buttons = {}
        # 定义分类及其对应的图标
        categories_data = [
            ("全部音色", "res/列表.png"),
            ("官方音色", "res/官方核验.png"),
            ("免费音色", "res/免费.png"),
            ("收藏夹", "res/收藏.png")
        ]
        
        for category, icon_path in categories_data:
            # 创建图标
            icon = QIcon(icon_path)
            btn = QPushButton(icon, category)
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setIconSize(QSize(16, 16))  # 设置图标大小
            btn.clicked.connect(lambda checked, cat=category: self.on_category_changed(cat))
            
            if category == "全部音色":
                btn.setChecked(True)
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: #e74c3c;
                        color: #ffffff;
                        border: none;
                        border-radius: 6px;
                        padding: 8px 20px;
                        font-size: 14px;
                        font-weight: bold;
                        text-align: left;
                    }
                """)
            else:
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: #2d2d2d;
                        color: #ffffff;
                        border: none;
                        border-radius: 6px;
                        padding: 8px 20px;
                        font-size: 14px;
                        text-align: left;
                    }
                    QPushButton:hover {
                        background-color: #3d3d3d;
                    }
                    QPushButton:checked {
                        background-color: #8b5cf6;
                    }
                """)
            
            self.category_buttons[category] = btn
            categories_layout.addWidget(btn)

        categories_layout.addStretch()
        
        # 当前选择指示器
        self.selection_indicator = QLabel(f"当前选择: {self.current_category}")
        self.selection_indicator.setStyleSheet("""
            QLabel {
                background-color: #8b5cf6;
                color: #ffffff;
                border: none;
                border-radius: 6px;
                padding: 8px 15px;
                font-size: 14px;
                font-weight: bold;
            }
        """)
        categories_layout.addWidget(self.selection_indicator)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("请输入你想要的声音")
        # 基础样式由全局样式表提供，只设置特殊样式
        self.search_input.setStyleSheet("""
            QLineEdit {
                background-color: #1e1e1e;
                border: 2px solid #3d3d3d;
                border-radius: 8px;
                padding: 2px 15px;
                font-size: 14px;
            }
            QLineEdit:focus {
                border: 2px solid #8b5cf6;
            }
        """)
        self.search_input.textChanged.connect(self.on_search_changed)
        categories_layout.addWidget(self.search_input)

        layout.addLayout(categories_layout)
        
        return toolbar
    
    def load_models(self):
        """从服务器加载模型数据（模拟）"""
        # 模拟从服务器获取数据
        self.models_data = self.fetch_models_from_server()
        self.filtered_models = self.models_data.copy()
        self.update_model_grid()
    
    def fetch_models_from_server(self):
        """从服务器获取模型数据（模拟）
        
        实际项目中可以替换为真实的API调用：
        import requests
        try:
            response = requests.get("https://api.example.com/management/models")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"获取模型数据失败: {e}")
            return []
        """
        # 模拟API调用延迟
        # 实际项目中这里会是异步请求
        
        # 返回模拟数据（管理页面可能包含更多管理相关的信息）
        return [
            {"id": "m1", "name": "茶可", "category": "免费音色", "image": "", "description": "温柔甜美的声音", "is_official": False, "is_favorite": False},
            {"id": "m2", "name": "云深", "category": "免费音色", "image": "", "description": "清新自然的声音", "is_official": False, "is_favorite": True},
            {"id": "m3", "name": "官方音色A", "category": "官方音色", "image": "", "description": "官方认证的高质量音色", "is_official": True, "is_favorite": False},
            {"id": "m4", "name": "官方音色B", "category": "官方音色", "image": "", "description": "官方认证的专业音色", "is_official": True, "is_favorite": True},
            {"id": "m5", "name": "少女1", "category": "免费音色", "image": "", "description": "活泼可爱的声音", "is_official": False, "is_favorite": False},
            {"id": "m6", "name": "大乔", "category": "官方音色", "image": "", "description": "成熟优雅的声音", "is_official": True, "is_favorite": False},
            {"id": "m7", "name": "男主角", "category": "官方音色", "image": "", "description": "磁性低沉的男声", "is_official": True, "is_favorite": True},
            {"id": "m8", "name": "小团团", "category": "免费音色", "image": "", "description": "萌系可爱声音", "is_official": False, "is_favorite": True},
            {"id": "m9", "name": "兮梦", "category": "免费音色", "image": "", "description": "梦幻空灵的声音", "is_official": False, "is_favorite": False},
            {"id": "m10", "name": "御姐", "category": "官方音色", "image": "", "description": "成熟御姐音", "is_official": True, "is_favorite": False},
            {"id": "m11", "name": "萌妹", "category": "免费音色", "image": "", "description": "软萌甜美的声音", "is_official": False, "is_favorite": True},
            {"id": "m12", "name": "碎碎", "category": "免费音色", "image": "", "description": "温柔细腻的声音", "is_official": False, "is_favorite": False},
            {"id": "m13", "name": "软妹", "category": "免费音色", "image": "", "description": "软糯可爱的声音", "is_official": False, "is_favorite": True},
            {"id": "m14", "name": "少萝", "category": "免费音色", "image": "", "description": "萝莉音色", "is_official": False, "is_favorite": False},
            {"id": "m15", "name": "少御", "category": "官方音色", "image": "", "description": "年轻御姐音", "is_official": True, "is_favorite": True},
            {"id": "m16", "name": "少女2", "category": "免费音色", "image": "", "description": "青春活力的声音", "is_official": False, "is_favorite": False},
            {"id": "m17", "name": "布布", "category": "免费音色", "image": "", "description": "活泼开朗的声音", "is_official": False, "is_favorite": True},
            {"id": "m18", "name": "海绵宝宝", "category": "免费音色", "image": "", "description": "搞怪有趣的声音", "is_official": False, "is_favorite": False},
        ]
    
    def on_category_changed(self, category):
        """分类改变"""
        self.current_category = category
        
        # 更新当前选择指示器
        self.selection_indicator.setText(f"当前选择: {category}")
        
        # 更新按钮样式
        for cat, btn in self.category_buttons.items():
            if cat == category:
                if category == "全部音色":
                    btn.setStyleSheet("""
                        QPushButton {
                            background-color: #e74c3c;
                            color: #ffffff;
                            border: none;
                            border-radius: 6px;
                            padding: 8px 20px;
                            font-size: 14px;
                            font-weight: bold;
                            text-align: left;
                        }
                    """)
                else:
                    btn.setStyleSheet("""
                        QPushButton {
                            background-color: #8b5cf6;
                            color: #ffffff;
                            border: none;
                            border-radius: 6px;
                            padding: 8px 20px;
                            font-size: 14px;
                            font-weight: bold;
                            text-align: left;
                        }
                    """)
            else:
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: #2d2d2d;
                        color: #ffffff;
                        border: none;
                        border-radius: 6px;
                        padding: 8px 20px;
                        font-size: 14px;
                        text-align: left;
                    }
                    QPushButton:hover {
                        background-color: #3d3d3d;
                    }
                """)
        
        # 过滤模型
        self.filter_models()
    
    def on_search_changed(self, text):
        """搜索文本改变"""
        self.filter_models()
    
    def filter_models(self):
        """过滤模型"""
        search_text = self.search_input.text().strip().lower()
        
        self.filtered_models = []
        for model in self.models_data:
            # 分类过滤
            if self.current_category == "全部音色":
                # 显示所有
                pass
            elif self.current_category == "官方音色":
                if not model.get("is_official", False):
                    continue
            elif self.current_category == "免费音色":
                if model.get("is_official", False):
                    continue
            elif self.current_category == "收藏夹":
                if not model.get("is_favorite", False):
                    continue
            
            # 搜索过滤
            if search_text and search_text not in model["name"].lower():
                continue
            
            self.filtered_models.append(model)
        
        self.update_model_grid()
    
    def update_model_grid(self):
        """更新模型网格"""
        # 清除现有卡片
        while self.grid_layout.count():
            child = self.grid_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        # 添加模型卡片
        columns = 5  # 每行5个
        for i, model_data in enumerate(self.filtered_models):
            card = ModelCard(model_data)
            card.detail_clicked.connect(self.on_model_detail_clicked)
            
            row = i // columns
            col = i % columns
            self.grid_layout.addWidget(card, row, col)
        
        # 添加弹性空间
        self.grid_layout.setRowStretch(self.grid_layout.rowCount(), 1)
    
    def on_model_detail_clicked(self, model_id):
        """模型详情按钮点击"""
        # 查找模型数据
        model_data = None
        for model in self.models_data:
            if model["id"] == model_id:
                model_data = model
                break
        
        if not model_data:
            QMessageBox.warning(self, "错误", "未找到模型信息")
            return
        
        # 创建或更新详情页面
        if self.detail_page:
            self.detail_page.deleteLater()
        
        # 添加更多详情数据
        detail_data = model_data.copy()
        detail_data.update({
            "price": 0,
            "version": "V1",
            "sample_rate": "48K",
            "category_name": "免费音色" if not detail_data.get("is_official", False) else "官方音色",
            "description": detail_data.get("description", "茶韵悠悠可音袅袅少御音介于少女与御姐之间既有少女清脆又具御姐沉稳圆润柔和年龄感适中清嗓咳嗽呢喃细语悄悄话 笑声 自带情绪感")
        })
        
        self.detail_page = ModelDetailPage(detail_data)
        self.detail_page.back_clicked.connect(self.show_list_page)
        self.detail_page.setParent(self.stacked_widget)
        
        # 如果详情页面不在堆叠中，添加它
        if self.stacked_widget.indexOf(self.detail_page) == -1:
            self.stacked_widget.addWidget(self.detail_page)
        
        # 切换到详情页面
        self.stacked_widget.setCurrentWidget(self.detail_page)
        self.current_model = model_data
    
    def show_list_page(self):
        """显示列表页面"""
        self.stacked_widget.setCurrentWidget(self.list_page)
