"""认证相关API"""
import requests
from typing import Optional, Dict, Any
from .config import API_AUTH_REGISTER, API_AUTH_LOGIN, API_AUTH_ME
from .storage import token_storage


class AuthAPI:
    """认证API客户端"""
    
    def __init__(self, base_url: Optional[str] = None):
        """
        初始化API客户端
        
        Args:
            base_url: API基础URL，如果为None则使用默认配置
        """
        self.base_url = base_url
        self.token: Optional[str] = None
        self.user_info: Optional[Dict[str, Any]] = None
        # 尝试加载已保存的Token
        self._load_saved_token()
    
    def _get_url(self, endpoint: str) -> str:
        """获取完整的API URL"""
        if self.base_url:
            return f"{self.base_url}{endpoint.replace(API_AUTH_REGISTER.split('/api')[0], '')}"
        return endpoint
    
    def register(
        self,
        username: str,
        password: str,
        phone: Optional[str] = None,
        email: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        用户注册
        
        Args:
            username: 用户名
            password: 密码
            phone: 手机号（可选）
            email: 邮箱（可选）
        
        Returns:
            注册结果字典，包含用户信息
        
        Raises:
            requests.RequestException: 请求失败时抛出
        """
        url = self._get_url(API_AUTH_REGISTER)
        data = {
            "username": username,
            "password": password
        }
        if phone:
            data["phone"] = phone
        if email:
            data["email"] = email
        
        try:
            response = requests.post(url, json=data, timeout=10)
            response.raise_for_status()
            result = response.json()
            return {
                "success": True,
                "data": result,
                "message": "注册成功"
            }
        except requests.exceptions.HTTPError as e:
            error_msg = "注册失败"
            try:
                error_data = e.response.json()
                error_msg = error_data.get("detail", error_msg)
            except:
                error_msg = f"注册失败: {e.response.status_code}"
            return {
                "success": False,
                "message": error_msg
            }
        except requests.exceptions.RequestException as e:
            return {
                "success": False,
                "message": f"网络错误: {str(e)}"
            }
    
    def login(self, username: str, password: str) -> Dict[str, Any]:
        """
        用户登录
        
        Args:
            username: 用户名
            password: 密码
        
        Returns:
            登录结果字典，包含token和用户信息
        
        Raises:
            requests.RequestException: 请求失败时抛出
        """
        url = self._get_url(API_AUTH_LOGIN)
        # 使用 form-data 格式（OAuth2PasswordRequestForm）
        data = {
            "username": username,
            "password": password
        }
        
        try:
            response = requests.post(url, data=data, timeout=10)
            response.raise_for_status()
            result = response.json()
            
            # 保存token和用户信息
            self.token = result.get("access_token")
            self.user_info = result.get("user")
            
            # 持久化保存Token
            token_storage.save_token(self.token, self.user_info)
            
            return {
                "success": True,
                "data": result,
                "token": self.token,
                "user": self.user_info,
                "message": "登录成功"
            }
        except requests.exceptions.HTTPError as e:
            error_msg = "登录失败"
            try:
                error_data = e.response.json()
                error_msg = error_data.get("detail", error_msg)
            except:
                error_msg = f"登录失败: {e.response.status_code}"
            return {
                "success": False,
                "message": error_msg
            }
        except requests.exceptions.RequestException as e:
            return {
                "success": False,
                "message": f"网络错误: {str(e)}"
            }
    
    def get_current_user(self) -> Dict[str, Any]:
        """
        获取当前用户信息
        
        Returns:
            用户信息字典
        
        Raises:
            requests.RequestException: 请求失败时抛出
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
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            result = response.json()
            self.user_info = result
            return {
                "success": True,
                "data": result,
                "user": result
            }
        except requests.exceptions.HTTPError as e:
            error_msg = "获取用户信息失败"
            try:
                error_data = e.response.json()
                error_msg = error_data.get("detail", error_msg)
            except:
                error_msg = f"获取用户信息失败: {e.response.status_code}"
            return {
                "success": False,
                "message": error_msg
            }
        except requests.exceptions.RequestException as e:
            return {
                "success": False,
                "message": f"网络错误: {str(e)}"
            }
    
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

