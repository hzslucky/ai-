# AI 赋能的智能简历分析系统

基于 AI 的智能简历解析、信息提取与岗位匹配评分系统。上传 PDF 简历，自动提取关键信息，并与岗位需求进行智能匹配打分。

## 功能概述

| 模块      | 说明                                      | 状态   |
| ------- | --------------------------------------- | ---- |
| 简历上传与解析 | 上传 PDF 简历，多页解析，文本清洗                     | ✅ 必选 |
| 关键信息提取  | AI 提取姓名/电话/邮箱/地址（必选）及求职意向/薪资/学历/项目（加分项） | ✅ 必选 |
| 简历评分与匹配 | 岗位关键词提取 + 多维匹配度评分（技能匹配率、经验相关性、学历匹配度）    | ✅ 必选 |
| 结果返回与缓存 | JSON 结构化返回 + Redis/内存缓存机制               | ✅ 必选 |
| 前端页面    | 简洁可用的交互页面，支持拖拽上传                        | ✅ 必选 |

## 项目结构

```
resume-analyzer/
├── backend/
│   ├── app.py              # FastAPI 主应用
│   ├── config.py           # 配置管理（环境变量）
│   ├── pdf_parser.py       # PDF 解析与文本清洗
│   ├── ai_extractor.py     # AI 关键信息提取
│   ├── matcher.py          # 简历评分与岗位匹配
│   ├── cache.py            # 缓存层（Redis + 内存）
│   └── requirements.txt    # Python 依赖
├── frontend/
│   ├── index.html          # 前端页面
│   ├── style.css           # 样式
│   └── app.js              # 交互逻辑
├── .gitignore
└── README.md
```

## API 文档

### POST /api/resume/upload

上传简历 PDF，提取关键信息。

**请求**：`multipart/form-data`

- `file`: PDF 文件

**响应**：

```json
{
  "resume_id": "a1b2c3d4e5f6",
  "parse_time_ms": 1250,
  "raw_text_length": 1523,
  "info": {
    "name": "张三",
    "phone": "13800138000",
    "email": "zhangsan@example.com",
    "address": "北京市朝阳区",
    "job_intent": "Python 后端工程师",
    "expected_salary": "15K-25K",
    "work_years": "5年",
    "education": "本科",
    "projects": [
      {"name": "电商平台", "description": "负责后端API开发"}
    ]
  },
  "cached": false
}
```

### POST /api/resume/analyze

上传简历并进行岗位匹配分析。

**请求**：`multipart/form-data`

- `file`: PDF 文件
- `job_description`: 岗位需求描述（可选）

**响应**（含匹配结果）：

```json
{
  "resume_id": "a1b2c3d4e5f6",
  "parse_time_ms": 2450,
  "info": { ... },
  "match": {
    "overall_score": 0.78,
    "skill_match_rate": 0.85,
    "experience_score": 0.80,
    "education_score": 0.60,
    "analysis": "候选人技能与岗位要求高度匹配...",
    "matched_skills": ["Python", "FastAPI", "PostgreSQL"],
    "missing_skills": ["Docker", "Kubernetes"]
  },
  "cached": false
}
```

## 技术方案

### AI 模型

- 默认使用 OpenAI GPT-4o-mini（通过 API 调用）
- 支持任意 OpenAI 兼容接口（如阿里云百炼、DeepSeek 等）
- 无 API Key 时自动降级为规则匹配，保证功能可用

### 缓存策略

- **Redis 模式**：适合生产环境，简历内容 SHA256 哈希作为 Key
- **内存模式**：开发/测试环境默认使用，无需外部依赖
- 缓存命中时跳过解析和 AI 调用，显著降低延迟和成本

### 评分算法

- **AI 模式**：由大模型多维度评估，输出技能匹配率、经验相关性、综合分析
- **规则模式**：关键词匹配率 (60%) + 工作年限评分 (30%) + 学历加分 (10%)

## 前端部署（GitHub Pages）

1. 修改 `frontend/app.js` 第一行的 `API_BASE` 为实际后端地址
2. 将 `frontend/` 目录推送到 GitHub 仓库的 `gh-pages` 分支
3. 在仓库 Settings → Pages 中启用 GitHub Pages

## 阿里云 Serverless 部署

### 函数计算 FC 配置

```bash
# 安装 Serverless Devs 工具
npm install -g @serverless-devs/s

# 配置 s.yaml，使用 custom-container 或 Python 3 运行时
# 将 backend/ 目录部署为函数
s deploy
```

关键配置：

- 运行时：Python 3.10
- 内存：512MB+
- 超时：30s
- 触发器：HTTP 触发器

## License

MIT
