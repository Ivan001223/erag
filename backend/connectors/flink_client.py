"""Apache Flink 流处理客户端"""

import asyncio
import json
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
from pathlib import Path

import aiohttp
from aiohttp import ClientSession, ClientTimeout

from backend.utils.logger import get_logger
from backend.config.constants import TaskStatus, TaskType


class FlinkClient:
    """Apache Flink 异步客户端"""
    
    def __init__(
        self,
        jobmanager_host: str = "localhost",
        jobmanager_port: int = 8081,
        timeout: int = 30,
        max_retries: int = 3,
        retry_delay: float = 1.0
    ):
        self.jobmanager_host = jobmanager_host
        self.jobmanager_port = jobmanager_port
        self.base_url = f"http://{jobmanager_host}:{jobmanager_port}"
        self.timeout = ClientTimeout(total=timeout)
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.session: Optional[ClientSession] = None
        self.logger = get_logger(__name__)
    
    async def connect(self) -> None:
        """建立Flink连接"""
        try:
            self.session = ClientSession(timeout=self.timeout)
            
            # 测试连接
            await self._test_connection()
            self.logger.info(f"Flink 连接成功: {self.base_url}")
            
        except Exception as e:
            self.logger.error(f"Flink 连接失败: {str(e)}")
            if self.session:
                await self.session.close()
            raise
    
    async def close(self) -> None:
        """关闭Flink连接"""
        if self.session:
            await self.session.close()
            self.logger.info("Flink 连接已关闭")
    
    async def _test_connection(self) -> None:
        """测试连接"""
        if not self.session:
            raise RuntimeError("Flink 客户端未初始化")
        
        try:
            async with self.session.get(f"{self.base_url}/config") as response:
                if response.status != 200:
                    raise ConnectionError(f"Flink 连接测试失败: HTTP {response.status}")
        except Exception as e:
            raise ConnectionError(f"Flink 连接测试失败: {str(e)}")
    
    async def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        files: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """发送HTTP请求"""
        if not self.session:
            raise RuntimeError("Flink 客户端未初始化")
        
        url = f"{self.base_url}{endpoint}"
        
        for attempt in range(self.max_retries):
            try:
                kwargs = {}
                if data:
                    kwargs["json"] = data
                if params:
                    kwargs["params"] = params
                if files:
                    kwargs["data"] = files
                
                async with self.session.request(method, url, **kwargs) as response:
                    if response.status == 200:
                        if response.content_type == "application/json":
                            return await response.json()
                        else:
                            text = await response.text()
                            return {"response": text}
                    else:
                        error_text = await response.text()
                        self.logger.error(f"Flink API 错误: {response.status} - {error_text}")
                        if attempt == self.max_retries - 1:
                            raise Exception(f"HTTP {response.status}: {error_text}")
                        
            except Exception as e:
                if attempt == self.max_retries - 1:
                    self.logger.error(f"Flink 请求失败: {str(e)}")
                    raise
                else:
                    self.logger.warning(f"Flink 请求重试 {attempt + 1}/{self.max_retries}: {str(e)}")
                    await asyncio.sleep(self.retry_delay)
        
        return None
    
    # 集群信息相关
    async def get_cluster_overview(self) -> Optional[Dict[str, Any]]:
        """获取集群概览"""
        return await self._make_request("GET", "/overview")
    
    async def get_cluster_config(self) -> Optional[Dict[str, Any]]:
        """获取集群配置"""
        return await self._make_request("GET", "/config")
    
    async def get_taskmanagers(self) -> Optional[List[Dict[str, Any]]]:
        """获取TaskManager列表"""
        result = await self._make_request("GET", "/taskmanagers")
        return result.get("taskmanagers", []) if result else []
    
    async def get_taskmanager_details(self, taskmanager_id: str) -> Optional[Dict[str, Any]]:
        """获取TaskManager详情"""
        return await self._make_request("GET", f"/taskmanagers/{taskmanager_id}")
    
    # 作业管理相关
    async def get_jobs(self) -> Optional[List[Dict[str, Any]]]:
        """获取所有作业"""
        result = await self._make_request("GET", "/jobs")
        return result.get("jobs", []) if result else []
    
    async def get_job_details(self, job_id: str) -> Optional[Dict[str, Any]]:
        """获取作业详情"""
        return await self._make_request("GET", f"/jobs/{job_id}")
    
    async def get_job_plan(self, job_id: str) -> Optional[Dict[str, Any]]:
        """获取作业执行计划"""
        return await self._make_request("GET", f"/jobs/{job_id}/plan")
    
    async def get_job_config(self, job_id: str) -> Optional[Dict[str, Any]]:
        """获取作业配置"""
        return await self._make_request("GET", f"/jobs/{job_id}/config")
    
    async def get_job_exceptions(self, job_id: str) -> Optional[Dict[str, Any]]:
        """获取作业异常信息"""
        return await self._make_request("GET", f"/jobs/{job_id}/exceptions")
    
    async def get_job_metrics(self, job_id: str) -> Optional[List[Dict[str, Any]]]:
        """获取作业指标"""
        result = await self._make_request("GET", f"/jobs/{job_id}/metrics")
        return result if isinstance(result, list) else []
    
    async def cancel_job(self, job_id: str) -> bool:
        """取消作业"""
        try:
            result = await self._make_request("PATCH", f"/jobs/{job_id}")
            if result:
                self.logger.info(f"作业 {job_id} 取消成功")
                return True
            return False
        except Exception as e:
            self.logger.error(f"取消作业失败: {str(e)}")
            return False
    
    async def stop_job(self, job_id: str, drain: bool = False) -> bool:
        """停止作业"""
        try:
            params = {"mode": "stop"}
            if drain:
                params["drain"] = "true"
            
            result = await self._make_request("POST", f"/jobs/{job_id}/stop", params=params)
            if result:
                self.logger.info(f"作业 {job_id} 停止成功")
                return True
            return False
        except Exception as e:
            self.logger.error(f"停止作业失败: {str(e)}")
            return False
    
    # JAR包管理
    async def upload_jar(self, jar_path: Union[str, Path]) -> Optional[str]:
        """上传JAR包"""
        jar_path = Path(jar_path)
        if not jar_path.exists():
            raise FileNotFoundError(f"JAR文件不存在: {jar_path}")
        
        try:
            with open(jar_path, "rb") as f:
                files = {"jarfile": (jar_path.name, f, "application/java-archive")}
                result = await self._make_request("POST", "/jars/upload", files=files)
                
                if result and "filename" in result:
                    jar_id = result["filename"].split("/")[-1]
                    self.logger.info(f"JAR包上传成功: {jar_id}")
                    return jar_id
                
        except Exception as e:
            self.logger.error(f"JAR包上传失败: {str(e)}")
        
        return None
    
    async def list_jars(self) -> Optional[List[Dict[str, Any]]]:
        """列出已上传的JAR包"""
        result = await self._make_request("GET", "/jars")
        return result.get("files", []) if result else []
    
    async def delete_jar(self, jar_id: str) -> bool:
        """删除JAR包"""
        try:
            result = await self._make_request("DELETE", f"/jars/{jar_id}")
            if result:
                self.logger.info(f"JAR包 {jar_id} 删除成功")
                return True
            return False
        except Exception as e:
            self.logger.error(f"删除JAR包失败: {str(e)}")
            return False
    
    async def run_jar(
        self,
        jar_id: str,
        entry_class: Optional[str] = None,
        program_args: Optional[List[str]] = None,
        parallelism: Optional[int] = None,
        job_id: Optional[str] = None,
        allow_non_restored_state: bool = False
    ) -> Optional[str]:
        """运行JAR包"""
        try:
            data = {}
            
            if entry_class:
                data["entryClass"] = entry_class
            if program_args:
                data["programArgs"] = " ".join(program_args)
            if parallelism:
                data["parallelism"] = parallelism
            if job_id:
                data["jobId"] = job_id
            if allow_non_restored_state:
                data["allowNonRestoredState"] = True
            
            result = await self._make_request("POST", f"/jars/{jar_id}/run", data=data)
            
            if result and "jobid" in result:
                job_id = result["jobid"]
                self.logger.info(f"作业启动成功: {job_id}")
                return job_id
            
        except Exception as e:
            self.logger.error(f"运行JAR包失败: {str(e)}")
        
        return None
    
    # Savepoint管理
    async def trigger_savepoint(
        self,
        job_id: str,
        target_directory: Optional[str] = None,
        cancel_job: bool = False
    ) -> Optional[str]:
        """触发Savepoint"""
        try:
            data = {}
            if target_directory:
                data["target-directory"] = target_directory
            if cancel_job:
                data["cancel-job"] = True
            
            result = await self._make_request("POST", f"/jobs/{job_id}/savepoints", data=data)
            
            if result and "request-id" in result:
                request_id = result["request-id"]
                self.logger.info(f"Savepoint 触发成功: {request_id}")
                return request_id
            
        except Exception as e:
            self.logger.error(f"触发Savepoint失败: {str(e)}")
        
        return None
    
    async def get_savepoint_status(self, job_id: str, request_id: str) -> Optional[Dict[str, Any]]:
        """获取Savepoint状态"""
        return await self._make_request("GET", f"/jobs/{job_id}/savepoints/{request_id}")
    
    # 检查点管理
    async def get_checkpoints(self, job_id: str) -> Optional[Dict[str, Any]]:
        """获取检查点信息"""
        return await self._make_request("GET", f"/jobs/{job_id}/checkpoints")
    
    async def get_checkpoint_config(self, job_id: str) -> Optional[Dict[str, Any]]:
        """获取检查点配置"""
        return await self._make_request("GET", f"/jobs/{job_id}/checkpoints/config")
    
    async def get_checkpoint_details(self, job_id: str, checkpoint_id: str) -> Optional[Dict[str, Any]]:
        """获取检查点详情"""
        return await self._make_request("GET", f"/jobs/{job_id}/checkpoints/details/{checkpoint_id}")
    
    # 数据流处理任务
    async def submit_sql_job(
        self,
        sql_statements: List[str],
        job_name: Optional[str] = None,
        parallelism: Optional[int] = None
    ) -> Optional[str]:
        """提交SQL作业"""
        try:
            # 这里需要根据实际的Flink SQL Gateway API进行调整
            data = {
                "statements": sql_statements
            }
            
            if job_name:
                data["jobName"] = job_name
            if parallelism:
                data["parallelism"] = parallelism
            
            # 注意：这个端点可能需要根据实际的Flink SQL Gateway配置进行调整
            result = await self._make_request("POST", "/sql/submit", data=data)
            
            if result and "jobId" in result:
                job_id = result["jobId"]
                self.logger.info(f"SQL作业提交成功: {job_id}")
                return job_id
            
        except Exception as e:
            self.logger.error(f"提交SQL作业失败: {str(e)}")
        
        return None
    
    # 知识库相关的流处理任务
    async def create_document_processing_job(
        self,
        source_config: Dict[str, Any],
        sink_config: Dict[str, Any],
        processing_config: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """创建文档处理流作业"""
        try:
            # 构建Flink SQL语句
            sql_statements = []
            
            # 创建源表
            source_sql = self._build_source_table_sql(source_config)
            sql_statements.append(source_sql)
            
            # 创建目标表
            sink_sql = self._build_sink_table_sql(sink_config)
            sql_statements.append(sink_sql)
            
            # 创建处理逻辑
            process_sql = self._build_processing_sql(processing_config or {})
            sql_statements.append(process_sql)
            
            return await self.submit_sql_job(
                sql_statements,
                job_name="document_processing_job"
            )
            
        except Exception as e:
            self.logger.error(f"创建文档处理作业失败: {str(e)}")
            return None
    
    def _build_source_table_sql(self, config: Dict[str, Any]) -> str:
        """构建源表SQL"""
        # 这里根据实际需求构建源表SQL
        # 例如：Kafka源、文件源等
        return f"""
        CREATE TABLE document_source (
            doc_id STRING,
            content STRING,
            doc_type STRING,
            timestamp_col TIMESTAMP(3),
            WATERMARK FOR timestamp_col AS timestamp_col - INTERVAL '5' SECOND
        ) WITH (
            'connector' = '{config.get('connector', 'kafka')}',
            'topic' = '{config.get('topic', 'documents')}',
            'properties.bootstrap.servers' = '{config.get('bootstrap.servers', 'localhost:9092')}',
            'format' = 'json'
        )
        """
    
    def _build_sink_table_sql(self, config: Dict[str, Any]) -> str:
        """构建目标表SQL"""
        return f"""
        CREATE TABLE processed_documents (
            doc_id STRING,
            processed_content STRING,
            entities STRING,
            relations STRING,
            processing_time TIMESTAMP(3)
        ) WITH (
            'connector' = '{config.get('connector', 'kafka')}',
            'topic' = '{config.get('topic', 'processed_documents')}',
            'properties.bootstrap.servers' = '{config.get('bootstrap.servers', 'localhost:9092')}',
            'format' = 'json'
        )
        """
    
    def _build_processing_sql(self, config: Dict[str, Any]) -> str:
        """构建处理逻辑SQL"""
        return """
        INSERT INTO processed_documents
        SELECT 
            doc_id,
            UPPER(content) as processed_content,
            '' as entities,
            '' as relations,
            CURRENT_TIMESTAMP as processing_time
        FROM document_source
        """
    
    # 监控和指标
    async def get_job_vertex_metrics(
        self,
        job_id: str,
        vertex_id: str,
        metrics: Optional[List[str]] = None
    ) -> Optional[List[Dict[str, Any]]]:
        """获取作业顶点指标"""
        endpoint = f"/jobs/{job_id}/vertices/{vertex_id}/metrics"
        if metrics:
            endpoint += f"?get={','.join(metrics)}"
        
        result = await self._make_request("GET", endpoint)
        return result if isinstance(result, list) else []
    
    async def get_system_metrics(self) -> Optional[Dict[str, Any]]:
        """获取系统指标"""
        # 获取集群级别的指标
        overview = await self.get_cluster_overview()
        taskmanagers = await self.get_taskmanagers()
        
        if overview and taskmanagers:
            return {
                "cluster_overview": overview,
                "taskmanagers": taskmanagers,
                "timestamp": datetime.now().isoformat()
            }
        
        return None
    
    async def health_check(self) -> bool:
        """健康检查"""
        try:
            overview = await self.get_cluster_overview()
            return overview is not None
        except Exception as e:
            self.logger.error(f"Flink 健康检查失败: {str(e)}")
            return False
    
    # 工具方法
    async def wait_for_job_completion(
        self,
        job_id: str,
        timeout: int = 300,
        check_interval: int = 5
    ) -> bool:
        """等待作业完成"""
        start_time = datetime.now()
        
        while (datetime.now() - start_time).seconds < timeout:
            try:
                job_details = await self.get_job_details(job_id)
                if job_details:
                    state = job_details.get("state")
                    if state in ["FINISHED", "CANCELED", "FAILED"]:
                        self.logger.info(f"作业 {job_id} 完成，状态: {state}")
                        return state == "FINISHED"
                
                await asyncio.sleep(check_interval)
                
            except Exception as e:
                self.logger.error(f"检查作业状态失败: {str(e)}")
                return False
        
        self.logger.warning(f"作业 {job_id} 等待超时")
        return False
    
    async def get_job_summary(self, job_id: str) -> Optional[Dict[str, Any]]:
        """获取作业摘要信息"""
        try:
            details = await self.get_job_details(job_id)
            metrics = await self.get_job_metrics(job_id)
            
            if details:
                summary = {
                    "job_id": job_id,
                    "name": details.get("name"),
                    "state": details.get("state"),
                    "start_time": details.get("start-time"),
                    "end_time": details.get("end-time"),
                    "duration": details.get("duration"),
                    "parallelism": details.get("parallelism"),
                    "vertices": len(details.get("vertices", [])),
                    "metrics": metrics[:10] if metrics else []  # 只取前10个指标
                }
                
                return summary
            
        except Exception as e:
            self.logger.error(f"获取作业摘要失败: {str(e)}")
        
        return None