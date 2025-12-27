"""邀请码管理路由"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from datetime import datetime
from server.database import get_db
from server.models import InvitationCode, User
from server.auth import get_current_active_user
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/invitation", tags=["邀请码"])


class InvitationCodeCreate(BaseModel):
    """创建邀请码"""
    code: str = Field(..., min_length=1, max_length=50, description="邀请码")
    note: Optional[str] = Field(None, max_length=200, description="备注")


class InvitationCodeResponse(BaseModel):
    """邀请码响应"""
    id: int
    code: str
    is_used: bool
    used_by: Optional[int] = None
    used_at: Optional[datetime] = None
    created_at: datetime
    created_by: Optional[int] = None
    note: Optional[str] = None
    
    class Config:
        from_attributes = True


class InvitationCodeListResponse(BaseModel):
    """邀请码列表响应"""
    total: int
    items: List[InvitationCodeResponse]


@router.post("/", response_model=InvitationCodeResponse, status_code=status.HTTP_201_CREATED)
def create_invitation_code(
    invitation_data: InvitationCodeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """创建邀请码（需要登录）"""
    # 检查邀请码是否已存在
    existing_code = db.query(InvitationCode).filter(
        InvitationCode.code == invitation_data.code.strip()
    ).first()
    
    if existing_code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="邀请码已存在"
        )
    
    # 创建新邀请码
    db_invitation = InvitationCode(
        code=invitation_data.code.strip(),
        created_by=current_user.id,
        note=invitation_data.note
    )
    db.add(db_invitation)
    db.commit()
    db.refresh(db_invitation)
    
    return db_invitation


@router.get("/", response_model=InvitationCodeListResponse)
def list_invitation_codes(
    skip: int = Query(0, ge=0, description="跳过数量"),
    limit: int = Query(100, ge=1, le=1000, description="返回数量"),
    is_used: Optional[bool] = Query(None, description="筛选是否已使用"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """获取邀请码列表（需要登录）"""
    query = db.query(InvitationCode)
    
    # 筛选是否已使用
    if is_used is not None:
        query = query.filter(InvitationCode.is_used == is_used)
    
    # 获取总数
    total = query.count()
    
    # 分页查询
    items = query.order_by(InvitationCode.created_at.desc()).offset(skip).limit(limit).all()
    
    return {
        "total": total,
        "items": items
    }


@router.get("/{code}", response_model=InvitationCodeResponse)
def get_invitation_code(
    code: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """获取指定邀请码信息（需要登录）"""
    invitation_code = db.query(InvitationCode).filter(
        InvitationCode.code == code.strip()
    ).first()
    
    if not invitation_code:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="邀请码不存在"
        )
    
    return invitation_code


@router.delete("/{code}", status_code=status.HTTP_204_NO_CONTENT)
def delete_invitation_code(
    code: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """删除邀请码（需要登录）"""
    invitation_code = db.query(InvitationCode).filter(
        InvitationCode.code == code.strip()
    ).first()
    
    if not invitation_code:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="邀请码不存在"
        )
    
    if invitation_code.is_used:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="已使用的邀请码不能删除"
        )
    
    db.delete(invitation_code)
    db.commit()
    
    return None

