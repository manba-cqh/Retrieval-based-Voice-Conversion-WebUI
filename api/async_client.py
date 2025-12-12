"""通用异步API客户端基类"""
import asyncio
import httpx
from typing import Optional, Dict, Any
from abc import ABC


class AsyncAPIClient(ABC):
    """异步API客户端基类"""
    
    def __init__(self, base_url: Optional[str] = None, timeout: float = 10.0):
        """
        初始化API客户端
        
        Args:
            base_url: API基础URL
            timeout: 请求超时时间（秒）
        """
        self.base_url = base_url
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None
    
    def _get_client(self) -> httpx.AsyncClient:
        """获取或创建HTTP客户端（延迟创建）"""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client
    
    async def _request(
        self,
        method: str,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        files: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        通用异步HTTP请求方法
        
        Args:
            method: HTTP方法（GET, POST, PUT, DELETE等）
            url: 请求URL
            headers: 请求头
            params: URL参数
            data: form-data数据
            json_data: JSON数据
            files: 文件数据
        
        Returns:
            响应结果字典，包含success、data、message等字段
        """
        client = self._get_client()
        
        # 准备请求参数
        request_kwargs = {}
        if headers:
            request_kwargs["headers"] = headers
        if params:
            request_kwargs["params"] = params
        if data:
            request_kwargs["data"] = data
        if json_data:
            request_kwargs["json"] = json_data
        if files:
            request_kwargs["files"] = files
        
        try:
            response = await client.request(method, url, **request_kwargs)
            response.raise_for_status()
            result = response.json()
            
            return {
                "success": True,
                "data": result,
                "status_code": response.status_code
            }
        except httpx.HTTPStatusError as e:
            error_msg = "请求失败"
            try:
                error_data = e.response.json()
                error_msg = error_data.get("detail", error_msg)
            except:
                error_msg = f"请求失败: {e.response.status_code}"
            return {
                "success": False,
                "message": error_msg,
                "status_code": e.response.status_code
            }
        except httpx.RequestError as e:
            return {
                "success": False,
                "message": f"网络错误: {str(e)}"
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"未知错误: {str(e)}"
            }
    
    async def get(self, url: str, headers: Optional[Dict[str, str]] = None, 
                  params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """GET请求"""
        return await self._request("GET", url, headers=headers, params=params)
    
    async def post(self, url: str, headers: Optional[Dict[str, str]] = None,
                   data: Optional[Dict[str, Any]] = None,
                   json_data: Optional[Dict[str, Any]] = None,
                   files: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """POST请求"""
        return await self._request("POST", url, headers=headers, data=data, 
                                  json_data=json_data, files=files)
    
    async def put(self, url: str, headers: Optional[Dict[str, str]] = None,
                  data: Optional[Dict[str, Any]] = None,
                  json_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """PUT请求"""
        return await self._request("PUT", url, headers=headers, data=data, json_data=json_data)
    
    async def delete(self, url: str, headers: Optional[Dict[str, str]] = None,
                     params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """DELETE请求"""
        return await self._request("DELETE", url, headers=headers, params=params)
    
    async def close(self):
        """关闭HTTP客户端"""
        if self._client:
            await self._client.aclose()
            self._client = None

