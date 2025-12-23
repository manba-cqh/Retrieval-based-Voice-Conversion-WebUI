"""数据库模型"""
from typing import List
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Float, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base


class User(Base):
    """用户表"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    phone = Column(String(20), unique=True, index=True, nullable=True)
    email = Column(String(100), nullable=True)
    available_models = Column(Text, nullable=True)  # 可用模型的UUID列表，用分号分隔
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关联关系
    models = relationship("Model", back_populates="owner")
    
    def get_available_model_uids(self) -> List[str]:
        """获取用户可用模型的UUID列表"""
        if not self.available_models:
            return []
        return [uid.strip() for uid in self.available_models.split(";") if uid.strip()]
    
    def add_available_model(self, model_uid: str) -> bool:
        """添加可用模型UUID（如果不存在）"""
        if not model_uid or not model_uid.strip():
            return False
        
        model_uid = model_uid.strip()
        current_uids = self.get_available_model_uids()
        
        if model_uid not in current_uids:
            current_uids.append(model_uid)
            self.available_models = ";".join(current_uids)
            return True
        return False
    
    def remove_available_model(self, model_uid: str) -> bool:
        """移除可用模型UUID（如果存在）"""
        if not model_uid or not model_uid.strip():
            return False
        
        model_uid = model_uid.strip()
        current_uids = self.get_available_model_uids()
        
        if model_uid in current_uids:
            current_uids.remove(model_uid)
            self.available_models = ";".join(current_uids) if current_uids else None
            return True
        return False
    
    def has_available_model(self, model_uid: str) -> bool:
        """检查用户是否有该模型的访问权限"""
        if not model_uid or not model_uid.strip():
            return False
        return model_uid.strip() in self.get_available_model_uids()


class Model(Base):
    """模型表"""
    __tablename__ = "models"
    
    id = Column(Integer, primary_key=True, index=True)
    uid = Column(String(64), nullable=False, unique=True, index=True)  # 唯一标识符（基于文件路径和哈希）
    name = Column(String(200), nullable=False, index=True)
    description = Column(Text, nullable=True)
    file_path = Column(String(500), nullable=False, index=True)  # 服务器上的文件路径（不再唯一）
    file_name = Column(String(200), nullable=False)  # 原始文件名
    file_size = Column(Integer, nullable=False)  # 文件大小（字节）
    file_hash = Column(String(64), nullable=True)  # 文件MD5哈希值
    version = Column(String(20), default="1.0.0")
    category = Column(String(50), nullable=True)  # 模型分类
    tags = Column(String(200), nullable=True)  # 标签，逗号分隔
    price = Column(Float, default=0.0)  # 价格
    download_count = Column(Integer, default=0)  # 下载次数
    is_public = Column(Boolean, default=True)  # 是否公开
    is_active = Column(Boolean, default=True)  # 是否可用
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # 上传者ID，None表示系统模型
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关联关系
    owner = relationship("User", back_populates="models")

