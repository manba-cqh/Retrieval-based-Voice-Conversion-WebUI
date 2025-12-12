"""模型相关API（异步版本）"""
from typing import Optional, Dict, Any, List
import os
import httpx
from .async_client import AsyncAPIClient
from .config import API_MODELS
from .auth import auth_api


class ModelsAPI(AsyncAPIClient):
    """模型API客户端（异步）"""
    
    def __init__(self, base_url: Optional[str] = None):
        """
        初始化API客户端
        
        Args:
            base_url: API基础URL，如果为None则使用默认配置
        """
        super().__init__(base_url=base_url)
    
    def _get_url(self, endpoint: str) -> str:
        """获取完整的API URL"""
        if self.base_url:
            if endpoint.startswith("http"):
                return endpoint.replace(API_MODELS.split('/api')[0], self.base_url)
            return f"{self.base_url}{endpoint.split('/api')[1] if '/api' in endpoint else endpoint}"
        return endpoint
    
    def _get_headers(self) -> Dict[str, str]:
        """获取请求头（包含认证token）"""
        headers = {}
        if auth_api.token:
            headers["Authorization"] = f"Bearer {auth_api.token}"
        return headers
    
    async def get_models(
        self,
        skip: int = 0,
        limit: int = 20,
        category: Optional[str] = None,
        search: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        获取模型列表（异步）
        
        Args:
            skip: 跳过的记录数
            limit: 返回的记录数
            category: 分类筛选
            search: 搜索关键词
        
        Returns:
            模型列表结果字典
        """
        url = self._get_url(API_MODELS)
        params = {
            "skip": skip,
            "limit": limit
        }
        if category:
            params["category"] = category
        if search:
            params["search"] = search
        
        result = await self.get(url, headers=self._get_headers(), params=params)
        
        if result.get("success"):
            data = result.get("data", {})
            result["models"] = data.get("items", [])
            result["total"] = data.get("total", 0)
        
        return result
    
    async def get_model(self, model_id: int) -> Dict[str, Any]:
        """
        获取模型详情（异步）
        
        Args:
            model_id: 模型ID
        
        Returns:
            模型详情字典
        """
        url = f"{self._get_url(API_MODELS)}/{model_id}"
        
        result = await self.get(url, headers=self._get_headers())
        
        if result.get("success"):
            result["model"] = result.get("data")
        
        return result
    
    async def download_model(self, model_id: int, save_path: str) -> Dict[str, Any]:
        """
        下载模型文件（异步）
        
        Args:
            model_id: 模型ID
            save_path: 保存路径
        
        Returns:
            下载结果字典
        """
        url = f"{self._get_url(API_MODELS)}/{model_id}/file"
        headers = self._get_headers()
        
        client = self._get_client()
        
        try:
            async with client.stream("GET", url, headers=headers) as response:
                response.raise_for_status()
                
                # 确保目录存在
                os.makedirs(os.path.dirname(save_path), exist_ok=True)
                
                # 保存文件
                with open(save_path, 'wb') as f:
                    async for chunk in response.aiter_bytes():
                        f.write(chunk)
                
                return {
                    "success": True,
                    "message": "下载成功",
                    "path": save_path
                }
        except httpx.HTTPStatusError as e:
            error_msg = "下载模型失败"
            try:
                error_data = e.response.json()
                error_msg = error_data.get("detail", error_msg)
            except:
                error_msg = f"下载模型失败: {e.response.status_code}"
            return {
                "success": False,
                "message": error_msg
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"下载错误: {str(e)}"
            }


# 全局API实例
models_api = ModelsAPI()

