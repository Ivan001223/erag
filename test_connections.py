#!/usr/bin/env python3
"""测试数据中台服务连接的脚本"""

import asyncio
import sys
from typing import Dict, Any
import mysql.connector
import redis
from neo4j import GraphDatabase
from minio import Minio
import requests
from datetime import datetime


class ServiceTester:
    """服务连接测试器"""
    
    def __init__(self):
        self.results = {}
    
    async def test_mysql(self) -> Dict[str, Any]:
        """测试MySQL连接"""
        try:
            connection = mysql.connector.connect(
                host='localhost',
                port=3306,
                user='root',
                password='rootpass',
                connect_timeout=5
            )
            
            cursor = connection.cursor()
            cursor.execute("SELECT VERSION()")
            version = cursor.fetchone()[0]
            
            cursor.close()
            connection.close()
            
            return {
                "status": "success",
                "message": f"MySQL连接成功，版本: {version}",
                "version": version
            }
        except Exception as e:
            return {
                "status": "failed",
                "message": f"MySQL连接失败: {str(e)}"
            }
    
    async def test_redis(self) -> Dict[str, Any]:
        """测试Redis连接"""
        try:
            r = redis.Redis(
                host='localhost',
                port=6379,
                socket_connect_timeout=5
            )
            
            # 测试ping
            pong = r.ping()
            info = r.info()
            
            return {
                "status": "success" if pong else "failed",
                "message": f"Redis连接成功，版本: {info.get('redis_version')}",
                "version": info.get('redis_version'),
                "memory_used": info.get('used_memory_human')
            }
        except Exception as e:
            return {
                "status": "failed",
                "message": f"Redis连接失败: {str(e)}"
            }
    
    async def test_neo4j(self) -> Dict[str, Any]:
        """测试Neo4j连接"""
        try:
            driver = GraphDatabase.driver(
                "bolt://localhost:7687",
                auth=("neo4j", "password")
            )
            
            # 验证连接
            driver.verify_connectivity()
            
            with driver.session() as session:
                result = session.run("CALL dbms.components() YIELD versions")
                record = result.single()
                versions = record["versions"] if record else []
                version = versions[0] if versions else "Unknown"
            
            driver.close()
            
            return {
                "status": "success",
                "message": f"Neo4j连接成功，版本: {version}",
                "version": version
            }
        except Exception as e:
            return {
                "status": "failed",
                "message": f"Neo4j连接失败: {str(e)}"
            }
    
    async def test_minio(self) -> Dict[str, Any]:
        """测试MinIO连接"""
        try:
            client = Minio(
                "localhost:9000",
                access_key="admin",
                secret_key="StrongPass!",
                secure=False
            )
            
            # 测试连接
            buckets = client.list_buckets()
            bucket_names = [bucket.name for bucket in buckets]
            
            return {
                "status": "success",
                "message": f"MinIO连接成功，存储桶: {bucket_names}",
                "buckets": bucket_names
            }
        except Exception as e:
            return {
                "status": "failed",
                "message": f"MinIO连接失败: {str(e)}"
            }
    
    async def test_starrocks(self) -> Dict[str, Any]:
        """测试StarRocks连接"""
        try:
            connection = mysql.connector.connect(
                host='localhost',
                port=9030,
                user='root',
                connect_timeout=5
            )
            
            cursor = connection.cursor()
            cursor.execute("SELECT @@version_comment")
            version = cursor.fetchone()[0]
            
            cursor.execute("SHOW DATABASES")
            databases = [row[0] for row in cursor.fetchall()]
            
            cursor.close()
            connection.close()
            
            return {
                "status": "success",
                "message": f"StarRocks连接成功，版本: {version}",
                "version": version,
                "databases": databases
            }
        except Exception as e:
            return {
                "status": "failed",
                "message": f"StarRocks连接失败: {str(e)}"
            }
    
    async def test_flink(self) -> Dict[str, Any]:
        """测试Flink连接"""
        try:
            response = requests.get("http://localhost:8081/overview", timeout=5)
            if response.status_code == 200:
                data = response.json()
                return {
                    "status": "success",
                    "message": f"Flink连接成功，版本: {data.get('flink-version')}",
                    "version": data.get("flink-version"),
                    "taskmanagers": data.get("taskmanagers"),
                    "slots_total": data.get("slots-total"),
                    "jobs_running": data.get("jobs-running")
                }
            else:
                return {
                    "status": "failed",
                    "message": f"Flink连接失败，HTTP状态: {response.status_code}"
                }
        except Exception as e:
            return {
                "status": "failed",
                "message": f"Flink连接失败: {str(e)}"
            }
    
    async def run_all_tests(self):
        """运行所有测试"""
        print("🚀 开始测试数据中台服务连接...\n")
        
        tests = [
            ("MySQL", self.test_mysql()),
            ("Redis", self.test_redis()),
            ("Neo4j", self.test_neo4j()),
            ("MinIO", self.test_minio()),
            ("StarRocks", self.test_starrocks()),
            ("Flink", self.test_flink())
        ]
        
        for service_name, test_coro in tests:
            print(f"📋 测试 {service_name}...")
            result = await test_coro
            self.results[service_name] = result
            
            if result["status"] == "success":
                print(f"✅ {result['message']}")
            else:
                print(f"❌ {result['message']}")
            print()
        
        # 总结
        print("=" * 50)
        print("📊 测试结果总结:")
        print("=" * 50)
        
        success_count = sum(1 for r in self.results.values() if r["status"] == "success")
        total_count = len(self.results)
        
        for service, result in self.results.items():
            status_icon = "✅" if result["status"] == "success" else "❌"
            print(f"{status_icon} {service:12}: {result['status'].upper()}")
        
        print(f"\n🎯 成功率: {success_count}/{total_count} ({success_count/total_count*100:.1f}%)")
        
        if success_count == total_count:
            print("\n🎉 所有服务连接正常，可以开始开发了！")
        else:
            print(f"\n⚠️  有 {total_count - success_count} 个服务连接失败，请检查相关配置")


async def main():
    """主函数"""
    tester = ServiceTester()
    await tester.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main()) 