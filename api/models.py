"""模型相关API"""
import requests
from typing import Optional, Dict, Any, List
from .config import API_MODELS
from .auth import auth_api


class ModelsAPI:
    """模型API客户端"""
    
    def __init__(self, base_url: Optional[str] = None):
        """
        初始化API客户端
        
        Args:
            base_url: API基础URL，如果为None则使用默认配置
        """
        self.base_url = base_url
    
    def _get_url(self, endpoint: str) -> str:
        """获取完整的API URL"""
        if self.base_url:
            return f"{self.base_url}{endpoint.replace(API_MODELS.split('/api')[0], '')}"
        return endpoint
    
    def _get_headers(self) -> Dict[str, str]:
        """获取请求头（包含认证token）"""
        headers = {}
        if auth_api.token:
            headers["Authorization"] = f"Bearer {auth_api.token}"
        return headers
    
    def get_models(
        self,
        skip: int = 0,
        limit: int = 20,
        category: Optional[str] = None,
        search: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        获取模型列表
        
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
        
        try:
            response = requests.get(
                url,
                params=params,
                headers=self._get_headers(),
                timeout=10
            )
            response.raise_for_status()
            result = response.json()
            return {
                "success": True,
                "data": result,
                "models": result.get("items", []),
                "total": result.get("total", 0)
            }
        except requests.exceptions.HTTPError as e:
            error_msg = "获取模型列表失败"
            try:
                error_data = e.response.json()
                error_msg = error_data.get("detail", error_msg)
            except:
                error_msg = f"获取模型列表失败: {e.response.status_code}"
            return {
                "success": False,
                "message": error_msg
            }
        except requests.exceptions.RequestException as e:
            return {
                "success": False,
                "message": f"网络错误: {str(e)}"
            }
    
    def get_model(self, model_id: int) -> Dict[str, Any]:
        """
        获取模型详情
        
        Args:
            model_id: 模型ID
        
        Returns:
            模型详情字典
        """
        url = f"{self._get_url(API_MODELS)}/{model_id}"
        
        try:
            response = requests.get(
                url,
                headers=self._get_headers(),
                timeout=10
            )
            response.raise_for_status()
            result = response.json()
            return {
                "success": True,
                "data": result,
                "model": result
            }
        except requests.exceptions.HTTPError as e:
            error_msg = "获取模型详情失败"
            try:
                error_data = e.response.json()
                error_msg = error_data.get("detail", error_msg)
            except:
                error_msg = f"获取模型详情失败: {e.response.status_code}"
            return {
                "success": False,
                "message": error_msg
            }
        except requests.exceptions.RequestException as e:
            return {
                "success": False,
                "message": f"网络错误: {str(e)}"
            }
    
    def download_model(self, model_id: int, save_path: str) -> Dict[str, Any]:
        """
        下载模型文件
        
        Args:
            model_id: 模型ID
            save_path: 保存路径
        
        Returns:
            下载结果字典
        """
        url = f"{self._get_url(API_MODELS)}/{model_id}/file"
        
        try:
            response = requests.get(
                url,
                headers=self._get_headers(),
                stream=True,
                timeout=30
            )
            response.raise_for_status()
            
            # 保存文件
            import os
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            
            with open(save_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            return {
                "success": True,
                "message": "下载成功",
                "path": save_path
            }
        except requests.exceptions.HTTPError as e:
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
        except requests.exceptions.RequestException as e:
            return {
                "success": False,
                "message": f"网络错误: {str(e)}"
            }


# 全局API实例
models_api = ModelsAPI()

