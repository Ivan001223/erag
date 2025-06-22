"""分布式追踪中间件

集成OpenTelemetry进行分布式追踪和高级监控。
"""

import time
import asyncio
import json
import traceback
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
from datetime import datetime
from contextlib import asynccontextmanager
from uuid import uuid4

from opentelemetry import trace, metrics, baggage
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.exporter.prometheus import PrometheusMetricReader
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.resources import Resource
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.propagate import set_global_textmap
from opentelemetry.propagators.b3 import B3MultiFormat
from opentelemetry.semconv.trace import SpanAttributes
from opentelemetry.trace.status import Status, StatusCode

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import structlog

from backend.config.settings import get_settings
from backend.utils.logger import get_logger

settings = get_settings()
logger = get_logger(__name__)


@dataclass
class TraceContext:
    """追踪上下文"""
    trace_id: str
    span_id: str
    parent_span_id: Optional[str] = None
    baggage: Dict[str, str] = field(default_factory=dict)
    start_time: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MetricData:
    """指标数据"""
    name: str
    value: float
    labels: Dict[str, str] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    metric_type: str = "counter"  # counter, gauge, histogram


class TracingManager:
    """追踪管理器"""
    
    def __init__(
        self,
        service_name: str = "knowledge-system",
        jaeger_endpoint: Optional[str] = None,
        enable_metrics: bool = True,
        enable_logging: bool = True
    ):
        self.service_name = service_name
        self.jaeger_endpoint = jaeger_endpoint
        self.enable_metrics = enable_metrics
        self.enable_logging = enable_logging
        
        # 初始化追踪
        self._setup_tracing()
        
        # 初始化指标
        if enable_metrics:
            self._setup_metrics()
        
        # 初始化日志
        if enable_logging:
            self._setup_logging()
        
        # 获取tracer和meter
        self.tracer = trace.get_tracer(__name__)
        self.meter = metrics.get_meter(__name__) if enable_metrics else None
        
        # 创建指标
        if self.meter:
            self.request_counter = self.meter.create_counter(
                name="http_requests_total",
                description="Total number of HTTP requests"
            )
            self.request_duration = self.meter.create_histogram(
                name="http_request_duration_seconds",
                description="HTTP request duration in seconds"
            )
            self.active_requests = self.meter.create_up_down_counter(
                name="http_requests_active",
                description="Number of active HTTP requests"
            )
            self.error_counter = self.meter.create_counter(
                name="http_errors_total",
                description="Total number of HTTP errors"
            )
    
    def _setup_tracing(self):
        """设置分布式追踪"""
        resource = Resource.create({
            "service.name": self.service_name,
            "service.version": settings.app_version,
            "deployment.environment": settings.app_env
        })
        
        # 配置TracerProvider
        trace.set_tracer_provider(TracerProvider(resource=resource))
        
        # 配置Jaeger导出器
        if self.jaeger_endpoint:
            jaeger_exporter = JaegerExporter(
                agent_host_name=self.jaeger_endpoint.split(":")[0],
                agent_port=int(self.jaeger_endpoint.split(":")[1]) if ":" in self.jaeger_endpoint else 14268,
            )
            
            span_processor = BatchSpanProcessor(jaeger_exporter)
            trace.get_tracer_provider().add_span_processor(span_processor)
        
        # 设置传播器
        set_global_textmap(B3MultiFormat())
        
        # 自动插桩
        FastAPIInstrumentor.instrument()
        RequestsInstrumentor.instrument()
        SQLAlchemyInstrumentor.instrument()
        RedisInstrumentor.instrument()
    
    def _setup_metrics(self):
        """设置指标收集"""
        resource = Resource.create({
            "service.name": self.service_name,
            "service.version": settings.app_version
        })
        
        # 配置Prometheus导出器
        prometheus_reader = PrometheusMetricReader()
        metrics.set_meter_provider(MeterProvider(
            resource=resource,
            metric_readers=[prometheus_reader]
        ))
    
    def _setup_logging(self):
        """设置结构化日志"""
        structlog.configure(
            processors=[
                structlog.stdlib.filter_by_level,
                structlog.stdlib.add_logger_name,
                structlog.stdlib.add_log_level,
                structlog.stdlib.PositionalArgumentsFormatter(),
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.processors.UnicodeDecoder(),
                structlog.processors.JSONRenderer()
            ],
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
            cache_logger_on_first_use=True,
        )
    
    @asynccontextmanager
    async def trace_span(
        self,
        name: str,
        attributes: Optional[Dict[str, Any]] = None,
        kind: trace.SpanKind = trace.SpanKind.INTERNAL
    ):
        """创建追踪span的上下文管理器"""
        with self.tracer.start_as_current_span(name, kind=kind) as span:
            try:
                # 设置属性
                if attributes:
                    for key, value in attributes.items():
                        span.set_attribute(key, value)
                
                yield span
                
                # 设置成功状态
                span.set_status(Status(StatusCode.OK))
                
            except Exception as e:
                # 记录异常
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                raise
    
    def add_baggage(self, key: str, value: str):
        """添加baggage"""
        baggage.set_baggage(key, value)
    
    def get_baggage(self, key: str) -> Optional[str]:
        """获取baggage"""
        return baggage.get_baggage(key)
    
    def record_metric(self, metric_data: MetricData):
        """记录指标"""
        if not self.meter:
            return
        
        try:
            if metric_data.metric_type == "counter":
                counter = self.meter.create_counter(metric_data.name)
                counter.add(metric_data.value, metric_data.labels)
            elif metric_data.metric_type == "gauge":
                gauge = self.meter.create_gauge(metric_data.name)
                gauge.set(metric_data.value, metric_data.labels)
            elif metric_data.metric_type == "histogram":
                histogram = self.meter.create_histogram(metric_data.name)
                histogram.record(metric_data.value, metric_data.labels)
        except Exception as e:
            logger.error(f"记录指标失败: {str(e)}")


class TracingMiddleware(BaseHTTPMiddleware):
    """分布式追踪中间件"""
    
    def __init__(self, app, tracing_manager: TracingManager):
        super().__init__(app)
        self.tracing_manager = tracing_manager
        self.logger = structlog.get_logger(__name__)
    
    async def dispatch(self, request: Request, call_next):
        """处理请求追踪"""
        start_time = time.time()
        
        # 生成追踪ID
        trace_id = str(uuid4())
        request.state.trace_id = trace_id
        
        # 提取追踪上下文
        trace_context = self._extract_trace_context(request)
        
        # 创建span属性
        span_attributes = {
            SpanAttributes.HTTP_METHOD: request.method,
            SpanAttributes.HTTP_URL: str(request.url),
            SpanAttributes.HTTP_SCHEME: request.url.scheme,
            SpanAttributes.HTTP_HOST: request.url.hostname,
            SpanAttributes.HTTP_TARGET: request.url.path,
            SpanAttributes.USER_AGENT: request.headers.get("user-agent", ""),
            "trace.id": trace_id,
            "service.name": self.tracing_manager.service_name
        }
        
        # 添加用户信息
        if hasattr(request.state, "user_id"):
            span_attributes["user.id"] = request.state.user_id
        
        # 开始追踪
        async with self.tracing_manager.trace_span(
            f"{request.method} {request.url.path}",
            attributes=span_attributes,
            kind=trace.SpanKind.SERVER
        ) as span:
            try:
                # 设置baggage
                self.tracing_manager.add_baggage("trace.id", trace_id)
                if hasattr(request.state, "user_id"):
                    self.tracing_manager.add_baggage("user.id", request.state.user_id)
                
                # 记录请求开始指标
                if self.tracing_manager.meter:
                    self.tracing_manager.active_requests.add(1, {
                        "method": request.method,
                        "endpoint": request.url.path
                    })
                
                # 处理请求
                response = await call_next(request)
                
                # 记录响应属性
                span.set_attribute(SpanAttributes.HTTP_STATUS_CODE, response.status_code)
                
                # 记录指标
                duration = time.time() - start_time
                labels = {
                    "method": request.method,
                    "endpoint": request.url.path,
                    "status_code": str(response.status_code)
                }
                
                if self.tracing_manager.meter:
                    self.tracing_manager.request_counter.add(1, labels)
                    self.tracing_manager.request_duration.record(duration, labels)
                    self.tracing_manager.active_requests.add(-1, {
                        "method": request.method,
                        "endpoint": request.url.path
                    })
                
                # 记录错误
                if response.status_code >= 400:
                    span.set_status(Status(StatusCode.ERROR, f"HTTP {response.status_code}"))
                    if self.tracing_manager.meter:
                        self.tracing_manager.error_counter.add(1, labels)
                
                # 添加追踪头到响应
                response.headers["X-Trace-Id"] = trace_id
                
                # 结构化日志
                self.logger.info(
                    "HTTP请求完成",
                    method=request.method,
                    path=request.url.path,
                    status_code=response.status_code,
                    duration=duration,
                    trace_id=trace_id,
                    user_id=getattr(request.state, "user_id", None)
                )
                
                return response
                
            except Exception as e:
                # 记录异常
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                
                # 记录错误指标
                if self.tracing_manager.meter:
                    self.tracing_manager.error_counter.add(1, {
                        "method": request.method,
                        "endpoint": request.url.path,
                        "error_type": type(e).__name__
                    })
                    self.tracing_manager.active_requests.add(-1, {
                        "method": request.method,
                        "endpoint": request.url.path
                    })
                
                # 结构化错误日志
                self.logger.error(
                    "HTTP请求异常",
                    method=request.method,
                    path=request.url.path,
                    error=str(e),
                    trace_id=trace_id,
                    traceback=traceback.format_exc()
                )
                
                raise
    
    def _extract_trace_context(self, request: Request) -> TraceContext:
        """从请求中提取追踪上下文"""
        headers = request.headers
        
        # 提取B3追踪头
        trace_id = headers.get("x-b3-traceid") or headers.get("x-trace-id")
        span_id = headers.get("x-b3-spanid")
        parent_span_id = headers.get("x-b3-parentspanid")
        
        # 提取baggage
        baggage_header = headers.get("baggage", "")
        baggage_dict = {}
        if baggage_header:
            for item in baggage_header.split(","):
                if "=" in item:
                    key, value = item.strip().split("=", 1)
                    baggage_dict[key] = value
        
        return TraceContext(
            trace_id=trace_id or str(uuid4()),
            span_id=span_id or str(uuid4()),
            parent_span_id=parent_span_id,
            baggage=baggage_dict
        )


class CustomSpanProcessor:
    """自定义Span处理器"""
    
    def __init__(self, enable_sampling: bool = True, sample_rate: float = 1.0):
        self.enable_sampling = enable_sampling
        self.sample_rate = sample_rate
        self.span_storage: List[Dict[str, Any]] = []
    
    def on_start(self, span, parent_context=None):
        """Span开始时调用"""
        if self.enable_sampling and self.sample_rate < 1.0:
            import random
            if random.random() > self.sample_rate:
                span.set_attribute("sampled", False)
                return
        
        span.set_attribute("sampled", True)
        span.set_attribute("processor.start_time", time.time())
    
    def on_end(self, span):
        """Span结束时调用"""
        if span.get_attribute("sampled"):
            span_data = {
                "trace_id": format(span.get_span_context().trace_id, "032x"),
                "span_id": format(span.get_span_context().span_id, "016x"),
                "name": span.name,
                "start_time": span.start_time,
                "end_time": span.end_time,
                "duration": span.end_time - span.start_time,
                "attributes": dict(span.attributes) if span.attributes else {},
                "status": span.status.status_code.name if span.status else "OK"
            }
            
            self.span_storage.append(span_data)
            
            # 保持存储大小
            if len(self.span_storage) > 10000:
                self.span_storage = self.span_storage[-5000:]
    
    def get_spans(self, limit: int = 100) -> List[Dict[str, Any]]:
        """获取存储的span数据"""
        return self.span_storage[-limit:]
    
    def clear_spans(self):
        """清空span存储"""
        self.span_storage.clear()


def trace_async_function(name: Optional[str] = None):
    """异步函数追踪装饰器"""
    def decorator(func: Callable) -> Callable:
        func_name = name or f"{func.__module__}.{func.__name__}"
        
        async def wrapper(*args, **kwargs):
            tracer = trace.get_tracer(__name__)
            
            with tracer.start_as_current_span(func_name) as span:
                try:
                    # 设置函数属性
                    span.set_attribute("function.name", func.__name__)
                    span.set_attribute("function.module", func.__module__)
                    span.set_attribute("function.args_count", len(args))
                    span.set_attribute("function.kwargs_count", len(kwargs))
                    
                    # 执行函数
                    result = await func(*args, **kwargs)
                    
                    # 记录成功
                    span.set_status(Status(StatusCode.OK))
                    return result
                    
                except Exception as e:
                    # 记录异常
                    span.record_exception(e)
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    raise
        
        return wrapper
    return decorator


def trace_database_operation(operation_type: str):
    """数据库操作追踪装饰器"""
    def decorator(func: Callable) -> Callable:
        async def wrapper(*args, **kwargs):
            tracer = trace.get_tracer(__name__)
            
            with tracer.start_as_current_span(f"db.{operation_type}") as span:
                try:
                    # 设置数据库属性
                    span.set_attribute("db.operation", operation_type)
                    span.set_attribute("db.system", "neo4j")  # 或其他数据库类型
                    
                    # 执行操作
                    result = await func(*args, **kwargs)
                    
                    span.set_status(Status(StatusCode.OK))
                    return result
                    
                except Exception as e:
                    span.record_exception(e)
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    raise
        
        return wrapper
    return decorator 