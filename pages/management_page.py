"""管理页面"""
from .base_page import BasePage


class ManagementPage(BasePage):
    """管理页面"""
    
    def __init__(self):
        super().__init__("管理")
        self.setup_content()
    
    def setup_content(self):
        """设置管理页面内容"""
        # TODO: 添加管理页面具体内容
        pass

