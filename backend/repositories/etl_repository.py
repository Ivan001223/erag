from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import text, and_, or_, func, desc
from backend.models.database import ETLJob, ETLJobRun, ETLMetric
from backend.core.logger import logger
import json


class ETLRepository:
    """ETL数据访问层"""
    
    def __init__(self, db_session: Session):
        self.db = db_session
    
    async def save_job(
        self,
        job_id: str,
        name: str,
        description: Optional[str],
        job_type: str,
        source_config: Dict[str, Any],
        target_config: Dict[str, Any],
        steps_config: List[Dict[str, Any]],
        schedule_config: Optional[str],
        config: Dict[str, Any],
        status: str,
        priority: int,
        created_by: str
    ) -> bool:
        """保存ETL作业"""
        try:
            job = ETLJob(
                id=job_id,
                name=name,
                description=description,
                job_type=job_type,
                source_config=source_config,
                target_config=target_config,
                steps_config=steps_config,
                schedule_config=schedule_config,
                config=config,
                status=status,
                priority=priority,
                created_by=created_by,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                run_count=0,
                success_count=0,
                failure_count=0,
                metrics={}
            )
            
            self.db.add(job)
            self.db.commit()
            
            return True
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to save ETL job {job_id}: {str(e)}")
            raise
    
    async def save_job_run(
        self,
        run_id: str,
        job_id: str,
        run_number: int,
        status: str,
        start_time: datetime,
        end_time: Optional[datetime] = None,
        duration_seconds: Optional[int] = None,
        records_processed: int = 0,
        records_success: int = 0,
        records_failed: int = 0,
        error_message: Optional[str] = None,
        step_results: Optional[List[Dict[str, Any]]] = None,
        metrics: Optional[Dict[str, Any]] = None,
        logs: Optional[List[str]] = None
    ) -> bool:
        """保存作业运行记录"""
        try:
            # 检查是否已存在
            existing_run = self.db.query(ETLJobRun).filter(
                ETLJobRun.id == run_id
            ).first()
            
            if existing_run:
                # 更新现有记录
                existing_run.status = status
                existing_run.end_time = end_time
                existing_run.duration_seconds = duration_seconds
                existing_run.records_processed = records_processed
                existing_run.records_success = records_success
                existing_run.records_failed = records_failed
                existing_run.error_message = error_message
                existing_run.step_results = step_results or []
                existing_run.metrics = metrics or {}
                existing_run.logs = logs or []
            else:
                # 创建新记录
                job_run = ETLJobRun(
                    id=run_id,
                    job_id=job_id,
                    run_number=run_number,
                    status=status,
                    start_time=start_time,
                    end_time=end_time,
                    duration_seconds=duration_seconds,
                    records_processed=records_processed,
                    records_success=records_success,
                    records_failed=records_failed,
                    error_message=error_message,
                    step_results=step_results or [],
                    metrics=metrics or {},
                    logs=logs or []
                )
                self.db.add(job_run)
            
            self.db.commit()
            return True
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to save ETL job run {run_id}: {str(e)}")
            raise
    
    async def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """获取ETL作业"""
        try:
            job = self.db.query(ETLJob).filter(ETLJob.id == job_id).first()
            
            if job:
                return {
                    "id": job.id,
                    "name": job.name,
                    "description": job.description,
                    "job_type": job.job_type,
                    "source_config": job.source_config,
                    "target_config": job.target_config,
                    "steps_config": job.steps_config,
                    "schedule_config": job.schedule_config,
                    "config": job.config,
                    "status": job.status,
                    "priority": job.priority,
                    "created_by": job.created_by,
                    "created_at": job.created_at,
                    "updated_at": job.updated_at,
                    "start_time": job.start_time,
                    "end_time": job.end_time,
                    "last_run_time": job.last_run_time,
                    "next_run_time": job.next_run_time,
                    "run_count": job.run_count,
                    "success_count": job.success_count,
                    "failure_count": job.failure_count,
                    "error_message": job.error_message,
                    "metrics": job.metrics
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get ETL job {job_id}: {str(e)}")
            raise
    
    async def list_jobs(
        self,
        job_type: Optional[str] = None,
        status: Optional[str] = None,
        created_by: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """列出ETL作业"""
        try:
            query = self.db.query(ETLJob)
            
            if job_type:
                query = query.filter(ETLJob.job_type == job_type)
            
            if status:
                query = query.filter(ETLJob.status == status)
            
            if created_by:
                query = query.filter(ETLJob.created_by == created_by)
            
            jobs = query.order_by(desc(ETLJob.created_at)).offset(offset).limit(limit).all()
            
            return [
                {
                    "id": job.id,
                    "name": job.name,
                    "description": job.description,
                    "job_type": job.job_type,
                    "status": job.status,
                    "priority": job.priority,
                    "created_by": job.created_by,
                    "created_at": job.created_at,
                    "updated_at": job.updated_at,
                    "last_run_time": job.last_run_time,
                    "run_count": job.run_count,
                    "success_count": job.success_count,
                    "failure_count": job.failure_count
                }
                for job in jobs
            ]
            
        except Exception as e:
            logger.error(f"Failed to list ETL jobs: {str(e)}")
            raise
    
    async def update_job_status(
        self,
        job_id: str,
        status: str,
        error_message: Optional[str] = None
    ) -> bool:
        """更新作业状态"""
        try:
            job = self.db.query(ETLJob).filter(ETLJob.id == job_id).first()
            
            if job:
                job.status = status
                job.updated_at = datetime.now()
                
                if error_message:
                    job.error_message = error_message
                
                self.db.commit()
                return True
            
            return False
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to update job status {job_id}: {str(e)}")
            raise
    
    async def update_job_stats(
        self,
        job_id: str,
        run_status: str
    ) -> bool:
        """更新作业统计"""
        try:
            job = self.db.query(ETLJob).filter(ETLJob.id == job_id).first()
            
            if job:
                job.run_count += 1
                job.last_run_time = datetime.now()
                
                if run_status == "COMPLETED":
                    job.success_count += 1
                elif run_status == "FAILED":
                    job.failure_count += 1
                
                self.db.commit()
                return True
            
            return False
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to update job stats {job_id}: {str(e)}")
            raise
    
    async def list_job_runs(
        self,
        job_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """列出作业运行记录"""
        try:
            query = self.db.query(ETLJobRun)
            
            if job_id:
                query = query.filter(ETLJobRun.job_id == job_id)
            
            if status:
                query = query.filter(ETLJobRun.status == status)
            
            runs = query.order_by(desc(ETLJobRun.start_time)).offset(offset).limit(limit).all()
            
            return [
                {
                    "id": run.id,
                    "job_id": run.job_id,
                    "run_number": run.run_number,
                    "status": run.status,
                    "start_time": run.start_time,
                    "end_time": run.end_time,
                    "duration_seconds": run.duration_seconds,
                    "records_processed": run.records_processed,
                    "records_success": run.records_success,
                    "records_failed": run.records_failed,
                    "error_message": run.error_message,
                    "step_results": run.step_results,
                    "metrics": run.metrics
                }
                for run in runs
            ]
            
        except Exception as e:
            logger.error(f"Failed to list job runs: {str(e)}")
            raise
    
    async def get_job_metrics(
        self,
        job_id: str,
        metric_names: Optional[List[str]] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """获取作业指标"""
        try:
            query = self.db.query(ETLMetric).filter(ETLMetric.job_id == job_id)
            
            if metric_names:
                query = query.filter(ETLMetric.metric_name.in_(metric_names))
            
            if start_time:
                query = query.filter(ETLMetric.timestamp >= start_time)
            
            if end_time:
                query = query.filter(ETLMetric.timestamp <= end_time)
            
            metrics = query.order_by(desc(ETLMetric.timestamp)).all()
            
            return [
                {
                    "id": metric.id,
                    "job_id": metric.job_id,
                    "run_id": metric.run_id,
                    "step_id": metric.step_id,
                    "metric_name": metric.metric_name,
                    "metric_value": metric.metric_value,
                    "metric_type": metric.metric_type,
                    "timestamp": metric.timestamp,
                    "tags": metric.tags
                }
                for metric in metrics
            ]
            
        except Exception as e:
            logger.error(f"Failed to get job metrics {job_id}: {str(e)}")
            raise
    
    async def save_metric(
        self,
        metric_id: str,
        job_id: str,
        run_id: str,
        step_id: Optional[str],
        metric_name: str,
        metric_value: str,
        metric_type: str,
        tags: Optional[Dict[str, str]] = None
    ) -> bool:
        """保存指标"""
        try:
            metric = ETLMetric(
                id=metric_id,
                job_id=job_id,
                run_id=run_id,
                step_id=step_id,
                metric_name=metric_name,
                metric_value=metric_value,
                metric_type=metric_type,
                timestamp=datetime.now(),
                tags=tags or {}
            )
            
            self.db.add(metric)
            self.db.commit()
            
            return True
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to save metric {metric_id}: {str(e)}")
            raise
    
    async def get_running_jobs(self) -> List[Dict[str, Any]]:
        """获取运行中的作业"""
        try:
            jobs = self.db.query(ETLJob).filter(
                ETLJob.status == "RUNNING"
            ).all()
            
            return [
                {
                    "id": job.id,
                    "name": job.name,
                    "job_type": job.job_type,
                    "status": job.status,
                    "start_time": job.start_time,
                    "created_by": job.created_by
                }
                for job in jobs
            ]
            
        except Exception as e:
            logger.error(f"Failed to get running jobs: {str(e)}")
            raise
    
    async def delete_job(self, job_id: str) -> bool:
        """删除ETL作业"""
        try:
            # 先删除相关的运行记录和指标
            self.db.query(ETLJobRun).filter(ETLJobRun.job_id == job_id).delete()
            self.db.query(ETLMetric).filter(ETLMetric.job_id == job_id).delete()
            
            # 删除作业
            job = self.db.query(ETLJob).filter(ETLJob.id == job_id).first()
            if job:
                self.db.delete(job)
                self.db.commit()
                return True
            
            return False
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to delete job {job_id}: {str(e)}")
            raise
    
    async def get_job_stats(
        self,
        job_type: Optional[str] = None,
        created_by: Optional[str] = None
    ) -> Dict[str, Any]:
        """获取作业统计信息"""
        try:
            query = self.db.query(ETLJob)
            
            if job_type:
                query = query.filter(ETLJob.job_type == job_type)
            
            if created_by:
                query = query.filter(ETLJob.created_by == created_by)
            
            total_jobs = query.count()
            
            # 按状态统计
            status_stats = self.db.query(
                ETLJob.status,
                func.count(ETLJob.id).label('count')
            ).group_by(ETLJob.status).all()
            
            # 按类型统计
            type_stats = self.db.query(
                ETLJob.job_type,
                func.count(ETLJob.id).label('count')
            ).group_by(ETLJob.job_type).all()
            
            # 成功率统计
            success_rate = 0
            if total_jobs > 0:
                total_runs = self.db.query(func.sum(ETLJob.run_count)).scalar() or 0
                total_success = self.db.query(func.sum(ETLJob.success_count)).scalar() or 0
                if total_runs > 0:
                    success_rate = (total_success / total_runs) * 100
            
            return {
                "total_jobs": total_jobs,
                "status_distribution": {
                    status: count for status, count in status_stats
                },
                "type_distribution": {
                    job_type: count for job_type, count in type_stats
                },
                "success_rate": success_rate
            }
            
        except Exception as e:
            logger.error(f"Failed to get job stats: {str(e)}")
            raise