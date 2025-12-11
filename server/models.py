"""数据库模型"""
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
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关联关系
    models = relationship("Model", back_populates="owner")


class Model(Base):
    """模型表"""
    __tablename__ = "models"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False, index=True)
    description = Column(Text, nullable=True)
    file_path = Column(String(500), nullable=False)  # 服务器上的文件路径
    file_name = Column(String(200), nullable=False)  # 原始文件名
    file_size = Column(Integer, nullable=False)  # 文件大小（字节）
    file_hash = Column(String(64), nullable=True)  # 文件MD5哈希值
    version = Column(String(20), default="1.0.0")
    category = Column(String(50), nullable=True)  # 模型分类
    tags = Column(String(200), nullable=True)  # 标签，逗号分隔
    download_count = Column(Integer, default=0)  # 下载次数
    is_public = Column(Boolean, default=True)  # 是否公开
    is_active = Column(Boolean, default=True)  # 是否可用
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # 上传者ID，None表示系统模型
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关联关系
    owner = relationship("User", back_populates="models")

