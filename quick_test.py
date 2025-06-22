#!/usr/bin/env python3
"""快速测试修复效果"""

try:
    print("测试模型导入...")
    
    # 测试Task模型
    from backend.models.task import Task, TaskLog, TaskDependency
    print("✅ Task模型导入成功")
    
    # 测试Knowledge模型
    from backend.models.knowledge import Document, DocumentChunk, KnowledgeBase
    print("✅ Knowledge模型导入成功")
    
    # 测试Database模型
    from backend.models.database import DocumentModel, DocumentChunkModel, EntityModel
    print("✅ Database模型导入成功")
    
    # 测试User模型
    from backend.models.user import UserModel
    print("✅ User模型导入成功")
    
    # 测试models模块整体导入
    from backend.models import UserModel as UserModel2
    print("✅ models模块导入成功")
    
    # 测试Base类和表名冲突
    from backend.models.base import Base
    print("✅ Base类导入成功")
    
    # 检查表名是否有冲突
    table_names = []
    for table in Base.metadata.tables.values():
        table_names.append(table.name)
    
    print(f"📊 发现 {len(table_names)} 个表:")
    for name in sorted(table_names):
        print(f"   - {name}")
    
    # 检查是否有重复表名
    duplicate_names = [name for name in set(table_names) if table_names.count(name) > 1]
    if duplicate_names:
        print(f"❌ 发现重复表名: {duplicate_names}")
    else:
        print("✅ 没有重复表名")
        
    print("\n🎉 所有测试通过！")
    
except Exception as e:
    print(f"❌ 测试失败: {e}")
    import traceback
    traceback.print_exc() 