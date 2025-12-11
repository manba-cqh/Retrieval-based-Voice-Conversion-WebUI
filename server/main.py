"""FastAPI应用主入口"""
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from server.database import init_db
from server.routers import auth, models
from server.config import settings

# 创建FastAPI应用
app = FastAPI(
    title="RVC模型服务API",
    description="用户认证和模型管理API",
    version="1.0.0"
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境请设置具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(auth.router)
app.include_router(models.router)


@app.on_event("startup")
async def startup_event():
    """应用启动时初始化数据库"""
    import os
    # 确保模型目录存在
    os.makedirs(settings.models_base_path, exist_ok=True)
    
    # 确保数据库目录存在
    db_path = settings.database_url.replace("sqlite:///", "")
    if db_path and not db_path.startswith(":memory:"):
        db_dir = os.path.dirname(db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)
    
    # 初始化数据库
    try:
        init_db()
        print(f"数据库初始化完成")
        print(f"数据库文件路径: {os.path.abspath(db_path) if db_path else '内存数据库'}")
        print(f"模型文件路径: {os.path.abspath(settings.models_base_path)}")
    except Exception as e:
        print(f"数据库初始化失败: {e}")
        raise


@app.get("/")
def root():
    """根路径"""
    return {
        "message": "RVC模型服务API",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health")
def health_check():
    """健康检查"""
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    # 直接运行应用实例，而不是通过字符串引用
    uvicorn.run(
        app,
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )

