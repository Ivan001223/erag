# 企业级智能知识库系统 (ERAG)

## 项目概述

企业级智能知识库系统是一个基于知识图谱和向量数据库的智能文档处理和检索系统。系统集成了OCR、NLP、知识图谱构建、向量搜索等多种AI技术，为企业提供智能化的知识管理解决方案。

## 核心功能

- 🔍 **智能文档处理**：支持多格式文档的OCR识别和结构化处理
- 🕸️ **知识图谱构建**：自动提取实体关系，构建企业知识图谱
- 🔎 **混合检索**：结合向量搜索和图谱查询的智能检索
- 🤖 **LLM集成**：支持多种大语言模型的智能问答
- 📊 **实时数据处理**：基于Flink的流式数据处理
- 🎯 **Dify集成**：无缝对接Dify平台

## 技术架构

### 后端技术栈
- **框架**：FastAPI + Python 3.9+
- **数据库**：Neo4j (图数据库) + StarRocks (向量数据库) + Redis (缓存)
- **存储**：MinIO (对象存储)
- **流处理**：Apache Flink + FlinkCDC
- **OCR**：OnnxOCR
- **AI**：支持多种LLM模型

### 前端技术栈
- **框架**：Vue.js 3 + TypeScript
- **构建工具**：Vite
- **UI库**：Element Plus
- **状态管理**：Pinia

## 快速开始

### 环境要求
- Docker & Docker Compose
- Python 3.9+
- Node.js 16+

### 安装步骤

1. **克隆项目**
```bash
git clone <repository-url>
cd erag
```

2. **环境配置**
```bash
cp .env.example .env
# 编辑 .env 文件，配置必要的环境变量
```

3. **启动服务**
```bash
# 启动所有服务
docker-compose up -d

# 或者分别启动
docker-compose up -d neo4j redis minio
docker-compose up -d backend
docker-compose up -d frontend
```

4. **初始化数据库**
```bash
python scripts/init_db.py
```

5. **访问应用**
- 前端界面：http://localhost:3000
- API文档：http://localhost:8000/docs
- Neo4j浏览器：http://localhost:7474

## 项目结构

```
erag/
├── backend/                    # 后端服务
│   ├── api/                   # API路由
│   ├── core/                  # 核心业务逻辑
│   ├── connectors/            # 外部系统连接器
│   ├── models/                # 数据模型
│   ├── schemas/               # Pydantic模式
│   └── utils/                 # 工具函数
├── frontend/                   # 前端应用
├── ocr_service/               # OCR服务
├── scripts/                   # 工具脚本
├── deployments/               # 部署配置
└── docs/                      # 项目文档
```

## API文档

启动服务后，访问 http://localhost:8000/docs 查看完整的API文档。

## 开发指南

### 后端开发

1. **安装依赖**
```bash
cd backend
pip install -r requirements.txt
```

2. **运行开发服务器**
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 前端开发

1. **安装依赖**
```bash
cd frontend
npm install
```

2. **运行开发服务器**
```bash
npm run dev
```

### 测试

```bash
# 后端测试
cd backend
pytest

# 前端测试
cd frontend
npm run test
```

## 部署

### Docker部署

```bash
# 构建并启动所有服务
docker-compose up -d --build
```

### Kubernetes部署

```bash
# 应用Kubernetes配置
kubectl apply -f deployments/kubernetes/
```

## 贡献指南

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开 Pull Request

## 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 联系方式

- 项目维护者：[Your Name]
- 邮箱：[your.email@example.com]
- 项目链接：[https://github.com/yourusername/erag](https://github.com/yourusername/erag)