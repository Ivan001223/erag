"""API主模块

为了兼容测试导入，此文件重新导出backend.main中的应用实例。
"""

from ..main import app, get_connector, get_neo4j_client, get_redis_client, get_minio_client

__all__ = ["app", "get_connector", "get_neo4j_client", "get_redis_client", "get_minio_client"] 