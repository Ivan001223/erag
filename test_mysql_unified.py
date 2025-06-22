#!/usr/bin/env python3
"""MySQL统一架构连接测试脚本"""

import mysql.connector
from mysql.connector import Error
import sys


def test_mysql_connection():
    """测试MySQL基本连接"""
    try:
        connection = mysql.connector.connect(
            host='localhost',
            port=3306,
            user='erag',
            password='erag123',
            database='erag'
        )
        
        cursor = connection.cursor()
        cursor.execute("SELECT VERSION()")
        version = cursor.fetchone()[0]
        print(f"✅ MySQL连接成功，版本: {version}")
        
        cursor.close()
        connection.close()
        return True
        
    except Error as e:
        print(f"❌ MySQL连接失败: {e}")
        return False


def test_mysql_tables():
    """测试MySQL表结构"""
    try:
        connection = mysql.connector.connect(
            host='localhost',
            port=3306,
            user='erag',
            password='erag123',
            database='erag'
        )
        
        cursor = connection.cursor()
        
        # 检查表是否存在
        expected_tables = [
            'documents', 'document_chunks', 'entities', 'relations', 'vectors',
            'tasks', 'query_logs', 'metrics', 'configs', 'config_history', 'config_templates',
            'etl_jobs', 'etl_job_runs', 'etl_metrics',
            'graphs', 'graph_entities', 'graph_relations', 'graph_statistics',
            'users', 'knowledge_bases', 'notifications', 'cdc_monitoring'
        ]
        
        cursor.execute("SHOW TABLES")
        existing_tables = [row[0] for row in cursor.fetchall()]
        
        print(f"✅ 数据库中共有 {len(existing_tables)} 个表")
        
        missing_tables = []
        for table in expected_tables:
            if table in existing_tables:
                print(f"  ✓ {table}")
            else:
                print(f"  ✗ {table} (缺失)")
                missing_tables.append(table)
        
        if missing_tables:
            print(f"⚠️  缺失表: {', '.join(missing_tables)}")
            return False
        else:
            print("✅ 所有预期表都存在")
            return True
        
    except Error as e:
        print(f"❌ 表结构检查失败: {e}")
        return False
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()


def test_mysql_cdc_config():
    """测试MySQL CDC配置"""
    try:
        connection = mysql.connector.connect(
            host='localhost',
            port=3306,
            user='erag',
            password='erag123',
            database='erag'
        )
        
        cursor = connection.cursor()
        
        # 检查CDC相关配置
        cdc_configs = [
            ('log_bin', 'ON'),
            ('binlog_format', 'ROW'),
            ('binlog_row_image', 'FULL'),
            ('gtid_mode', 'ON')
        ]
        
        print("🔍 检查MySQL CDC配置:")
        all_good = True
        
        for config_name, expected_value in cdc_configs:
            cursor.execute(f"SHOW VARIABLES LIKE '{config_name}'")
            result = cursor.fetchone()
            
            if result:
                actual_value = result[1]
                if actual_value == expected_value:
                    print(f"  ✓ {config_name}: {actual_value}")
                else:
                    print(f"  ✗ {config_name}: {actual_value} (期望: {expected_value})")
                    all_good = False
            else:
                print(f"  ✗ {config_name}: 配置不存在")
                all_good = False
        
        # 检查CDC用户
        cursor.execute("SELECT User, Host FROM mysql.user WHERE User = 'cdc_user'")
        cdc_user = cursor.fetchone()
        
        if cdc_user:
            print(f"  ✓ CDC用户存在: {cdc_user[0]}@{cdc_user[1]}")
        else:
            print("  ✗ CDC用户不存在")
            all_good = False
        
        if all_good:
            print("✅ MySQL CDC配置正确")
        else:
            print("⚠️  MySQL CDC配置有问题")
        
        return all_good
        
    except Error as e:
        print(f"❌ CDC配置检查失败: {e}")
        return False
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()


def test_sample_data():
    """测试示例数据"""
    try:
        connection = mysql.connector.connect(
            host='localhost',
            port=3306,
            user='erag',
            password='erag123',
            database='erag'
        )
        
        cursor = connection.cursor()
        
        # 检查示例数据
        cursor.execute("SELECT COUNT(*) FROM documents")
        doc_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM entities")
        entity_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM relations")
        relation_count = cursor.fetchone()[0]
        
        print(f"📊 示例数据统计:")
        print(f"  • 文档: {doc_count} 条")
        print(f"  • 实体: {entity_count} 条")
        print(f"  • 关系: {relation_count} 条")
        
        if doc_count > 0 and entity_count > 0 and relation_count > 0:
            print("✅ 示例数据已加载")
            return True
        else:
            print("⚠️  示例数据可能未完全加载")
            return False
        
    except Error as e:
        print(f"❌ 示例数据检查失败: {e}")
        return False
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()


def main():
    """主函数"""
    print("🔍 MySQL统一架构测试")
    print("=" * 50)
    
    tests = [
        ("MySQL基本连接", test_mysql_connection),
        ("表结构检查", test_mysql_tables),
        ("CDC配置检查", test_mysql_cdc_config),
        ("示例数据检查", test_sample_data),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n🧪 {test_name}:")
        try:
            result = test_func()
            results.append(result)
        except Exception as e:
            print(f"❌ 测试失败: {e}")
            results.append(False)
    
    # 统计结果
    success_count = sum(results)
    total_count = len(results)
    
    print("\n" + "=" * 50)
    print(f"📊 测试结果: {success_count}/{total_count} 通过")
    
    if success_count == total_count:
        print("🎉 MySQL统一架构测试全部通过！")
        print("💡 系统已准备就绪，可以开始使用。")
    else:
        print(f"⚠️  有 {total_count - success_count} 个测试失败")
        print("💡 请检查MySQL服务和数据库初始化。")
        
    print("\n🔗 连接信息:")
    print("   • 数据库: erag")
    print("   • 用户: erag")
    print("   • 密码: erag123")
    print("   • 端口: 3306")
    
    return 0 if success_count == total_count else 1


if __name__ == "__main__":
    sys.exit(main()) 