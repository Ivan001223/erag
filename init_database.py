#!/usr/bin/env python3
"""数据库初始化脚本"""

import asyncio
import mysql.connector
from mysql.connector import Error
from neo4j import GraphDatabase
import redis
from minio import Minio


async def init_mysql():
    """初始化MySQL数据库"""
    try:
        # 连接MySQL
        connection = mysql.connector.connect(
            host='localhost',
            port=3306,
            user='root',
            password='rootpass'
        )
        
        cursor = connection.cursor()
        
        # 创建数据库
        cursor.execute("CREATE DATABASE IF NOT EXISTS erag_metadata CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        cursor.execute("USE erag_metadata")
        
        # 创建用户表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(50) UNIQUE NOT NULL,
                email VARCHAR(100) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                full_name VARCHAR(100),
                is_active BOOLEAN DEFAULT TRUE,
                is_superuser BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            )
        """)
        
        # 创建文档表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                id INT AUTO_INCREMENT PRIMARY KEY,
                title VARCHAR(255) NOT NULL,
                content LONGTEXT,
                file_path VARCHAR(500),
                file_type VARCHAR(50),
                file_size BIGINT,
                status VARCHAR(20) DEFAULT 'pending',
                uploaded_by INT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                FOREIGN KEY (uploaded_by) REFERENCES users(id)
            )
        """)
        
        # 创建任务表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INT AUTO_INCREMENT PRIMARY KEY,
                task_type VARCHAR(50) NOT NULL,
                status VARCHAR(20) DEFAULT 'pending',
                input_data JSON,
                result_data JSON,
                error_message TEXT,
                created_by INT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                FOREIGN KEY (created_by) REFERENCES users(id)
            )
        """)
        
        # 创建配置表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS configurations (
                id INT AUTO_INCREMENT PRIMARY KEY,
                config_key VARCHAR(100) UNIQUE NOT NULL,
                config_value JSON,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            )
        """)
        
        # 插入默认用户
        cursor.execute("""
            INSERT IGNORE INTO users (username, email, password_hash, full_name, is_superuser)
            VALUES ('admin', 'admin@example.com', '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW', '系统管理员', TRUE)
        """)
        
        connection.commit()
        cursor.close()
        connection.close()
        
        print("✅ MySQL数据库初始化完成")
        return True
        
    except Error as e:
        print(f"❌ MySQL数据库初始化失败: {e}")
        return False


async def init_neo4j():
    """初始化Neo4j数据库"""
    try:
        driver = GraphDatabase.driver(
            "bolt://localhost:7687",
            auth=("neo4j", "password")
        )
        
        with driver.session() as session:
            # 创建索引
            session.run("CREATE INDEX entity_name_index IF NOT EXISTS FOR (n:Entity) ON (n.name)")
            session.run("CREATE INDEX document_id_index IF NOT EXISTS FOR (n:Document) ON (n.id)")
            
            # 创建约束
            session.run("CREATE CONSTRAINT entity_unique IF NOT EXISTS FOR (n:Entity) REQUIRE n.id IS UNIQUE")
            session.run("CREATE CONSTRAINT document_unique IF NOT EXISTS FOR (n:Document) REQUIRE n.id IS UNIQUE")
        
        driver.close()
        print("✅ Neo4j数据库初始化完成")
        return True
        
    except Exception as e:
        print(f"❌ Neo4j数据库初始化失败: {e}")
        return False


async def init_minio():
    """初始化MinIO存储桶"""
    try:
        client = Minio(
            "localhost:9000",
            access_key="admin",
            secret_key="StrongPass!",
            secure=False
        )
        
        # 创建存储桶
        buckets = ["knowledge-base", "documents", "vectors", "logs"]
        
        for bucket in buckets:
            if not client.bucket_exists(bucket):
                client.make_bucket(bucket)
                print(f"✅ 创建存储桶: {bucket}")
            else:
                print(f"ℹ️  存储桶已存在: {bucket}")
        
        print("✅ MinIO存储桶初始化完成")
        return True
        
    except Exception as e:
        print(f"❌ MinIO存储桶初始化失败: {e}")
        return False


async def init_redis():
    """初始化Redis"""
    try:
        r = redis.Redis(host='localhost', port=6379)
        
        # 设置一些基础配置
        r.set("app:initialized", "true")
        r.set("app:version", "1.0.0")
        
        print("✅ Redis初始化完成")
        return True
        
    except Exception as e:
        print(f"❌ Redis初始化失败: {e}")
        return False


async def main():
    """主函数"""
    print("🚀 开始初始化数据中台数据库...\n")
    
    results = []
    
    # 初始化各个服务
    results.append(await init_mysql())
    results.append(await init_neo4j())
    results.append(await init_minio())
    results.append(await init_redis())
    
    # 总结
    success_count = sum(results)
    total_count = len(results)
    
    print(f"\n📊 初始化结果:")
    print("=" * 40)
    print(f"成功: {success_count}/{total_count}")
    
    if success_count == total_count:
        print("\n🎉 数据中台数据库初始化完成，可以开始开发了！")
        print("\n🔗 服务访问地址:")
        print("   • MySQL: localhost:3306 (root/rootpass)")
        print("   • Redis: localhost:6379")
        print("   • Neo4j: http://localhost:7474 (neo4j/password)")
        print("   • MinIO: http://localhost:9001 (admin/StrongPass!)")
        print("   • Flink: http://localhost:8081")
        print("   • Grafana: http://localhost:3000 (admin/admin)")
        print("   • Adminer: http://localhost:8082")
    else:
        print(f"\n⚠️  有 {total_count - success_count} 个服务初始化失败")


if __name__ == "__main__":
    asyncio.run(main()) 