# RAG Local Enterprise System

> 本地化企业级 RAG（Retrieval-Augmented Generation）知识库系统

学习 & 开源项目，旨在提供一个可扩展的 RAG 实现，并作为学习总结。



***

## 📌 项目概述

RAG Local Enterprise System 是一个面向企业的本地化问答系统，支持多文档管理、本地向量化检索、LLM 推理与对话历史管理，具备模块化、可扩展和易部署的特性。

项目目标：



1. 学习 RAG 系统设计与实现

2. 提供可部署的开源 RAG 框架

3. 支持本地化、多文档、多租户部署



***

## 🏗 技术架构

```mermaid
flowchart TD
    %% 样式定义
    classDef frontend fill:#f0f8ff,stroke:#4682b4,stroke-width:2px;
    classDef api fill:#e6f3ff,stroke:#2e86ab,stroke-width:2px;
    classDef core fill:#d4edda,stroke:#28a745,stroke-width:2px;
    classDef database fill:#fff3cd,stroke:#ffc107,stroke-width:2px;
    classDef llm fill:#f8d7da,stroke:#dc3545,stroke-width:2px;
    
    %% 前端层
    subgraph 前端界面层
        A[Web界面\nHTMX + Jinja2 + CSS/JS]
    end
    class A frontend;

    %% API网关层
    subgraph API服务层
        B[FastAPI\nREST API接口]
        C[认证授权\nJWT/OAuth2]
        D[请求验证\nPydantic Schema]
    end
    class B,C,D api;

    %% 核心服务层
    subgraph 核心服务层
        E[文档处理服务]
        F[向量数据库服务]
        G[检索增强服务]
        H[对话管理服务]
        I[配置管理服务]
    end
    class E,F,G,H,I core;

    %% 数据存储层
    subgraph 数据存储层
        J[文档存储\nPDF/DOCX/TXT]
        K[向量数据库\nChromaDB]
        L[对话历史\nSQLite/PostgreSQL]
        M[系统配置\nYAML/Environment]
    end
    class J,K,L,M database;

    %% LLM服务层
    subgraph LLM服务层
        N[Ollama服务\n本地大模型]
        O[模型管理\n多模型支持]
        P[推理优化\n量化/缓存]
    end
    class N,O,P llm;

    %% 数据流
    A -->|HTTP请求| B
    B --> C
    C --> D
    D --> E
    D --> F
    D --> G
    D --> H
    D --> I

    %% 文档处理流程
    E -->|读取文档| J
    E -->|文档解析| E1[文档解析\n分块/清洗]
    E1 -->|文本向量化| F
    F -->|存储向量| K

    %% 检索流程
    G -->|查询向量库| K
    G --> G1[粗排检索\n向量相似度]
    G1 --> G2[精排优化\n重排序模型]
    G2 --> G3[Query改写\n查询扩展]

    %% 对话流程
    H -->|存储对话| L
    H --> H1[上下文维护\n多轮记忆]
    H1 --> G3

    %% 配置管理
    I -->|加载配置| M

    %% LLM推理流程
    G3 -->|检索结果| N
    H1 -->|对话历史| N
    I -->|模型配置| O
    O --> N
    N --> P
    P --> Q[生成回答\n引用来源]

    %% 响应返回
    Q -->|JSON响应| B
    B -->|渲染页面| A
```





***

## 🚀 功能阶段

### 第一阶段：基础功能实现



* 文档上传与处理

* 本地向量化存储

* 基础问答

* 简单前端界面

### 第二阶段：增强功能



* 多文档管理

* 对话历史管理

* Query 改写与扩展

* 粗排 + 精排算法

### 第三阶段：企业级特性



* 用户权限管理

* 多租户支持

* 监控与日志

* 性能优化



***

## 🛠 技术栈

**后端**：



* FastAPI, LangChain, ChromaDB, Sentence-Transformers, Ollama, loguru

**前端**：



* HTMX, Jinja2, Vanilla JS/CSS



***

## 📂 项目结构



```
rag-local-enterprise-system/

├── backend/               # 后端代码

│   ├── api/               # 路由和接口

│   ├── core/              # 配置与依赖

│   ├── models/            # 数据模型

│   ├── schemas/           # Pydantic schema

│   ├── services/          # 核心业务逻辑

│   └── utils/             # 工具模块（如日志、异常处理）

├── frontend/              # 前端模板和静态资源

├── data/                  # 数据存储

│   ├── documents/        # 原始文档

│   └── vector\_db/        # 向量数据库持久化

├── tests/                 # 测试代码

├── pyproject.toml        # 项目配置

├── uv.toml               # uv 项目配置

├── makefile              # 开发任务脚本

├── Dockerfile            # 容器化文件

├── docker-compose.yml    # 容器编排

└── README.md             # 项目说明
```



***

## ⚡ 快速上手

### 1. 克隆项目



```
git clone https://github.com/LeafInCode/RAG-Local-Enterprise-System.git

cd rag-local-enterprise-system
```

### 2. 创建虚拟环境



```
uv venv --python 3.12

source .venv/bin/activate
```

### 3. 安装依赖



```
uv pip install -e .
```

### 4. 启动项目



```
make serve
```

访问：`http://localhost:8000`



***

## 🧪 测试



```
make lint

make format

make typecheck
```



***

## 📦 部署方案

### 本地开发



* 使用 uvicorn 开发服务器，支持热重载

### 生产部署



* Docker 容器化部署

* Docker Compose 编排



***

## 📜 License

MIT License



***

## 💡 贡献

欢迎提交 PR，Fork 后修改，Issue 讨论功能优化。
