#!/usr/bin/env python3
"""
Dify API客户端

该模块负责与Dify平台的API通信：
- 应用管理
- 对话管理
- 知识库集成
- 工作流执行
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional, Union
from datetime import datetime
import json
import aiohttp
import time

from backend.config.settings import get_settings
from backend.utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()

class DifyAPIError(Exception):
    """Dify API错误"""
    
    def __init__(self, message: str, status_code: int = None, response_data: Dict = None):
        self.message = message
        self.status_code = status_code
        self.response_data = response_data
        super().__init__(self.message)

class DifyClient:
    """
    Dify API客户端
    
    提供与Dify平台的完整API交互功能。
    """
    
    def __init__(self, api_key: str = None, base_url: str = None, timeout: int = 30):
        self.api_key = api_key or getattr(settings, 'DIFY_API_KEY', None)
        self.base_url = (base_url or getattr(settings, 'DIFY_BASE_URL', 'https://api.dify.ai')).rstrip('/')
        self.timeout = timeout
        
        if not self.api_key:
            raise ValueError("Dify API密钥未配置")
        
        self.session = None
        self._rate_limit_remaining = 100
        self._rate_limit_reset = time.time()
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self._ensure_session()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.close()
    
    async def _ensure_session(self):
        """确保HTTP会话存在"""
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            self.session = aiohttp.ClientSession(
                timeout=timeout,
                headers={
                    'Authorization': f'Bearer {self.api_key}',
                    'Content-Type': 'application/json',
                    'User-Agent': 'ERAG-System/1.0'
                }
            )
    
    async def close(self):
        """关闭HTTP会话"""
        if self.session and not self.session.closed:
            await self.session.close()
    
    async def _make_request(self, method: str, endpoint: str, 
                          data: Dict = None, params: Dict = None,
                          files: Dict = None) -> Dict[str, Any]:
        """
        发起HTTP请求
        
        参数:
            method: HTTP方法
            endpoint: API端点
            data: 请求数据
            params: 查询参数
            files: 文件数据
        
        返回:
            Dict[str, Any]: 响应数据
        """
        await self._ensure_session()
        await self._check_rate_limit()
        
        url = f"{self.base_url}{endpoint}"
        
        try:
            # 准备请求参数
            kwargs = {
                'params': params
            }
            
            if files:
                # 文件上传请求
                form_data = aiohttp.FormData()
                for key, value in (data or {}).items():
                    form_data.add_field(key, str(value))
                for key, file_data in files.items():
                    form_data.add_field(key, file_data)
                kwargs['data'] = form_data
                # 移除Content-Type头，让aiohttp自动设置
                headers = dict(self.session.headers)
                headers.pop('Content-Type', None)
                kwargs['headers'] = headers
            elif data:
                kwargs['json'] = data
            
            async with self.session.request(method, url, **kwargs) as response:
                # 更新速率限制信息
                self._update_rate_limit(response.headers)
                
                response_text = await response.text()
                
                if response.status >= 400:
                    try:
                        error_data = json.loads(response_text)
                    except json.JSONDecodeError:
                        error_data = {"message": response_text}
                    
                    raise DifyAPIError(
                        f"Dify API错误: {error_data.get('message', 'Unknown error')}",
                        status_code=response.status,
                        response_data=error_data
                    )
                
                try:
                    return json.loads(response_text)
                except json.JSONDecodeError:
                    return {"raw_response": response_text}
        
        except aiohttp.ClientError as e:
            logger.error(f"Dify API请求失败: {e}")
            raise DifyAPIError(f"网络请求失败: {e}")
    
    async def _check_rate_limit(self):
        """检查速率限制"""
        current_time = time.time()
        
        if current_time < self._rate_limit_reset and self._rate_limit_remaining <= 0:
            sleep_time = self._rate_limit_reset - current_time
            logger.warning(f"达到速率限制，等待 {sleep_time:.2f} 秒")
            await asyncio.sleep(sleep_time)
    
    def _update_rate_limit(self, headers: Dict[str, str]):
        """更新速率限制信息"""
        if 'X-RateLimit-Remaining' in headers:
            self._rate_limit_remaining = int(headers['X-RateLimit-Remaining'])
        
        if 'X-RateLimit-Reset' in headers:
            self._rate_limit_reset = int(headers['X-RateLimit-Reset'])
    
    # 应用管理API
    async def get_applications(self) -> List[Dict[str, Any]]:
        """
        获取应用列表
        
        返回:
            List[Dict[str, Any]]: 应用列表
        """
        response = await self._make_request('GET', '/v1/apps')
        return response.get('data', [])
    
    async def get_application(self, app_id: str) -> Dict[str, Any]:
        """
        获取应用详情
        
        参数:
            app_id: 应用ID
        
        返回:
            Dict[str, Any]: 应用详情
        """
        response = await self._make_request('GET', f'/v1/apps/{app_id}')
        return response.get('data', {})
    
    async def create_application(self, name: str, description: str = None,
                               app_type: str = 'chatbot') -> Dict[str, Any]:
        """
        创建应用
        
        参数:
            name: 应用名称
            description: 应用描述
            app_type: 应用类型
        
        返回:
            Dict[str, Any]: 创建的应用信息
        """
        data = {
            'name': name,
            'type': app_type
        }
        if description:
            data['description'] = description
        
        response = await self._make_request('POST', '/v1/apps', data=data)
        return response.get('data', {})
    
    # 对话管理API
    async def create_conversation(self, app_id: str, user_id: str = None) -> Dict[str, Any]:
        """
        创建对话
        
        参数:
            app_id: 应用ID
            user_id: 用户ID
        
        返回:
            Dict[str, Any]: 对话信息
        """
        data = {}
        if user_id:
            data['user'] = user_id
        
        response = await self._make_request(
            'POST', f'/v1/apps/{app_id}/conversations', data=data
        )
        return response.get('data', {})
    
    async def send_message(self, app_id: str, conversation_id: str, 
                         message: str, user_id: str = None,
                         files: List[str] = None) -> Dict[str, Any]:
        """
        发送消息
        
        参数:
            app_id: 应用ID
            conversation_id: 对话ID
            message: 消息内容
            user_id: 用户ID
            files: 文件ID列表
        
        返回:
            Dict[str, Any]: 消息响应
        """
        data = {
            'inputs': {},
            'query': message,
            'response_mode': 'blocking',
            'conversation_id': conversation_id
        }
        
        if user_id:
            data['user'] = user_id
        
        if files:
            data['files'] = files
        
        response = await self._make_request(
            'POST', f'/v1/apps/{app_id}/chat-messages', data=data
        )
        return response
    
    async def get_conversation_messages(self, app_id: str, conversation_id: str,
                                      limit: int = 20, offset: int = 0) -> List[Dict[str, Any]]:
        """
        获取对话消息
        
        参数:
            app_id: 应用ID
            conversation_id: 对话ID
            limit: 限制数量
            offset: 偏移量
        
        返回:
            List[Dict[str, Any]]: 消息列表
        """
        params = {
            'conversation_id': conversation_id,
            'limit': limit,
            'offset': offset
        }
        
        response = await self._make_request(
            'GET', f'/v1/apps/{app_id}/messages', params=params
        )
        return response.get('data', [])
    
    # 知识库管理API
    async def get_datasets(self) -> List[Dict[str, Any]]:
        """
        获取知识库列表
        
        返回:
            List[Dict[str, Any]]: 知识库列表
        """
        response = await self._make_request('GET', '/v1/datasets')
        return response.get('data', [])
    
    async def create_dataset(self, name: str, description: str = None) -> Dict[str, Any]:
        """
        创建知识库
        
        参数:
            name: 知识库名称
            description: 知识库描述
        
        返回:
            Dict[str, Any]: 创建的知识库信息
        """
        data = {'name': name}
        if description:
            data['description'] = description
        
        response = await self._make_request('POST', '/v1/datasets', data=data)
        return response.get('data', {})
    
    async def upload_document(self, dataset_id: str, file_content: bytes,
                            filename: str, document_type: str = 'text') -> Dict[str, Any]:
        """
        上传文档到知识库
        
        参数:
            dataset_id: 知识库ID
            file_content: 文件内容
            filename: 文件名
            document_type: 文档类型
        
        返回:
            Dict[str, Any]: 上传结果
        """
        files = {
            'file': file_content
        }
        
        data = {
            'name': filename,
            'indexing_technique': 'high_quality',
            'process_rule': {
                'mode': 'automatic'
            }
        }
        
        response = await self._make_request(
            'POST', f'/v1/datasets/{dataset_id}/documents', 
            data=data, files=files
        )
        return response.get('data', {})
    
    async def get_dataset_documents(self, dataset_id: str, 
                                  limit: int = 20, offset: int = 0) -> List[Dict[str, Any]]:
        """
        获取知识库文档列表
        
        参数:
            dataset_id: 知识库ID
            limit: 限制数量
            offset: 偏移量
        
        返回:
            List[Dict[str, Any]]: 文档列表
        """
        params = {
            'limit': limit,
            'offset': offset
        }
        
        response = await self._make_request(
            'GET', f'/v1/datasets/{dataset_id}/documents', params=params
        )
        return response.get('data', [])
    
    async def search_dataset(self, dataset_id: str, query: str, 
                           top_k: int = 5) -> List[Dict[str, Any]]:
        """
        搜索知识库
        
        参数:
            dataset_id: 知识库ID
            query: 搜索查询
            top_k: 返回结果数量
        
        返回:
            List[Dict[str, Any]]: 搜索结果
        """
        data = {
            'query': query,
            'retrieval_model': {
                'search_method': 'semantic_search',
                'reranking_enable': True,
                'top_k': top_k
            }
        }
        
        response = await self._make_request(
            'POST', f'/v1/datasets/{dataset_id}/retrieve', data=data
        )
        return response.get('data', [])
    
    # 工作流API
    async def run_workflow(self, app_id: str, inputs: Dict[str, Any],
                         user_id: str = None) -> Dict[str, Any]:
        """
        运行工作流
        
        参数:
            app_id: 应用ID
            inputs: 输入参数
            user_id: 用户ID
        
        返回:
            Dict[str, Any]: 工作流执行结果
        """
        data = {
            'inputs': inputs,
            'response_mode': 'blocking'
        }
        
        if user_id:
            data['user'] = user_id
        
        response = await self._make_request(
            'POST', f'/v1/apps/{app_id}/workflows/run', data=data
        )
        return response
    
    async def get_workflow_logs(self, app_id: str, workflow_run_id: str) -> Dict[str, Any]:
        """
        获取工作流执行日志
        
        参数:
            app_id: 应用ID
            workflow_run_id: 工作流运行ID
        
        返回:
            Dict[str, Any]: 执行日志
        """
        response = await self._make_request(
            'GET', f'/v1/apps/{app_id}/workflows/runs/{workflow_run_id}/logs'
        )
        return response.get('data', {})
    
    # 文件管理API
    async def upload_file(self, file_content: bytes, filename: str,
                        purpose: str = 'document') -> Dict[str, Any]:
        """
        上传文件
        
        参数:
            file_content: 文件内容
            filename: 文件名
            purpose: 文件用途
        
        返回:
            Dict[str, Any]: 文件信息
        """
        files = {
            'file': file_content
        }
        
        data = {
            'purpose': purpose
        }
        
        response = await self._make_request(
            'POST', '/v1/files/upload', data=data, files=files
        )
        return response.get('data', {})
    
    async def get_file(self, file_id: str) -> Dict[str, Any]:
        """
        获取文件信息
        
        参数:
            file_id: 文件ID
        
        返回:
            Dict[str, Any]: 文件信息
        """
        response = await self._make_request('GET', f'/v1/files/{file_id}')
        return response.get('data', {})
    
    # 健康检查
    async def health_check(self) -> bool:
        """
        健康检查
        
        返回:
            bool: 服务是否健康
        """
        try:
            await self._make_request('GET', '/v1/apps')
            return True
        except Exception as e:
            logger.error(f"Dify健康检查失败: {e}")
            return False
    
    # 统计信息
    async def get_usage_statistics(self, app_id: str = None, 
                                 start_date: str = None, 
                                 end_date: str = None) -> Dict[str, Any]:
        """
        获取使用统计
        
        参数:
            app_id: 应用ID（可选）
            start_date: 开始日期
            end_date: 结束日期
        
        返回:
            Dict[str, Any]: 统计信息
        """
        params = {}
        if start_date:
            params['start'] = start_date
        if end_date:
            params['end'] = end_date
        
        endpoint = '/v1/apps/statistics'
        if app_id:
            endpoint = f'/v1/apps/{app_id}/statistics'
        
        response = await self._make_request('GET', endpoint, params=params)
        return response.get('data', {})