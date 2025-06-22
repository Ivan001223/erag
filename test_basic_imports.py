#!/usr/bin/env python3
"""基础导入测试"""

def test_basic_imports():
    """测试基本模块导入"""
    try:
        # 测试模型导入
        from backend.models.base import Base, BaseModel, FullModel
        from backend.models.knowledge import KnowledgeBase, Document, DocumentChunk
        from backend.models.notification import Notification
        
        # 测试配置导入
        from backend.config.settings import get_settings
        from backend.config.database import get_db
        
        # 测试连接器导入
        from backend.connectors.redis_client import RedisClient
        from backend.connectors.neo4j_client import Neo4jClient
        
        # 测试工具导入
        from backend.utils.logger import get_logger
        
        print("✅ 所有基础模块导入成功")
        return True
        
    except ImportError as e:
        print(f"❌ 导入失败: {e}")
        return False

def test_database_models():
    """测试数据库模型创建"""
    try:
        from backend.models.knowledge import KnowledgeBase, Document
        from backend.models.notification import Notification
        
        # 尝试创建模型实例
        kb = KnowledgeBase(
            name="测试知识库",
            description="测试描述",
            owner_id="test-user-id"
        )
        
        doc = Document(
            knowledge_base_id="test-kb-id",
            title="测试文档",
            filename="test.txt",
            file_type="text"
        )
        
        notification = Notification(
            user_id="test-user-id",
            title="测试通知",
            content="测试内容"
        )
        
        print("✅ 数据库模型创建成功")
        return True
        
    except Exception as e:
        print(f"❌ 模型创建失败: {e}")
        return False

if __name__ == "__main__":
    print("开始基础导入测试...")
    
    import_success = test_basic_imports()
    model_success = test_database_models()
    
    if import_success and model_success:
        print("\n🎉 所有基础测试通过!")
        exit(0)
    else:
        print("\n💥 基础测试失败!")
        exit(1) 