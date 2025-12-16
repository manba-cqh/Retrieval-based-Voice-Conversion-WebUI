"""模型管理路由"""
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import or_
import os
from pathlib import Path
from server.database import get_db
from server.models import Model, User
from server.schemas import ModelResponse, ModelListResponse, ModelDownloadResponse
from server.auth import get_current_active_user
from server.config import settings

router = APIRouter(prefix="/api/models", tags=["模型"])


@router.post("/sync")
def sync_models(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    手动触发模型同步
    扫描models目录并更新数据库
    """
    try:
        from server.services.model_sync import model_sync_service
        stats = model_sync_service.sync_to_database(db)
        return {
            "success": True,
            "message": "模型同步完成",
            "stats": stats
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"模型同步失败: {str(e)}"
        )


@router.get("/", response_model=ModelListResponse)
def get_models(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=1000),  # 增加最大限制到1000
    category: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """获取模型列表"""
    query = db.query(Model).filter(Model.is_active == True)
    
    # 只显示公开模型或用户自己的模型
    query = query.filter(
        or_(Model.is_public == True, Model.user_id == current_user.id)
    )
    
    # 分类筛选
    if category:
        query = query.filter(Model.category == category)
    
    # 搜索
    if search:
        query = query.filter(
            or_(
                Model.name.contains(search),
                Model.description.contains(search),
                Model.tags.contains(search)
            )
        )
    
    # 获取总数
    total = query.count()
    
    # 分页
    models = query.order_by(Model.created_at.desc()).offset(skip).limit(limit).all()
    
    return {
        "total": total,
        "items": models
    }


@router.get("/by-uuid/{uuid}/package")
def download_model_package_by_uuid(
    uuid: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """通过UUID下载模型压缩包（.7z文件）"""
    # 根据uuid查找模型
    model = db.query(Model).filter(
        Model.uid == uuid,
        Model.is_active == True
    ).first()
    
    if not model:
        print(f"[DEBUG] 未找到UUID为 {uuid} 的模型")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"模型不存在 (UUID: {uuid})"
        )
    
    # 检查权限
    if not model.is_public and model.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权下载此模型"
        )
    
    package_file_str = ''
    if '/' in model.file_path:
        package_file_str = 'models/' + model.file_path.split('/')[0] + '.7z'
    elif '\\' in model.file_path:
        package_file_str = 'models/' + model.file_path.split('\\')[0] + '.7z'
    package_file = Path(package_file_str)
    
    if not package_file or not package_file.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="模型压缩包不存在"
        )
    
    # 更新下载次数
    model.download_count += 1
    db.commit()

    print(f"[DEBUG] 模型压缩包路径: {package_file}")
    
    return FileResponse(
        path=str(package_file),
        filename=package_file.name,
        media_type="application/x-7z-compressed"
    )


@router.get("/{model_id}", response_model=ModelResponse)
def get_model(
    model_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """获取模型详情"""
    model = db.query(Model).filter(
        Model.id == model_id,
        Model.is_active == True
    ).first()
    
    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="模型不存在"
        )
    
    # 检查权限：公开模型或用户自己的模型
    if not model.is_public and model.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权访问此模型"
        )
    
    return model


@router.get("/{model_id}/download", response_model=ModelDownloadResponse)
def download_model(
    model_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """下载模型"""
    model = db.query(Model).filter(
        Model.id == model_id,
        Model.is_active == True
    ).first()
    
    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="模型不存在"
        )
    
    # 检查权限
    if not model.is_public and model.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权下载此模型"
        )
    
    # 检查文件是否存在
    file_path = os.path.join(settings.models_base_path, model.file_path)
    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="模型文件不存在"
        )
    
    # 更新下载次数
    model.download_count += 1
    db.commit()
    
    return {
        "download_url": f"/api/models/{model_id}/file",
        "file_name": model.file_name,
        "file_size": model.file_size
    }


@router.get("/{model_id}/file")
def download_model_file(
    model_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """下载模型文件（实际文件流）"""
    model = db.query(Model).filter(
        Model.id == model_id,
        Model.is_active == True
    ).first()
    
    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="模型不存在"
        )
    
    # 检查权限
    if not model.is_public and model.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权下载此模型"
        )
    
    # 检查文件是否存在
    file_path = os.path.join(settings.models_base_path, model.file_path)
    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="模型文件不存在"
        )
    
    return FileResponse(
        path=file_path,
        filename=model.file_name,
        media_type="application/octet-stream"
    )

