"""认证相关API（异步版本）"""
from typing import Optional, Dict, Any
from .async_client import AsyncAPIClient
from .config import API_AUTH_REGISTER, API_AUTH_LOGIN, API_AUTH_ME
from .storage import token_storage


class AuthAPI(AsyncAPIClient):
    """认证API客户端（异步）"""
    
    def __init__(self, base_url: Optional[str] = None):
        """
        初始化API客户端
        
        Args:
            base_url: API基础URL，如果为None则使用默认配置
        """
        super().__init__(base_url=base_url)
        self.token: Optional[str] = None
        self.user_info: Optional[Dict[str, Any]] = None
        # 尝试加载已保存的Token
        self._load_saved_token()
    
    def _get_url(self, endpoint: str) -> str:
        """获取完整的API URL"""
        if self.base_url:
            # 从endpoint中提取路径部分
            if endpoint.startswith("http"):
                return endpoint.replace(API_AUTH_REGISTER.split('/api')[0], self.base_url)
            return f"{self.base_url}{endpoint.split('/api')[1] if '/api' in endpoint else endpoint}"
        return endpoint
    
    async def register(
        self,
        username: str,
        password: str,
        mac: str,
        phone: Optional[str] = None,
        email: Optional[str] = None,
        invitation_code: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        用户注册（异步）
        
        Args:
            username: 用户名
            password: 密码
            mac: MAC地址（必填）
            phone: 手机号（可选）
            email: 邮箱（可选）
            invitation_code: 邀请码（必填）
        
        Returns:
            注册结果字典
        """
        url = self._get_url(API_AUTH_REGISTER)
        json_data = {
            "username": username,
            "password": password,
            "mac": mac
        }
        if phone:
            json_data["phone"] = phone
        if email:
            json_data["email"] = email
        if invitation_code:
            json_data["invitation_code"] = invitation_code
        
        result = await self.post(url, json_data=json_data)
        
        if result.get("success"):
            result["message"] = "注册成功"
        else:
            result.setdefault("message", result.get("message", "注册失败"))
        
        return result
    
    async def login(self, username: str, password: str, mac: str) -> Dict[str, Any]:
        """
        用户登录（异步）
        
        Args:
            username: 用户名
            password: 密码
            mac: MAC地址（必填）
        
        Returns:
            登录结果字典，包含token和用户信息
        """
        url = self._get_url(API_AUTH_LOGIN)
        # 使用 JSON 格式（因为需要传递 MAC 地址）
        json_data = {
            "username": username,
            "password": password,
            "mac": mac
        }
        
        result = await self.post(url, json_data=json_data)
        
        if result.get("success"):
            # 保存token和用户信息
            data_result = result.get("data", {})
            self.token = data_result.get("access_token")
            self.user_info = data_result.get("user")
            
            # 持久化保存Token
            token_storage.save_token(self.token, self.user_info)
            
            result["token"] = self.token
            result["user"] = self.user_info
            result["message"] = "登录成功"
        else:
            result.setdefault("message", result.get("message", "登录失败"))
        
        return result
    
    async def get_current_user(self) -> Dict[str, Any]:
        """
        获取当前用户信息（异步）
        
        Returns:
            用户信息字典
        """
        if not self.token:
            return {
                "success": False,
                "message": "未登录"
            }
        
        url = self._get_url(API_AUTH_ME)
        headers = {
            "Authorization": f"Bearer {self.token}"
        }
        
        result = await self.get(url, headers=headers)
        
        if result.get("success"):
            self.user_info = result.get("data")
            result["user"] = self.user_info
        
        return result
    
    def logout(self):
        """退出登录"""
        self.token = None
        self.user_info = None
        # 清除保存的Token
        token_storage.clear()
    
    def _load_saved_token(self):
        """加载已保存的Token"""
        saved_token = token_storage.load_token()
        saved_user_info = token_storage.load_user_info()
        if saved_token:
            self.token = saved_token
            self.user_info = saved_user_info
    
    def is_logged_in(self) -> bool:
        """检查是否已登录"""
        return self.token is not None and self.user_info is not None


# 全局API实例
auth_api = AuthAPI()

