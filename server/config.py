"""服务端配置"""
import os
import sys
from pydantic_settings import BaseSettings
from typing import Optional


def get_base_dir():
    """
    获取应用基目录
    打包后的exe使用exe所在目录，开发环境使用当前文件所在目录
    """
    if getattr(sys, 'frozen', False):
        # 打包后的exe环境，使用exe所在目录
        return os.path.dirname(sys.executable)
    else:
        # 开发环境，使用当前文件所在目录（server目录）
        return os.path.dirname(os.path.abspath(__file__))


class Settings(BaseSettings):
    """应用配置"""
    # 数据库配置
    database_url: str = "sqlite:///data.db"
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # 获取基目录
        base_dir = get_base_dir()
        
        # 确保数据库目录存在
        db_path = self.database_url.replace("sqlite:///", "")
        if db_path and not db_path.startswith(":memory:"):
            # 转换为绝对路径
            if not os.path.isabs(db_path):
                # 从基目录开始
                db_path = os.path.join(base_dir, db_path)
            
            db_dir = os.path.dirname(db_path)
            if db_dir:
                os.makedirs(db_dir, exist_ok=True)
            # 更新 database_url 为绝对路径
            self.database_url = f"sqlite:///{db_path}"
        
        # 将模型路径转换为绝对路径
        if not os.path.isabs(self.models_base_path):
            # 如果路径以 ./ 开头，去掉它
            models_path = self.models_base_path
            if models_path.startswith("./"):
                models_path = models_path[2:]
            # 从基目录开始
            self.models_base_path = os.path.join(base_dir, models_path)
    
    # JWT配置
    secret_key: str = "your-secret-key-change-this-in-production"  # 生产环境请修改
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 7  # 7天
    
    # 服务器配置
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = True
    
    # 模型文件配置
    models_base_path: str = "./models"  # 模型文件存储路径（models/XXX/）
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()

