"""认证路由"""
from datetime import timedelta, datetime
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from server.database import get_db
from server.models import User, InvitationCode
from server.schemas import UserCreate, UserResponse, Token, UserLogin
from server.auth import (
    authenticate_user,
    create_access_token,
    get_password_hash,
    get_current_active_user,
    settings
)
from server.schemas import UserResponse as UserResponseSchema

router = APIRouter(prefix="/api/auth", tags=["认证"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """用户注册"""
    # 检查用户名是否已存在
    existing_user = db.query(User).filter(User.username == user_data.username).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户名已存在"
        )
    
    # 检查手机号是否已存在（如果提供）
    if user_data.phone:
        existing_phone = db.query(User).filter(User.phone == user_data.phone).first()
        if existing_phone:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="手机号已被注册"
            )
    
    # 验证邀请码
    invitation_code = db.query(InvitationCode).filter(
        InvitationCode.code == user_data.invitation_code.strip()
    ).first()
    
    if not invitation_code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="邀请码不存在"
        )
    
    if invitation_code.is_used:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="邀请码已被使用"
        )
    
    # 创建新用户
    hashed_password = get_password_hash(user_data.password)
    db_user = User(
        username=user_data.username,
        password_hash=hashed_password,
        phone=user_data.phone,
        email=user_data.email,
        mac=user_data.mac.strip().upper()  # 统一转换为大写
    )
    db.add(db_user)
    db.flush()  # 先刷新以获取用户ID
    
    # 标记邀请码为已使用并关联用户
    invitation_code.is_used = True
    invitation_code.used_by = db_user.id
    invitation_code.used_at = datetime.utcnow()
    
    db.commit()
    db.refresh(db_user)
    
    return db_user


@router.post("/login", response_model=Token)
def login(
    login_data: UserLogin,
    db: Session = Depends(get_db)
):
    """用户登录"""
    user = authenticate_user(db, login_data.username, login_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 验证MAC地址
    client_mac = login_data.mac.strip().upper()
    
    # 如果用户没有MAC地址，拒绝登录（注册时应该已经保存了MAC地址）
    if not user.mac:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="账号未绑定设备，请联系管理员"
        )
    
    # 比对MAC地址，不一致则拒绝登录
    if user.mac != client_mac:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="该账号已在其他设备上登录，一个账号只能在一台设备上使用"
        )
    
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": user.username},
        expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": UserResponseSchema.model_validate(user)
    }


@router.get("/me", response_model=UserResponse)
def get_current_user_info(current_user: User = Depends(get_current_active_user)):
    """获取当前用户信息"""
    return current_user

