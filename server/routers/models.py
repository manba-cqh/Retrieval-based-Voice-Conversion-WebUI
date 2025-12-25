"""模型管理路由"""
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from datetime import datetime, timedelta
import os
from pathlib import Path
from server.database import get_db
from server.models import Model, User, TrialRecord
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


@router.get("/by-uuid/{uuid}/image")
def get_model_image_by_uuid(
    uuid: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """通过UUID获取模型图片文件"""
    model = db.query(Model).filter(
        Model.uid == uuid,
        Model.is_active == True
    ).first()

    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"模型不存在 (UUID: {uuid})"
        )

    # 检查权限
    if not model.is_public and model.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权访问此模型"
        )

    # 根据file_path找到模型目录
    models_base_path = Path(settings.models_base_path)
    if not models_base_path.is_absolute():
        project_root = Path(__file__).parent.parent.parent
        models_base_path = project_root / models_base_path

    # 获取模型目录
    model_dir = models_base_path / Path(model.file_path).parent

    if not model_dir.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="模型目录不存在"
        )

    # 查找图片文件
    image_extensions = [".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp"]
    image_file = None

    # 尝试查找与模型文件同名的图片
    file_name_without_ext = Path(model.file_path).stem
    for ext in image_extensions:
        potential_image = model_dir / (file_name_without_ext + ext)
        if potential_image.exists():
            image_file = potential_image
            break
    
    # 如果没有找到同名图片，查找目录下的任意图片文件
    if not image_file:
        for ext in image_extensions:
            images_in_dir = list(model_dir.glob(f"*{ext}"))
            if images_in_dir:
                image_file = images_in_dir[0]
                break

    if not image_file or not image_file.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="图片文件不存在"
        )

    # 根据文件扩展名确定媒体类型
    media_types = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".bmp": "image/bmp",
        ".gif": "image/gif",
        ".webp": "image/webp"
    }
    media_type = media_types.get(image_file.suffix.lower(), "application/octet-stream")

    return FileResponse(
        path=str(image_file),
        filename=image_file.name,
        media_type=media_type
    )


@router.get("/by-uuid/{uuid}/audio")
def get_model_audio_by_uuid(
    uuid: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """通过UUID获取模型音频文件（用于试听）"""
    model = db.query(Model).filter(
        Model.uid == uuid,
        Model.is_active == True
    ).first()
    
    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"模型不存在 (UUID: {uuid})"
        )
    
    # 检查权限
    if not model.is_public and model.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权访问此模型"
        )
    
    # 根据file_path找到模型目录
    models_base_path = Path(settings.models_base_path)
    if not models_base_path.is_absolute():
        project_root = Path(__file__).parent.parent.parent
        models_base_path = project_root / models_base_path
    
    # 获取模型目录
    model_dir = models_base_path / Path(model.file_path).parent
    
    if not model_dir.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="模型目录不存在"
        )
    
    # 查找音频文件
    audio_extensions = [".wav", ".mp3", ".flac", ".m4a", ".ogg", ".aac"]
    audio_file = None
    
    for ext in audio_extensions:
        audio_files = list(model_dir.glob(f"*{ext}"))
        if audio_files:
            audio_file = audio_files[0]
            break
    
    if not audio_file or not audio_file.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="音频文件不存在"
        )
    
    # 根据文件扩展名确定媒体类型
    media_types = {
        ".wav": "audio/wav",
        ".mp3": "audio/mpeg",
        ".flac": "audio/flac",
        ".m4a": "audio/mp4",
        ".ogg": "audio/ogg",
        ".aac": "audio/aac"
    }
    media_type = media_types.get(audio_file.suffix.lower(), "audio/mpeg")
    
    return FileResponse(
        path=str(audio_file),
        filename=audio_file.name,
        media_type=media_type
    )


@router.get("/trials")
def get_user_trials(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    获取用户的所有试用记录（包括活跃和已结束的）
    """
    # 先更新所有过期试用的状态
    expired_trials = db.query(TrialRecord).filter(
        and_(
            TrialRecord.user_id == current_user.id,
            TrialRecord.is_active == True
        )
    ).all()
    
    now = datetime.utcnow()
    for trial in expired_trials:
        if trial.is_expired():
            trial.is_active = False
    
    db.commit()
    
    # 获取所有试用记录
    trials = db.query(TrialRecord).filter(
        TrialRecord.user_id == current_user.id
    ).order_by(TrialRecord.created_at.desc()).all()
    
    trial_list = []
    for trial in trials:
        remaining_seconds = trial.get_remaining_seconds() if trial.is_active else 0
        trial_list.append({
            "id": trial.id,
            "model_uid": trial.model_uid,
            "model_name": trial.model_name,
            "start_time": trial.start_time.isoformat() if trial.start_time else None,
            "end_time": trial.end_time.isoformat() if trial.end_time else None,
            "duration_seconds": trial.duration_seconds,
            "is_active": trial.is_active,
            "remaining_seconds": remaining_seconds,
            "trial_count": trial.trial_count,
            "created_at": trial.created_at.isoformat() if trial.created_at else None
        })
    
    return {
        "success": True,
        "data": {
            "trials": trial_list,
            "total": len(trial_list),
            "active_count": sum(1 for t in trials if t.is_active)
        }
    }


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


@router.post("/by-uuid/{uuid}/start-trial")
def start_trial(
    uuid: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    开始模型试用
    """
    # 查找模型
    model = db.query(Model).filter(Model.uid == uuid, Model.is_active == True).first()
    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="模型不存在"
        )
    
    # 检查是否为免费模型（免费模型不需要试用）
    if model.price == 0 or model.price is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="免费模型无需试用"
        )
    
    # 检查是否已有正在进行的试用
    existing_trial = db.query(TrialRecord).filter(
        and_(
            TrialRecord.user_id == current_user.id,
            TrialRecord.model_uid == uuid,
            TrialRecord.is_active == True
        )
    ).first()
    
    if existing_trial:
        # 检查是否已过期
        if existing_trial.is_expired():
            existing_trial.is_active = False
            db.commit()
        else:
            # 返回现有试用的剩余时间
            remaining = existing_trial.get_remaining_seconds()
            return {
                "success": True,
                "message": "试用已在进行中",
                "data": {
                    "start_time": existing_trial.start_time.isoformat(),
                    "end_time": existing_trial.end_time.isoformat(),
                    "remaining_seconds": remaining
                }
            }
    
    # 创建新的试用记录
    duration_seconds = 3600  # 默认1小时
    start_time = datetime.utcnow()
    end_time = start_time + timedelta(seconds=duration_seconds)
    
    new_trial = TrialRecord(
        user_id=current_user.id,
        model_uid=uuid,
        model_name=model.name,
        start_time=start_time,
        end_time=end_time,
        duration_seconds=duration_seconds,
        is_active=True,
        trial_count=1
    )
    
    db.add(new_trial)
    db.commit()
    db.refresh(new_trial)
    
    return {
        "success": True,
        "message": "试用已开始",
        "data": {
            "start_time": new_trial.start_time.isoformat(),
            "end_time": new_trial.end_time.isoformat(),
            "remaining_seconds": duration_seconds
        }
    }


@router.get("/by-uuid/{uuid}/trial-status")
def get_trial_status(
    uuid: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    获取模型的试用状态
    """
    # 查找试用记录
    trial = db.query(TrialRecord).filter(
        and_(
            TrialRecord.user_id == current_user.id,
            TrialRecord.model_uid == uuid
        )
    ).order_by(TrialRecord.created_at.desc()).first()
    
    if not trial:
        return {
            "success": True,
            "data": {
                "has_trialed": False,
                "is_active": False,
                "remaining_seconds": 0
            }
        }
    
    # 检查是否已过期
    if trial.is_expired() and trial.is_active:
        trial.is_active = False
        db.commit()
    
    remaining_seconds = trial.get_remaining_seconds() if trial.is_active else 0
    
    return {
        "success": True,
        "data": {
            "has_trialed": True,
            "is_active": trial.is_active,
            "remaining_seconds": remaining_seconds,
            "start_time": trial.start_time.isoformat() if trial.start_time else None,
            "end_time": trial.end_time.isoformat() if trial.end_time else None
        }
    }

