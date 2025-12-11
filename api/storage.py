"""Token存储管理"""
import json
import os
from typing import Optional


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


# 全局存储实例
token_storage = TokenStorage()

