"""数据库配置和会话管理"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from server.config import settings

# 创建数据库引擎
engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {}
)

# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 创建基础模型类
Base = declarative_base()


def get_db():
    """获取数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """初始化数据库（创建表）"""
    Base.metadata.create_all(bind=engine)
    # 执行迁移（如果数据库已存在）
    _run_migrations()


def _run_migrations():
    """运行数据库迁移"""
    try:
        from sqlalchemy import inspect, text
        from server.models import TrialRecord
        inspector = inspect(engine)
        table_names = inspector.get_table_names()
        
        # 检查 users 表是否存在 available_models 列
        if "users" in table_names:
            # 表已存在，检查列
            columns = [col["name"] for col in inspector.get_columns("users")]
            
            if "available_models" not in columns:
                # 列不存在，添加列
                print("检测到数据库需要迁移：添加 available_models 列...")
                with engine.connect() as conn:
                    conn.execute(text("ALTER TABLE users ADD COLUMN available_models TEXT"))
                    conn.commit()
                print("迁移完成：已添加 available_models 列")
            
            if "mac" not in columns:
                # 列不存在，添加列
                print("检测到数据库需要迁移：添加 mac 列...")
                with engine.connect() as conn:
                    conn.execute(text("ALTER TABLE users ADD COLUMN mac VARCHAR(50)"))
                    conn.commit()
                print("迁移完成：已添加 mac 列")
        
        # 检查 trial_records 表是否存在
        if "trial_records" not in table_names:
            print("检测到数据库需要迁移：创建 trial_records 表...")
            # 创建表
            TrialRecord.__table__.create(bind=engine, checkfirst=True)
            print("迁移完成：已创建 trial_records 表")
    except Exception as e:
        # 如果迁移失败，记录错误但不阻止启动
        print(f"数据库迁移警告: {e}")
        # 不抛出异常，允许应用继续运行

