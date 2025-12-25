"""管理页面"""
import json
import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QScrollArea, QGridLayout, QFrame, QStackedWidget,
    QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QFont, QIcon, QPixmap, QMovie

from .base_page import BasePage
from api.auth import auth_api
from api.models import models_api
from .home_page import ModelCard, ModelDetailPage
import asyncio


class ManagementPage(BasePage):
    """管理页面"""
    
    def __init__(self):
        super().__init__("管理")
        self.models_data = []  # 存储所有模型数据
        self.filtered_models = []  # 过滤后的模型
        self.current_category = "全部音色"  # 当前选中的分类
        self.current_model = None  # 当前查看的模型
        self.setup_content()
        # 不在初始化时加载模型，等待登录成功后再加载
        # self.load_models()  # 加载模型数据
    
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
                border: none;
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
        grid_container = QHBoxLayout()
        grid_container.setContentsMargins(12, 0, 0, 0)  # 左边距 12px，避免被遮挡
        grid_container.setSpacing(0)
        
        self.grid_layout = QGridLayout()
        self.grid_layout.setSpacing(20)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        
        grid_container.addLayout(self.grid_layout)
        grid_container.addStretch()  # 添加右侧拉伸，使卡片靠左对齐
        
        grid_widget.setLayout(grid_container)
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
        """从models目录加载模型数据"""
        self.models_data = self.fetch_models_from_models_dir()
        # 按模型名称排序
        self.models_data.sort(key=lambda x: x.get("name", "").lower())
        self.filtered_models = self.models_data.copy()
        self.update_model_grid()
    
    def _refresh_models_with_filter(self):
        """刷新模型数据，但保持当前的筛选条件"""
        # 保存当前的筛选条件
        current_category = self.current_category
        current_search = self.search_input.text() if hasattr(self, 'search_input') else ""
        
        # 重新加载模型数据
        self.models_data = self.fetch_models_from_models_dir()
        # 按模型名称排序
        self.models_data.sort(key=lambda x: x.get("name", "").lower())
        
        # 恢复筛选条件并应用筛选
        self.current_category = current_category
        if hasattr(self, 'search_input'):
            self.search_input.setText(current_search)
        
        # 更新选择指示器
        if hasattr(self, 'selection_indicator'):
            self.selection_indicator.setText(f"当前选择: {self.current_category}")
        
        # 应用筛选条件
        self.filter_models()
    
    def fetch_models_from_models_dir(self):
        """从models目录获取模型数据（只返回用户可用的模型）"""
        models_dir = os.path.join(os.getcwd(), "models")
        models_data = []
        
        # 如果models目录不存在，返回空列表
        if not os.path.exists(models_dir):
            return models_data
        
        # 获取用户可用的模型UUID列表
        available_model_uids = self._get_user_available_model_uids()
        
        # 扫描models目录下的所有子目录
        model_id = 1
        for item in os.listdir(models_dir):
            model_dir_path = os.path.join(models_dir, item)
            
            # 只处理目录
            if not os.path.isdir(model_dir_path):
                continue
            
            # 查找.pth文件（文件名可以是任意的，只要扩展名是.pth即可）
            pth_files = [f for f in os.listdir(model_dir_path) if f.endswith(".pth")]
            if not pth_files:
                continue  # 如果没有.pth文件，跳过这个目录
            
            # 查找index文件（文件名可以是任意的，只要扩展名是.index即可）
            index_files = [f for f in os.listdir(model_dir_path) if f.endswith(".index")]
            
            # 查找json信息文件
            json_files = [f for f in os.listdir(model_dir_path) if f.endswith(".json")]
            
            # 查找图片文件（支持常见图片格式）
            image_extensions = (".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp")
            image_files = [f for f in os.listdir(model_dir_path) 
                          if f.lower().endswith(image_extensions)]
            
            # 使用第一个找到的.pth文件
            pth_path = os.path.join(model_dir_path, pth_files[0])
            
            # 使用第一个找到的index文件，如果没有则设为空字符串
            index_path = os.path.join(model_dir_path, index_files[0]) if index_files else ""
            
            # 读取json信息文件（如果存在）
            model_info = {}
            if json_files:
                json_path = os.path.join(model_dir_path, json_files[0])
                try:
                    with open(json_path, 'r', encoding='utf-8') as f:
                        model_info = json.load(f)
                except Exception as e:
                    print(f"读取模型信息文件失败 {json_path}: {e}")
            
            # 构建模型数据
            model_name = model_info.get("name", item)  # 如果json中没有name，使用目录名
            
            # 确定模型图片路径（优先级：json中的image > 目录下的图片文件）
            model_image = model_info.get("image", "")
            if model_image:
                # 如果json中指定了图片路径
                if not os.path.isabs(model_image):
                    # 如果是相对路径，转换为相对于模型目录的路径
                    model_image = os.path.join(model_dir_path, model_image)
            elif image_files:
                # 如果json中没有指定，但目录下有图片文件，使用第一个找到的图片
                model_image = os.path.join(model_dir_path, image_files[0])
            else:
                # 没有图片
                model_image = ""
            
            # 获取分类信息（从json中读取，默认为"免费音色"，支持多个分类用分号分隔）
            category = model_info.get("category", "免费音色")
            # 判断是否为官方音色（如果category中包含"官方音色"）
            categories = [cat.strip() for cat in category.split(";")]
            is_official = "官方音色" in categories
            # 判断是否为收藏（如果category中包含"收藏"）
            is_favorite = "收藏" in categories
            
            # 读取uid（支持uuid或uid字段）
            model_uid = model_info.get("uuid") or model_info.get("uid")
            
            # 判断是否为免费音色
            is_free_model = "免费音色" in categories
            
            # 对于免费音色，只要本地存在就显示，不需要在用户的可用列表中
            # 对于非免费音色（官方音色等），必须同时在用户的可用列表中或正在试用中
            if not is_free_model:
                result = self._check_model_trial_status(model_uid)
                # 非免费音色，需要检查用户的可用模型列表或试用状态
                if available_model_uids is None:
                    # 用户未登录或没有可用模型列表，检查是否有试用
                    has_trial = self._check_model_trial_status(model_uid)
                    if not has_trial:
                        continue
                elif not model_uid or model_uid not in available_model_uids:
                    # 模型不在用户的可用列表中，检查是否有试用
                    has_trial = self._check_model_trial_status(model_uid)
                    if not has_trial:
                        # 既不在可用列表，也没有试用，跳过
                        continue
            
            # 构建模型数据（兼容管理页面的数据结构）
            model_data = {
                "id": f"m{model_id}",
                "name": model_name,
                "image": model_image,
                "description": model_info.get("description", ""),
                "category": category,
                "is_official": is_official,
                "is_favorite": is_favorite,  # 从category字段中判断，如果包含"收藏"则为True
                "version": model_info.get("version", "V1"),
                "sample_rate": model_info.get("sample_rate", "48K"),
                "pth_path": pth_path,
                "index_path": index_path,
                "uid": model_uid,  # 添加uid字段
            }
            
            # 添加json中的其他信息（如果有）
            for key in ["price", "category_name"]:
                if key in model_info:
                    model_data[key] = model_info[key]
            
            models_data.append(model_data)
            model_id += 1
        
        return models_data
    
    def _get_user_available_model_uids(self):
        """
        获取用户可用的模型UUID列表
        
        Returns:
            可用模型UUID的集合（set），如果用户未登录或没有可用模型列表则返回None（不显示任何模型）
        """
        try:
            # 尝试从auth_api获取用户信息
            user_info = auth_api.user_info
            if not user_info:
                # 如果auth_api中没有，尝试从存储中加载
                from api.storage import token_storage
                user_info = token_storage.load_user_info()
            
            if not user_info:
                # 用户未登录，返回None表示不显示任何模型
                return None
            
            # 获取available_models字段
            available_models = user_info.get("available_models")
            if not available_models:
                # 如果没有available_models字段或为空，返回None表示不显示任何模型
                return None
            
            # 解析分号分隔的UUID列表
            uids = [uid.strip() for uid in available_models.split(";") if uid.strip()]
            if not uids:
                # 如果解析后列表为空，返回None表示不显示任何模型
                return None
            return set(uids)  # 返回集合以便快速查找
            
        except Exception as e:
            print(f"获取用户可用模型列表失败: {e}")
            # 出错时返回None，不显示任何模型
            return None
    
    def _check_model_trial_status(self, model_uid):
        """
        检查模型是否有正在进行的试用（直接调用服务器API查询数据库）
        
        Args:
            model_uid: 模型UUID
        
        Returns:
            bool: 如果有正在进行的试用返回True，否则返回False
        """
        if not model_uid:
            return False
        
        # 检查登录状态
        if not auth_api.is_logged_in():
            return False
        
        try:
            # 直接调用服务器API检查试用状态
            # 使用 asyncio.run() 在同步方法中运行异步代码
            async def check_trial():
                return await models_api.get_trial_status(model_uid)
            
            # 尝试获取当前事件循环，如果没有则创建新的
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # 如果事件循环正在运行，不能使用 run_until_complete
                    # 这种情况下返回 False（应该不会发生，因为这是在同步方法中调用）
                    print("警告: 事件循环正在运行，无法同步调用API")
                    return False
            except RuntimeError:
                # 没有事件循环，创建新的
                pass
            
            # 运行异步函数
            result = asyncio.run(check_trial())
            
            # 处理API返回结果（API客户端会包装响应）
            if result.get("success"):
                data = result.get("data", {})
                # 如果data中还有success字段，说明是服务器返回的完整响应，需要再取一次data
                if isinstance(data, dict) and "success" in data and "data" in data:
                    data = data.get("data", {})
                
                is_active = data.get("is_active", False)
                remaining_seconds = data.get("remaining_seconds", 0)
                
                if is_active and remaining_seconds > 0:
                    return True
            
            return False
        except Exception as e:
            print(f"检查模型试用状态失败: {e}")
            import traceback
            traceback.print_exc()
            return False
    
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
            # 分类过滤（支持多个分类，用分号分隔）
            if self.current_category == "全部音色":
                # 显示所有
                pass
            elif self.current_category == "官方音色":
                # 检查category字段中是否包含"官方音色"，或is_official字段
                model_categories = [cat.strip() for cat in model.get("category", "").split(";")]
                if "官方音色" not in model_categories and not model.get("is_official", False):
                    continue
            elif self.current_category == "免费音色":
                # 检查category字段中是否包含"免费音色"，且不是官方音色
                model_categories = [cat.strip() for cat in model.get("category", "").split(";")]
                if "免费音色" not in model_categories and model.get("is_official", False):
                    continue
            elif self.current_category == "收藏夹":
                # 检查category字段中是否包含"收藏"，或is_favorite字段
                model_categories = [cat.strip() for cat in model.get("category", "").split(";")]
                if "收藏" not in model_categories and not model.get("is_favorite", False):
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
        
        # 设置列的对齐方式，使卡片靠左对齐
        for col in range(columns):
            self.grid_layout.setColumnStretch(col, 0)  # 不拉伸列，让卡片靠左
        
        # 添加弹性空间（只在最后一行）
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
        
        # 查找对应的 ModelCard，获取图片对象
        model_image = None
        for i in range(self.grid_layout.count()):
            item = self.grid_layout.itemAt(i)
            if item and item.widget():
                widget = item.widget()
                if isinstance(widget, ModelCard) and widget.model_id == model_id:
                    # 优先使用 movie（GIF），否则尝试从 image_label 获取 pixmap
                    if hasattr(widget, 'movie') and widget.movie:
                        # 创建新的 QMovie 实例（因为 QMovie 不能直接复制）
                        # 如果 ModelCard 有图片路径，使用路径创建新的 QMovie
                        if widget.model_image and os.path.exists(widget.model_image):
                            model_image = QMovie(widget.model_image)
                            model_image.start()
                    elif hasattr(widget, 'image_label') and widget.image_label:
                        # 尝试从 image_label 获取 pixmap
                        pixmap = widget.image_label.pixmap()
                        if pixmap and not pixmap.isNull():
                            model_image = QPixmap(pixmap)
                    break
        
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
        
        # 管理页面的模型都是已购买/已下载的
        # 尝试获取主窗口引用
        main_window = None
        parent = self.parent()
        while parent:
            if hasattr(parent, 'pages'):
                main_window = parent
                break
            parent = parent.parent()
        
        self.detail_page = ModelDetailPage(detail_data, is_purchased=True, main_window=main_window, model_image=model_image)
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
