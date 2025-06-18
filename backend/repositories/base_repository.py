from typing import Optional, List, Dict, Any, Type, TypeVar, Generic, Union
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy import select, update, delete, func, and_, or_, text
from sqlalchemy.exc import SQLAlchemyError
from contextlib import asynccontextmanager
import logging
from abc import ABC, abstractmethod

from ..models.base import Base
from ..config.database import get_db
from ..utils.logger import get_logger

T = TypeVar('T', bound=Base)

logger = get_logger(__name__)


class BaseRepository(Generic[T], ABC):
    """基础仓储类，提供通用的CRUD操作"""
    
    def __init__(self, model: Type[T], db_session: Optional[AsyncSession] = None):
        self.model = model
        self.db_session = db_session
        self.logger = get_logger(self.__class__.__name__)
    
    @asynccontextmanager
    async def get_session(self):
        """获取数据库会话"""
        if self.db_session:
            yield self.db_session
        else:
            async with get_db() as session:
                yield session
    
    async def create(self, **kwargs) -> Optional[T]:
        """创建记录"""
        try:
            async with self.get_session() as session:
                instance = self.model(**kwargs)
                session.add(instance)
                await session.commit()
                await session.refresh(instance)
                return instance
        except SQLAlchemyError as e:
            self.logger.error(f"Failed to create {self.model.__name__}: {str(e)}")
            return None
    
    async def get_by_id(self, id: str) -> Optional[T]:
        """根据ID获取记录"""
        try:
            async with self.get_session() as session:
                stmt = select(self.model).where(self.model.id == id)
                result = await session.execute(stmt)
                return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            self.logger.error(f"Failed to get {self.model.__name__} by id {id}: {str(e)}")
            return None
    
    async def get_all(
        self,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        order_by: Optional[str] = None,
        **filters
    ) -> List[T]:
        """获取所有记录"""
        try:
            async with self.get_session() as session:
                stmt = select(self.model)
                
                # 添加过滤条件
                if filters:
                    conditions = []
                    for key, value in filters.items():
                        if hasattr(self.model, key):
                            if isinstance(value, list):
                                conditions.append(getattr(self.model, key).in_(value))
                            else:
                                conditions.append(getattr(self.model, key) == value)
                    if conditions:
                        stmt = stmt.where(and_(*conditions))
                
                # 添加排序
                if order_by:
                    if order_by.startswith('-'):
                        field = order_by[1:]
                        if hasattr(self.model, field):
                            stmt = stmt.order_by(getattr(self.model, field).desc())
                    else:
                        if hasattr(self.model, order_by):
                            stmt = stmt.order_by(getattr(self.model, order_by))
                else:
                    stmt = stmt.order_by(self.model.created_at.desc())
                
                # 添加分页
                if offset:
                    stmt = stmt.offset(offset)
                if limit:
                    stmt = stmt.limit(limit)
                
                result = await session.execute(stmt)
                return result.scalars().all()
        except SQLAlchemyError as e:
            self.logger.error(f"Failed to get all {self.model.__name__}: {str(e)}")
            return []
    
    async def update(self, id: str, **kwargs) -> Optional[T]:
        """更新记录"""
        try:
            async with self.get_session() as session:
                stmt = (
                    update(self.model)
                    .where(self.model.id == id)
                    .values(**kwargs)
                    .returning(self.model)
                )
                result = await session.execute(stmt)
                await session.commit()
                return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            self.logger.error(f"Failed to update {self.model.__name__} {id}: {str(e)}")
            return None
    
    async def delete(self, id: str) -> bool:
        """删除记录"""
        try:
            async with self.get_session() as session:
                stmt = delete(self.model).where(self.model.id == id)
                result = await session.execute(stmt)
                await session.commit()
                return result.rowcount > 0
        except SQLAlchemyError as e:
            self.logger.error(f"Failed to delete {self.model.__name__} {id}: {str(e)}")
            return False
    
    async def soft_delete(self, id: str) -> bool:
        """软删除记录"""
        if hasattr(self.model, 'is_deleted'):
            return await self.update(id, is_deleted=True) is not None
        else:
            return await self.delete(id)
    
    async def count(self, **filters) -> int:
        """统计记录数量"""
        try:
            async with self.get_session() as session:
                stmt = select(func.count(self.model.id))
                
                # 添加过滤条件
                if filters:
                    conditions = []
                    for key, value in filters.items():
                        if hasattr(self.model, key):
                            if isinstance(value, list):
                                conditions.append(getattr(self.model, key).in_(value))
                            else:
                                conditions.append(getattr(self.model, key) == value)
                    if conditions:
                        stmt = stmt.where(and_(*conditions))
                
                result = await session.execute(stmt)
                return result.scalar() or 0
        except SQLAlchemyError as e:
            self.logger.error(f"Failed to count {self.model.__name__}: {str(e)}")
            return 0
    
    async def exists(self, **filters) -> bool:
        """检查记录是否存在"""
        try:
            async with self.get_session() as session:
                stmt = select(self.model.id)
                
                # 添加过滤条件
                if filters:
                    conditions = []
                    for key, value in filters.items():
                        if hasattr(self.model, key):
                            conditions.append(getattr(self.model, key) == value)
                    if conditions:
                        stmt = stmt.where(and_(*conditions))
                
                stmt = stmt.limit(1)
                result = await session.execute(stmt)
                return result.scalar() is not None
        except SQLAlchemyError as e:
            self.logger.error(f"Failed to check existence in {self.model.__name__}: {str(e)}")
            return False
    
    async def bulk_create(self, items: List[Dict[str, Any]]) -> List[T]:
        """批量创建记录"""
        try:
            async with self.get_session() as session:
                instances = [self.model(**item) for item in items]
                session.add_all(instances)
                await session.commit()
                for instance in instances:
                    await session.refresh(instance)
                return instances
        except SQLAlchemyError as e:
            self.logger.error(f"Failed to bulk create {self.model.__name__}: {str(e)}")
            return []
    
    async def bulk_update(self, updates: List[Dict[str, Any]]) -> bool:
        """批量更新记录"""
        try:
            async with self.get_session() as session:
                for update_data in updates:
                    if 'id' in update_data:
                        id = update_data.pop('id')
                        stmt = (
                            update(self.model)
                            .where(self.model.id == id)
                            .values(**update_data)
                        )
                        await session.execute(stmt)
                await session.commit()
                return True
        except SQLAlchemyError as e:
            self.logger.error(f"Failed to bulk update {self.model.__name__}: {str(e)}")
            return False
    
    async def bulk_delete(self, ids: List[str]) -> bool:
        """批量删除记录"""
        try:
            async with self.get_session() as session:
                stmt = delete(self.model).where(self.model.id.in_(ids))
                result = await session.execute(stmt)
                await session.commit()
                return result.rowcount > 0
        except SQLAlchemyError as e:
            self.logger.error(f"Failed to bulk delete {self.model.__name__}: {str(e)}")
            return False
    
    async def search(
        self,
        search_fields: List[str],
        search_term: str,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        **filters
    ) -> List[T]:
        """搜索记录"""
        try:
            async with self.get_session() as session:
                stmt = select(self.model)
                
                # 添加搜索条件
                if search_term and search_fields:
                    search_conditions = []
                    for field in search_fields:
                        if hasattr(self.model, field):
                            search_conditions.append(
                                getattr(self.model, field).like(f"%{search_term}%")
                            )
                    if search_conditions:
                        stmt = stmt.where(or_(*search_conditions))
                
                # 添加过滤条件
                if filters:
                    conditions = []
                    for key, value in filters.items():
                        if hasattr(self.model, key):
                            conditions.append(getattr(self.model, key) == value)
                    if conditions:
                        stmt = stmt.where(and_(*conditions))
                
                # 添加排序
                stmt = stmt.order_by(self.model.created_at.desc())
                
                # 添加分页
                if offset:
                    stmt = stmt.offset(offset)
                if limit:
                    stmt = stmt.limit(limit)
                
                result = await session.execute(stmt)
                return result.scalars().all()
        except SQLAlchemyError as e:
            self.logger.error(f"Failed to search {self.model.__name__}: {str(e)}")
            return []
    
    async def execute_raw_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """执行原生SQL查询（仅在必要时使用）"""
        try:
            async with self.get_session() as session:
                stmt = text(query)
                if params:
                    result = await session.execute(stmt, params)
                else:
                    result = await session.execute(stmt)
                return result.fetchall()
        except SQLAlchemyError as e:
            self.logger.error(f"Failed to execute raw query: {str(e)}")
            return None
    
    async def get_statistics(self) -> Dict[str, Any]:
        """获取表统计信息"""
        try:
            async with self.get_session() as session:
                # 总记录数
                total_count = await self.count()
                
                # 今日新增
                today_count = 0
                if hasattr(self.model, 'created_at'):
                    stmt = select(func.count(self.model.id)).where(
                        func.date(self.model.created_at) == func.current_date()
                    )
                    result = await session.execute(stmt)
                    today_count = result.scalar() or 0
                
                return {
                    'total_count': total_count,
                    'today_count': today_count,
                    'table_name': self.model.__tablename__
                }
        except SQLAlchemyError as e:
            self.logger.error(f"Failed to get statistics for {self.model.__name__}: {str(e)}")
            return {'total_count': 0, 'today_count': 0, 'table_name': self.model.__tablename__}