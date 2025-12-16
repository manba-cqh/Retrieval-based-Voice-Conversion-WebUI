"""Token存储管理"""
import json
import os
import base64
from typing import Optional, Tuple


class TokenStorage:
    """Token存储类"""
    
    def __init__(self, storage_file: str = "configs/auth_token.json"):
        """
        初始化Token存储
        
        Args:
            storage_file: 存储文件路径
        """
        self.storage_file = storage_file
        self._ensure_storage_dir()
    
    def _ensure_storage_dir(self):
        """确保存储目录存在"""
        storage_dir = os.path.dirname(self.storage_file)
        if storage_dir:
            os.makedirs(storage_dir, exist_ok=True)
    
    def save_token(self, token: str, user_info: Optional[dict] = None):
        """
        保存Token
        
        Args:
            token: 访问令牌
            user_info: 用户信息（可选）
        """
        data = {
            "token": token,
            "user_info": user_info or {}
        }
        try:
            with open(self.storage_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存Token失败: {e}")
    
    def load_token(self) -> Optional[str]:
        """
        加载Token
        
        Returns:
            Token字符串，如果不存在则返回None
        """
        if not os.path.exists(self.storage_file):
            return None
        
        try:
            with open(self.storage_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get("token")
        except Exception as e:
            print(f"加载Token失败: {e}")
            return None
    
    def load_user_info(self) -> Optional[dict]:
        """
        加载用户信息
        
        Returns:
            用户信息字典，如果不存在则返回None
        """
        if not os.path.exists(self.storage_file):
            return None
        
        try:
            with open(self.storage_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get("user_info")
        except Exception as e:
            print(f"加载用户信息失败: {e}")
            return None
    
    def clear(self):
        """清除存储的Token"""
        try:
            if os.path.exists(self.storage_file):
                os.remove(self.storage_file)
        except Exception as e:
            print(f"清除Token失败: {e}")
    
    def save_credentials(self, username: str, password: str):
        """
        保存用户名和密码（加密存储）
        
        Args:
            username: 用户名
            password: 密码
        """
        try:
            # 读取现有数据
            data = {}
            if os.path.exists(self.storage_file):
                with open(self.storage_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            
            # 使用base64编码密码（简单加密）
            encoded_password = base64.b64encode(password.encode('utf-8')).decode('utf-8')
            
            # 保存凭据
            data["saved_username"] = username
            data["saved_password"] = encoded_password
            data["remember_password"] = True
            
            # 写入文件
            with open(self.storage_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存凭据失败: {e}")
    
    def load_credentials(self) -> Optional[Tuple[str, str]]:
        """
        加载保存的用户名和密码
        
        Returns:
            (用户名, 密码) 元组，如果不存在则返回None
        """
        if not os.path.exists(self.storage_file):
            return None
        
        try:
            with open(self.storage_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            username = data.get("saved_username")
            encoded_password = data.get("saved_password")
            remember_password = data.get("remember_password", False)
            
            if username and encoded_password and remember_password:
                # 解码密码
                password = base64.b64decode(encoded_password.encode('utf-8')).decode('utf-8')
                return (username, password)
        except Exception as e:
            print(f"加载凭据失败: {e}")
        
        return None
    
    def clear_credentials(self):
        """清除保存的用户名和密码"""
        try:
            if os.path.exists(self.storage_file):
                with open(self.storage_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # 移除凭据相关字段
                data.pop("saved_username", None)
                data.pop("saved_password", None)
                data["remember_password"] = False
                
                # 写回文件
                with open(self.storage_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"清除凭据失败: {e}")


# 全局存储实例
token_storage = TokenStorage()

