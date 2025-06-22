#!/usr/bin/env python3
"""
远程环境连接测试脚本
测试连接到192.168.0.101上部署的数据平台服务
"""

import asyncio
import sys
import traceback
from typing import Dict, Any
import pymysql
import redis
import requests
from neo4j import GraphDatabase
from minio import Minio
from backend.config.settings import get_settings


class RemoteEnvironmentTester:
    """远程环境测试器"""
    
    def __init__(self):
        self.settings = get_settings()
        self.test_results = {}
        
    def print_header(self, title: str):
        """打印测试标题"""
        print(f"\n🧪 {title}:")
        print("=" * 50)
    
    def print_result(self, test_name: str, success: bool, message: str = ""):
        """打印测试结果"""
        status = "✅" if success else "❌"
        print(f"{status} {test_name}: {message}")
        self.test_results[test_name] = success
    
    def test_mysql_connection(self) -> bool:
        """测试MySQL连接"""
        try:
            connection = pymysql.connect(
                host=self.settings.mysql_host,
                port=self.settings.mysql_port,
                user=self.settings.mysql_user,
                password=self.settings.mysql_password,
                database=self.settings.mysql_database,
                charset='utf8mb4'
            )
            
            with connection.cursor() as cursor:
                cursor.execute("SELECT VERSION()")
                version = cursor.fetchone()[0]
                self.print_result("MySQL连接", True, f"版本: {version}")
                
                # 检查数据库
                cursor.execute("SELECT DATABASE()")
                db_name = cursor.fetchone()[0]
                self.print_result("数据库检查", True, f"当前数据库: {db_name}")
                
                # 检查表
                cursor.execute("SHOW TABLES")
                tables = cursor.fetchall()
                table_count = len(tables)
                self.print_result("表结构检查", True, f"发现 {table_count} 个表")
                
                if table_count > 0:
                    print("   表列表:")
                    for table in tables[:10]:  # 只显示前10个表
                        print(f"   - {table[0]}")
                    if table_count > 10:
                        print(f"   ... 还有 {table_count - 10} 个表")
            
            connection.close()
            return True
            
        except Exception as e:
            self.print_result("MySQL连接", False, f"错误: {str(e)}")
            return False
    
    def test_redis_connection(self) -> bool:
        """测试Redis连接"""
        try:
            r = redis.Redis(
                host="192.168.0.101",
                port=6379,
                password="redis123",
                db=0,
                decode_responses=True
            )
            
            # 测试连接
            r.ping()
            self.print_result("Redis连接", True, "连接成功")
            
            # 测试读写
            r.set("test_key", "test_value", ex=10)
            value = r.get("test_key")
            self.print_result("Redis读写", True, f"测试值: {value}")
            
            # 获取信息
            info = r.info()
            version = info.get('redis_version', 'unknown')
            self.print_result("Redis信息", True, f"版本: {version}")
            
            return True
            
        except Exception as e:
            self.print_result("Redis连接", False, f"错误: {str(e)}")
            return False
    
    def test_neo4j_connection(self) -> bool:
        """测试Neo4j连接"""
        try:
            driver = GraphDatabase.driver(
                self.settings.neo4j_url,
                auth=(self.settings.neo4j_user, self.settings.neo4j_password)
            )
            
            with driver.session() as session:
                # 测试连接
                result = session.run("RETURN 'Hello Neo4j' as message")
                message = result.single()["message"]
                self.print_result("Neo4j连接", True, f"消息: {message}")
                
                # 获取版本信息
                result = session.run("CALL dbms.components() YIELD name, versions")
                components = list(result)
                if components:
                    version = components[0]["versions"][0]
                    self.print_result("Neo4j版本", True, f"版本: {version}")
                
                # 检查节点数量
                result = session.run("MATCH (n) RETURN count(n) as count")
                count = result.single()["count"]
                self.print_result("Neo4j节点数", True, f"节点数量: {count}")
            
            driver.close()
            return True
            
        except Exception as e:
            self.print_result("Neo4j连接", False, f"错误: {str(e)}")
            return False
    
    def test_minio_connection(self) -> bool:
        """测试MinIO连接"""
        try:
            client = Minio(
                self.settings.minio_endpoint,
                access_key=self.settings.minio_access_key,
                secret_key=self.settings.minio_secret_key,
                secure=self.settings.minio_secure
            )
            
            # 测试连接
            buckets = client.list_buckets()
            bucket_names = [bucket.name for bucket in buckets]
            self.print_result("MinIO连接", True, f"发现 {len(bucket_names)} 个存储桶")
            
            if bucket_names:
                print("   存储桶列表:")
                for bucket_name in bucket_names:
                    print(f"   - {bucket_name}")
            
            # 检查目标存储桶是否存在
            bucket_exists = client.bucket_exists(self.settings.minio_bucket_name)
            self.print_result("目标存储桶", bucket_exists, 
                            f"存储桶 '{self.settings.minio_bucket_name}' {'存在' if bucket_exists else '不存在'}")
            
            return True
            
        except Exception as e:
            self.print_result("MinIO连接", False, f"错误: {str(e)}")
            return False
    
    def test_starrocks_connection(self) -> bool:
        """测试StarRocks连接"""
        try:
            connection = pymysql.connect(
                host=self.settings.starrocks_host,
                port=self.settings.starrocks_port,
                user=self.settings.starrocks_user,
                password=self.settings.starrocks_password or "",
                charset='utf8mb4'
            )
            
            with connection.cursor() as cursor:
                cursor.execute("SELECT VERSION()")
                version = cursor.fetchone()[0]
                self.print_result("StarRocks连接", True, f"版本: {version}")
                
                # 检查数据库
                cursor.execute("SHOW DATABASES")
                databases = cursor.fetchall()
                db_names = [db[0] for db in databases]
                self.print_result("StarRocks数据库", True, f"发现 {len(db_names)} 个数据库")
                
                if db_names:
                    print("   数据库列表:")
                    for db_name in db_names:
                        print(f"   - {db_name}")
            
            connection.close()
            return True
            
        except Exception as e:
            self.print_result("StarRocks连接", False, f"错误: {str(e)}")
            return False
    
    def test_flink_connection(self) -> bool:
        """测试Flink连接"""
        try:
            # 测试Flink JobManager REST API
            response = requests.get(f"{self.settings.flink_jobmanager_url}/config", timeout=10)
            response.raise_for_status()
            
            config = response.json()
            self.print_result("Flink连接", True, "JobManager REST API 可用")
            
            # 获取集群信息
            response = requests.get(f"{self.settings.flink_jobmanager_url}/overview", timeout=10)
            if response.status_code == 200:
                overview = response.json()
                task_managers = overview.get('taskmanagers', 0)
                slots_total = overview.get('slots-total', 0)
                self.print_result("Flink集群信息", True, 
                                f"TaskManager: {task_managers}, 总槽位: {slots_total}")
            
            # 获取作业列表
            response = requests.get(f"{self.settings.flink_jobmanager_url}/jobs", timeout=10)
            if response.status_code == 200:
                jobs = response.json()
                job_count = len(jobs.get('jobs', []))
                self.print_result("Flink作业", True, f"运行中的作业: {job_count}")
            
            return True
            
        except Exception as e:
            self.print_result("Flink连接", False, f"错误: {str(e)}")
            return False
    
    def test_service_health(self) -> bool:
        """测试服务健康状态"""
        health_checks = [
            ("Neo4j Web界面", "http://192.168.0.101:7474"),
            ("MinIO控制台", "http://192.168.0.101:9001"),
            ("Flink Web界面", "http://192.168.0.101:8081"),
        ]
        
        all_healthy = True
        for service_name, url in health_checks:
            try:
                response = requests.get(url, timeout=5)
                if response.status_code == 200:
                    self.print_result(f"{service_name}健康检查", True, "服务可用")
                else:
                    self.print_result(f"{service_name}健康检查", False, 
                                    f"HTTP {response.status_code}")
                    all_healthy = False
            except Exception as e:
                self.print_result(f"{service_name}健康检查", False, f"错误: {str(e)}")
                all_healthy = False
        
        return all_healthy
    
    def run_all_tests(self):
        """运行所有测试"""
        print("🔍 远程环境连接测试")
        print("=" * 50)
        print(f"🎯 目标服务器: 192.168.0.101")
        print(f"🔧 配置文件: backend/config/settings.py")
        
        # 显示连接信息
        print("\n📋 连接配置:")
        print(f"   • MySQL: {self.settings.mysql_host}:{self.settings.mysql_port}/{self.settings.mysql_database}")
        print(f"   • Neo4j: {self.settings.neo4j_url}")
        print(f"   • Redis: 192.168.0.101:6379")
        print(f"   • MinIO: {self.settings.minio_endpoint}")
        print(f"   • StarRocks: {self.settings.starrocks_host}:{self.settings.starrocks_port}")
        print(f"   • Flink: {self.settings.flink_jobmanager_url}")
        
        # 运行测试
        self.print_header("MySQL数据库测试")
        self.test_mysql_connection()
        
        self.print_header("Redis缓存测试")
        self.test_redis_connection()
        
        self.print_header("Neo4j图数据库测试")
        self.test_neo4j_connection()
        
        self.print_header("MinIO对象存储测试")
        self.test_minio_connection()
        
        self.print_header("StarRocks向量数据库测试")
        self.test_starrocks_connection()
        
        self.print_header("Flink实时处理测试")
        self.test_flink_connection()
        
        self.print_header("服务健康状态检查")
        self.test_service_health()
        
        # 统计结果
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results.values() if result)
        failed_tests = total_tests - passed_tests
        
        print("\n" + "=" * 50)
        print("📊 测试结果汇总:")
        print(f"   ✅ 通过: {passed_tests}")
        print(f"   ❌ 失败: {failed_tests}")
        print(f"   📈 成功率: {passed_tests/total_tests*100:.1f}%")
        
        if failed_tests == 0:
            print("\n🎉 所有服务连接正常！可以开始使用系统。")
            return True
        else:
            print(f"\n⚠️  有 {failed_tests} 个服务连接失败，请检查服务状态。")
            return False


def main():
    """主函数"""
    try:
        tester = RemoteEnvironmentTester()
        success = tester.run_all_tests()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  测试被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 测试过程中发生错误: {str(e)}")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main() 