"""集成测试模块

本模块包含系统各组件之间的集成测试，确保整个系统的协调工作。
"""

# 安全的显式导入，替代通配符导入
from .test_api_integration import (
    APIIntegrationTest,
)
from .test_database_integration import (
    DatabaseIntegrationTest,
)
from .test_service_integration import (
    ServiceIntegrationTest,
)
from .test_end_to_end import (
    EndToEndTest,
)
from .test_knowledge_graph_integration import (
    KnowledgeGraphIntegrationTest,
)

__all__ = [
    'APIIntegrationTest',
    'DatabaseIntegrationTest', 
    'ServiceIntegrationTest',
    'EndToEndTest',
    'KnowledgeGraphIntegrationTest'
]