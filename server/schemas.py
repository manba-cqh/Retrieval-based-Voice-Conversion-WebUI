"""Pydantic模型（用于API请求/响应）"""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime


# 用户相关Schema
class UserBase(BaseModel):
    """用户基础信息"""
    username: str = Field(..., min_length=3, max_length=50)
    phone: Optional[str] = Field(None, pattern=r'^1[3-9]\d{9}$')
    email: Optional[EmailStr] = None


class UserCreate(UserBase):
    """用户注册"""
    password: str = Field(..., min_length=6, max_length=50)


class UserLogin(BaseModel):
    """用户登录"""
    username: str
    password: str


class UserResponse(UserBase):
    """用户响应"""
    id: int
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True
        populate_by_name = True


class Token(BaseModel):
    """Token响应"""
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


# 模型相关Schema
class ModelBase(BaseModel):
    """模型基础信息"""
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    version: str = "1.0.0"
    category: Optional[str] = None
    tags: Optional[str] = None


class ModelCreate(ModelBase):
    """创建模型（管理员）"""
    file_path: str
    file_name: str
    file_size: int
    file_hash: Optional[str] = None


class ModelResponse(ModelBase):
    """模型响应"""
    id: int
    file_name: str
    file_size: int
    download_count: int
    is_public: bool
    is_active: bool
    user_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class ModelListResponse(BaseModel):
    """模型列表响应"""
    total: int
    items: List[ModelResponse]


class ModelDownloadResponse(BaseModel):
    """模型下载响应"""
    download_url: str
    file_name: str
    file_size: int

