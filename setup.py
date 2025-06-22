from setuptools import setup, find_packages

setup(
    name="erag",
    version="1.0.0",
    description="企业级智能知识库系统",
    packages=find_packages(),
    python_requires=">=3.8",
    install_requires=[
        "fastapi>=0.104.0",
        "uvicorn>=0.24.0",
        "sqlalchemy>=2.0.0",
        "pymysql>=1.1.0",
        "redis>=5.0.0",
        "neo4j>=5.0.0",
        "minio>=7.0.0",
        "pydantic>=2.0.0",
    ],
) 