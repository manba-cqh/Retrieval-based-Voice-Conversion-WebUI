"""服务端配置"""
import os
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """应用配置"""
    # 数据库配置
    database_url: str = "sqlite:///data.db"
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # 确保数据库目录存在
        db_path = self.database_url.replace("sqlite:///", "")
        if db_path and not db_path.startswith(":memory:"):
            # 转换为绝对路径
            if not os.path.isabs(db_path):
                # 从项目根目录开始
                project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                db_path = os.path.join(project_root, db_path)
            
            db_dir = os.path.dirname(db_path)
            if db_dir:
                os.makedirs(db_dir, exist_ok=True)
            # 更新 database_url 为绝对路径
            self.database_url = f"sqlite:///{db_path}"
    
    # JWT配置
    secret_key: str = "your-secret-key-change-this-in-production"  # 生产环境请修改
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 7  # 7天
    
    # 服务器配置
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = True
    
    # 模型文件配置
    models_base_path: str = "./models"  # 模型文件存储路径
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()

