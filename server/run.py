"""服务端启动脚本"""
import sys
import os

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

import uvicorn
from server.config import settings


if __name__ == "__main__":
    # 冻结为 exe（例如 PyInstaller 打包）时，必须关闭 reload，
    # 否则 uvicorn 的重载器会不断拉起子进程，造成日志刷屏和内存上涨
    reload_flag = settings.debug
    if getattr(sys, "frozen", False):
        reload_flag = False

    uvicorn.run(
        "server.main:app",
        host=settings.host,
        port=settings.port,
        reload=reload_flag,
        log_level="info"
    )

