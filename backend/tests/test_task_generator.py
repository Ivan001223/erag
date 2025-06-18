"""任务生成器测试

测试TaskGenerator类的各种功能，包括任务生成、调度优化、依赖管理等。
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta
from typing import Dict, List, Any

from backend.core.etl.task_generator import (
    TaskGenerator, TaskPriority, TaskType, ScheduleType, TaskStatus,
    DataSourceInfo, ProcessingRequirement, ScheduleConfig, ETLTask,
    TaskDependency, TaskExecution
)


class TestTaskGenerator:
    """任务生成器测试类"""
    
    @pytest.fixture
    def generator(self):
        """创建任务生成器实例"""
        return TaskGenerator()
    
    @pytest.fixture
    def sample_data_source(self):
        """示例数据源"""
        return DataSourceInfo(
            source_id="source_1",
            name="测试数据源",
            source_type="database",
            connection_config={
                "host": "localhost",
                "port": 5432,
                "database": "test_db",
                "username": "user",
                "password": "pass"
            },
            tables=["users", "orders"],
            estimated_size_mb=100,
            update_frequency="daily",
            priority=TaskPriority.MEDIUM,
            tags=["production", "customer_data"]
        )
    
    @pytest.fixture
    def sample_processing_requirement(self):
        """示例处理需求"""
        return ProcessingRequirement(
            requirement_id="req_1",
            name="数据清洗和转换",
            description="清洗用户数据并转换格式",
            processing_type="transform",
            steps=[
                {"type": "clean", "config": {"remove_nulls": True}},
                {"type": "transform", "config": {"format": "json"}}
            ],
            estimated_duration_minutes=30,
            resource_requirements={
                "cpu": 2,
                "memory_gb": 4,
                "disk_gb": 10
            },
            priority=TaskPriority.HIGH,
            tags=["data_quality", "transformation"]
        )
    
    @pytest.fixture
    def sample_schedule_config(self):
        """示例调度配置"""
        return ScheduleConfig(
            schedule_type=ScheduleType.CRON,
            cron_expression="0 2 * * *",  # 每天凌晨2点
            timezone="Asia/Shanghai",
            max_concurrent_tasks=5,
            retry_policy={
                "max_retries": 3,
                "retry_delay_seconds": 300,
                "exponential_backoff": True
            },
            timeout_minutes=120,
            priority=TaskPriority.MEDIUM
        )
    
    # ==================== 基本任务生成测试 ====================
    
    @pytest.mark.asyncio
    async def test_generate_single_task(self, generator, sample_data_source, sample_processing_requirement):
        """测试生成单个任务"""
        task = await generator.generate_task(
            data_source=sample_data_source,
            processing_requirement=sample_processing_requirement
        )
        
        assert isinstance(task, ETLTask)
        assert task.task_id
        assert task.name
        assert task.data_source_id == sample_data_source.source_id
        assert task.processing_requirement_id == sample_processing_requirement.requirement_id
        assert task.status == TaskStatus.PENDING
        assert task.priority == TaskPriority.HIGH  # 应该使用处理需求的优先级
        assert task.estimated_duration_minutes == 30
    
    @pytest.mark.asyncio
    async def test_generate_task_with_schedule(self, generator, sample_data_source, sample_processing_requirement, sample_schedule_config):
        """测试生成带调度的任务"""
        task = await generator.generate_task(
            data_source=sample_data_source,
            processing_requirement=sample_processing_requirement,
            schedule_config=sample_schedule_config
        )
        
        assert isinstance(task, ETLTask)
        assert task.schedule_config is not None
        assert task.schedule_config.schedule_type == ScheduleType.CRON
        assert task.schedule_config.cron_expression == "0 2 * * *"
    
    @pytest.mark.asyncio
    async def test_generate_task_with_custom_config(self, generator, sample_data_source, sample_processing_requirement):
        """测试生成自定义配置任务"""
        custom_config = {
            "batch_size": 1000,
            "parallel_workers": 4,
            "enable_monitoring": True
        }
        
        task = await generator.generate_task(
            data_source=sample_data_source,
            processing_requirement=sample_processing_requirement,
            custom_config=custom_config
        )
        
        assert isinstance(task, ETLTask)
        assert task.config["batch_size"] == 1000
        assert task.config["parallel_workers"] == 4
        assert task.config["enable_monitoring"] is True
    
    # ==================== 批量任务生成测试 ====================
    
    @pytest.mark.asyncio
    async def test_generate_tasks_multiple_sources(self, generator, sample_processing_requirement):
        """测试多数据源任务生成"""
        data_sources = [
            DataSourceInfo(
                source_id=f"source_{i}",
                name=f"数据源{i}",
                source_type="database",
                connection_config={"host": f"host{i}"},
                tables=[f"table{i}"],
                estimated_size_mb=50 * i,
                update_frequency="daily",
                priority=TaskPriority.MEDIUM
            )
            for i in range(1, 4)
        ]
        
        processing_requirements = [sample_processing_requirement]
        
        tasks = await generator.generate_tasks(
            data_sources=data_sources,
            processing_requirements=processing_requirements
        )
        
        assert isinstance(tasks, list)
        assert len(tasks) == 3  # 3个数据源 × 1个处理需求
        
        # 检查每个任务
        for i, task in enumerate(tasks):
            assert isinstance(task, ETLTask)
            assert task.data_source_id == f"source_{i+1}"
            assert task.processing_requirement_id == sample_processing_requirement.requirement_id
    
    @pytest.mark.asyncio
    async def test_generate_tasks_multiple_requirements(self, generator, sample_data_source):
        """测试多处理需求任务生成"""
        processing_requirements = [
            ProcessingRequirement(
                requirement_id=f"req_{i}",
                name=f"处理需求{i}",
                description=f"处理需求{i}的描述",
                processing_type="transform",
                steps=[{"type": "step", "config": {}}],
                estimated_duration_minutes=15 * i,
                priority=TaskPriority.MEDIUM
            )
            for i in range(1, 4)
        ]
        
        data_sources = [sample_data_source]
        
        tasks = await generator.generate_tasks(
            data_sources=data_sources,
            processing_requirements=processing_requirements
        )
        
        assert isinstance(tasks, list)
        assert len(tasks) == 3  # 1个数据源 × 3个处理需求
        
        # 检查每个任务
        for i, task in enumerate(tasks):
            assert isinstance(task, ETLTask)
            assert task.data_source_id == sample_data_source.source_id
            assert task.processing_requirement_id == f"req_{i+1}"
    
    @pytest.mark.asyncio
    async def test_generate_batch_tasks(self, generator, sample_data_source, sample_processing_requirement):
        """测试批量任务生成"""
        data_sources = [sample_data_source] * 10
        processing_requirements = [sample_processing_requirement] * 5
        
        tasks = await generator.generate_batch_tasks(
            data_sources=data_sources,
            processing_requirements=processing_requirements,
            batch_size=3
        )
        
        assert isinstance(tasks, list)
        assert len(tasks) == 50  # 10个数据源 × 5个处理需求
    
    # ==================== 任务依赖测试 ====================
    
    @pytest.mark.asyncio
    async def test_generate_dependency_chain(self, generator, sample_data_source):
        """测试生成依赖链任务"""
        # 创建有依赖关系的处理需求
        requirements = [
            ProcessingRequirement(
                requirement_id="extract",
                name="数据提取",
                processing_type="extract",
                steps=[{"type": "extract", "config": {}}],
                estimated_duration_minutes=10,
                priority=TaskPriority.HIGH
            ),
            ProcessingRequirement(
                requirement_id="transform",
                name="数据转换",
                processing_type="transform",
                steps=[{"type": "transform", "config": {}}],
                estimated_duration_minutes=20,
                priority=TaskPriority.MEDIUM,
                dependencies=["extract"]  # 依赖提取任务
            ),
            ProcessingRequirement(
                requirement_id="load",
                name="数据加载",
                processing_type="load",
                steps=[{"type": "load", "config": {}}],
                estimated_duration_minutes=15,
                priority=TaskPriority.LOW,
                dependencies=["transform"]  # 依赖转换任务
            )
        ]
        
        tasks = await generator.generate_dependency_chain(
            data_source=sample_data_source,
            processing_requirements=requirements
        )
        
        assert isinstance(tasks, list)
        assert len(tasks) == 3
        
        # 检查依赖关系
        task_map = {task.processing_requirement_id: task for task in tasks}
        
        # 提取任务没有依赖
        extract_task = task_map["extract"]
        assert len(extract_task.dependencies) == 0
        
        # 转换任务依赖提取任务
        transform_task = task_map["transform"]
        assert len(transform_task.dependencies) == 1
        assert transform_task.dependencies[0].dependency_task_id == extract_task.task_id
        
        # 加载任务依赖转换任务
        load_task = task_map["load"]
        assert len(load_task.dependencies) == 1
        assert load_task.dependencies[0].dependency_task_id == transform_task.task_id
    
    @pytest.mark.asyncio
    async def test_detect_circular_dependency(self, generator, sample_data_source):
        """测试检测循环依赖"""
        # 创建循环依赖的处理需求
        requirements = [
            ProcessingRequirement(
                requirement_id="req_a",
                name="需求A",
                processing_type="transform",
                steps=[],
                estimated_duration_minutes=10,
                priority=TaskPriority.MEDIUM,
                dependencies=["req_b"]  # A依赖B
            ),
            ProcessingRequirement(
                requirement_id="req_b",
                name="需求B",
                processing_type="transform",
                steps=[],
                estimated_duration_minutes=10,
                priority=TaskPriority.MEDIUM,
                dependencies=["req_a"]  # B依赖A，形成循环
            )
        ]
        
        with pytest.raises(ValueError, match="检测到循环依赖"):
            await generator.generate_dependency_chain(
                data_source=sample_data_source,
                processing_requirements=requirements
            )
    
    # ==================== 调度优化测试 ====================
    
    @pytest.mark.asyncio
    async def test_optimize_schedule_by_priority(self, generator):
        """测试按优先级优化调度"""
        tasks = [
            ETLTask(
                task_id=f"task_{i}",
                name=f"任务{i}",
                data_source_id="source_1",
                processing_requirement_id="req_1",
                task_type=TaskType.ETL,
                priority=TaskPriority.LOW if i % 3 == 0 else TaskPriority.HIGH if i % 3 == 1 else TaskPriority.MEDIUM,
                estimated_duration_minutes=10,
                status=TaskStatus.PENDING
            )
            for i in range(9)
        ]
        
        optimized_tasks = await generator.optimize_schedule(
            tasks=tasks,
            optimization_goals=["priority"],
            constraints={"max_concurrent_tasks": 3}
        )
        
        assert isinstance(optimized_tasks, list)
        assert len(optimized_tasks) == 9
        
        # 检查优先级排序（HIGH > MEDIUM > LOW）
        priorities = [task.priority for task in optimized_tasks]
        high_indices = [i for i, p in enumerate(priorities) if p == TaskPriority.HIGH]
        medium_indices = [i for i, p in enumerate(priorities) if p == TaskPriority.MEDIUM]
        low_indices = [i for i, p in enumerate(priorities) if p == TaskPriority.LOW]
        
        # 高优先级任务应该排在前面
        if high_indices and medium_indices:
            assert max(high_indices) < min(medium_indices)
        if medium_indices and low_indices:
            assert max(medium_indices) < min(low_indices)
    
    @pytest.mark.asyncio
    async def test_optimize_schedule_by_duration(self, generator):
        """测试按持续时间优化调度"""
        tasks = [
            ETLTask(
                task_id=f"task_{i}",
                name=f"任务{i}",
                data_source_id="source_1",
                processing_requirement_id="req_1",
                task_type=TaskType.ETL,
                priority=TaskPriority.MEDIUM,
                estimated_duration_minutes=10 * (i + 1),  # 10, 20, 30, ...
                status=TaskStatus.PENDING
            )
            for i in range(5)
        ]
        
        optimized_tasks = await generator.optimize_schedule(
            tasks=tasks,
            optimization_goals=["duration"],
            constraints={}
        )
        
        assert isinstance(optimized_tasks, list)
        assert len(optimized_tasks) == 5
        
        # 检查持续时间排序（短任务优先）
        durations = [task.estimated_duration_minutes for task in optimized_tasks]
        assert durations == sorted(durations)
    
    @pytest.mark.asyncio
    async def test_optimize_schedule_with_dependencies(self, generator):
        """测试带依赖的调度优化"""
        # 创建有依赖关系的任务
        task1 = ETLTask(
            task_id="task_1",
            name="任务1",
            data_source_id="source_1",
            processing_requirement_id="req_1",
            task_type=TaskType.ETL,
            priority=TaskPriority.LOW,
            estimated_duration_minutes=10,
            status=TaskStatus.PENDING,
            dependencies=[]
        )
        
        task2 = ETLTask(
            task_id="task_2",
            name="任务2",
            data_source_id="source_1",
            processing_requirement_id="req_2",
            task_type=TaskType.ETL,
            priority=TaskPriority.HIGH,
            estimated_duration_minutes=20,
            status=TaskStatus.PENDING,
            dependencies=[
                TaskDependency(
                    dependency_task_id="task_1",
                    dependency_type="finish_to_start"
                )
            ]
        )
        
        tasks = [task2, task1]  # 故意颠倒顺序
        
        optimized_tasks = await generator.optimize_schedule(
            tasks=tasks,
            optimization_goals=["dependencies"],
            constraints={}
        )
        
        assert isinstance(optimized_tasks, list)
        assert len(optimized_tasks) == 2
        
        # 任务1应该排在任务2前面（因为任务2依赖任务1）
        assert optimized_tasks[0].task_id == "task_1"
        assert optimized_tasks[1].task_id == "task_2"
    
    # ==================== 任务管理测试 ====================
    
    @pytest.mark.asyncio
    async def test_get_task(self, generator, sample_data_source, sample_processing_requirement):
        """测试获取任务"""
        # 先生成一个任务
        task = await generator.generate_task(
            data_source=sample_data_source,
            processing_requirement=sample_processing_requirement
        )
        
        # 获取任务
        retrieved_task = await generator.get_task(task.task_id)
        
        assert retrieved_task is not None
        assert retrieved_task.task_id == task.task_id
        assert retrieved_task.name == task.name
    
    @pytest.mark.asyncio
    async def test_get_nonexistent_task(self, generator):
        """测试获取不存在的任务"""
        task = await generator.get_task("nonexistent_task_id")
        assert task is None
    
    @pytest.mark.asyncio
    async def test_update_task(self, generator, sample_data_source, sample_processing_requirement):
        """测试更新任务"""
        # 先生成一个任务
        task = await generator.generate_task(
            data_source=sample_data_source,
            processing_requirement=sample_processing_requirement
        )
        
        # 更新任务
        updates = {
            "status": TaskStatus.RUNNING,
            "priority": TaskPriority.LOW,
            "estimated_duration_minutes": 45
        }
        
        success = await generator.update_task(task.task_id, updates)
        assert success is True
        
        # 验证更新
        updated_task = await generator.get_task(task.task_id)
        assert updated_task.status == TaskStatus.RUNNING
        assert updated_task.priority == TaskPriority.LOW
        assert updated_task.estimated_duration_minutes == 45
    
    @pytest.mark.asyncio
    async def test_delete_task(self, generator, sample_data_source, sample_processing_requirement):
        """测试删除任务"""
        # 先生成一个任务
        task = await generator.generate_task(
            data_source=sample_data_source,
            processing_requirement=sample_processing_requirement
        )
        
        # 删除任务
        success = await generator.delete_task(task.task_id)
        assert success is True
        
        # 验证删除
        deleted_task = await generator.get_task(task.task_id)
        assert deleted_task is None
    
    @pytest.mark.asyncio
    async def test_get_tasks_by_status(self, generator, sample_data_source, sample_processing_requirement):
        """测试按状态获取任务"""
        # 生成多个任务
        tasks = []
        for i in range(5):
            task = await generator.generate_task(
                data_source=sample_data_source,
                processing_requirement=sample_processing_requirement
            )
            # 更新部分任务状态
            if i < 2:
                await generator.update_task(task.task_id, {"status": TaskStatus.RUNNING})
            tasks.append(task)
        
        # 获取运行中的任务
        running_tasks = await generator.get_tasks_by_status(TaskStatus.RUNNING)
        assert len(running_tasks) == 2
        
        # 获取待处理的任务
        pending_tasks = await generator.get_tasks_by_status(TaskStatus.PENDING)
        assert len(pending_tasks) == 3
    
    # ==================== 配置管理测试 ====================
    
    @pytest.mark.asyncio
    async def test_export_task_config(self, generator, sample_data_source, sample_processing_requirement):
        """测试导出任务配置"""
        # 生成任务
        task = await generator.generate_task(
            data_source=sample_data_source,
            processing_requirement=sample_processing_requirement
        )
        
        # 导出配置
        config = await generator.export_task_config(task.task_id)
        
        assert isinstance(config, dict)
        assert "task_id" in config
        assert "name" in config
        assert "data_source" in config
        assert "processing_requirement" in config
        assert config["task_id"] == task.task_id
    
    @pytest.mark.asyncio
    async def test_import_task_config(self, generator):
        """测试导入任务配置"""
        # 准备配置
        config = {
            "name": "导入的任务",
            "data_source": {
                "source_id": "imported_source",
                "name": "导入数据源",
                "source_type": "file",
                "connection_config": {"path": "/data/file.csv"}
            },
            "processing_requirement": {
                "requirement_id": "imported_req",
                "name": "导入处理需求",
                "processing_type": "transform",
                "steps": [{"type": "clean", "config": {}}]
            },
            "priority": "high",
            "estimated_duration_minutes": 25
        }
        
        # 导入配置
        task = await generator.import_task_config(config)
        
        assert isinstance(task, ETLTask)
        assert task.name == "导入的任务"
        assert task.priority == TaskPriority.HIGH
        assert task.estimated_duration_minutes == 25
    
    @pytest.mark.asyncio
    async def test_export_all_configs(self, generator, sample_data_source, sample_processing_requirement):
        """测试导出所有配置"""
        # 生成多个任务
        tasks = []
        for i in range(3):
            task = await generator.generate_task(
                data_source=sample_data_source,
                processing_requirement=sample_processing_requirement
            )
            tasks.append(task)
        
        # 导出所有配置
        all_configs = await generator.export_all_configs()
        
        assert isinstance(all_configs, list)
        assert len(all_configs) >= 3
        
        # 检查配置格式
        for config in all_configs:
            assert isinstance(config, dict)
            assert "task_id" in config
            assert "name" in config
    
    # ==================== 统计信息测试 ====================
    
    @pytest.mark.asyncio
    async def test_get_statistics(self, generator, sample_data_source, sample_processing_requirement):
        """测试获取统计信息"""
        # 生成一些任务
        for i in range(5):
            task = await generator.generate_task(
                data_source=sample_data_source,
                processing_requirement=sample_processing_requirement
            )
            # 更新部分任务状态
            if i < 2:
                await generator.update_task(task.task_id, {"status": TaskStatus.COMPLETED})
            elif i < 4:
                await generator.update_task(task.task_id, {"status": TaskStatus.RUNNING})
        
        # 获取统计信息
        stats = await generator.get_statistics()
        
        assert isinstance(stats, dict)
        assert "total_tasks" in stats
        assert "tasks_by_status" in stats
        assert "tasks_by_priority" in stats
        assert "tasks_by_type" in stats
        
        assert stats["total_tasks"] >= 5
        assert stats["tasks_by_status"]["completed"] >= 2
        assert stats["tasks_by_status"]["running"] >= 2
        assert stats["tasks_by_status"]["pending"] >= 1
    
    # ==================== 错误处理测试 ====================
    
    @pytest.mark.asyncio
    async def test_generate_task_invalid_data_source(self, generator, sample_processing_requirement):
        """测试无效数据源处理"""
        invalid_source = DataSourceInfo(
            source_id="",  # 空ID
            name="",      # 空名称
            source_type="invalid",
            connection_config={},
            tables=[],
            estimated_size_mb=0,
            update_frequency="never",
            priority=TaskPriority.LOW
        )
        
        with pytest.raises(ValueError, match="数据源配置无效"):
            await generator.generate_task(
                data_source=invalid_source,
                processing_requirement=sample_processing_requirement
            )
    
    @pytest.mark.asyncio
    async def test_generate_task_invalid_processing_requirement(self, generator, sample_data_source):
        """测试无效处理需求处理"""
        invalid_requirement = ProcessingRequirement(
            requirement_id="",  # 空ID
            name="",           # 空名称
            processing_type="invalid",
            steps=[],
            estimated_duration_minutes=-1,  # 负数
            priority=TaskPriority.LOW
        )
        
        with pytest.raises(ValueError, match="处理需求配置无效"):
            await generator.generate_task(
                data_source=sample_data_source,
                processing_requirement=invalid_requirement
            )
    
    @pytest.mark.asyncio
    async def test_update_nonexistent_task(self, generator):
        """测试更新不存在的任务"""
        success = await generator.update_task(
            "nonexistent_task_id",
            {"status": TaskStatus.COMPLETED}
        )
        assert success is False
    
    @pytest.mark.asyncio
    async def test_delete_nonexistent_task(self, generator):
        """测试删除不存在的任务"""
        success = await generator.delete_task("nonexistent_task_id")
        assert success is False
    
    # ==================== 性能测试 ====================
    
    @pytest.mark.asyncio
    async def test_performance_large_batch_generation(self, generator):
        """测试大批量任务生成性能"""
        import time
        
        # 创建大量数据源和处理需求
        data_sources = [
            DataSourceInfo(
                source_id=f"source_{i}",
                name=f"数据源{i}",
                source_type="database",
                connection_config={"host": f"host{i}"},
                tables=[f"table{i}"],
                estimated_size_mb=10,
                update_frequency="daily",
                priority=TaskPriority.MEDIUM
            )
            for i in range(100)
        ]
        
        processing_requirements = [
            ProcessingRequirement(
                requirement_id=f"req_{i}",
                name=f"处理需求{i}",
                processing_type="transform",
                steps=[{"type": "step", "config": {}}],
                estimated_duration_minutes=10,
                priority=TaskPriority.MEDIUM
            )
            for i in range(10)
        ]
        
        # 测试生成时间
        start_time = time.time()
        tasks = await generator.generate_batch_tasks(
            data_sources=data_sources,
            processing_requirements=processing_requirements,
            batch_size=50
        )
        end_time = time.time()
        
        # 检查性能
        generation_time = end_time - start_time
        assert generation_time < 30  # 30秒内完成
        assert len(tasks) == 1000  # 100 × 10
    
    @pytest.mark.asyncio
    async def test_memory_usage_optimization(self, generator):
        """测试内存使用优化"""
        import psutil
        import os
        
        # 获取初始内存使用
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        # 生成大量任务
        data_sources = [
            DataSourceInfo(
                source_id=f"source_{i}",
                name=f"数据源{i}",
                source_type="database",
                connection_config={"host": f"host{i}"},
                tables=[f"table{i}"],
                estimated_size_mb=10,
                update_frequency="daily",
                priority=TaskPriority.MEDIUM
            )
            for i in range(500)
        ]
        
        processing_requirements = [
            ProcessingRequirement(
                requirement_id=f"req_{i}",
                name=f"处理需求{i}",
                processing_type="transform",
                steps=[{"type": "step", "config": {}}],
                estimated_duration_minutes=10,
                priority=TaskPriority.MEDIUM
            )
            for i in range(5)
        ]
        
        tasks = await generator.generate_batch_tasks(
            data_sources=data_sources,
            processing_requirements=processing_requirements,
            batch_size=100
        )
        
        # 检查内存增长
        final_memory = process.memory_info().rss
        memory_growth = final_memory - initial_memory
        
        # 内存增长应该在合理范围内（小于200MB）
        assert memory_growth < 200 * 1024 * 1024
        assert len(tasks) == 2500  # 500 × 5
    
    # ==================== 集成测试 ====================
    
    @pytest.mark.asyncio
    async def test_end_to_end_workflow(self, generator):
        """测试端到端工作流"""
        # 1. 创建数据源
        data_source = DataSourceInfo(
            source_id="e2e_source",
            name="端到端测试数据源",
            source_type="database",
            connection_config={
                "host": "localhost",
                "database": "test_db"
            },
            tables=["users", "orders", "products"],
            estimated_size_mb=500,
            update_frequency="hourly",
            priority=TaskPriority.HIGH,
            tags=["e2e_test", "production"]
        )
        
        # 2. 创建处理需求链
        extract_req = ProcessingRequirement(
            requirement_id="extract",
            name="数据提取",
            processing_type="extract",
            steps=[{"type": "extract", "config": {"format": "json"}}],
            estimated_duration_minutes=15,
            priority=TaskPriority.HIGH
        )
        
        transform_req = ProcessingRequirement(
            requirement_id="transform",
            name="数据转换",
            processing_type="transform",
            steps=[
                {"type": "clean", "config": {"remove_nulls": True}},
                {"type": "normalize", "config": {"format": "standard"}}
            ],
            estimated_duration_minutes=30,
            priority=TaskPriority.MEDIUM,
            dependencies=["extract"]
        )
        
        load_req = ProcessingRequirement(
            requirement_id="load",
            name="数据加载",
            processing_type="load",
            steps=[{"type": "load", "config": {"target": "warehouse"}}],
            estimated_duration_minutes=20,
            priority=TaskPriority.LOW,
            dependencies=["transform"]
        )
        
        # 3. 生成依赖链任务
        tasks = await generator.generate_dependency_chain(
            data_source=data_source,
            processing_requirements=[extract_req, transform_req, load_req]
        )
        
        assert len(tasks) == 3
        
        # 4. 优化调度
        optimized_tasks = await generator.optimize_schedule(
            tasks=tasks,
            optimization_goals=["dependencies", "priority"],
            constraints={"max_concurrent_tasks": 2}
        )
        
        assert len(optimized_tasks) == 3
        
        # 5. 验证任务顺序（应该按依赖关系排序）
        task_order = [task.processing_requirement_id for task in optimized_tasks]
        assert task_order == ["extract", "transform", "load"]
        
        # 6. 模拟任务执行
        for task in optimized_tasks:
            # 开始执行
            await generator.update_task(task.task_id, {"status": TaskStatus.RUNNING})
            
            # 完成执行
            await generator.update_task(task.task_id, {"status": TaskStatus.COMPLETED})
        
        # 7. 验证最终状态
        final_stats = await generator.get_statistics()
        assert final_stats["tasks_by_status"]["completed"] >= 3
        
        # 8. 导出配置
        configs = await generator.export_all_configs()
        assert len(configs) >= 3


if __name__ == "__main__":
    # 运行测试
    pytest.main(["-v", __file__])