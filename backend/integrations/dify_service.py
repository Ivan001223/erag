#!/usr/bin/env python3
"""
Dify集成服务

该模块提供Dify平台的高级业务逻辑封装：
- 智能对话服务
- 知识库同步
- 工作流自动化
- 企业级集成
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional, Union, AsyncGenerator
from datetime import datetime, timedelta
import json
from dataclasses import dataclass
from enum import Enum

from backend.integrations.dify_client import DifyClient, DifyAPIError
from backend.core.knowledge_graph.graph_manager import GraphManager
from backend.core.llm.llm_orchestrator import LLMOrchestrator
from backend.core.vector.vector_store import VectorStore
from backend.core.vector.embedder import Embedder
from backend.services.vector_service import VectorService
from backend.models.database import DocumentModel
from backend.models.conversation import Conversation, Message
from backend.services.cache_service import CacheService
from backend.utils.logger import get_logger
from backend.config.settings import get_settings

logger = get_logger(__name__)
settings = get_settings()

class ConversationMode(Enum):
    """对话模式"""
    CHAT = "chat"
    COMPLETION = "completion"
    WORKFLOW = "workflow"

class SyncStatus(Enum):
    """同步状态"""
    PENDING = "pending"
    SYNCING = "syncing"
    COMPLETED = "completed"
    FAILED = "failed"

@dataclass
class DifyConversation:
    """Dify对话信息"""
    id: str
    app_id: str
    user_id: str
    created_at: datetime
    updated_at: datetime
    message_count: int = 0
    status: str = "active"

@dataclass
class DifyMessage:
    """Dify消息信息"""
    id: str
    conversation_id: str
    role: str  # user, assistant
    content: str
    created_at: datetime
    metadata: Dict[str, Any] = None
    files: List[str] = None

@dataclass
class SyncTask:
    """同步任务"""
    id: str
    dataset_id: str
    document_ids: List[str]
    status: SyncStatus
    created_at: datetime
    updated_at: datetime
    error_message: str = None
    progress: float = 0.0

class DifyService:
    """
    Dify集成服务
    
    提供与Dify平台的高级业务逻辑集成。
    """
    
    def __init__(self, 
                 graph_manager: GraphManager = None,
                 vector_service: VectorService = None,
                 cache_service: CacheService = None):
        self.client = DifyClient()
        self.graph_manager = graph_manager
        self.vector_service = vector_service
        self.cache_service = cache_service
        
        # 配置信息
        self.default_app_id = getattr(settings, 'DIFY_DEFAULT_APP_ID', None)
        self.default_dataset_id = getattr(settings, 'DIFY_DEFAULT_DATASET_ID', None)
        self.sync_batch_size = getattr(settings, 'DIFY_SYNC_BATCH_SIZE', 10)
        self.cache_ttl = getattr(settings, 'DIFY_CACHE_TTL', 3600)
        
        # 内部状态
        self._sync_tasks: Dict[str, SyncTask] = {}
        self._conversation_cache: Dict[str, DifyConversation] = {}
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self.client.__aenter__()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.client.__aexit__(exc_type, exc_val, exc_tb)
    
    # 对话管理
    async def create_conversation(self, user_id: str, app_id: str = None,
                                mode: ConversationMode = ConversationMode.CHAT) -> DifyConversation:
        """
        创建对话
        
        参数:
            user_id: 用户ID
            app_id: 应用ID
            mode: 对话模式
        
        返回:
            DifyConversation: 对话信息
        """
        app_id = app_id or self.default_app_id
        if not app_id:
            raise ValueError("应用ID未配置")
        
        try:
            # 创建Dify对话
            response = await self.client.create_conversation(app_id, user_id)
            
            conversation = DifyConversation(
                id=response['id'],
                app_id=app_id,
                user_id=user_id,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            
            # 缓存对话信息
            self._conversation_cache[conversation.id] = conversation
            
            if self.cache_service:
                await self.cache_service.set(
                    f"dify:conversation:{conversation.id}",
                    conversation.__dict__,
                    ttl=self.cache_ttl
                )
            
            logger.info(f"创建Dify对话成功: {conversation.id}")
            return conversation
        
        except DifyAPIError as e:
            logger.error(f"创建Dify对话失败: {e}")
            raise
    
    async def send_message(self, conversation_id: str, message: str,
                         user_id: str = None, files: List[str] = None,
                         use_knowledge_graph: bool = True) -> DifyMessage:
        """
        发送消息
        
        参数:
            conversation_id: 对话ID
            message: 消息内容
            user_id: 用户ID
            files: 文件列表
            use_knowledge_graph: 是否使用知识图谱增强
        
        返回:
            DifyMessage: 消息响应
        """
        try:
            # 获取对话信息
            conversation = await self._get_conversation(conversation_id)
            if not conversation:
                raise ValueError(f"对话不存在: {conversation_id}")
            
            # 知识图谱增强
            enhanced_message = message
            if use_knowledge_graph and self.graph_manager:
                enhanced_message = await self._enhance_message_with_kg(message)
            
            # 发送消息到Dify
            response = await self.client.send_message(
                conversation.app_id,
                conversation_id,
                enhanced_message,
                user_id or conversation.user_id,
                files
            )
            
            # 解析响应
            dify_message = DifyMessage(
                id=response['message_id'],
                conversation_id=conversation_id,
                role='assistant',
                content=response['answer'],
                created_at=datetime.now(),
                metadata=response.get('metadata', {}),
                files=response.get('files', [])
            )
            
            # 更新对话统计
            conversation.message_count += 1
            conversation.updated_at = datetime.now()
            
            logger.info(f"发送Dify消息成功: {dify_message.id}")
            return dify_message
        
        except DifyAPIError as e:
            logger.error(f"发送Dify消息失败: {e}")
            raise
    
    async def get_conversation_history(self, conversation_id: str,
                                     limit: int = 20, offset: int = 0) -> List[DifyMessage]:
        """
        获取对话历史
        
        参数:
            conversation_id: 对话ID
            limit: 限制数量
            offset: 偏移量
        
        返回:
            List[DifyMessage]: 消息列表
        """
        try:
            conversation = await self._get_conversation(conversation_id)
            if not conversation:
                raise ValueError(f"对话不存在: {conversation_id}")
            
            # 获取消息历史
            messages_data = await self.client.get_conversation_messages(
                conversation.app_id, conversation_id, limit, offset
            )
            
            messages = []
            for msg_data in messages_data:
                message = DifyMessage(
                    id=msg_data['id'],
                    conversation_id=conversation_id,
                    role=msg_data['role'],
                    content=msg_data['content'],
                    created_at=datetime.fromisoformat(msg_data['created_at']),
                    metadata=msg_data.get('metadata', {}),
                    files=msg_data.get('files', [])
                )
                messages.append(message)
            
            return messages
        
        except DifyAPIError as e:
            logger.error(f"获取对话历史失败: {e}")
            raise
    
    # 知识库同步
    async def sync_documents_to_dify(self, document_ids: List[str],
                                   dataset_id: str = None) -> str:
        """
        同步文档到Dify知识库
        
        参数:
            document_ids: 文档ID列表
            dataset_id: 数据集ID
        
        返回:
            str: 同步任务ID
        """
        dataset_id = dataset_id or self.default_dataset_id
        if not dataset_id:
            raise ValueError("数据集ID未配置")
        
        # 创建同步任务
        task_id = f"sync_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{len(self._sync_tasks)}"
        task = SyncTask(
            id=task_id,
            dataset_id=dataset_id,
            document_ids=document_ids,
            status=SyncStatus.PENDING,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        self._sync_tasks[task_id] = task
        
        # 异步执行同步
        asyncio.create_task(self._execute_sync_task(task))
        
        logger.info(f"创建文档同步任务: {task_id}")
        return task_id
    
    async def _execute_sync_task(self, task: SyncTask):
        """
        执行同步任务
        
        参数:
            task: 同步任务
        """
        try:
            task.status = SyncStatus.SYNCING
            task.updated_at = datetime.now()
            
            total_docs = len(task.document_ids)
            processed_docs = 0
            
            # 批量处理文档
            for i in range(0, total_docs, self.sync_batch_size):
                batch_ids = task.document_ids[i:i + self.sync_batch_size]
                
                for doc_id in batch_ids:
                    try:
                        await self._sync_single_document(doc_id, task.dataset_id)
                        processed_docs += 1
                        task.progress = processed_docs / total_docs
                        
                    except Exception as e:
                        logger.error(f"同步文档失败 {doc_id}: {e}")
                        continue
                
                # 更新进度
                task.updated_at = datetime.now()
                
                # 避免API限制
                await asyncio.sleep(1)
            
            task.status = SyncStatus.COMPLETED
            task.progress = 1.0
            logger.info(f"同步任务完成: {task.id}")
        
        except Exception as e:
            task.status = SyncStatus.FAILED
            task.error_message = str(e)
            logger.error(f"同步任务失败 {task.id}: {e}")
        
        finally:
            task.updated_at = datetime.now()
    
    async def _sync_single_document(self, document_id: str, dataset_id: str):
        """
        同步单个文档
        
        参数:
            document_id: 文档ID
            dataset_id: 数据集ID
        """
        # 这里需要根据实际的文档模型来获取文档内容
        # 假设有一个文档服务可以获取文档
        # document = await self.document_service.get_document(document_id)
        
        # 模拟文档内容
        document_content = f"Document {document_id} content".encode('utf-8')
        filename = f"document_{document_id}.txt"
        
        # 上传到Dify
        await self.client.upload_document(
            dataset_id, document_content, filename
        )
    
    async def get_sync_task_status(self, task_id: str) -> Optional[SyncTask]:
        """
        获取同步任务状态
        
        参数:
            task_id: 任务ID
        
        返回:
            Optional[SyncTask]: 任务信息
        """
        return self._sync_tasks.get(task_id)
    
    async def search_knowledge_base(self, query: str, dataset_id: str = None,
                                  top_k: int = 5) -> List[Dict[str, Any]]:
        """
        搜索知识库
        
        参数:
            query: 搜索查询
            dataset_id: 数据集ID
            top_k: 返回结果数量
        
        返回:
            List[Dict[str, Any]]: 搜索结果
        """
        dataset_id = dataset_id or self.default_dataset_id
        if not dataset_id:
            raise ValueError("数据集ID未配置")
        
        try:
            results = await self.client.search_dataset(dataset_id, query, top_k)
            return results
        
        except DifyAPIError as e:
            logger.error(f"搜索知识库失败: {e}")
            raise
    
    # 工作流管理
    async def run_workflow(self, workflow_inputs: Dict[str, Any],
                         app_id: str = None, user_id: str = None) -> Dict[str, Any]:
        """
        运行工作流
        
        参数:
            workflow_inputs: 工作流输入
            app_id: 应用ID
            user_id: 用户ID
        
        返回:
            Dict[str, Any]: 工作流结果
        """
        app_id = app_id or self.default_app_id
        if not app_id:
            raise ValueError("应用ID未配置")
        
        try:
            result = await self.client.run_workflow(app_id, workflow_inputs, user_id)
            return result
        
        except DifyAPIError as e:
            logger.error(f"运行工作流失败: {e}")
            raise
    
    # 知识图谱增强
    async def _enhance_message_with_kg(self, message: str) -> str:
        """
        使用知识图谱增强消息
        
        参数:
            message: 原始消息
        
        返回:
            str: 增强后的消息
        """
        if not self.graph_manager:
            return message
        
        try:
            # 提取实体
            entities = await self.graph_manager.extract_entities(message)
            
            if not entities:
                return message
            
            # 获取相关信息
            context_info = []
            for entity in entities[:3]:  # 限制实体数量
                related_info = await self.graph_manager.get_entity_context(
                    entity.name, max_depth=2
                )
                if related_info:
                    context_info.append(related_info)
            
            if context_info:
                enhanced_message = f"{message}\n\n相关背景信息:\n{json.dumps(context_info, ensure_ascii=False, indent=2)}"
                return enhanced_message
            
            return message
        
        except Exception as e:
            logger.error(f"知识图谱增强失败: {e}")
            return message
    
    # 辅助方法
    async def _get_conversation(self, conversation_id: str) -> Optional[DifyConversation]:
        """
        获取对话信息
        
        参数:
            conversation_id: 对话ID
        
        返回:
            Optional[DifyConversation]: 对话信息
        """
        # 先从缓存获取
        if conversation_id in self._conversation_cache:
            return self._conversation_cache[conversation_id]
        
        # 从缓存服务获取
        if self.cache_service:
            cached_data = await self.cache_service.get(f"dify:conversation:{conversation_id}")
            if cached_data:
                conversation = DifyConversation(**cached_data)
                self._conversation_cache[conversation_id] = conversation
                return conversation
        
        return None
    
    # 健康检查和统计
    async def health_check(self) -> Dict[str, Any]:
        """
        健康检查
        
        返回:
            Dict[str, Any]: 健康状态
        """
        try:
            dify_healthy = await self.client.health_check()
            
            return {
                'dify_api': dify_healthy,
                'active_conversations': len(self._conversation_cache),
                'active_sync_tasks': len([t for t in self._sync_tasks.values() 
                                        if t.status == SyncStatus.SYNCING]),
                'total_sync_tasks': len(self._sync_tasks)
            }
        
        except Exception as e:
            logger.error(f"健康检查失败: {e}")
            return {
                'dify_api': False,
                'error': str(e)
            }
    
    async def get_usage_statistics(self, days: int = 7) -> Dict[str, Any]:
        """
        获取使用统计
        
        参数:
            days: 统计天数
        
        返回:
            Dict[str, Any]: 统计信息
        """
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            stats = await self.client.get_usage_statistics(
                self.default_app_id,
                start_date.isoformat(),
                end_date.isoformat()
            )
            
            return stats
        
        except Exception as e:
            logger.error(f"获取统计信息失败: {e}")
            return {}
    
    # 清理方法
    async def cleanup_old_tasks(self, days: int = 7):
        """
        清理旧的同步任务
        
        参数:
            days: 保留天数
        """
        cutoff_date = datetime.now() - timedelta(days=days)
        
        tasks_to_remove = [
            task_id for task_id, task in self._sync_tasks.items()
            if task.updated_at < cutoff_date and task.status in [SyncStatus.COMPLETED, SyncStatus.FAILED]
        ]
        
        for task_id in tasks_to_remove:
            del self._sync_tasks[task_id]
        
        logger.info(f"清理了 {len(tasks_to_remove)} 个旧同步任务")
    
    async def cleanup_old_conversations(self, hours: int = 24):
        """
        清理旧的对话缓存
        
        参数:
            hours: 保留小时数
        """
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        conversations_to_remove = [
            conv_id for conv_id, conv in self._conversation_cache.items()
            if conv.updated_at < cutoff_time
        ]
        
        for conv_id in conversations_to_remove:
            del self._conversation_cache[conv_id]
        
        logger.info(f"清理了 {len(conversations_to_remove)} 个旧对话缓存")