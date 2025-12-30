"""API配置"""
import os

# 服务端API基础URL
API_BASE_URL = os.getenv("API_BASE_URL", "http://106.54.161.84:8000")

# API端点
API_AUTH_REGISTER = f"{API_BASE_URL}/api/auth/register"
API_AUTH_LOGIN = f"{API_BASE_URL}/api/auth/login"
API_AUTH_ME = f"{API_BASE_URL}/api/auth/me"
API_MODELS = f"{API_BASE_URL}/api/models/"

