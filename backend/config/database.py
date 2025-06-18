from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import QueuePool
from typing import Generator, AsyncGenerator
import os
from functools import lru_cache

from .settings import get_settings

# SQLAlchemy 基础类
Base = declarative_base()

# 数据库引擎
engine = None
SessionLocal = None
async_engine = None
AsyncSessionLocal = None


def init_database():
    """初始化数据库连接"""
    global engine, SessionLocal, async_engine, AsyncSessionLocal
    
    settings = get_settings()
    
    # 构建数据库URL
    database_url = (
        f"mysql+aiomysql://{settings.mysql_user}:{settings.mysql_password}"
        f"@{settings.mysql_host}:{settings.mysql_port}/{settings.mysql_database}"
    )
    
    # 创建同步引擎
    sync_database_url = (
        f"mysql+pymysql://{settings.mysql_user}:{settings.mysql_password}"
        f"@{settings.mysql_host}:{settings.mysql_port}/{settings.mysql_database}"
    )
    
    engine = create_engine(
        sync_database_url,
        poolclass=QueuePool,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,
        pool_recycle=3600,
        echo=settings.app_debug,
    )
    
    # 创建异步引擎
    async_engine = create_async_engine(
        database_url,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,
        pool_recycle=3600,
        echo=settings.app_debug,
    )
    
    # 创建会话工厂
    SessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine
    )
    
    # 创建异步会话工厂
    AsyncSessionLocal = async_sessionmaker(
        async_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )


def get_db() -> Generator:
    """获取数据库会话"""
    if SessionLocal is None:
        init_database()
    
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """获取异步数据库会话"""
    if AsyncSessionLocal is None:
        init_database()
    
    async with AsyncSessionLocal() as session:
        yield session


def create_tables():
    """创建所有表"""
    if engine is None:
        init_database()
    
    Base.metadata.create_all(bind=engine)


def drop_tables():
    """删除所有表"""
    if engine is None:
        init_database()
    
    Base.metadata.drop_all(bind=engine)