"""模型同步服务 - 自动扫描models目录并更新数据库"""
import os
import json
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, List
from sqlalchemy.orm import Session
from server.database import SessionLocal
from server.models import Model
from server.config import settings


class ModelSyncService:
    """模型同步服务"""
    
    def __init__(self, models_base_paths: Optional[List[str]] = None):
        """
        初始化模型同步服务
        
        Args:
            models_base_paths: 模型文件基础路径列表，如果为None则使用默认路径
        """
        import sys
        
        # 获取基目录（打包后使用exe目录，开发环境使用server目录）
        if getattr(sys, 'frozen', False):
            # 打包后的exe环境，使用exe所在目录
            base_dir = Path(sys.executable).parent
        else:
            # 开发环境，使用server目录
            base_dir = Path(__file__).parent.parent
        
        if models_base_paths is None:
            # 默认只扫描基目录下的 models 目录
            default_paths = ["./models"]
            models_base_paths = default_paths
        
        # 转换为绝对路径列表
        self.models_base_paths = []
        for path_str in models_base_paths:
            path = Path(path_str)
            if not path.is_absolute():
                # 如果路径以 ./ 开头，需要去掉
                if str(path).startswith("./"):
                    path = Path(str(path)[2:])
                path = base_dir / path
            self.models_base_paths.append(path)
        
        # 保持向后兼容：第一个路径作为主路径
        self.models_base_path = self.models_base_paths[0] if self.models_base_paths else None
    
    def scan_models(self) -> List[Dict]:
        """
        扫描所有配置的models目录，返回所有找到的模型信息
        
        Returns:
            模型信息列表
        """
        models = []
        
        # 遍历所有配置的模型目录
        for models_base_path in self.models_base_paths:
            if not models_base_path.exists():
                print(f"模型目录不存在，跳过: {models_base_path}")
                continue
            
            print(f"扫描模型目录: {models_base_path}")
            
            # 遍历该目录下的所有子目录
            for model_dir in models_base_path.iterdir():
                if not model_dir.is_dir():
                    continue
                
                model_info = self._scan_model_directory(model_dir, models_base_path)
                if model_info:
                    models.append(model_info)
        
        return models
    
    def _scan_model_directory(self, model_dir: Path, base_path: Path) -> Optional[Dict]:
        """
        扫描单个模型目录
        
        Args:
            model_dir: 模型目录路径
            base_path: 基础路径（用于计算相对路径）
        
        Returns:
            模型信息字典，如果目录无效则返回None
        """
        # 查找.pth文件
        pth_files = list(model_dir.glob("*.pth"))
        if not pth_files:
            print(f"  跳过目录 {model_dir.name}: 未找到.pth文件")
            return None
        
        print(f"  找到模型目录: {model_dir.name}, .pth文件: {pth_files[0].name}")
        
        pth_file = pth_files[0]  # 使用第一个找到的.pth文件
        
        # 查找.index文件
        index_files = list(model_dir.glob("*.index"))
        index_file = index_files[0] if index_files else None
        
        # 查找info.json文件
        info_json_path = model_dir / "info.json"
        if not info_json_path.exists():
            print(f"  跳过目录 {model_dir.name}: 未找到info.json文件")
            return None
        
        model_info = {}
        try:
            with open(info_json_path, 'r', encoding='utf-8') as f:
                model_info = json.load(f)
        except Exception as e:
            print(f"读取模型信息文件失败 {info_json_path}: {e}")
            return None
        
        # 从info.json中读取uuid（必需字段）
        uid = model_info.get("uuid") or model_info.get("uid")
        if not uid:
            print(f"  跳过目录 {model_dir.name}: info.json中未找到uuid字段")
            return None
        
        # 查找图片文件
        image_extensions = [".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp"]
        image_file = None
        for ext in image_extensions:
            image_files = list(model_dir.glob(f"*{ext}"))
            if image_files:
                image_file = image_files[0]
                break
        
        # 计算文件大小和哈希值
        file_size = pth_file.stat().st_size
        file_hash = self._calculate_file_hash(pth_file)
        
        # 获取文件修改时间
        json_mtime = info_json_path.stat().st_mtime
        pth_mtime = pth_file.stat().st_mtime
        
        # 构建相对路径（相对于base_path）
        relative_path = pth_file.relative_to(base_path)
        
        # 从info.json读取is_public字段，默认为True（公开）
        is_public = model_info.get("is_public", True)
        # 支持多种格式：true/false, "true"/"false", 1/0
        if isinstance(is_public, str):
            is_public = is_public.lower() in ("true", "1", "yes")
        elif isinstance(is_public, int):
            is_public = bool(is_public)
        
        return {
            "uid": uid,
            "name": model_info.get("name", model_dir.name),
            "description": model_info.get("description", ""),
            "version": model_info.get("version", "1.0.0"),
            "category": model_info.get("category", ""),
            "tags": model_info.get("tags", ""),
            "sample_rate": model_info.get("sample_rate", "48K"),
            "is_public": is_public,
            "file_path": str(relative_path),
            "file_name": pth_file.name,
            "file_size": file_size,
            "file_hash": file_hash,
            "pth_file": pth_file,
            "index_file": index_file,
            "image_file": image_file,
            "json_mtime": json_mtime,
            "pth_mtime": pth_mtime,
            "model_dir": model_dir,
        }
    
    def _calculate_file_hash(self, file_path: Path) -> str:
        """
        计算文件的MD5哈希值
        
        Args:
            file_path: 文件路径
        
        Returns:
            MD5哈希值（十六进制字符串）
        """
        hash_md5 = hashlib.md5()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except Exception as e:
            print(f"计算文件哈希失败 {file_path}: {e}")
            return ""
    
    def sync_to_database(self, db: Optional[Session] = None) -> Dict[str, int]:
        """
        将扫描到的模型同步到数据库
        
        Args:
            db: 数据库会话，如果为None则创建新会话
        
        Returns:
            同步结果统计字典
        """
        should_close = False
        if db is None:
            db = SessionLocal()
            should_close = True
        
        try:
            # 扫描所有模型
            scanned_models = self.scan_models()
            print(f"扫描到 {len(scanned_models)} 个模型")
            
            if len(scanned_models) == 0:
                print("警告: 没有扫描到任何模型，请检查模型目录路径和文件")
            
            stats = {
                "total": len(scanned_models),
                "created": 0,
                "updated": 0,
                "skipped": 0,
                "errors": 0
            }
            
            for model_data in scanned_models:
                # 确保有uid（从info.json读取的）
                uid = model_data.get("uid")
                if not uid:
                    print(f"跳过模型 {model_data.get('name', 'unknown')}: 没有uid")
                    stats["skipped"] += 1
                    continue
                
                print(f"处理模型: {model_data.get('name')} - UID: {uid}")
                try:
                    # 使用uid查找数据库中是否已存在该模型
                    existing_model = db.query(Model).filter(
                        Model.uid == uid
                    ).first()
                    
                    if existing_model:
                        # 检查是否需要更新
                        needs_update = False
                        update_reasons = []
                        
                        # 检查文件哈希是否变化
                        if existing_model.file_hash != model_data["file_hash"]:
                            needs_update = True
                            update_reasons.append("文件哈希变化")
                        
                        # 检查JSON文件修改时间（如果存在）
                        if model_data.get("json_mtime"):
                            # 如果JSON文件修改时间比数据库更新时间新，也需要更新
                            if existing_model.updated_at:
                                json_mtime_dt = datetime.fromtimestamp(model_data["json_mtime"])
                                db_updated_at = existing_model.updated_at.replace(tzinfo=None) if existing_model.updated_at.tzinfo else existing_model.updated_at
                                if json_mtime_dt > db_updated_at:
                                    needs_update = True
                                    update_reasons.append("JSON文件更新")
                        
                        # 检查关键字段是否有变化（即使文件哈希没变，info.json内容可能变了）
                        if (existing_model.name != model_data["name"] or
                            existing_model.description != model_data.get("description", "") or
                            existing_model.category != model_data.get("category") or
                            existing_model.tags != model_data.get("tags") or
                            existing_model.version != model_data.get("version", "1.0.0") or
                            existing_model.is_public != model_data.get("is_public", True)):
                            needs_update = True
                            update_reasons.append("模型信息变化")
                        
                        if needs_update:
                            # 更新模型信息
                            print(f"更新模型: {model_data['name']} - 原因: {', '.join(update_reasons)}")
                            existing_model.name = model_data["name"]
                            existing_model.description = model_data.get("description", "")
                            existing_model.version = model_data.get("version", "1.0.0")
                            existing_model.category = model_data.get("category")
                            existing_model.tags = model_data.get("tags")
                            existing_model.is_public = model_data.get("is_public", True)
                            existing_model.file_name = model_data["file_name"]
                            existing_model.file_size = model_data["file_size"]
                            existing_model.file_hash = model_data["file_hash"]
                            existing_model.updated_at = datetime.utcnow()
                            existing_model.is_active = True
                            
                            stats["updated"] += 1
                        else:
                            print(f"跳过模型: {model_data['name']} - 无需更新")
                            stats["skipped"] += 1
                    else:
                        # 创建新模型记录
                        print(f"创建新模型: {model_data['name']} - UID: {uid}, is_public: {model_data.get('is_public', True)}")
                        new_model = Model(
                            uid=uid,
                            name=model_data["name"],
                            description=model_data.get("description", ""),
                            version=model_data.get("version", "1.0.0"),
                            category=model_data.get("category"),
                            tags=model_data.get("tags"),
                            file_path=model_data["file_path"],
                            file_name=model_data["file_name"],
                            file_size=model_data["file_size"],
                            file_hash=model_data["file_hash"],
                            is_public=model_data.get("is_public", True),  # 从info.json读取，默认True
                            is_active=True,
                            user_id=None  # 系统模型
                        )
                        db.add(new_model)
                        stats["created"] += 1
                    
                except Exception as e:
                    print(f"同步模型失败 {model_data.get('name', 'unknown')}: {e}")
                    stats["errors"] += 1
            
            # 提交更改
            db.commit()
            print(f"数据库提交成功: 创建={stats['created']}, 更新={stats['updated']}, 跳过={stats['skipped']}, 错误={stats['errors']}")
            
            return stats
            
        except Exception as e:
            db.rollback()
            print(f"同步模型到数据库失败: {e}")
            raise
        finally:
            if should_close:
                db.close()
    
    def sync(self) -> Dict[str, int]:
        """
        执行完整的同步操作（扫描并更新数据库）
        
        Returns:
            同步结果统计字典
        """
        print(f"开始同步模型，扫描目录: {', '.join([str(p) for p in self.models_base_paths])}")
        stats = self.sync_to_database()
        print(f"模型同步完成: 总计={stats['total']}, "
              f"新建={stats['created']}, 更新={stats['updated']}, "
              f"跳过={stats['skipped']}, 错误={stats['errors']}")
        return stats


# 全局服务实例（扫描 server/models 和 models 两个目录）
model_sync_service = ModelSyncService()


def start_file_watcher():
    """
    启动文件监听服务（后台任务）
    监听models目录的变化，自动同步到数据库
    """
    import threading
    import time
    
    try:
        from watchfiles import watch
    except ImportError:
        print("警告: watchfiles未安装，文件监听功能不可用。请运行: pip install watchfiles")
        return None
    
    def watch_models():
        """文件监听线程函数"""
        # 监听所有配置的模型目录
        models_paths = [str(path) for path in model_sync_service.models_base_paths if path.exists()]
        
        if not models_paths:
            print(f"没有可用的模型目录，无法启动文件监听")
            return
        
        print(f"开始监听模型目录: {', '.join(models_paths)}")
        
        # 过滤函数：只关注info.json和.pth文件的变化
        def watch_filter(change, path: str) -> bool:
            path_obj = Path(path)
            # 只关注info.json和.pth文件
            if path_obj.name == "info.json" or path_obj.suffix == ".pth":
                return True
            return False
        
        try:
            # 监听所有模型目录
            for changes in watch(
                *models_paths,  # 传入多个路径
                watch_filter=watch_filter,
                recursive=True,
                debounce=2000,  # 2秒防抖，避免频繁触发
                step=500  # 500ms检查一次
            ):
                if changes:
                    # changes已经是过滤后的结果
                    print(f"检测到模型文件变化: {len(changes)} 个文件")
                    # 等待一小段时间，确保文件写入完成
                    time.sleep(1)
                    # 执行同步
                    try:
                        stats = model_sync_service.sync()
                        print(f"自动同步完成: 总计={stats['total']}, "
                              f"新建={stats['created']}, 更新={stats['updated']}, "
                              f"跳过={stats['skipped']}, 错误={stats['errors']}")
                    except Exception as e:
                        print(f"自动同步失败: {e}")
                        import traceback
                        traceback.print_exc()
        except Exception as e:
            print(f"文件监听出错: {e}")
            import traceback
            traceback.print_exc()
    
    # 在后台线程中启动监听
    watcher_thread = threading.Thread(target=watch_models, daemon=True)
    watcher_thread.start()
    return watcher_thread

