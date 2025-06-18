#!/usr/bin/env python3
"""
企业知识库项目问题修复脚本
自动检测和修复项目中的常见问题
"""

import subprocess
import sys
import os
from pathlib import Path

def run_command(cmd, description=""):
    """运行命令并处理错误"""
    print(f"🔧 {description}")
    print(f"   执行: {cmd}")
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"   ✅ 成功")
            return True
        else:
            print(f"   ❌ 失败: {result.stderr}")
            return False
    except Exception as e:
        print(f"   ❌ 异常: {str(e)}")
        return False

def check_and_install_python_deps():
    """检查并安装Python依赖"""
    print("\n📦 检查Python依赖...")
    
    # 核心依赖列表
    core_deps = [
        "pydantic-settings",
        "fastapi",
        "uvicorn",
        "neo4j",
        "redis",
        "pymysql",
        "sqlalchemy",
        "minio",
        "aiofiles",
        "aioredis",
        "loguru",
        "email-validator",
        "PyJWT",
        "passlib[bcrypt]",
        "spacy",
        "jieba",
        "openai",
        "anthropic",
        "aiosqlite",
        "scikit-learn",
        "transformers",
        "sentence-transformers",
        "httpx",
        "requests"
    ]
    
    # 分批安装以避免冲突
    batch1 = ["pydantic-settings", "fastapi", "uvicorn", "httpx", "requests"]
    batch2 = ["neo4j", "redis", "pymysql", "sqlalchemy", "aiosqlite"]
    batch3 = ["minio", "aiofiles", "aioredis", "loguru", "email-validator"]
    batch4 = ["PyJWT", "passlib[bcrypt]"]
    batch5 = ["openai", "anthropic"]
    
    batches = [
        (batch1, "核心Web框架"),
        (batch2, "数据库连接器"),
        (batch3, "异步和存储"),
        (batch4, "认证"),
        (batch5, "LLM客户端")
    ]
    
    for batch, desc in batches:
        cmd = f"pip install {' '.join(batch)}"
        run_command(cmd, f"安装{desc}依赖")

def check_env_file():
    """检查并创建.env文件"""
    print("\n🔧 检查环境配置...")
    
    env_file = Path(".env")
    if not env_file.exists():
        print("   创建.env文件...")
        env_content = """# 应用配置
APP_NAME=Enterprise Knowledge Base
APP_VERSION=1.0.0
APP_DEBUG=true
APP_HOST=0.0.0.0
APP_PORT=8000

# 安全配置
SECRET_KEY=your-secret-key-change-in-production-12345678901234567890
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# Neo4j 配置
NEO4J_URL=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password123

# MySQL 配置
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=erag
MYSQL_PASSWORD=erag123
MYSQL_DATABASE=erag_metadata
MYSQL_URL=mysql+pymysql://erag:erag123@localhost:3306/erag_metadata

# Redis 配置
REDIS_URL=redis://:redis123@localhost:6379
REDIS_PASSWORD=redis123
REDIS_DB=0

# MinIO 配置
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin123
MINIO_BUCKET_NAME=knowledge-base
MINIO_SECURE=false

# LLM 配置
LLM_API_KEY=your-llm-api-key-here
LLM_MODEL=qwen-max
LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
LLM_TEMPERATURE=0.7
LLM_MAX_TOKENS=2048

# OCR 服务配置
OCR_SERVICE_URL=http://localhost:8002
OCR_MAX_FILE_SIZE=10485760
OCR_SUPPORTED_FORMATS=pdf,png,jpg,jpeg,tiff,bmp
"""
        with open(".env", "w", encoding="utf-8") as f:
            f.write(env_content)
        print("   ✅ .env文件已创建")
    else:
        print("   ✅ .env文件已存在")

def check_frontend_deps():
    """检查前端依赖"""
    print("\n📦 检查前端依赖...")
    
    frontend_dir = Path("frontend")
    if frontend_dir.exists():
        os.chdir("frontend")
        
        # 检查package.json中的版本冲突
        package_json = Path("package.json")
        if package_json.exists():
            with open(package_json, "r", encoding="utf-8") as f:
                content = f.read()
            
            # 修复已知的版本冲突
            if '"pinia-plugin-persistedstate": "^4.3.0"' in content:
                content = content.replace(
                    '"pinia-plugin-persistedstate": "^4.3.0"',
                    '"pinia-plugin-persistedstate": "^3.2.1"'
                )
                with open(package_json, "w", encoding="utf-8") as f:
                    f.write(content)
                print("   🔧 修复了pinia-plugin-persistedstate版本冲突")
        
        # 尝试安装依赖
        if run_command("npm install", "安装前端依赖"):
            print("   ✅ 前端依赖安装成功")
        else:
            print("   ⚠️  前端依赖安装失败，可能需要手动处理")
        
        os.chdir("..")
    else:
        print("   ⚠️  frontend目录不存在")

def test_backend_import():
    """测试后端导入"""
    print("\n🧪 测试后端导入...")
    
    try:
        # 尝试导入主要模块
        import backend.config.settings
        print("   ✅ 配置模块导入成功")
        
        # 测试设置加载
        from backend.config.settings import get_settings
        settings = get_settings()
        print("   ✅ 设置加载成功")
        
        # 尝试导入主应用（可能会因为缺少一些依赖而失败）
        try:
            from backend.main import app
            print("   ✅ 主应用导入成功")
        except ImportError as e:
            print(f"   ⚠️  主应用导入失败: {str(e)}")
            return False
            
    except Exception as e:
        print(f"   ❌ 后端导入测试失败: {str(e)}")
        return False
    
    return True

def create_directories():
    """创建必要的目录"""
    print("\n📁 创建必要目录...")
    
    dirs = [
        "logs",
        "data",
        "uploads",
        "temp"
    ]
    
    for dir_name in dirs:
        dir_path = Path(dir_name)
        if not dir_path.exists():
            dir_path.mkdir(parents=True, exist_ok=True)
            print(f"   ✅ 创建目录: {dir_name}")
        else:
            print(f"   ✅ 目录已存在: {dir_name}")

def main():
    """主函数"""
    print("🚀 企业知识库项目问题修复脚本")
    print("=" * 50)
    
    # 确保在项目根目录
    if not Path("backend").exists() or not Path("requirements.txt").exists():
        print("❌ 请在项目根目录运行此脚本")
        sys.exit(1)
    
    # 执行修复步骤
    steps = [
        create_directories,
        check_env_file,
        check_and_install_python_deps,
        test_backend_import,
        check_frontend_deps,
    ]
    
    success_count = 0
    for step in steps:
        try:
            if step():
                success_count += 1
        except Exception as e:
            print(f"   ❌ 步骤执行失败: {str(e)}")
    
    print("\n" + "=" * 50)
    print(f"🎉 修复完成! 成功执行 {success_count}/{len(steps)} 个步骤")
    
    print("\n📋 下一步操作建议:")
    print("1. 启动外部服务: docker-compose -f docker-compose-dataplatform.yml up -d")
    print("2. 初始化数据库: python scripts/init_db.py")
    print("3. 启动后端服务: cd backend && uvicorn main:app --reload")
    print("4. 启动前端服务: cd frontend && npm run dev")
    
    print("\n⚠️  注意事项:")
    print("- 请确保设置真实的LLM API密钥")
    print("- 生产环境请修改默认密码")
    print("- 检查ISSUES_FIXED.md了解详细信息")

if __name__ == "__main__":
    main() 