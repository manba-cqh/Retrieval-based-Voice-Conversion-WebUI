"""API配置"""
import os
import sys

# 服务端API基础URL
API_BASE_URL = os.getenv("API_BASE_URL", "http://106.54.161.84:8000")

# 客户端模型下载与读取目录：C 盘下较隐蔽目录，避免用户轻易发现
def _get_client_models_dir():
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA", "")
        if not base:
            base = os.path.join(os.environ.get("USERPROFILE", "C:\\"), "AppData", "Local")
        return os.path.join(base, "Yuyin", "Models")
    return os.path.join(os.path.expanduser("~"), ".yuyin", "models")


CLIENT_MODELS_DIR = _get_client_models_dir()

# API端点
API_AUTH_REGISTER = f"{API_BASE_URL}/api/auth/register"
API_AUTH_LOGIN = f"{API_BASE_URL}/api/auth/login"
API_AUTH_ME = f"{API_BASE_URL}/api/auth/me"
API_MODELS = f"{API_BASE_URL}/api/models/"

