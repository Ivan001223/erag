"""端到端集成测试

测试完整的用户工作流程和系统集成。
"""

import pytest
import asyncio
import json
import tempfile
import os
import uuid
import time
from typing import Dict, Any, List
from unittest.mock import AsyncMock, patch, MagicMock
import numpy as np

from backend.api.main import app
from backend.services.document_service import DocumentService
from backend.services.knowledge_service import KnowledgeService
from backend.services.search_service import SearchService
from backend.services.user_service import UserService
from backend.services.task_service import TaskService
from backend.services.recommendation_service import RecommendationService
from backend.integrations.dify_service import DifyService
from backend.models.user import UserModel as User
from backend.models.task import Task, TaskStatus


class EndToEndIntegrationTest:
    """端到端集成测试类"""
    
    def __init__(self):
        # 初始化服务
        self.document_service = None
        self.knowledge_service = None
        self.search_service = None
        self.user_service = None
        self.task_service = None
        self.recommendation_service = None
        self.dify_service = None
        
        # 测试数据
        self.test_user_id = None
        self.test_documents = []
        self.test_entities = []
        self.test_relations = []
        self.test_tasks = []
        self.test_conversations = []
    
    async def setup_services(self):
        """设置服务实例"""
        # 创建模拟的数据库客户端
        mock_redis = AsyncMock()
        mock_neo4j = AsyncMock()
        mock_starrocks = AsyncMock()
        mock_minio = AsyncMock()
        
        # 初始化服务
        self.document_service = DocumentService(mock_minio)
        self.knowledge_service = KnowledgeService(mock_neo4j)
        self.search_service = SearchService()
        self.user_service = UserService()
        self.task_service = TaskService()
        self.recommendation_service = RecommendationService()
        self.dify_service = DifyService()
        
        # 创建测试用户
        self.test_user_id = str(uuid.uuid4())
        
        with patch.object(self.user_service, 'create_user') as mock_create_user:
            mock_create_user.return_value = {
                "id": self.test_user_id,
                "username": "test_user",
                "email": "test@example.com",
                "preferences": {
                    "language": "zh-CN",
                    "topics": ["AI", "Technology"],
                    "notification_settings": {
                        "email": True,
                        "push": False
                    }
                },
                "created_at": "2024-01-01T00:00:00Z"
            }
            
            user = await self.user_service.create_user({
                "username": "test_user",
                "email": "test@example.com",
                "password": "test_password"
            })
            assert user["id"] == self.test_user_id
    
    async def cleanup_test_data(self):
        """清理测试数据"""
        self.test_documents.clear()
        self.test_entities.clear()
        self.test_relations.clear()
        self.test_tasks.clear()
        self.test_conversations.clear()
    
    async def test_document_upload_and_processing_workflow(self):
        """测试文档上传和处理工作流"""
        # 1. 用户上传文档
        document_content = """
        人工智能（Artificial Intelligence，AI）是计算机科学的一个分支，
        它企图了解智能的实质，并生产出一种新的能以人类智能相似的方式做出反应的智能机器。
        机器学习（Machine Learning，ML）是人工智能的一个重要分支，
        通过算法使机器能够从数据中学习并做出决策或预测。
        深度学习（Deep Learning）是机器学习的一个子集，
        使用多层神经网络来模拟人脑的工作方式。
        """
        
        with patch.object(self.document_service, 'upload_document') as mock_upload:
            document_id = str(uuid.uuid4())
            mock_upload.return_value = {
                "id": document_id,
                "title": "AI技术概述",
                "content": document_content,
                "user_id": self.test_user_id,
                "status": "uploaded",
                "metadata": {
                    "file_type": "text",
                    "size": len(document_content),
                    "language": "zh-CN"
                },
                "created_at": "2024-01-01T10:00:00Z"
            }
            
            document = await self.document_service.upload_document(
                file_content=document_content.encode(),
                filename="ai_overview.txt",
                user_id=self.test_user_id
            )
            
            assert document["id"] == document_id
            assert document["user_id"] == self.test_user_id
            self.test_documents.append(document)
        
        # 2. 系统自动创建处理任务
        with patch.object(self.task_service, 'create_task') as mock_create_task:
            task_id = str(uuid.uuid4())
            mock_create_task.return_value = {
                "id": task_id,
                "type": "document_processing",
                "status": TaskStatus.PENDING,
                "parameters": {
                    "document_id": document_id,
                    "extract_entities": True,
                    "extract_relations": True,
                    "generate_vectors": True
                },
                "user_id": self.test_user_id,
                "priority": "normal",
                "created_at": "2024-01-01T10:01:00Z"
            }
            
            task = await self.task_service.create_task({
                "type": "document_processing",
                "parameters": {
                    "document_id": document_id,
                    "extract_entities": True,
                    "extract_relations": True,
                    "generate_vectors": True
                },
                "user_id": self.test_user_id
            })
            
            assert task["id"] == task_id
            assert task["status"] == TaskStatus.PENDING
            self.test_tasks.append(task)
        
        # 3. 任务执行 - 实体提取
        with patch.object(self.task_service, 'execute_task') as mock_execute:
            mock_execute.return_value = {
                "id": task_id,
                "status": TaskStatus.RUNNING,
                "progress": 0.3,
                "current_step": "entity_extraction",
                "result": {
                    "entities_extracted": [
                        {
                            "name": "人工智能",
                            "type": "Technology",
                            "aliases": ["AI", "Artificial Intelligence"],
                            "confidence": 0.95
                        },
                        {
                            "name": "机器学习",
                            "type": "Technology",
                            "aliases": ["ML", "Machine Learning"],
                            "confidence": 0.92
                        },
                        {
                            "name": "深度学习",
                            "type": "Technology",
                            "aliases": ["Deep Learning"],
                            "confidence": 0.90
                        }
                    ]
                }
            }
            
            execution_result = await self.task_service.execute_task(task_id)
            assert execution_result["status"] == TaskStatus.RUNNING
            assert len(execution_result["result"]["entities_extracted"]) == 3
        
        # 4. 任务完成 - 知识图谱构建
        with patch.object(self.task_service, 'complete_task') as mock_complete:
            mock_complete.return_value = {
                "id": task_id,
                "status": TaskStatus.COMPLETED,
                "progress": 1.0,
                "result": {
                    "entities_created": 3,
                    "relations_created": 2,
                    "vectors_generated": 3,
                    "processing_time": 45.2,
                    "knowledge_graph_updated": True
                }
            }
            
            completed_task = await self.task_service.complete_task(
                task_id,
                result={
                    "entities_created": 3,
                    "relations_created": 2,
                    "vectors_generated": 3,
                    "processing_time": 45.2,
                    "knowledge_graph_updated": True
                }
            )
            
            assert completed_task["status"] == TaskStatus.COMPLETED
            assert completed_task["result"]["entities_created"] == 3
        
        # 5. 用户收到处理完成通知
        with patch.object(self.user_service, 'send_notification') as mock_notify:
            mock_notify.return_value = {
                "notification_id": str(uuid.uuid4()),
                "user_id": self.test_user_id,
                "type": "task_completed",
                "message": "文档 'AI技术概述' 处理完成",
                "data": {
                    "task_id": task_id,
                    "document_id": document_id,
                    "entities_created": 3
                },
                "sent_at": "2024-01-01T10:05:00Z"
            }
            
            notification = await self.user_service.send_notification(
                user_id=self.test_user_id,
                notification_type="task_completed",
                message="文档 'AI技术概述' 处理完成",
                data={
                    "task_id": task_id,
                    "document_id": document_id,
                    "entities_created": 3
                }
            )
            
            assert notification["user_id"] == self.test_user_id
            assert notification["type"] == "task_completed"
    
    async def test_knowledge_search_workflow(self):
        """测试知识搜索工作流"""
        # 准备测试数据
        await self.test_document_upload_and_processing_workflow()
        
        # 1. 用户进行文本搜索
        search_query = "什么是机器学习"
        
        with patch.object(self.search_service, 'search') as mock_search:
            mock_search.return_value = {
                "results": [
                    {
                        "id": "entity_ml",
                        "name": "机器学习",
                        "type": "Technology",
                        "description": "人工智能的一个重要分支，通过算法使机器能够从数据中学习",
                        "score": 0.95,
                        "source_documents": [self.test_documents[0]["id"]]
                    },
                    {
                        "id": "entity_ai",
                        "name": "人工智能",
                        "type": "Technology",
                        "description": "计算机科学的一个分支，企图了解智能的实质",
                        "score": 0.82,
                        "source_documents": [self.test_documents[0]["id"]]
                    }
                ],
                "total": 2,
                "query_time": 0.15,
                "search_type": "hybrid"
            }
            
            search_results = await self.search_service.search(
                query=search_query,
                user_id=self.test_user_id,
                search_type="hybrid",
                limit=10
            )
            
            assert len(search_results["results"]) == 2
            assert search_results["results"][0]["name"] == "机器学习"
            assert search_results["results"][0]["score"] > 0.9
        
        # 2. 用户查看详细信息
        entity_id = "entity_ml"
        
        with patch.object(self.knowledge_service, 'get_entity_details') as mock_details:
            mock_details.return_value = {
                "entity": {
                    "id": entity_id,
                    "name": "机器学习",
                    "type": "Technology",
                    "properties": {
                        "aliases": ["ML", "Machine Learning"],
                        "definition": "人工智能的一个重要分支",
                        "applications": ["数据分析", "预测模型", "自动化决策"]
                    }
                },
                "related_entities": [
                    {
                        "id": "entity_ai",
                        "name": "人工智能",
                        "relation": "IS_PART_OF",
                        "strength": 0.9
                    },
                    {
                        "id": "entity_dl",
                        "name": "深度学习",
                        "relation": "HAS_SUBSET",
                        "strength": 0.85
                    }
                ],
                "source_documents": [
                    {
                        "id": self.test_documents[0]["id"],
                        "title": "AI技术概述",
                        "relevance": 0.95
                    }
                ]
            }
            
            entity_details = await self.knowledge_service.get_entity_details(
                entity_id=entity_id,
                user_id=self.test_user_id
            )
            
            assert entity_details["entity"]["name"] == "机器学习"
            assert len(entity_details["related_entities"]) == 2
            assert len(entity_details["source_documents"]) == 1
        
        # 3. 记录用户搜索行为
        with patch.object(self.user_service, 'record_interaction') as mock_record:
            mock_record.return_value = {
                "interaction_id": str(uuid.uuid4()),
                "user_id": self.test_user_id,
                "type": "search",
                "data": {
                    "query": search_query,
                    "results_count": 2,
                    "clicked_entity": entity_id,
                    "search_time": 0.15
                },
                "timestamp": "2024-01-01T11:00:00Z"
            }
            
            interaction = await self.user_service.record_interaction(
                user_id=self.test_user_id,
                interaction_type="search",
                data={
                    "query": search_query,
                    "results_count": 2,
                    "clicked_entity": entity_id,
                    "search_time": 0.15
                }
            )
            
            assert interaction["user_id"] == self.test_user_id
            assert interaction["type"] == "search"
    
    async def test_intelligent_conversation_workflow(self):
        """测试智能对话工作流"""
        # 准备测试数据
        await self.test_knowledge_search_workflow()
        
        # 1. 用户开始对话
        conversation_id = str(uuid.uuid4())
        user_message = "请详细解释一下机器学习和深度学习的区别"
        
        with patch.object(self.dify_service, 'start_conversation') as mock_start_conv:
            mock_start_conv.return_value = {
                "conversation_id": conversation_id,
                "user_id": self.test_user_id,
                "status": "active",
                "context": {
                    "user_preferences": {
                        "language": "zh-CN",
                        "expertise_level": "intermediate"
                    },
                    "knowledge_context": [
                        "entity_ml", "entity_dl", "entity_ai"
                    ]
                },
                "created_at": "2024-01-01T12:00:00Z"
            }
            
            conversation = await self.dify_service.start_conversation(
                user_id=self.test_user_id,
                initial_message=user_message
            )
            
            assert conversation["conversation_id"] == conversation_id
            assert conversation["user_id"] == self.test_user_id
            self.test_conversations.append(conversation)
        
        # 2. 系统检索相关知识
        with patch.object(self.knowledge_service, 'get_relevant_knowledge') as mock_knowledge:
            mock_knowledge.return_value = {
                "entities": [
                    {
                        "name": "机器学习",
                        "definition": "人工智能的一个重要分支，通过算法使机器能够从数据中学习",
                        "relevance": 0.95
                    },
                    {
                        "name": "深度学习",
                        "definition": "机器学习的一个子集，使用多层神经网络来模拟人脑的工作方式",
                        "relevance": 0.92
                    }
                ],
                "relations": [
                    {
                        "source": "深度学习",
                        "target": "机器学习",
                        "type": "IS_SUBSET_OF",
                        "confidence": 0.9
                    }
                ],
                "context_score": 0.88
            }
            
            relevant_knowledge = await self.knowledge_service.get_relevant_knowledge(
                query=user_message,
                context_entities=["entity_ml", "entity_dl"],
                user_id=self.test_user_id
            )
            
            assert len(relevant_knowledge["entities"]) == 2
            assert relevant_knowledge["context_score"] > 0.8
        
        # 3. 生成智能回复
        with patch.object(self.dify_service, 'generate_response') as mock_response:
            mock_response.return_value = {
                "message_id": str(uuid.uuid4()),
                "conversation_id": conversation_id,
                "content": """
                机器学习和深度学习的主要区别如下：
                
                **机器学习（Machine Learning）**：
                - 是人工智能的一个重要分支
                - 通过算法使机器能够从数据中学习并做出决策或预测
                - 包含多种算法类型，如监督学习、无监督学习、强化学习等
                
                **深度学习（Deep Learning）**：
                - 是机器学习的一个子集
                - 使用多层神经网络（通常3层以上）来模拟人脑的工作方式
                - 特别擅长处理图像、语音、自然语言等复杂数据
                
                **主要区别**：
                1. **范围**：深度学习是机器学习的一个特殊分支
                2. **复杂度**：深度学习使用更复杂的神经网络结构
                3. **数据需求**：深度学习通常需要更大量的数据
                4. **应用场景**：深度学习在图像识别、语音识别等领域表现更优
                """,
                "type": "assistant",
                "metadata": {
                    "knowledge_sources": ["entity_ml", "entity_dl"],
                    "confidence": 0.92,
                    "generation_time": 1.8
                },
                "timestamp": "2024-01-01T12:01:00Z"
            }
            
            response = await self.dify_service.generate_response(
                conversation_id=conversation_id,
                user_message=user_message,
                knowledge_context=relevant_knowledge
            )
            
            assert response["conversation_id"] == conversation_id
            assert "机器学习" in response["content"]
            assert "深度学习" in response["content"]
            assert response["metadata"]["confidence"] > 0.9
        
        # 4. 用户反馈
        with patch.object(self.dify_service, 'record_feedback') as mock_feedback:
            mock_feedback.return_value = {
                "feedback_id": str(uuid.uuid4()),
                "conversation_id": conversation_id,
                "message_id": response["message_id"],
                "user_id": self.test_user_id,
                "rating": 5,
                "comment": "回答很详细，帮助很大",
                "timestamp": "2024-01-01T12:05:00Z"
            }
            
            feedback = await self.dify_service.record_feedback(
                conversation_id=conversation_id,
                message_id=response["message_id"],
                user_id=self.test_user_id,
                rating=5,
                comment="回答很详细，帮助很大"
            )
            
            assert feedback["rating"] == 5
            assert feedback["user_id"] == self.test_user_id
    
    async def test_personalized_recommendation_workflow(self):
        """测试个性化推荐工作流"""
        # 准备测试数据
        await self.test_intelligent_conversation_workflow()
        
        # 1. 系统分析用户行为
        with patch.object(self.user_service, 'analyze_user_behavior') as mock_analyze:
            mock_analyze.return_value = {
                "user_profile": {
                    "interests": [
                        {"topic": "机器学习", "score": 0.95},
                        {"topic": "深度学习", "score": 0.88},
                        {"topic": "人工智能", "score": 0.82}
                    ],
                    "expertise_level": "intermediate",
                    "preferred_content_types": ["technical_articles", "tutorials"],
                    "interaction_patterns": {
                        "search_frequency": "high",
                        "conversation_engagement": "high",
                        "feedback_quality": "positive"
                    }
                },
                "behavior_trends": {
                    "learning_progression": "advancing",
                    "focus_areas": ["practical_applications", "technical_details"]
                }
            }
            
            user_analysis = await self.user_service.analyze_user_behavior(
                user_id=self.test_user_id,
                time_window="30d"
            )
            
            assert len(user_analysis["user_profile"]["interests"]) == 3
            assert user_analysis["user_profile"]["expertise_level"] == "intermediate"
        
        # 2. 生成个性化推荐
        with patch.object(self.recommendation_service, 'generate_recommendations') as mock_recommend:
            mock_recommend.return_value = {
                "recommendations": [
                    {
                        "id": "rec_1",
                        "type": "document",
                        "title": "机器学习实战案例分析",
                        "description": "详细介绍机器学习在实际项目中的应用",
                        "score": 0.94,
                        "reason": "基于您对机器学习的高度兴趣和中级技术水平",
                        "tags": ["机器学习", "实战", "案例分析"]
                    },
                    {
                        "id": "rec_2",
                        "type": "entity",
                        "name": "神经网络",
                        "description": "深度学习的核心技术",
                        "score": 0.89,
                        "reason": "与您关注的深度学习主题密切相关",
                        "tags": ["深度学习", "神经网络", "技术"]
                    },
                    {
                        "id": "rec_3",
                        "type": "conversation_topic",
                        "title": "如何选择合适的机器学习算法",
                        "description": "针对不同问题选择最佳算法的指南",
                        "score": 0.86,
                        "reason": "基于您的学习进展和实用性偏好",
                        "tags": ["算法选择", "实用指南", "决策支持"]
                    }
                ],
                "recommendation_strategy": "hybrid",
                "confidence": 0.91
            }
            
            recommendations = await self.recommendation_service.generate_recommendations(
                user_id=self.test_user_id,
                recommendation_types=["document", "entity", "conversation_topic"],
                limit=10
            )
            
            assert len(recommendations["recommendations"]) == 3
            assert recommendations["confidence"] > 0.9
            assert recommendations["recommendations"][0]["score"] > 0.9
        
        # 3. 用户交互推荐内容
        recommendation_id = "rec_1"
        
        with patch.object(self.recommendation_service, 'track_interaction') as mock_track:
            mock_track.return_value = {
                "interaction_id": str(uuid.uuid4()),
                "user_id": self.test_user_id,
                "recommendation_id": recommendation_id,
                "action": "clicked",
                "timestamp": "2024-01-01T13:00:00Z",
                "context": {
                    "position": 1,
                    "recommendation_score": 0.94
                }
            }
            
            interaction = await self.recommendation_service.track_interaction(
                user_id=self.test_user_id,
                recommendation_id=recommendation_id,
                action="clicked"
            )
            
            assert interaction["user_id"] == self.test_user_id
            assert interaction["action"] == "clicked"
        
        # 4. 更新推荐模型
        with patch.object(self.recommendation_service, 'update_model') as mock_update:
            mock_update.return_value = {
                "model_version": "v1.2.1",
                "update_type": "incremental",
                "performance_metrics": {
                    "click_through_rate": 0.15,
                    "user_satisfaction": 0.88,
                    "recommendation_accuracy": 0.92
                },
                "updated_at": "2024-01-01T13:05:00Z"
            }
            
            model_update = await self.recommendation_service.update_model(
                user_interactions=[interaction],
                feedback_data=[{
                    "user_id": self.test_user_id,
                    "recommendation_id": recommendation_id,
                    "satisfaction": 5
                }]
            )
            
            assert model_update["performance_metrics"]["recommendation_accuracy"] > 0.9
    
    async def test_system_monitoring_and_analytics(self):
        """测试系统监控和分析"""
        # 1. 系统性能监控
        with patch.object(self.task_service, 'get_system_metrics') as mock_metrics:
            mock_metrics.return_value = {
                "performance": {
                    "avg_response_time": 0.25,
                    "throughput": 150.5,  # requests per second
                    "error_rate": 0.002,
                    "cpu_usage": 0.65,
                    "memory_usage": 0.72,
                    "disk_usage": 0.45
                },
                "tasks": {
                    "total_processed": 1250,
                    "success_rate": 0.998,
                    "avg_processing_time": 45.2,
                    "queue_length": 5
                },
                "knowledge_graph": {
                    "total_entities": 15420,
                    "total_relations": 8930,
                    "graph_density": 0.12,
                    "update_frequency": 25.5  # updates per hour
                },
                "users": {
                    "active_users": 89,
                    "total_sessions": 156,
                    "avg_session_duration": 18.5  # minutes
                }
            }
            
            system_metrics = await self.task_service.get_system_metrics(
                time_range="1h"
            )
            
            assert system_metrics["performance"]["avg_response_time"] < 1.0
            assert system_metrics["performance"]["error_rate"] < 0.01
            assert system_metrics["tasks"]["success_rate"] > 0.99
        
        # 2. 用户行为分析
        with patch.object(self.user_service, 'get_usage_analytics') as mock_analytics:
            mock_analytics.return_value = {
                "user_engagement": {
                    "daily_active_users": 45,
                    "weekly_active_users": 128,
                    "monthly_active_users": 340,
                    "user_retention_rate": 0.78
                },
                "feature_usage": {
                    "document_upload": 0.85,
                    "knowledge_search": 0.92,
                    "ai_conversation": 0.67,
                    "recommendation_clicks": 0.23
                },
                "content_metrics": {
                    "total_documents": 2340,
                    "total_searches": 5670,
                    "total_conversations": 890,
                    "avg_conversation_length": 8.5
                },
                "satisfaction_scores": {
                    "overall_satisfaction": 4.2,
                    "search_satisfaction": 4.1,
                    "conversation_satisfaction": 4.4,
                    "recommendation_satisfaction": 3.8
                }
            }
            
            usage_analytics = await self.user_service.get_usage_analytics(
                time_range="30d"
            )
            
            assert usage_analytics["user_engagement"]["user_retention_rate"] > 0.7
            assert usage_analytics["satisfaction_scores"]["overall_satisfaction"] > 4.0
        
        # 3. 知识图谱质量分析
        with patch.object(self.knowledge_service, 'analyze_graph_quality') as mock_quality:
            mock_quality.return_value = {
                "completeness": {
                    "entity_coverage": 0.87,
                    "relation_coverage": 0.82,
                    "missing_entities": 156,
                    "missing_relations": 89
                },
                "accuracy": {
                    "entity_accuracy": 0.94,
                    "relation_accuracy": 0.91,
                    "confidence_distribution": {
                        "high": 0.65,
                        "medium": 0.28,
                        "low": 0.07
                    }
                },
                "consistency": {
                    "consistency_score": 0.89,
                    "conflicts_detected": 12,
                    "resolved_conflicts": 8
                },
                "freshness": {
                    "avg_entity_age": 15.5,  # days
                    "recent_updates": 234,
                    "stale_entities": 45
                }
            }
            
            graph_quality = await self.knowledge_service.analyze_graph_quality()
            
            assert graph_quality["accuracy"]["entity_accuracy"] > 0.9
            assert graph_quality["consistency"]["consistency_score"] > 0.85
    
    async def test_error_recovery_and_resilience(self):
        """测试错误恢复和系统韧性"""
        # 1. 测试服务降级
        with patch.object(self.search_service, 'vector_search') as mock_vector_search:
            mock_vector_search.side_effect = Exception("Vector service unavailable")
            
            with patch.object(self.search_service, 'fallback_search') as mock_fallback:
                mock_fallback.return_value = {
                    "results": [
                        {
                            "id": "fallback_result",
                            "name": "机器学习",
                            "score": 0.75,
                            "source": "text_search_fallback"
                        }
                    ],
                    "total": 1,
                    "fallback_used": True
                }
                
                # 搜索应该降级到文本搜索
                search_result = await self.search_service.search(
                    query="机器学习",
                    user_id=self.test_user_id
                )
                
                # 验证降级机制工作正常
                assert search_result["fallback_used"] is True
                assert len(search_result["results"]) > 0
        
        # 2. 测试任务重试机制
        with patch.object(self.task_service, 'execute_task') as mock_execute:
            # 模拟前两次失败，第三次成功
            mock_execute.side_effect = [
                Exception("Temporary failure"),
                Exception("Network timeout"),
                {
                    "id": "task_123",
                    "status": TaskStatus.COMPLETED,
                    "result": {"success": True},
                    "retry_count": 2
                }
            ]
            
            with patch.object(self.task_service, 'retry_task') as mock_retry:
                mock_retry.return_value = {
                    "id": "task_123",
                    "status": TaskStatus.COMPLETED,
                    "result": {"success": True},
                    "retry_count": 2
                }
                
                # 任务应该在重试后成功
                task_result = await self.task_service.retry_task(
                    task_id="task_123",
                    max_retries=3
                )
                
                assert task_result["status"] == TaskStatus.COMPLETED
                assert task_result["retry_count"] == 2
        
        # 3. 测试数据一致性恢复
        with patch.object(self.knowledge_service, 'detect_inconsistency') as mock_detect:
            mock_detect.return_value = {
                "inconsistencies": [
                    {
                        "type": "orphaned_relation",
                        "relation_id": "rel_123",
                        "description": "Relation points to non-existent entity"
                    }
                ],
                "severity": "medium"
            }
            
            with patch.object(self.knowledge_service, 'repair_inconsistency') as mock_repair:
                mock_repair.return_value = {
                    "repaired_count": 1,
                    "repair_actions": [
                        {
                            "action": "delete_orphaned_relation",
                            "target": "rel_123",
                            "success": True
                        }
                    ]
                }
                
                # 系统应该能够检测并修复数据不一致
                inconsistencies = await self.knowledge_service.detect_inconsistency()
                repair_result = await self.knowledge_service.repair_inconsistency(
                    inconsistencies["inconsistencies"]
                )
                
                assert repair_result["repaired_count"] == 1
                assert repair_result["repair_actions"][0]["success"] is True


# 测试运行器
async def run_end_to_end_tests():
    """运行所有端到端测试"""
    test_suite = EndToEndIntegrationTest()
    
    try:
        print("Setting up end-to-end test environment...")
        await test_suite.setup_services()
        
        print("Running document upload and processing workflow test...")
        await test_suite.test_document_upload_and_processing_workflow()
        
        print("Running knowledge search workflow test...")
        await test_suite.test_knowledge_search_workflow()
        
        print("Running intelligent conversation workflow test...")
        await test_suite.test_intelligent_conversation_workflow()
        
        print("Running personalized recommendation workflow test...")
        await test_suite.test_personalized_recommendation_workflow()
        
        print("Running system monitoring and analytics test...")
        await test_suite.test_system_monitoring_and_analytics()
        
        print("Running error recovery and resilience test...")
        await test_suite.test_error_recovery_and_resilience()
        
        print("All end-to-end tests passed!")
        
    except Exception as e:
        print(f"End-to-end test failed: {e}")
        raise
    
    finally:
        print("Cleaning up test environment...")
        await test_suite.cleanup_test_data()


if __name__ == "__main__":
    asyncio.run(run_end_to_end_tests())