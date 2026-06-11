# EduMind 智能导师系统 —— 完整方案设计书

> **版本**：V2.0-FINAL  
> **状态**：方案确认，待进入实施

---

## 第一章：项目概述

### 1.1 愿景

打造一个**开源的、AI 驱动的个人智能导师系统**——像一位私人家教，从零到一帮学习者建立完整知识图谱，**教、练、评、拓**一体化，最终可演进为平台级教育基础设施。

### 1.2 核心理念

| 原则 | 含义 |
|------|------|
| **先有图，后有课** | 每个知识点在知识图谱中有唯一位点，教学是对图的拓扑序遍历 |
| **教学是对话** | 不是单向灌输，而是问答 + 追问 + 延伸的循环 |
| **混合内容源** | 用户自备资料优先，AI 搜索补全，人机共同审核 |
| **领域感知** | 数学、编程、语言、历史……不同领域有不同的知识结构和教学策略 |
| **学习者感知** | 儿童、青少年、成人、老人……不同年龄段有不同的教学方式 |
| **内容与引擎分离** | 学习内容以结构化 Markdown 存储，渲染引擎可独立嵌入不同平台 |

### 1.3 核心能力清单

- **📚 混合内容采集**：用户上传（PDF/MD/链接）+ AI 自动搜索 + 多源交叉验证
- **🧠 领域自动识别**：LLM 分析内容 → 推断领域 → 加载对应 Domain Profile
- **🗂️ 智能大纲生成**：知识点拓扑排序 → 由浅入深的学习路径
- **📖 知识卡片教学**：按领域选模板（数学含 LaTeX，编程含代码编辑器……）
- **💬 双模交互**：文字对话 + 语音对话（ASR + TTS）
- **🔗 可视化知识图谱**：交互式 DAG，按掌握度着色，点击跳转
- **👤 学习者画像**：抽象程度、比喻密度、节奏快慢、反馈风格等完全自定义
- **📊 学习评估**：章节测验 + 进度追踪 + 掌握度量化 + 间隔重复
- **🔌 AI 自由配置**：Ollama / OpenAI / DeepSeek / 任何兼容 API
- **🔧 MCP 集成**：AI 可通过 MCP 协议调用搜索/工具/文件等外部能力
- **📦 跨平台**：Web → Tauri 桌面 → Docker → 未来多用户

---

## 第二章：系统架构

### 2.1 整体分层

```
┌────────────────────────────────────────────────────────────────────────┐
│                        表示层 (Presentation)                          │
│                                                                       │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────┐  ┌────────────┐ │
│  │知识卡片(React)│  │ 对话界面      │  │ 语音 UI    │  │ KG 可视化   │ │
│  │ 多模板按域切换  │  │ 文字/代码/公式 │  │ ASR+TTS   │  │ vis-network │ │
│  └──────┬───────┘  └──────┬───────┘  └──────┬─────┘  └──────┬─────┘ │
│         │                 │                 │               │         │
│  ┌──────┴─────────────────┴─────────────────┴───────────────┴──────┐ │
│  │               API Gateway (FastAPI / WebSocket)                  │ │
│  └─────────────────────────────────┬───────────────────────────────┘ │
│                                    │                                 │
├────────────────────────────────────┼─────────────────────────────────┤
│                        业务层 (Application)                         │
│                                    │                                 │
│  ┌─────────────────────────────────┼─────────────────────────────┐  │
│  │  ┌──────────┐  ┌──────────┐     │   ┌──────────┐             │  │
│  │  │内容管道   │  │大纲生成器  │     │   │教学引擎   │             │  │
│  │  │-多源提取   │  │-拓扑排序  │     │   │-对话管理  │             │  │
│  │  │-知识提取   │  │-领域分组  │     │   │-领域路由  │             │  │
│  │  │-入库前审核 │  │-用户调整  │     │   │-延伸策略  │             │  │
│  │  └──────────┘  └──────────┘     │   └──────────┘             │  │
│  │  ┌──────────┐  ┌──────────┐     │   ┌──────────┐             │  │
│  │  │评估引擎   │  │图谱管理器  │     │   │搜索编排   │             │  │
│  │  │-按域出题  │  │-节点CRUD  │     │   │-多源并行  │             │  │
│  │  │-掌握度    │  │-关系推断  │     │   │-交叉验证  │             │  │
│  │  │-间隔重复  │  │-子图查询  │     │   │-置信评分  │             │  │
│  │  └──────────┘  └──────────┘     │   └──────────┘             │  │
│  │  ┌──────────┐  ┌──────────┐     │                            │  │
│  │  │语音服务   │  │配置中心   │     │                            │  │
│  │  │-ASR      │  │-Domain   │     │                            │  │
│  │  │-TTS      │  │ Profile  │     │                            │  │
│  │  │-语音唤醒  │  │-Learner  │     │                            │  │
│  │  │          │  │ Profile  │     │                            │  │
│  │  └──────────┘  └──────────┘     │                            │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                    │                                 │
├────────────────────────────────────┼─────────────────────────────────┤
│                     基础设施层 (Infrastructure)                     │
│                                    │                                 │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐           │
│  │PostgreSQL│  │ Neo4j    │  │ pgvector  │  │ Redis    │           │
│  │用户/进度  │  │知识图谱   │  │语义检索   │  │会话/缓存 │           │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘           │
│                                    │                                 │
├────────────────────────────────────┼─────────────────────────────────┤
│                        AI 层 (Model Layer)                         │
│                                    │                                 │
│  ┌─────────────────────────────────┴────────────────────────────┐  │
│  │                      模型适配器                                │  │
│  │       统一接口，屏蔽不同 Provider 差异                         │  │
│  └──────┬─────────┬─────────┬──────────┬─────────┬────────────┘  │
│         │         │         │          │         │                 │
│  ┌──────┴┐  ┌────┴───┐  ┌──┴─────┐  ┌─┴──────┐ ┌┴──────────┐   │
│  │Ollama │  │OpenAI  │  │DeepSeek│  │Whisper │ │Kokoro     │   │
│  │(本地)  │  │兼容API  │  │API     │  │ASR    │ │TTS       │   │
│  └───────┘  └────────┘  └────────┘  └───────┘ └───────────┘   │
│                                    │                             │
│  ┌─────────────────────────────────┴────────────────────────┐   │
│  │                     MCP Client                            │   │
│  │     模型通过 MCP 协议调用外部工具：搜索/文件/代码执行等     │   │
│  └──────────────────────────────────────────────────────────┘   │
└────────────────────────────────────────────────────────────────────┘
```

### 2.2 模块职责矩阵

| 模块 | 职责 | 输入 | 输出 | 关键依赖 |
|------|------|------|------|----------|
| **内容管道** | 多源内容 → 结构化知识点 | 用户上传/链接/搜索文本 | 知识点列表 + 依赖关系 | LLM, Neo4j |
| **配置中心** | 管理 Domain Profile + Learner Profile | 领域/学习者参数 | 组合配置输出 | YAML 文件 + PG |
| **大纲生成器** | 知识点 → 按领域策略排序分组 | 知识图谱 + Profile | 结构化大纲 | LLM, Neo4j |
| **教学引擎** | 按领域 × 学习者策略逐节点教学 | 当前节点 + 双 Profile | 教学内容 + 对话 + 评估 | LLM, Vector, Profile |
| **图谱管理器** | 知识图 CRUD + 关系维护 | 节点/关系操作 | 查询结果 | Neo4j |
| **评估引擎** | 按域出题 → 判卷 → 更新 Mastery | 节点内容 + Profile | 题目 / 分数 / 掌握度 | LLM, PG |
| **搜索编排** | 多源并行搜索 + 交叉验证 | 主题/关键词 | 结构化内容摘要 | MCP Client |
| **语音服务** | ASR 语音→文字 + TTS 文字→语音 | 音频/文本 | 文本/音频 | Whisper, Kokoro |
| **MCP Client** | 模型调用外部工具的桥梁 | MCP Server 列表 | 工具调用结果 | MCP Python SDK |
| **模型适配器** | 统一接口屏蔽 Provider 差异 | 模型配置 | 统一调用结果 | LiteLLM |

---

## 第三章：Domain Profile —— 领域适配机制

### 3.1 设计动机

不同领域的知识结构差异巨大，不能用同一套教学逻辑：

| 领域 | 知识结构 | 适合的教学策略 |
|------|---------|--------------|
| **数学/物理** | 严格 DAG，A→B→C 不能跳 | 概念→公式→例题→练习 |
| **编程** | 技能树 + 项目实践 | Demo→动手写→Debug |
| **历史** | 网状关联（时间线+因果+人物） | 叙事→讨论→多视角分析 |
| **语言** | 螺旋上升（同知识点反复出现） | 输入→理解→发音→输出 |
| **音乐/绘画** | 技能渐进 + 感性理解 | 示范→模仿→创作 |

### 3.2 Domain Profile 结构定义

```yaml
# 完整 schema
domain:
  id: string                    # 唯一标识
  name: string                  # 中文名称
  aliases: string[]             # 别名（用于自动识别）

  graph_structure:
    type: "strict_dag" | "lattice" | "network" | "spiral" | "portfolio"
    allow_skip: boolean          # 是否可跳步
    allow_parallel: boolean      # 同级是否可并行学

  content_format:
    card_template: string       # 卡片模板名称（React 组件名）
    supports: string[]          # 特殊内容块（latex/audio/code/map/plot）
    examples_required: boolean

  pedagogy:
    strategy: string            # 策略标识
    steps_per_node: string[]    # 每节点的教学步骤
    dialogue_style: "socratic" | "supportive" | "lecture" | "coach"

  assessment:
    types: string[]             # 允许的题型列表
    passing_mastery: float      # 通过阈值 (0~1)
    allow_retake: boolean
    review_interval: string     # 间隔重复策略

  prompt_overrides:             # LLM 提示词覆盖
    generate_syllabus?: string
    teach_concept?: string
    generate_quiz?: string
    assess_answer?: string
    handle_question?: string
```

### 3.3 内置 Domain Profile（MVP 阶段）

| Profile | graph_structure | card_template | 教学策略 | 评估类型 |
|---------|---------------|---------------|---------|---------|
| **general** | network | default_card | 概念讲解→问答 | 选择+简答 |
| **math** | strict_dag | math_card | 概念→例题→练习 | 选择+填空+分步解题 |
| **programming** | lattice | programming_card | Demo→动手→Debug | 选择+代码编译 |
| **language** | spiral | language_card | 输入→理解→发音→输出 | 选择+发音+造句 |
| **history** | network | history_card | 叙事→因果→多视角 | 选择+论述+连线 |
| **physics** | strict_dag | math_card | 概念→实验→公式 | 选择+计算+实验分析 |
| **music** | lattice | music_card | 示范→模仿→创作 | 听力+演奏评估 |

### 3.4 领域自动检测

```
用户输入（主题/文件/链接）
  ↓
LLM 分析 → {"domain": "math", "confidence": 0.95}
  ↓
  confidence > 0.8  → 自动加载
  confidence > 0.5  → 推荐给用户确认
  否则              → 使用 general，可随时切换
```

---

## 第四章：Learner Profile —— 学习者画像

### 4.1 设计动机

同样是"教微积分"，对 12 岁和 30 岁的教法天差地别。必须让系统理解学习者是谁。

### 4.2 可调参数面板

```
┌─────────────────────────────────────────────────────────┐
│  🧑 学习风格设置（完全自定义）                            │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  1. 教学内容                                           │
│     ┌────抽象程度────┐  0 = 完全具象（多用比喻）           │
│     │ 具浅 ◉──────── 抽象 │  1 = 直接讲理论                │
│     └────────────────┘                                    │
│     ┌────比喻密度────┐                                    │
│     │ 少 ────────◉── 多 │                                    │
│     └────────────────┘                                    │
│     ┌────举例风格────┐                                    │
│     │ 生活化 ◉──────── 专业 │                              │
│     └────────────────┘                                    │
│                                                          │
│  2. 教学节奏                                           │
│     ┌────教学步速────┐                                    │
│     │ 慢 ──────◉────── 快 │                              │
│     └────────────────┘                                    │
│     ┌────单次时长────┐                                    │
│     │ 5分钟 ◉─────── 60分钟│                              │
│     └────────────────┘                                    │
│     ┌────重复偏好────┐                                    │
│     │ 少 ────◉──────── 多 │                              │
│     └────────────────┘                                    │
│                                                          │
│  3. 互动风格                                           │
│     ┌────反馈语气────┐                                    │
│     │ 鼓励 ◉───────── 直接 │                              │
│     └────────────────┘                                    │
│     ┌────错误处理────┐                                    │
│     │ 引导 ◉───────── 指出  │                              │
│     └────────────────┘                                    │
│     ┌────打断策略────┐                                    │
│     │ 随时 ◉───────── 听完  │                              │
│     └────────────────┘                                    │
│                                                          │
│  4. 评估方式                                           │
│     ┌────出题方式────┐                                    │
│     │ 游戏化 ◉──────── 传统  │                              │
│     └────────────────┘                                    │
│     ┌────容错率──────┐                                    │
│     │ 宽松 ◉───────── 严格  │                              │
│     └────────────────┘                                    │
│                                                          │
│  5. 界面偏好                                           │
│     ├─ 字体大小: [小 ■ 中 大 超大]                        │
│     ├─ 色彩模式: [柔和 ■ 标准 高对比]                       │
│     └─ □ 开启语音播报                                    │
├─────────────────────────────────────────────────────────┤
│  [保存]  [从预设导入 ▾]                                   │
│               ├─ 儿童友好                                │
│               ├─ 青少年探索                              │
│               ├─ 成人高效                                │
│               └─ 长辈关怀                                │
└─────────────────────────────────────────────────────────┘
```

### 4.3 数据模型

```json
{
  "learner_profile": {
    "content": {
      "abstraction_level": 0.3,     // 0=具象  1=抽象
      "analogy_density": 0.8,       // 0=少比喻  1=多比喻
      "example_style": 0.2          // 0=生活化  1=专业化
    },
    "pace": {
      "teaching_speed": 0.3,       // 0=慢  1=快
      "session_duration_min": 20,
      "repetition_preference": 0.6 // 0=不重复  1=多重复
    },
    "interaction": {
      "feedback_tone": 0.2,        // 0=鼓励  1=直接
      "error_handling": 0.2,       // 0=引导  1=指出
      "interrupt_policy": "anytime" // anytime | after_segment
    },
    "assessment": {
      "quiz_style": 0.2,           // 0=游戏化  1=传统
      "tolerance": 0.8,            // 0=全对  1=60%即可
      "review_frequency": 0.6
    },
    "ui": {
      "font_size": "medium",
      "color_scheme": "standard",
      "layout_density": "standard",
      "enable_tts": false
    }
  }
}
```

### 4.4 参数转 LLM Prompt 示例

```
"教学风格要求：
  - 尽量用比喻来解释，每个概念至少配一个生活化类比
  - 语速放慢，讲完一个点停顿确认
  - 反馈以鼓励为主，错误时先引导思考
  - 容错率高，答对60%就算通过
  - 推荐单次学习20分钟
  - 允许学生随时打断提问"
```

---

## 第五章：Domain × Learner 双维度合并机制

### 5.1 合并原则

```
Domain Profile（教什么）          Learner Profile（教给谁）
──────────────                   ──────────────
决定：                           决定：
- 知识图谱结构（DAG/网状/螺旋）      - 表达方式（比喻多少/抽象程度）
- 卡片模板（含公式/含代码/含音频）   - 节奏控制（快慢/重复/分段）
- 评估类型（选择题/编程题/发音题）   - 互动风格（鼓励/直接/引导/指出）
- 教学步骤流程                      - UI 呈现（字体/色彩/布局）
                                     - Prompt 语气覆盖

两维互不冲突，在 Prompt 中拼接。
```

### 5.2 教学引擎运行时决策树

```
教学引擎收到"教节点 X"

  1. 查 node.domain_id → 加载 Domain Profile
     → 确定：教学步骤流程、卡片模板、评估类型

  2. 查 user.learner_profile → 加载 Learner Profile
     → 确定：抽象程度、比喻密度、节奏、反馈风格

  3. 合并 Prompt：
     domain_prompt  +  learner_prompt  =  最终 Prompt

  4. 按合并后的步骤执行教学

  5. 学生消息进入分类器：
     ├── 提问 → LLM + 图谱上下文 → 回答
     ├── 要求延伸 → 查关联节点 → 判断掌握度 → 生成延伸内容
     └── 要求重讲 → 换角度/换类比

  6. 掌握度达标 → 解锁下一节点
     未达标    → 建议复习
```

### 5.3 组合示例

| Domain | Learner | 教学策略 | 对话风格 | 评估方式 |
|--------|---------|---------|---------|---------|
| math | child | 故事引入→游戏练习 | 苏格拉底式（温和） | 游戏化选择+填空 |
| math | adult | 概念→公式→应用 | 直接式 | 解题+证明 |
| programming | child | 拖拽积木→图形化 | 鼓励式 | 完成挑战 |
| programming | adult | Demo→动手→Debug | 教练式 | 代码审查+测试 |
| language | child | 儿歌→看图说话→游戏 | 鼓励式 | 跟读评分+游戏 |
| language | adult | 场景对话→语法→应用 | 支持式 | 听说读写四维 |

---

## 第六章：核心流程设计

### 6.1 完整用户旅程

```
┌────────────────────────────────────────────────────────────┐
│  【Step 1】 用户启动                                        │
│  "我想学 Python 深度学习"                                   │
│    或: 上传 zip + "以这些为主"                              │
│    或: 粘贴链接列表                                        │
├────────────────────────────────────────────────────────────┤
│  【Step 2】 内容采集 & 领域识别（并行）                       │
│  ├── LLM 分析 → domain = "programming"                    │
│  ├── 加载 Domain Profile                                  │
│  └── 内容收集：                                           │
│      ├── 用户资料 → 文本提取 → 分段                       │
│      └── AI 搜索 → 多源获取 → 交叉验证 → 置信度标记        │
├────────────────────────────────────────────────────────────┤
│  【Step 3】 知识提取                                       │
│  LLM 按 Domain Profile 的策略提取：                        │
│  ├── 知识点列表（标题/摘要/难度/类型）                      │
│  ├── 前置依赖关系                                          │
│  └── 关联关系                                              │
├────────────────────────────────────────────────────────────┤
│  【Step 4】 入库 & 审核                                    │
│  ├── 写入 Neo4j 知识图谱                                  │
│  ├── 生成大纲草案                                          │
│  ├── 展示给用户 → 可拖拽调整                               │
│  └── 用户确认 → 进入教学                                  │
├────────────────────────────────────────────────────────────┤
│  【Step 5】 逐节点教学（循环）                              │
│  ┌──────────────────────────────────────────────────┐     │
│  │  5.a 知识卡片展示（按领域选模板）                     │     │
│  │  5.b AI 按 Profile.pedagogy 步骤教学              │     │
│  │  5.c 学生可随时：                                  │     │
│  │      └─ 打字/语音提问 → AI 回答 + 可选延伸          │     │
│  │  5.d "已掌握" → 触发评估                           │     │
│  │  5.e 评估通过 → 更新掌握度 → 解锁下一个             │     │
│  │  5.f 图谱节点实时变色                              │     │
│  └──────────────────────────────────────────────────┘     │
├────────────────────────────────────────────────────────────┤
│  【Step 6】 全课程完成                                    │
│  ├── 生成学习报告（掌握度热力图 + 时间统计）               │
│  ├── 标记薄弱节点 → 间隔重复复习提醒                     │
│  └── 图谱全览（所有节点按掌握度着色）                      │
└────────────────────────────────────────────────────────────┘
```

### 6.2 内容生产流程（详细）

```
用户输入：
  A. "我想学 Python 深度学习"
  B. 上传 zip/pdf/md 文件 + "以这些为主，不足的你自己补"
  C. 粘贴链接列表

【Step 1: 意图解析】
  LLM 解析出：主题名称、范围边界、用户要求的深度级别

【Step 2: 内容收集】
  ├── 用户资料 → 文本提取 → 分段 + 清洗
  └── AI 搜索  → 并行调用多个搜索源
                → 抓取内容
                → 去重 + 交叉验证（多源一致则采纳，冲突则标注待审）

【Step 3: 知识提取】
  LLM 从所有资料中提取：
  - 知识点列表（每个包含：标题、摘要、关键概念、示例、参考链接）
  - 前置依赖关系（A 需要先学 B）
  - 难度分级（入门 / 进阶 / 高级）

【Step 4: 入库 + 用户审核】
  写入 Neo4j 知识图谱
  → 向用户展示大纲草案
  → 用户可拖拽调整顺序 / 标记删除 / 添加补充
  → 确认后进入教学阶段
```

### 6.3 大纲生成流程

```
知识节点集合（DAG）
    ↓
拓扑排序（保证依赖关系正确）
    ↓
按难度分层分组
    ↓
按 Domain Profile 的策略调整分组方式
    ↓
LLM 为每组生成自然语言标题和描述
    ↓
输出结构化大纲：
  - 模块 1: 基础概念（节点 A → B → C）
  - 模块 2: 核心原理（节点 D → E）
  - 模块 3: 实践进阶（节点 F → G → H）
    ↓
用户可手动调整 + 确认
```

---

## 第七章：上下文管理机制

### 7.1 设计动机

AI 教学对话的核心挑战是**在 Token 预算内保持上下文连贯性**。与普通聊天不同，教学场景要求：

- **长程记忆**：学生可能在第 20 轮提问"你刚才说的和之前的概念有什么关系"
- **断线恢复**：页面刷新或网络中断后，AI 要记得之前的教学进展
- **成本控制**：每次 API 调用都按 Token 计费，不能无限制传递全部历史
- **响应一致性**：相同内容（如出题、知识提取）不应重复调用 API 产生不同结果

### 7.2 四层缓存架构

```
┌──────────────────────────────────────────────────────────────┐
│                       LLM 请求层                              │
├──────────────────────────────────────────────────────────────┤
│                          │                                    │
│                  ┌───────▼────────┐                          │
│                  │  ❶ 进程级响应缓存  │                        │
│                  │  MD5(messages)  │ ← 出题/提取/检测等       │
│                  │  → response     │ ← 相同输入直接返回       │
│                  │  TTL: 1h       │ ← 节省 Token 和费用      │
│                  └───────┬────────┘                          │
│                          │ 未命中                              │
│                  ┌───────▼────────┐                          │
│                  │  ❷ Token 感知裁剪 │                          │
│                  │  trim_context() │ ← 保证不超上下文窗口       │
│                  │  - System 保留  │ ← 教学角色设定永不失      │
│                  │  - 最近 6 条保留 │ ← 当前交互连贯性          │
│                  │  - 早期丢弃     │ ← 超出 4096 token 部分    │
│                  └───────┬────────┘                          │
│                          │ 超过 12 轮                           │
│                  ┌───────▼────────┐                          │
│                  │  ❸ 摘要压缩      │                          │
│                  │  LLM 自行总结    │ ← "用 100 字概括已讨论内容" │
│                  │  + 保留最近 4 条 │ ← 关键信息不丢失           │
│                  └───────┬────────┘                          │
│                          │                                    │
│                  ┌───────▼────────┐                          │
│                  │  ❹ LiteLLM → API│ → DeepSeek / Ollama     │
│                  └────────────────┘                          │
├──────────────────────────────────────────────────────────────┤
│                      会话恢复层                                │
├──────────────────────────────────────────────────────────────┤
│                    ┌─── 快速路径 ───┐                          │
│                    │ Redis 缓存      │ ← 最近 20 条消息          │
│                    │ (2h 过期)      │ ← 断线秒级恢复            │
│                    └───────┬────────┘                          │
│                            │ Redis 未命中                      │
│                    ┌───────▼────────┐                          │
│                    │ PostgreSQL      │ ← 完整历史消息           │
│                    │ chat_messages   │ ← 百毫秒级恢复           │
│                    └────────────────┘                          │
├──────────────────────────────────────────────────────────────┤
│                      文件 / 配置缓存                            │
├──────────────────────────────────────────────────────────────┤
│  Domain Profile YAML  → 进程缓存 (5min 过期重新读盘)            │
│  LLM 响应缓存        → 进程缓存 dict (1h 过期)                 │
└──────────────────────────────────────────────────────────────┘
```

### 7.3 上下文裁剪算法

```python
def trim_context(messages, max_tokens=4096, reserve_recent=6):
    """
    裁剪对话历史，保证总 token 不超限。

    策略：
    1. System prompt（教学角色设定）始终保留
    2. 最近 reserve_recent 条消息始终保留（当前交互连贯性）
    3. 从最早的对话消息开始丢弃，直到 token 数达标
    4. Token 按中英文混合 1.5 字/token 估算
    """
```

| 场景 | 裁剪行为 |
|------|---------|
| 总 Token < 4096 | 全部保留，不裁剪 |
| 对话 > 12 轮 | 触发摘要压缩（见 7.4） |
| 早期消息被丢弃 | 用户只记得最近的讨论，AI 无感知 |

### 7.4 长对话摘要压缩

当单轮对话超过 **12 条** 消息时，自动触发摘要机制：

```
压缩前：【用户1, AI1, 用户2, AI2, ..., 用户12, AI12】 ← 24 条
                                              ↓
步骤 1：AI 对前 10 条对话生成 100 字以内的摘要
步骤 2：保留最近 4 条消息
步骤 3：构建新上下文 = 【摘要(旧)】 + 【最近 4 条】
```

摘要内容由 LLM 自行总结，包含：
- 已讨论的概念范围
- 学生的掌握程度判断
- 仍有疑问的知识点

### 7.5 断线重连恢复流程

```
前端在 sessionStorage 中保存 session_id

WebSocket 连接时：
  1. 前端传 session_id（如果有）
  2. 服务端尝试从 Redis 恢复上下文（快速路径，< 5ms）
  3. Redis 未命中 → 从 PostgreSQL 恢复（慢路径，< 100ms）
  4. 无 session_id → 创建全新会话

恢复成功后，AI 继续教学，学生不会感知到断线
```

### 7.6 缓存策略汇总

| 缓存对象 | 存储位置 | 过期时间 | 失效条件 |
|---------|---------|---------|---------|
| **LLM 响应缓存** | 进程内存 dict | 1 小时 | 手动清空/超时 |
| **Domain Profile** | 进程内存 dict | 5 分钟 | 重新读盘 |
| **会话上下文** | Redis | 2 小时 | 超时自动过期 |
| **对话历史** | PostgreSQL | 永久 | 用户删除路径 |

### 7.7 降级策略

| 组件不可用 | 影响 | 降级行为 |
|-----------|------|---------|
| Redis 不可用 | 会话恢复变慢 | 降级为 PostgreSQL 恢复，不影响主流程 |
| 进程缓存清空 | 响应变慢 | 重新调用 API，不影响正确性 |
| PostgreSQL 不可用 | 历史丢失 | WebSocket 会话中仍然正常对话，但断线后无法恢复 |
| Domain Profile 文件缺失 | 教学风格降级 | 自动 fallback 到 general 配置 |

---

## 第八章：知识卡片系统

### 8.1 卡片组件树

```
KnowledgeCard（容器，按 domain_id 选模板）
  ├── CardHeader（标题 + 难度 + 领域标签）
  │
  ├── CardBody
  │   ├── ConceptSection      # 概念解释（Markdown）
  │   ├── LatexSection        # 公式（仅 math/physics）
  │   ├── CodeSection         # 代码+运行按钮（仅 programming）
  │   ├── AudioSection        # 音频播放（仅 language/music）
  │   ├── TimelineSection     # 时间线（仅 history）
  │   ├── ExampleSection      # 示例/类比
  │   └── RelatedSection      # 关联节点链接
  │
  └── CardFooter
      ├── PrevButton / NextButton
      ├── QuizButton
      ├── AskButton（语音/文字）
      └── ProgressIndicator（本节点掌握度）
```

### 8.2 内容格式约定

```
内容存储格式：Markdown（LLM 输出）
扩展语法：
  $$...$$           → KaTeX 渲染（数学领域）
  ```python ... ``` → Monaco Editor（编程领域）
  [audio:pronunciation] → 音频播放（语言领域）
  [timeline:JSON]   → 时间线组件（历史领域）

前端按 domain_id 决定哪些扩展语法被启用
```

### 8.3 多平台渲染策略

| 平台 | 方案 |
|------|------|
| **Web** | React 组件，浏览器直接渲染 |
| **Tauri 桌面** | 同一套 React，Tauri WebView 加载 |
| **离线导出** | React → 构建时预渲染 → 静态 HTML |
| **第三方嵌入** | Web Component 封装 `<edu-card node-id="xxx">` |

---

## 第九章：语音交互系统

### 9.1 双模工作流

```
┌──────────────┐          ┌──────────────┐
│  文字输入     │─────────→│              │
└──────────────┘          │   教学引擎    │
                          │   (LLM)      │
┌──────────────┐          │              │
│  语音输入     │──ASR──→│              │
└──────────────┘          └──────┬───────┘
                                 │
                          ┌──────▼───────┐
                          │   输出       │
                          ├──────────────┤
                          │  文字渲染     │
                          │  TTS 语音输出  │
                          └──────────────┘
```

### 9.2 技术选型

| 功能 | 首选方案 | 备选方案 | 部署方式 |
|------|---------|---------|---------|
| **ASR** | faster-whisper (large-v3) | Whisper API | 本地离线 |
| **TTS** | Kokoro (ONNX) | Edge-TTS / ChatTTS | 本地离线 |
| **VAD** | Silero VAD | WebRTC VAD | 本地 |

### 9.3 语音 UI 规范

```
麦克风按钮 → 点击录音 → 波形动画 → VAD 静音检测自动停止
→ 转写文字展示 → 发送 → AI 回答 → TTS 播报

设置：
  □ 自动播报回答
  □ 仅文字回答
  ☑ 说话时自动暂停卡片翻页
```

---

## 第十章：评估与反馈系统

### 10.1 多维度评估

```
每个节点可按域配置题型：

general:    选择题 + 简答题
math:       选择题 + 填空题 + 分步解题
programming:选择题 + 代码编译测试 + 代码审查
language:   选择题 + 发音评分(ASR) + 造句评分
history:    选择题 + 论述题 + 因果链连接题
music:      听力题 + 演奏评估

mastery = f(quiz_correct_rate, review_count, time_spent)
        使用 遗忘曲线 + 间隔重复 加权
```

### 10.2 进度追踪

```
节点级：未开始 / 学习中 / 已完成
模块级：已完成节点数 / 总节点数
总览：加权（层级越高权重略高）

图谱可视化：
  节点颜色 = 掌握度
  红(0-30%) → 橙(30-60%) → 黄(60-80%) → 绿(80-100%)
```

### 10.3 间隔重复

```
节点首次学会后，按策略安排复习：
  [1天后] → [7天后] → [30天后] → [90天后]

每次复习重新计算 mastery
低于阈值 → 标记为 "需复习"，加入待办
```

---

## 第十一章：技术选型

### 11.1 选型总表

| 层级 | 技术 | 版本 | 选型理由 |
|------|------|------|----------|
| **前端框架** | React 18 + TypeScript | ≥18 | 生态最强，可嵌入 Tauri |
| **UI 组件** | Tailwind CSS + shadcn/ui | — | 快速开发，可定制主题 |
| **知识卡片** | React 组件（自研多模板） | — | Markdown 内容 + 领域模板切换 |
| **KG 可视化** | vis-network | ≥9 | 力导向图最成熟 |
| **代码编辑器** | Monaco Editor | — | 编程领域卡片（按需加载） |
| **LaTeX 渲染** | KaTeX | — | 数学领域卡片 |
| **语音 ASR** | faster-whisper | — | 开源、多语言、本地运行 |
| **语音 TTS** | Kokoro / Edge-TTS | — | 低延迟，中文效果好 |
| **后端框架** | Python FastAPI | ≥0.111 | AI 生态最佳，内置 WebSocket |
| **WS 通信** | WebSocket + HTTP REST | — | 对话实时 + CRUD |
| **主数据库** | PostgreSQL 15+ | ≥15 | 稳定性/扩展性 |
| **知识图谱** | Neo4j 5 | ≥5 | 图查询核心能力 |
| **向量搜索** | pgvector（PG 插件） | — | 少一个运维组件 |
| **缓存/会话** | Redis 7 | — | 对话上下文 |
| **模型适配** | LiteLLM | — | 统一接口屏蔽 Provider |
| **文档解析** | Unstructured.io | — | PDF/Word/HTML 统一解析 |
| **默认 LLM** | DeepSeek API（公开 API） | — | 默认使用，零部署成本 |
| **本地 LLM（可选）** | Ollama + llama.cpp | — | 按需开启，替代公开 API |
| **MCP 客户端** | MCP Python SDK | — | 标准协议 |
| **桌面端** | Tauri v2 | ≥2.0 | 比 Electron 轻 10x |
| **部署** | Docker Compose | — | 一键启动全栈 |

### 11.2 AI 模型配置示例

```json
{
  "models": {
    "teaching": {
      "provider": "openai-compatible",
      "model": "deepseek-v4-flash",
      "api_key": "sk-your-deepseek-api-key",
      "base_url": "https://api.deepseek.com/v1",
      "description": "教学问答默认使用 DeepSeek 公开 API"
    },
    "content_gen": {
      "provider": "openai-compatible",
      "model": "deepseek-v4-flash",
      "api_key": "sk-your-deepseek-api-key",
      "base_url": "https://api.deepseek.com/v1",
      "description": "内容提取复用同一 API"
    },
    "asr": {
      "provider": "local",
      "model": "whisper-large-v3"
    },
    "tts": {
      "provider": "local",
      "model": "kokoro"
    }
  },
  "mcp_servers": [
    {
      "name": "web-search",
      "transport": "stdio",
      "command": "npx",
      "args": ["-y", "@mcp-server/web-search"]
    },
    {
      "name": "filesystem",
      "transport": "stdio",
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "./data"]
    }
  ]
}
```

---

## 第十二章：数据模型

### 12.1 知识图谱（Neo4j CQL）

```cypher
CREATE CONSTRAINT FOR (n:KnowledgeNode) REQUIRE n.id IS UNIQUE;

(:KnowledgeNode {
  id: UUID,
  title: String,
  summary: String,
  content: String,           // Markdown
  difficulty: String,        // intro | intermediate | advanced
  domain_id: String,         // 所属领域
  node_type: String,         // concept | skill | fact | vocabulary | procedure
  examples: [String],
  code_snippets: [String],
  quiz_questions: JSON,      // [{type, question, options?, answer}]
  ref_links: [String],
  source: String,            // user | ai_search | hybrid
  confidence: Float          // AI 搜索来源的置信度
})

// 关系类型
(:KnowledgeNode)-[:PREREQUISITE]->(:KnowledgeNode)    // 前置依赖
(:KnowledgeNode)-[:RELATED {strength: Int}]->(:KnowledgeNode)  // 关联
(:KnowledgeNode)-[:EXTENDS]->(:KnowledgeNode)          // 延伸关系
(:KnowledgeNode)-[:PART_OF]->(:Module {name, order})   // 所属模块
```

### 12.2 用户数据（PostgreSQL DDL）

```sql
-- 用户表
CREATE TABLE users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  learner_profile JSONB DEFAULT '{}',
  model_config JSONB DEFAULT '{}',
  created_at TIMESTAMP DEFAULT NOW()
);

-- 学习路径
CREATE TABLE learning_paths (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id),
  topic TEXT NOT NULL,
  domain_id TEXT NOT NULL,
  syllabus JSONB NOT NULL,
  status TEXT DEFAULT 'active',
  learner_profile_override JSONB,  -- 本路径的学习者画像覆盖
  created_at TIMESTAMP DEFAULT NOW(),
  completed_at TIMESTAMP
);

-- 节点学习进度
CREATE TABLE node_progress (
  user_id UUID NOT NULL,
  path_id UUID NOT NULL,
  node_id TEXT NOT NULL,
  status TEXT DEFAULT 'not_started',
  mastery REAL DEFAULT 0.0,
  quiz_attempts JSONB[] DEFAULT '{}',
  review_count INT DEFAULT 0,
  first_learned TIMESTAMP,
  last_reviewed TIMESTAMP,
  next_review TIMESTAMP,
  PRIMARY KEY (user_id, path_id, node_id)
);

-- 对话历史
CREATE TABLE learning_sessions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL,
  path_id UUID NOT NULL,
  node_id TEXT NOT NULL,
  started_at TIMESTAMP DEFAULT NOW(),
  ended_at TIMESTAMP,
  message_count INT DEFAULT 0,
  messages JSONB[] DEFAULT '{}',
  user_rating INT
);

-- 掌握度快照（趋势分析用）
CREATE TABLE mastery_snapshots (
  user_id UUID NOT NULL,
  path_id UUID NOT NULL,
  snapshot JSONB NOT NULL,
  recorded_at TIMESTAMP DEFAULT NOW()
);

-- 索引
CREATE INDEX idx_np_user ON node_progress(user_id);
CREATE INDEX idx_np_review ON node_progress(next_review) WHERE next_review IS NOT NULL;
CREATE INDEX idx_ms_path ON mastery_snapshots(path_id, recorded_at);
```

---

## 第十三章：MCP 集成方案

### 13.1 MCP 在系统中的作用

```
教学引擎 (LLM)
    │
    ├── MCP Server: web-search
    │   → 学生问 "2024年有什么新进展"
    │   → AI 搜索最新资料并引用
    │
    ├── MCP Server: knowledge-graph
    │   → 查询关联节点
    │   → 用于回答 "这和之前学的XX有什么关系"
    │
    ├── MCP Server: filesystem
    │   → 读取用户上传的笔记
    │   → 写学习笔记到指定目录
    │
    └── MCP Server: 用户自定义
        → 可安装任意 MCP 扩展
```

### 13.2 内置 MCP Server

| Server 名 | 功能 | 实现方式 |
|-----------|------|---------|
| `core-search` | 多源搜索 + 抓取 | Python 实现，内部调用 SearXNG / Web 搜索 |
| `core-knowledge` | 查询/写入知识图谱 | 封装 Neo4j 驱动为 MCP 工具 |
| `core-filesystem` | 安全受限文件读写 | 限定在 data/ 目录下 |

---

## 第十四章：可移植性与部署方案

### 14.1 部署形态矩阵

| 形态 | 用户数 | 数据库 | AI 模型 | 启动复杂度 |
|------|--------|--------|---------|----------|
| **单机 Lite**（Tauri + SQLite + 本地 LLM） | 1 | SQLite + 嵌入式图 | Ollama 本地 | 低 |
| **单机 Pro**（Tauri + Docker 后端） | 1~3 | PG + Neo4j | 本地/远程 | 中 |
| **服务器**（Docker Compose） | 多用户 | PG + Neo4j + Redis | 远程 API | 中高 |
| **K8s 平台化** | 企业级 | 集群化 | 多模型池 | 高 |

### 14.2 开源仓库结构

```
edumind/
├── packages/
│   ├── core/                 # 核心业务逻辑（Python）
│   │   ├── content_pipeline/
│   │   ├── syllabus/
│   │   ├── teaching_engine/
│   │   ├── assessment/
│   │   ├── knowledge_graph/
│   │   ├── search_orchestrator/
│   │   ├── voice_service/
│   │   └── config_center/    # Domain + Learner Profile 管理
│   ├── web/                  # React 前端
│   │   ├── src/
│   │   │   ├── components/
│   │   │   │   ├── KnowledgeCard/    # 多模板卡片
│   │   │   │   ├── KnowledgeGraph/   # 图谱可视化
│   │   │   │   ├── ChatInterface/
│   │   │   │   ├── VoiceControl/
│   │   │   │   └── LearnerSettings/  # 学习者画像面板
│   │   │   └── pages/
│   │   └── package.json
│   ├── desktop/              # Tauri 桌面壳
│   ├── cli/                  # CLI 工具
│   └── shared/               # 共享类型/协议
├── domain_profiles/           # 内置领域配置
├── learner_profiles/          # 内置学习者预设
├── docs/
├── docker-compose.yml
└── README.md
```

---

## 第十五章：实施路线图

### Phase 0：MVP（8-10 周）

| 里程碑 | 周次 | 交付物 | 验收标准 |
|--------|------|--------|---------|
| **P0.1 基础设施** | W1-2 | FastAPI 骨架 + PG + Neo4j + Redis，Docker Compose | `docker compose up` 可启动 |
| **P0.2 内容管道** | W3-4 | 用户上传 → LLM 提取 → 入库，3 个内置 Domain Profile | 上传教程 → 图谱有节点有依赖 |
| **P0.3 教学引擎** | W5-6 | 知识卡片 + 文字对话，按 domain_id 切换模板 | 可逐节点学习，可打字提问 |
| **P0.4 评估+图谱** | W7-8 | Quiz 生成 + 掌握度 + 进度追踪 + KG 可视化 | 完成节点 → 出题 → 图谱变色 |
| **P0.5 整合打磨** | W9-10 | 大纲生成 + 用户审核 + 全流程闭环 | 从开始到完成的完整体验 |

**MVP 验证标准**：
> 用户说"我要学 Python 深度学习" → 系统自动生成大纲 → 逐节点教学 → 问答 → 评估 → 图谱可视化，全过程无需离开系统

### Phase 1：V1.0（8-12 周）

| 功能 | 时间 |
|------|------|
| AI 搜索编排 + 交叉验证 | 3 周 |
| 语音交互（ASR + TTS） | 3 周 |
| Learner Profile 系统（含参数面板 UI） | 2 周 |
| 内置 Profile 扩展至 7 个 | 2 周 |
| Tauri 桌面打包 | 2 周 |

### Phase 2：V2.0（持续）

- 间隔重复复习
- Domain Profile 市场（社区贡献）
- Web Component 发布（嵌入任意网站）
- 学习报告导出

### Phase 3：平台化

- 多用户支持
- 多人协作学习
- 学习内容市场

---

## 第十六章：开源策略

| 维度 | 策略 |
|------|------|
| **许可证** | AGPL v3（核心开源）+ 商业许可（企业平台版） |
| **仓库** | GitHub monorepo（edumind/edumind） |
| **开发语言** | Python（后端）+ TypeScript（前端） |
| **文档语言** | 中文主文档 + 英文 API 文档 |
| **贡献指南** | CONTRIBUTING.md + Docker 开发环境 |
| **发布策略** | Semantic Versioning + Changelog |

---

## 第十七章：风险登记表

| 风险 | 可能性 | 影响 | 缓解措施 |
|------|--------|------|---------|
| LLM 生成知识内容有事实错误 | 高 | 中 | 多源交叉验证 + 置信度标记 + 用户可编辑 |
| 本地 LLM 教学效果不如预期 | 中 | 中 | 模型可自由切换远程 API |
| 语音 ASR 延迟影响体验 | 中 | 低 | Whisper 本地运行，延迟可控 |
| 知识图谱规模增长性能下降 | 低 | 高 | Neo4j 索引优化，后期可集群 |
| 开源后质量被 PR 稀释 | 低 | 中 | 核心模块由维护者审查 |
| Domain Profile 覆盖不全 | 中 | 低 | general fallback + 用户可自定义 |

---

> **本方案书版本记录**：V2.0-FINAL | 2025  
> **涵盖所有讨论点**：混合内容源 | 语音交互 | Domain Profile | Learner Profile | 双维度合并 | 知识图谱 | 评估体系 | MCP 集成 | 跨平台 | 开源策略
