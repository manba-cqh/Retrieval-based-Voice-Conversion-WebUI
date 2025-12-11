"""初始化模型数据脚本"""
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from server.database import SessionLocal, init_db
from server.models import Model
from server.utils import calculate_file_hash, get_file_size
from server.config import settings


def scan_and_add_models():
    """扫描模型目录并添加到数据库"""
    db = SessionLocal()
    try:
        # 初始化数据库
        init_db()
        
        # 扫描模型目录
        models_path = settings.models_base_path
        if not os.path.exists(models_path):
            print(f"模型目录不存在: {models_path}")
            return
        
        added_count = 0
        skipped_count = 0
        
        # 遍历模型目录
        for root, dirs, files in os.walk(models_path):
            for file in files:
                # 只处理 .pth 文件（RVC模型文件）
                if file.endswith(('.pth', '.pt', '.onnx', '.index')):
                    file_path = os.path.join(root, file)
                    relative_path = os.path.relpath(file_path, models_path)
                    
                    # 检查是否已存在
                    existing = db.query(Model).filter(
                        Model.file_path == relative_path
                    ).first()
                    
                    if existing:
                        print(f"跳过已存在的模型: {file}")
                        skipped_count += 1
                        continue
                    
                    # 获取文件信息
                    file_size = get_file_size(file_path)
                    file_hash = calculate_file_hash(file_path)
                    
                    # 从文件名提取模型名称
                    model_name = os.path.splitext(file)[0]
                    
                    # 创建模型记录
                    model = Model(
                        name=model_name,
                        file_path=relative_path,
                        file_name=file,
                        file_size=file_size,
                        file_hash=file_hash,
                        is_public=True,
                        is_active=True
                    )
                    
                    db.add(model)
                    added_count += 1
                    print(f"添加模型: {model_name} ({file_size / 1024 / 1024:.2f} MB)")
        
        db.commit()
        print(f"\n完成！添加了 {added_count} 个模型，跳过了 {skipped_count} 个已存在的模型")
        
    except Exception as e:
        db.rollback()
        print(f"错误: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    print("开始扫描并初始化模型数据...")
    scan_and_add_models()

