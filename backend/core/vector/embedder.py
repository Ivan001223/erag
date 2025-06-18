"""向量嵌入器

提供文本和文档的向量嵌入功能，支持多种嵌入模型和批量处理。
"""

import asyncio
import hashlib
import json
import time
from enum import Enum
from typing import Dict, List, Optional, Union, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime

import numpy as np
from sentence_transformers import SentenceTransformer
import openai
import requests
from transformers import AutoTokenizer, AutoModel
import torch

from backend.utils.logger import get_logger

logger = get_logger(__name__)


class EmbeddingModel(Enum):
    """支持的嵌入模型类型"""
    SENTENCE_TRANSFORMERS = "sentence_transformers"
    OPENAI = "openai"
    HUGGINGFACE = "huggingface"
    BGE_LARGE = "bge_large"
    BGE_BASE = "bge_base"
    BGE_SMALL = "bge_small"
    M3E_BASE = "m3e_base"
    M3E_LARGE = "m3e_large"
    TEXT2VEC_BASE = "text2vec_base"
    TEXT2VEC_LARGE = "text2vec_large"
    CUSTOM_API = "custom_api"


class EmbeddingStrategy(Enum):
    """嵌入策略"""
    MEAN_POOLING = "mean_pooling"
    CLS_POOLING = "cls_pooling"
    MAX_POOLING = "max_pooling"
    WEIGHTED_POOLING = "weighted_pooling"


class TextSplitStrategy(Enum):
    """文本分割策略"""
    FIXED_SIZE = "fixed_size"
    SENTENCE_BASED = "sentence_based"
    PARAGRAPH_BASED = "paragraph_based"
    SEMANTIC_BASED = "semantic_based"
    SLIDING_WINDOW = "sliding_window"


@dataclass
class EmbeddingConfig:
    """嵌入配置"""
    model_name: str
    model_type: EmbeddingModel
    dimension: int = 768
    max_length: int = 512
    batch_size: int = 32
    device: str = "auto"  # auto, cpu, cuda
    normalize: bool = True
    pooling_strategy: EmbeddingStrategy = EmbeddingStrategy.MEAN_POOLING
    
    # 文本预处理配置
    lowercase: bool = True
    remove_special_chars: bool = False
    min_text_length: int = 10
    max_text_length: int = 8192
    
    # 分割配置
    split_strategy: TextSplitStrategy = TextSplitStrategy.FIXED_SIZE
    chunk_size: int = 512
    chunk_overlap: int = 50
    
    # API配置（用于远程模型）
    api_url: Optional[str] = None
    api_key: Optional[str] = None
    api_timeout: int = 30
    
    # 缓存配置
    enable_cache: bool = True
    cache_ttl: int = 3600  # 秒
    
    # 性能配置
    enable_gpu: bool = True
    max_workers: int = 4
    
    def __post_init__(self):
        """配置后处理"""
        if self.device == "auto":
            self.device = "cuda" if torch.cuda.is_available() and self.enable_gpu else "cpu"


@dataclass
class EmbeddingResult:
    """嵌入结果"""
    text: str
    embedding: np.ndarray
    model_name: str
    dimension: int
    processing_time: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "text": self.text,
            "embedding": self.embedding.tolist(),
            "model_name": self.model_name,
            "dimension": self.dimension,
            "processing_time": self.processing_time,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EmbeddingResult":
        """从字典创建"""
        return cls(
            text=data["text"],
            embedding=np.array(data["embedding"]),
            model_name=data["model_name"],
            dimension=data["dimension"],
            processing_time=data["processing_time"],
            metadata=data.get("metadata", {}),
            created_at=datetime.fromisoformat(data["created_at"])
        )


@dataclass
class BatchEmbeddingResult:
    """批量嵌入结果"""
    results: List[EmbeddingResult]
    total_texts: int
    successful_embeddings: int
    failed_embeddings: int
    total_processing_time: float
    average_processing_time: float
    model_name: str
    batch_size: int
    
    def get_embeddings_matrix(self) -> np.ndarray:
        """获取嵌入矩阵"""
        if not self.results:
            return np.array([])
        return np.vstack([result.embedding for result in self.results])
    
    def get_texts(self) -> List[str]:
        """获取文本列表"""
        return [result.text for result in self.results]


class Embedder:
    """向量嵌入器
    
    支持多种嵌入模型和策略，提供文本向量化功能。
    """
    
    def __init__(self, config: EmbeddingConfig):
        """初始化嵌入器
        
        Args:
            config: 嵌入配置
        """
        self.config = config
        self.model = None
        self.tokenizer = None
        self.cache: Dict[str, EmbeddingResult] = {}
        self.stats = {
            "total_embeddings": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "total_processing_time": 0.0,
            "average_processing_time": 0.0
        }
        
        logger.info(f"初始化嵌入器: {config.model_name} ({config.model_type.value})")
        self._load_model()
    
    def _load_model(self):
        """加载嵌入模型"""
        try:
            if self.config.model_type == EmbeddingModel.SENTENCE_TRANSFORMERS:
                self._load_sentence_transformer()
            elif self.config.model_type == EmbeddingModel.HUGGINGFACE:
                self._load_huggingface_model()
            elif self.config.model_type in [EmbeddingModel.BGE_LARGE, EmbeddingModel.BGE_BASE, EmbeddingModel.BGE_SMALL]:
                self._load_bge_model()
            elif self.config.model_type in [EmbeddingModel.M3E_BASE, EmbeddingModel.M3E_LARGE]:
                self._load_m3e_model()
            elif self.config.model_type in [EmbeddingModel.TEXT2VEC_BASE, EmbeddingModel.TEXT2VEC_LARGE]:
                self._load_text2vec_model()
            elif self.config.model_type == EmbeddingModel.OPENAI:
                self._setup_openai()
            elif self.config.model_type == EmbeddingModel.CUSTOM_API:
                self._setup_custom_api()
            else:
                raise ValueError(f"不支持的模型类型: {self.config.model_type}")
            
            logger.info(f"模型加载成功: {self.config.model_name}")
            
        except Exception as e:
            logger.error(f"模型加载失败: {str(e)}")
            raise
    
    def _load_sentence_transformer(self):
        """加载SentenceTransformer模型"""
        self.model = SentenceTransformer(self.config.model_name, device=self.config.device)
        self.config.dimension = self.model.get_sentence_embedding_dimension()
    
    def _load_huggingface_model(self):
        """加载HuggingFace模型"""
        self.tokenizer = AutoTokenizer.from_pretrained(self.config.model_name)
        self.model = AutoModel.from_pretrained(self.config.model_name)
        
        if self.config.device == "cuda" and torch.cuda.is_available():
            self.model = self.model.cuda()
        
        self.model.eval()
    
    def _load_bge_model(self):
        """加载BGE模型"""
        model_mapping = {
            EmbeddingModel.BGE_LARGE: "BAAI/bge-large-zh-v1.5",
            EmbeddingModel.BGE_BASE: "BAAI/bge-base-zh-v1.5",
            EmbeddingModel.BGE_SMALL: "BAAI/bge-small-zh-v1.5"
        }
        model_name = model_mapping.get(self.config.model_type, self.config.model_name)
        self.model = SentenceTransformer(model_name, device=self.config.device)
        self.config.dimension = self.model.get_sentence_embedding_dimension()
    
    def _load_m3e_model(self):
        """加载M3E模型"""
        model_mapping = {
            EmbeddingModel.M3E_BASE: "moka-ai/m3e-base",
            EmbeddingModel.M3E_LARGE: "moka-ai/m3e-large"
        }
        model_name = model_mapping.get(self.config.model_type, self.config.model_name)
        self.model = SentenceTransformer(model_name, device=self.config.device)
        self.config.dimension = self.model.get_sentence_embedding_dimension()
    
    def _load_text2vec_model(self):
        """加载Text2Vec模型"""
        model_mapping = {
            EmbeddingModel.TEXT2VEC_BASE: "shibing624/text2vec-base-chinese",
            EmbeddingModel.TEXT2VEC_LARGE: "shibing624/text2vec-large-chinese"
        }
        model_name = model_mapping.get(self.config.model_type, self.config.model_name)
        self.model = SentenceTransformer(model_name, device=self.config.device)
        self.config.dimension = self.model.get_sentence_embedding_dimension()
    
    def _setup_openai(self):
        """设置OpenAI API"""
        if not self.config.api_key:
            raise ValueError("OpenAI API密钥未设置")
        openai.api_key = self.config.api_key
        self.config.dimension = 1536  # text-embedding-ada-002的维度
    
    def _setup_custom_api(self):
        """设置自定义API"""
        if not self.config.api_url:
            raise ValueError("自定义API URL未设置")
    
    def _preprocess_text(self, text: str) -> str:
        """预处理文本"""
        if not text or not text.strip():
            return ""
        
        # 基本清理
        text = text.strip()
        
        if self.config.lowercase:
            text = text.lower()
        
        if self.config.remove_special_chars:
            import re
            text = re.sub(r'[^\w\s\u4e00-\u9fff]', '', text)
        
        # 长度检查
        if len(text) < self.config.min_text_length:
            return ""
        
        if len(text) > self.config.max_text_length:
            text = text[:self.config.max_text_length]
        
        return text
    
    def _split_text(self, text: str) -> List[str]:
        """分割文本"""
        if len(text) <= self.config.chunk_size:
            return [text]
        
        chunks = []
        
        if self.config.split_strategy == TextSplitStrategy.FIXED_SIZE:
            chunks = self._split_fixed_size(text)
        elif self.config.split_strategy == TextSplitStrategy.SENTENCE_BASED:
            chunks = self._split_by_sentences(text)
        elif self.config.split_strategy == TextSplitStrategy.PARAGRAPH_BASED:
            chunks = self._split_by_paragraphs(text)
        elif self.config.split_strategy == TextSplitStrategy.SLIDING_WINDOW:
            chunks = self._split_sliding_window(text)
        else:
            chunks = self._split_fixed_size(text)
        
        return [chunk for chunk in chunks if len(chunk.strip()) >= self.config.min_text_length]
    
    def _split_fixed_size(self, text: str) -> List[str]:
        """固定大小分割"""
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + self.config.chunk_size
            chunk = text[start:end]
            chunks.append(chunk)
            start = end - self.config.chunk_overlap
        
        return chunks
    
    def _split_by_sentences(self, text: str) -> List[str]:
        """按句子分割"""
        import re
        sentences = re.split(r'[。！？.!?]', text)
        
        chunks = []
        current_chunk = ""
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            
            if len(current_chunk + sentence) <= self.config.chunk_size:
                current_chunk += sentence + "。"
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = sentence + "。"
        
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return chunks
    
    def _split_by_paragraphs(self, text: str) -> List[str]:
        """按段落分割"""
        paragraphs = text.split('\n\n')
        
        chunks = []
        current_chunk = ""
        
        for paragraph in paragraphs:
            paragraph = paragraph.strip()
            if not paragraph:
                continue
            
            if len(current_chunk + paragraph) <= self.config.chunk_size:
                current_chunk += paragraph + "\n\n"
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = paragraph + "\n\n"
        
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return chunks
    
    def _split_sliding_window(self, text: str) -> List[str]:
        """滑动窗口分割"""
        chunks = []
        step = self.config.chunk_size - self.config.chunk_overlap
        
        for i in range(0, len(text), step):
            chunk = text[i:i + self.config.chunk_size]
            if len(chunk.strip()) >= self.config.min_text_length:
                chunks.append(chunk)
        
        return chunks
    
    def _get_cache_key(self, text: str) -> str:
        """生成缓存键"""
        content = f"{self.config.model_name}:{text}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def _get_from_cache(self, text: str) -> Optional[EmbeddingResult]:
        """从缓存获取结果"""
        if not self.config.enable_cache:
            return None
        
        cache_key = self._get_cache_key(text)
        result = self.cache.get(cache_key)
        
        if result:
            # 检查TTL
            age = (datetime.now() - result.created_at).total_seconds()
            if age <= self.config.cache_ttl:
                self.stats["cache_hits"] += 1
                return result
            else:
                # 过期，删除
                del self.cache[cache_key]
        
        self.stats["cache_misses"] += 1
        return None
    
    def _save_to_cache(self, text: str, result: EmbeddingResult):
        """保存到缓存"""
        if not self.config.enable_cache:
            return
        
        cache_key = self._get_cache_key(text)
        self.cache[cache_key] = result
    
    async def embed_text(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> EmbeddingResult:
        """嵌入单个文本
        
        Args:
            text: 要嵌入的文本
            metadata: 附加元数据
            
        Returns:
            嵌入结果
        """
        start_time = time.time()
        
        # 预处理
        processed_text = self._preprocess_text(text)
        if not processed_text:
            raise ValueError("文本为空或过短")
        
        # 检查缓存
        cached_result = self._get_from_cache(processed_text)
        if cached_result:
            logger.debug(f"缓存命中: {processed_text[:50]}...")
            return cached_result
        
        try:
            # 生成嵌入
            if self.config.model_type == EmbeddingModel.OPENAI:
                embedding = await self._embed_with_openai(processed_text)
            elif self.config.model_type == EmbeddingModel.CUSTOM_API:
                embedding = await self._embed_with_custom_api(processed_text)
            else:
                embedding = await self._embed_with_local_model(processed_text)
            
            processing_time = time.time() - start_time
            
            # 创建结果
            result = EmbeddingResult(
                text=processed_text,
                embedding=embedding,
                model_name=self.config.model_name,
                dimension=len(embedding),
                processing_time=processing_time,
                metadata=metadata or {}
            )
            
            # 保存到缓存
            self._save_to_cache(processed_text, result)
            
            # 更新统计
            self.stats["total_embeddings"] += 1
            self.stats["total_processing_time"] += processing_time
            self.stats["average_processing_time"] = (
                self.stats["total_processing_time"] / self.stats["total_embeddings"]
            )
            
            logger.debug(f"嵌入完成: {processed_text[:50]}... ({processing_time:.3f}s)")
            return result
            
        except Exception as e:
            logger.error(f"嵌入失败: {str(e)}")
            raise
    
    async def _embed_with_local_model(self, text: str) -> np.ndarray:
        """使用本地模型嵌入"""
        if self.config.model_type == EmbeddingModel.SENTENCE_TRANSFORMERS or \
           self.config.model_type in [EmbeddingModel.BGE_LARGE, EmbeddingModel.BGE_BASE, EmbeddingModel.BGE_SMALL, 
                                     EmbeddingModel.M3E_BASE, EmbeddingModel.M3E_LARGE,
                                     EmbeddingModel.TEXT2VEC_BASE, EmbeddingModel.TEXT2VEC_LARGE]:
            embedding = self.model.encode([text], normalize_embeddings=self.config.normalize)[0]
            return embedding.astype(np.float32)
        
        elif self.config.model_type == EmbeddingModel.HUGGINGFACE:
            return await self._embed_with_huggingface(text)
        
        else:
            raise ValueError(f"不支持的本地模型类型: {self.config.model_type}")
    
    async def _embed_with_huggingface(self, text: str) -> np.ndarray:
        """使用HuggingFace模型嵌入"""
        inputs = self.tokenizer(text, return_tensors="pt", truncation=True, 
                               max_length=self.config.max_length, padding=True)
        
        if self.config.device == "cuda":
            inputs = {k: v.cuda() for k, v in inputs.items()}
        
        with torch.no_grad():
            outputs = self.model(**inputs)
            
            if self.config.pooling_strategy == EmbeddingStrategy.CLS_POOLING:
                embedding = outputs.last_hidden_state[:, 0, :].cpu().numpy()[0]
            elif self.config.pooling_strategy == EmbeddingStrategy.MEAN_POOLING:
                attention_mask = inputs['attention_mask']
                token_embeddings = outputs.last_hidden_state
                input_mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
                embedding = torch.sum(token_embeddings * input_mask_expanded, 1) / torch.clamp(input_mask_expanded.sum(1), min=1e-9)
                embedding = embedding.cpu().numpy()[0]
            elif self.config.pooling_strategy == EmbeddingStrategy.MAX_POOLING:
                token_embeddings = outputs.last_hidden_state
                embedding = torch.max(token_embeddings, 1)[0].cpu().numpy()[0]
            else:
                embedding = outputs.last_hidden_state.mean(dim=1).cpu().numpy()[0]
        
        if self.config.normalize:
            embedding = embedding / np.linalg.norm(embedding)
        
        return embedding.astype(np.float32)
    
    async def _embed_with_openai(self, text: str) -> np.ndarray:
        """使用OpenAI API嵌入"""
        try:
            response = await openai.Embedding.acreate(
                model="text-embedding-ada-002",
                input=text
            )
            embedding = np.array(response['data'][0]['embedding'], dtype=np.float32)
            
            if self.config.normalize:
                embedding = embedding / np.linalg.norm(embedding)
            
            return embedding
            
        except Exception as e:
            logger.error(f"OpenAI嵌入失败: {str(e)}")
            raise
    
    async def _embed_with_custom_api(self, text: str) -> np.ndarray:
        """使用自定义API嵌入"""
        try:
            headers = {"Content-Type": "application/json"}
            if self.config.api_key:
                headers["Authorization"] = f"Bearer {self.config.api_key}"
            
            payload = {
                "text": text,
                "model": self.config.model_name
            }
            
            response = requests.post(
                self.config.api_url,
                json=payload,
                headers=headers,
                timeout=self.config.api_timeout
            )
            response.raise_for_status()
            
            data = response.json()
            embedding = np.array(data["embedding"], dtype=np.float32)
            
            if self.config.normalize:
                embedding = embedding / np.linalg.norm(embedding)
            
            return embedding
            
        except Exception as e:
            logger.error(f"自定义API嵌入失败: {str(e)}")
            raise
    
    async def embed_texts(self, texts: List[str], metadata_list: Optional[List[Dict[str, Any]]] = None) -> BatchEmbeddingResult:
        """批量嵌入文本
        
        Args:
            texts: 要嵌入的文本列表
            metadata_list: 元数据列表
            
        Returns:
            批量嵌入结果
        """
        start_time = time.time()
        
        if not texts:
            raise ValueError("文本列表为空")
        
        if metadata_list and len(metadata_list) != len(texts):
            raise ValueError("元数据列表长度与文本列表不匹配")
        
        results = []
        failed_count = 0
        
        # 分批处理
        for i in range(0, len(texts), self.config.batch_size):
            batch_texts = texts[i:i + self.config.batch_size]
            batch_metadata = metadata_list[i:i + self.config.batch_size] if metadata_list else [None] * len(batch_texts)
            
            # 并发处理批次
            tasks = [
                self.embed_text(text, metadata)
                for text, metadata in zip(batch_texts, batch_metadata)
            ]
            
            try:
                batch_results = await asyncio.gather(*tasks, return_exceptions=True)
                
                for result in batch_results:
                    if isinstance(result, Exception):
                        logger.warning(f"嵌入失败: {str(result)}")
                        failed_count += 1
                    else:
                        results.append(result)
                        
            except Exception as e:
                logger.error(f"批量嵌入失败: {str(e)}")
                failed_count += len(batch_texts)
        
        total_time = time.time() - start_time
        
        return BatchEmbeddingResult(
            results=results,
            total_texts=len(texts),
            successful_embeddings=len(results),
            failed_embeddings=failed_count,
            total_processing_time=total_time,
            average_processing_time=total_time / len(texts) if texts else 0,
            model_name=self.config.model_name,
            batch_size=self.config.batch_size
        )
    
    async def embed_documents(self, documents: List[Dict[str, Any]]) -> List[EmbeddingResult]:
        """嵌入文档
        
        Args:
            documents: 文档列表，每个文档包含text字段和其他元数据
            
        Returns:
            嵌入结果列表
        """
        results = []
        
        for doc in documents:
            if "text" not in doc:
                logger.warning(f"文档缺少text字段: {doc}")
                continue
            
            text = doc["text"]
            metadata = {k: v for k, v in doc.items() if k != "text"}
            
            # 分割长文本
            chunks = self._split_text(text)
            
            for i, chunk in enumerate(chunks):
                chunk_metadata = metadata.copy()
                chunk_metadata.update({
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                    "original_length": len(text),
                    "chunk_length": len(chunk)
                })
                
                try:
                    result = await self.embed_text(chunk, chunk_metadata)
                    results.append(result)
                except Exception as e:
                    logger.error(f"文档块嵌入失败: {str(e)}")
        
        return results
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        cache_hit_rate = 0
        if self.stats["cache_hits"] + self.stats["cache_misses"] > 0:
            cache_hit_rate = self.stats["cache_hits"] / (self.stats["cache_hits"] + self.stats["cache_misses"])
        
        return {
            "model_name": self.config.model_name,
            "model_type": self.config.model_type.value,
            "dimension": self.config.dimension,
            "device": self.config.device,
            "total_embeddings": self.stats["total_embeddings"],
            "cache_size": len(self.cache),
            "cache_hit_rate": cache_hit_rate,
            "total_processing_time": self.stats["total_processing_time"],
            "average_processing_time": self.stats["average_processing_time"]
        }
    
    def clear_cache(self):
        """清空缓存"""
        self.cache.clear()
        logger.info("嵌入缓存已清空")
    
    def save_model(self, path: str):
        """保存模型"""
        if self.config.model_type == EmbeddingModel.SENTENCE_TRANSFORMERS or \
           self.config.model_type in [EmbeddingModel.BGE_LARGE, EmbeddingModel.BGE_BASE, EmbeddingModel.BGE_SMALL,
                                     EmbeddingModel.M3E_BASE, EmbeddingModel.M3E_LARGE,
                                     EmbeddingModel.TEXT2VEC_BASE, EmbeddingModel.TEXT2VEC_LARGE]:
            self.model.save(path)
            logger.info(f"模型已保存到: {path}")
        else:
            logger.warning(f"模型类型 {self.config.model_type} 不支持保存")
    
    def load_model(self, path: str):
        """加载模型"""
        if self.config.model_type == EmbeddingModel.SENTENCE_TRANSFORMERS or \
           self.config.model_type in [EmbeddingModel.BGE_LARGE, EmbeddingModel.BGE_BASE, EmbeddingModel.BGE_SMALL,
                                     EmbeddingModel.M3E_BASE, EmbeddingModel.M3E_LARGE,
                                     EmbeddingModel.TEXT2VEC_BASE, EmbeddingModel.TEXT2VEC_LARGE]:
            self.model = SentenceTransformer(path, device=self.config.device)
            self.config.dimension = self.model.get_sentence_embedding_dimension()
            logger.info(f"模型已从 {path} 加载")
        else:
            logger.warning(f"模型类型 {self.config.model_type} 不支持加载")


# 预定义配置
DEFAULT_CONFIGS = {
    "bge_large_zh": EmbeddingConfig(
        model_name="BAAI/bge-large-zh-v1.5",
        model_type=EmbeddingModel.BGE_LARGE,
        dimension=1024,
        max_length=512,
        batch_size=16
    ),
    "bge_base_zh": EmbeddingConfig(
        model_name="BAAI/bge-base-zh-v1.5",
        model_type=EmbeddingModel.BGE_BASE,
        dimension=768,
        max_length=512,
        batch_size=32
    ),
    "m3e_base": EmbeddingConfig(
        model_name="moka-ai/m3e-base",
        model_type=EmbeddingModel.M3E_BASE,
        dimension=768,
        max_length=512,
        batch_size=32
    ),
    "text2vec_base": EmbeddingConfig(
        model_name="shibing624/text2vec-base-chinese",
        model_type=EmbeddingModel.TEXT2VEC_BASE,
        dimension=768,
        max_length=512,
        batch_size=32
    ),
    "openai_ada002": EmbeddingConfig(
        model_name="text-embedding-ada-002",
        model_type=EmbeddingModel.OPENAI,
        dimension=1536,
        max_length=8191,
        batch_size=16
    )
}


def create_embedder(config_name: str = "bge_base_zh", **kwargs) -> Embedder:
    """创建嵌入器
    
    Args:
        config_name: 预定义配置名称
        **kwargs: 额外配置参数
        
    Returns:
        嵌入器实例
    """
    if config_name not in DEFAULT_CONFIGS:
        raise ValueError(f"未知配置: {config_name}. 可用配置: {list(DEFAULT_CONFIGS.keys())}")
    
    config = DEFAULT_CONFIGS[config_name]
    
    # 应用额外参数
    for key, value in kwargs.items():
        if hasattr(config, key):
            setattr(config, key, value)
    
    return Embedder(config)