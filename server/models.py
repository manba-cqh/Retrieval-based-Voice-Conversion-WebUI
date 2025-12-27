"""数据库模型"""
from typing import List
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Float, ForeignKey, Text, Index
from sqlalchemy.orm import relationship
from datetime import datetime, timedelta
from .database import Base


class User(Base):
    """用户表"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    phone = Column(String(20), unique=True, index=True, nullable=True)
    email = Column(String(100), nullable=True)
    mac = Column(String(50), nullable=True, index=True)  # MAC地址，用于设备绑定
    available_models = Column(Text, nullable=True)  # 可用模型的UUID列表，用分号分隔
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关联关系
    models = relationship("Model", back_populates="owner")
    trial_records = relationship("TrialRecord", back_populates="user")
    
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
    # 使用 model_uid 字段关联，而不是外键
    trial_records = relationship(
        "TrialRecord",
        back_populates="model",
        primaryjoin="Model.uid == TrialRecord.model_uid",
        foreign_keys="[TrialRecord.model_uid]",
        viewonly=True  # 只读关系，因为不是标准外键
    )


class TrialRecord(Base):
    """试用记录表 - 存储收费模型的试用记录"""
    __tablename__ = "trial_records"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    model_uid = Column(String(64), nullable=False, index=True)  # 模型UUID
    model_name = Column(String(200), nullable=True)  # 模型名称（冗余字段，方便查询）
    start_time = Column(DateTime, nullable=False, default=datetime.utcnow)  # 试用开始时间
    end_time = Column(DateTime, nullable=False)  # 试用结束时间
    duration_seconds = Column(Integer, default=3600)  # 试用时长（秒），默认1小时
    is_active = Column(Boolean, default=True, index=True)  # 是否正在试用中
    trial_count = Column(Integer, default=1)  # 试用次数（同一模型）
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关联关系
    user = relationship("User", back_populates="trial_records")
    # 使用 model_uid 字段关联，而不是外键
    model = relationship(
        "Model",
        back_populates="trial_records",
        primaryjoin="TrialRecord.model_uid == Model.uid",
        foreign_keys="[TrialRecord.model_uid]",
        viewonly=True  # 只读关系，因为不是标准外键
    )
    
    # 复合索引：用于快速查询用户的活跃试用
    __table_args__ = (
        Index('idx_user_model_active', 'user_id', 'model_uid', 'is_active'),
    )
    
    def get_remaining_seconds(self) -> int:
        """获取剩余试用时间（秒）"""
        if not self.is_active:
            return 0
        now = datetime.utcnow()
        if now >= self.end_time:
            return 0
        return int((self.end_time - now).total_seconds())
    
    def is_expired(self) -> bool:
        """检查试用是否已过期"""
        if not self.is_active:
            return True
        return datetime.utcnow() >= self.end_time


class InvitationCode(Base):
    """邀请码表"""
    __tablename__ = "invitation_codes"
    
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, nullable=False, index=True)  # 邀请码
    is_used = Column(Boolean, default=False, index=True)  # 是否已使用
    used_by = Column(Integer, ForeignKey("users.id"), nullable=True)  # 使用该邀请码的用户ID
    used_at = Column(DateTime, nullable=True)  # 使用时间
    created_at = Column(DateTime, default=datetime.utcnow)  # 创建时间
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)  # 创建者ID（管理员）
    note = Column(String(200), nullable=True)  # 备注
    
    # 关联关系（可选，用于查询时关联用户信息）
    creator = relationship("User", foreign_keys=[created_by], backref="created_invitation_codes")
    user = relationship("User", foreign_keys=[used_by], backref="used_invitation_codes")

