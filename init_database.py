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
        cursor.execute("CREATE DATABASE IF NOT EXISTS erag CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        cursor.execute("USE erag")
        
        print("✅ MySQL数据库创建成功")
        
        # 执行初始化SQL脚本
        with open('scripts/init_mysql_cdc.sql', 'r', encoding='utf-8') as f:
            sql_content = f.read()
            
        # 分割SQL语句并执行
        sql_statements = sql_content.split(';')
        for statement in sql_statements:
            statement = statement.strip()
            if statement and not statement.startswith('--'):
                try:
                    cursor.execute(statement)
                except Error as e:
                    if "already exists" not in str(e).lower():
                        print(f"⚠️  SQL执行警告: {e}")
        
        connection.commit()
        print("✅ MySQL表结构创建成功")
        
    except Error as e:
        print(f"❌ MySQL初始化失败: {e}")
        raise
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()


async def init_neo4j():
    """初始化Neo4j数据库"""
    try:
        driver = GraphDatabase.driver(
            "bolt://localhost:7687",
            auth=("neo4j", "neo4j123")
        )
        
        with driver.session() as session:
            # 创建约束
            session.run("CREATE CONSTRAINT entity_id IF NOT EXISTS FOR (e:Entity) REQUIRE e.id IS UNIQUE")
            session.run("CREATE CONSTRAINT relation_id IF NOT EXISTS FOR (r:Relation) REQUIRE r.id IS UNIQUE")
            
            # 创建索引
            session.run("CREATE INDEX entity_name IF NOT EXISTS FOR (e:Entity) ON (e.name)")
            session.run("CREATE INDEX entity_type IF NOT EXISTS FOR (e:Entity) ON (e.type)")
            
        driver.close()
        print("✅ Neo4j数据库初始化成功")
        
    except Exception as e:
        print(f"❌ Neo4j初始化失败: {e}")
        raise


async def init_redis():
    """初始化Redis"""
    try:
        r = redis.Redis(host='localhost', port=6379, db=0)
        r.ping()
        print("✅ Redis连接成功")
        
    except Exception as e:
        print(f"❌ Redis初始化失败: {e}")
        raise


async def init_minio():
    """初始化MinIO"""
    try:
        client = Minio(
            "localhost:9000",
            access_key="minioadmin",
            secret_key="minioadmin",
            secure=False
        )
        
        # 创建存储桶
        bucket_name = "knowledge-base"
        if not client.bucket_exists(bucket_name):
            client.make_bucket(bucket_name)
            print(f"✅ MinIO存储桶 '{bucket_name}' 创建成功")
        else:
            print(f"✅ MinIO存储桶 '{bucket_name}' 已存在")
            
    except Exception as e:
        print(f"❌ MinIO初始化失败: {e}")
        raise


async def main():
    """主函数"""
    print("🚀 开始初始化数据库...")
    
    try:
        await init_mysql()
        await init_neo4j()
        await init_redis()
        await init_minio()
        
        print("🎉 所有数据库初始化完成！")
        
    except Exception as e:
        print(f"💥 初始化失败: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(asyncio.run(main())) 