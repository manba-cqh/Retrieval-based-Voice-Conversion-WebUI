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
                # 如果endpoint是完整URL，替换基础URL部分
                base_url_part = API_MODELS.split('/api')[0]
                result = endpoint.replace(base_url_part, self.base_url)
                # 确保末尾斜杠一致
                if endpoint.endswith('/') and not result.endswith('/'):
                    result += '/'
                elif not endpoint.endswith('/') and result.endswith('/'):
                    result = result.rstrip('/')
                return result
            # 如果是相对路径，拼接base_url
            path = endpoint.split('/api')[1] if '/api' in endpoint else endpoint
            # 确保路径以/开头
            if not path.startswith('/'):
                path = '/' + path
            # 保持末尾斜杠
            if endpoint.endswith('/'):
                path = path.rstrip('/') + '/'
            return f"{self.base_url}{path}"
        # 直接返回，保持末尾斜杠
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
    
    async def download_model_package(self, uuid: str, save_path: str, progress_callback=None) -> Dict[str, Any]:
        """
        下载模型压缩包（.7z文件）（异步）
        
        Args:
            uuid: 模型UUID
            save_path: 保存路径
            progress_callback: 进度回调函数，接收 (downloaded, total) 参数
        
        Returns:
            下载结果字典
        """
        import httpx
        import os
        
        # 构建URL，确保路径正确
        base_url = self._get_url(API_MODELS)
        if base_url.endswith('/'):
            base_url = base_url.rstrip('/')
        url = f"{base_url}/by-uuid/{uuid}/package"
        headers = self._get_headers()
        
        try:
            async with httpx.AsyncClient(timeout=300.0) as client:
                async with client.stream("GET", url, headers=headers) as response:
                    response.raise_for_status()
                    
                    # 获取文件大小
                    total_size = int(response.headers.get("content-length", 0))
                    
                    # 确保保存目录存在
                    os.makedirs(os.path.dirname(save_path), exist_ok=True)
                    
                    downloaded = 0
                    with open(save_path, "wb") as f:
                        async for chunk in response.aiter_bytes():
                            f.write(chunk)
                            downloaded += len(chunk)
                            if progress_callback and total_size > 0:
                                progress_callback(downloaded, total_size)
                    
                    return {
                        "success": True,
                        "message": "下载完成",
                        "file_path": save_path,
                        "file_size": downloaded
                    }
        except httpx.HTTPStatusError as e:
            error_msg = "下载失败"
            try:
                error_data = e.response.json()
                error_msg = error_data.get("detail", error_msg)
            except:
                error_msg = f"下载失败: {e.response.status_code}"
            return {
                "success": False,
                "message": error_msg
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"下载失败: {str(e)}"
            }
    
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

