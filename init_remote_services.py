#!/usr/bin/env python3
"""
远程服务初始化脚本
初始化192.168.0.101上的数据平台服务
"""

import pymysql
from minio import Minio
from minio.error import S3Error
from backend.config.settings import get_settings
import sys
import io


def init_mysql():
    """初始化MySQL数据库和用户"""
    settings = get_settings()
    
    print("🔧 初始化MySQL数据库...")
    
    # 尝试不同的root密码
    root_passwords = ['mysql123', 'root', '123456', '']
    
    for root_password in root_passwords:
        try:
            print(f"   尝试密码: {'(空)' if not root_password else '***'}")
            connection = pymysql.connect(
                host=settings.mysql_host,
                port=settings.mysql_port,
                user='root',
                password=root_password,
                charset='utf8mb4'
            )
            
            with connection.cursor() as cursor:
                # 创建数据库
                cursor.execute(f"CREATE DATABASE IF NOT EXISTS {settings.mysql_database}")
                print(f"✅ 数据库 '{settings.mysql_database}' 创建成功")
                
                # 创建用户并授权
                cursor.execute(f"DROP USER IF EXISTS '{settings.mysql_user}'@'%'")
                cursor.execute(f"CREATE USER '{settings.mysql_user}'@'%' IDENTIFIED BY '{settings.mysql_password}'")
                cursor.execute(f"GRANT ALL PRIVILEGES ON {settings.mysql_database}.* TO '{settings.mysql_user}'@'%'")
                cursor.execute("FLUSH PRIVILEGES")
                print(f"✅ 用户 '{settings.mysql_user}' 创建并授权成功")
                
                # 检查binlog状态
                cursor.execute("SHOW VARIABLES LIKE 'log_bin'")
                binlog_status = cursor.fetchone()
                if binlog_status and binlog_status[1] == 'ON':
                    print("✅ MySQL binlog 已启用")
                else:
                    print("⚠️  MySQL binlog 未启用，CDC功能可能受限")
            
            connection.close()
            return True
            
        except Exception as e:
            print(f"   密码失败: {str(e)}")
            continue
    
    print("❌ MySQL初始化失败: 所有root密码都尝试失败")
    return False


def init_minio():
    """初始化MinIO存储桶"""
    settings = get_settings()
    
    print("🔧 初始化MinIO存储桶...")
    
    try:
        client = Minio(
            settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_secure
        )
        
        # 创建存储桶
        bucket_name = settings.minio_bucket_name
        if not client.bucket_exists(bucket_name):
            client.make_bucket(bucket_name)
            print(f"✅ 存储桶 '{bucket_name}' 创建成功")
        else:
            print(f"✅ 存储桶 '{bucket_name}' 已存在")
        
        # 创建一个测试文件来验证存储桶可用性
        try:
            test_content = b"This is a test file for ERAG knowledge base."
            client.put_object(
                bucket_name, 
                "test/readme.txt", 
                io.BytesIO(test_content), 
                len(test_content)
            )
            print("✅ 测试文件上传成功")
        except Exception as e:
            print(f"⚠️  测试文件上传失败: {str(e)}")
        
        return True
        
    except Exception as e:
        print(f"❌ MinIO初始化失败: {str(e)}")
        return False


def init_starrocks():
    """初始化StarRocks数据库"""
    settings = get_settings()
    
    print("🔧 初始化StarRocks数据库...")
    
    try:
        connection = pymysql.connect(
            host=settings.starrocks_host,
            port=settings.starrocks_port,
            user=settings.starrocks_user,
            password=settings.starrocks_password or "",
            charset='utf8mb4'
        )
        
        with connection.cursor() as cursor:
            # 创建知识库数据库
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {settings.starrocks_database}")
            print(f"✅ StarRocks数据库 '{settings.starrocks_database}' 创建成功")
            
            # 切换到知识库数据库
            cursor.execute(f"USE {settings.starrocks_database}")
            
            # 创建向量表 (简化版本)
            vector_table_sql = """
            CREATE TABLE IF NOT EXISTS document_vectors (
                id BIGINT AUTO_INCREMENT,
                document_id VARCHAR(255) NOT NULL,
                chunk_id VARCHAR(255) NOT NULL,
                content TEXT,
                vector ARRAY<FLOAT> NOT NULL,
                metadata JSON,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=OLAP
            DUPLICATE KEY(id)
            DISTRIBUTED BY HASH(document_id) BUCKETS 10
            PROPERTIES (
                "replication_num" = "1"
            )
            """
            cursor.execute(vector_table_sql)
            print("✅ StarRocks向量表创建成功")
            
            # 创建实体表 (简化版本)
            entity_table_sql = """
            CREATE TABLE IF NOT EXISTS knowledge_entities (
                id BIGINT AUTO_INCREMENT,
                entity_id VARCHAR(255) NOT NULL,
                entity_name VARCHAR(500) NOT NULL,
                entity_type VARCHAR(100) NOT NULL,
                properties JSON,
                confidence FLOAT DEFAULT 0.0,
                source_documents JSON,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=OLAP
            DUPLICATE KEY(id)
            DISTRIBUTED BY HASH(entity_id) BUCKETS 10
            PROPERTIES (
                "replication_num" = "1"
            )
            """
            cursor.execute(entity_table_sql)
            print("✅ StarRocks实体表创建成功")
            
            # 创建关系表 (简化版本)
            relation_table_sql = """
            CREATE TABLE IF NOT EXISTS knowledge_relations (
                id BIGINT AUTO_INCREMENT,
                relation_id VARCHAR(255) NOT NULL,
                source_entity_id VARCHAR(255) NOT NULL,
                target_entity_id VARCHAR(255) NOT NULL,
                relation_type VARCHAR(100) NOT NULL,
                properties JSON,
                confidence FLOAT DEFAULT 0.0,
                source_documents JSON,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=OLAP
            DUPLICATE KEY(id)
            DISTRIBUTED BY HASH(relation_id) BUCKETS 10
            PROPERTIES (
                "replication_num" = "1"
            )
            """
            cursor.execute(relation_table_sql)
            print("✅ StarRocks关系表创建成功")
        
        connection.close()
        return True
        
    except Exception as e:
        print(f"❌ StarRocks初始化失败: {str(e)}")
        return False


def test_connections():
    """测试所有连接"""
    print("🧪 测试服务连接...")
    
    settings = get_settings()
    success_count = 0
    
    # 测试MySQL
    try:
        connection = pymysql.connect(
            host=settings.mysql_host,
            port=settings.mysql_port,
            user=settings.mysql_user,
            password=settings.mysql_password,
            database=settings.mysql_database,
            charset='utf8mb4'
        )
        connection.close()
        print("✅ MySQL连接测试成功")
        success_count += 1
    except Exception as e:
        print(f"❌ MySQL连接测试失败: {str(e)}")
    
    # 测试MinIO
    try:
        client = Minio(
            settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_secure
        )
        client.bucket_exists(settings.minio_bucket_name)
        print("✅ MinIO连接测试成功")
        success_count += 1
    except Exception as e:
        print(f"❌ MinIO连接测试失败: {str(e)}")
    
    # 测试StarRocks
    try:
        connection = pymysql.connect(
            host=settings.starrocks_host,
            port=settings.starrocks_port,
            user=settings.starrocks_user,
            password=settings.starrocks_password or "",
            database=settings.starrocks_database,
            charset='utf8mb4'
        )
        connection.close()
        print("✅ StarRocks连接测试成功")
        success_count += 1
    except Exception as e:
        print(f"❌ StarRocks连接测试失败: {str(e)}")
    
    return success_count


def main():
    """主函数"""
    print("🚀 开始初始化远程服务...")
    print("=" * 50)
    
    success_count = 0
    total_count = 3
    
    # 初始化MySQL
    if init_mysql():
        success_count += 1
    
    print()
    
    # 初始化MinIO
    if init_minio():
        success_count += 1
    
    print()
    
    # 初始化StarRocks
    if init_starrocks():
        success_count += 1
    
    print()
    print("=" * 50)
    print(f"📊 初始化结果: {success_count}/{total_count} 成功")
    
    if success_count > 0:
        print("\n🧪 测试连接...")
        test_success = test_connections()
        print(f"📊 连接测试: {test_success}/3 成功")
    
    if success_count == total_count:
        print("\n🎉 所有服务初始化完成！")
        print("🔄 请运行 'python test_remote_environment.py' 进行完整测试")
        return True
    else:
        print(f"\n⚠️  有 {total_count - success_count} 个服务初始化失败")
        print("💡 部分服务可能需要手动配置")
        return False


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  初始化被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 初始化过程中发生错误: {str(e)}")
        sys.exit(1) 