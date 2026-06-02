# MVP 前端架构

> React 18 + TypeScript + Tailwind CSS + Zustand

---

## 一、页面路由

```typescript
// react-router-dom v6 路由结构

/ → Landing / Login
/login → 登录
/register → 注册
/dashboard → 我的学习（路径列表 + 进度总览）
/learn/:pathId → 学习页面（知识卡片 + 对话 + 图谱）
/learn/:pathId/syllabus → 大纲编辑（拖拽调整）
/settings → 用户设置（模型配置）
```

---

## 二、组件树

```
App
├── AuthLayout
│   ├── LoginPage
│   └── RegisterPage
│
├── DashboardLayout (需要登录)
│   ├── Sidebar (路径列表 + 进度总览)
│   ├── DashboardPage
│   │   ├── PathCreateModal
│   │   │   ├── TopicInput (文本输入)
│   │   │   └── FileUploader (文件上传 + 进度条)
│   │   ├── PathCard (卡片列表)
│   │   │   ├── PathProgressBar
│   │   │   └── MasteryBadge
│   │   └── EmptyState (首次使用引导)
│   │
│   ├── LearnPage (核心页面)
│   │   ├── ProgressSidebar (左侧：模块+节点列表)
│   │   │   ├── ModuleAccordion
│   │   │   │   └── NodeItem (状态图标 + 标题 + 掌握度)
│   │   │   └── OverallProgress
│   │   │
│   │   ├── MainContent (中间主区域)
│   │   │   ├── KnowledgeCardContainer
│   │   │   │   ├── CardHeader (标题 + 难度标签)
│   │   │   │   ├── CardBody
│   │   │   │   │   ├── ConceptSection (Markdown)
│   │   │   │   │   ├── LatexSection (KaTeX, domain=math)
│   │   │   │   │   ├── CodeSection (Monaco, domain=programming)
│   │   │   │   │   ├── ExampleSection
│   │   │   │   │   └── RelatedSection (关联节点链接)
│   │   │   │   └── CardFooter
│   │   │   │       ├── PrevButton / NextButton
│   │   │   │       ├── QuizButton
│   │   │   │       ├── AskButton
│   │   │   │       └── MasteryIndicator
│   │   │   │
│   │   │   ├── ChatPanel (教学对话)
│   │   │   │   ├── MessageList
│   │   │   │   │   ├── UserMessage
│   │   │   │   │   ├── AIMessage (Markdown 渲染)
│   │   │   │   │   └── SystemMessage (提示/进度)
│   │   │   │   ├── MessageInput (文字)
│   │   │   │   └── TypingIndicator
│   │   │   │
│   │   │   └── QuizOverlay (弹窗)
│   │   │       ├── QuestionCard
│   │   │       │   ├── QuestionText
│   │   │       │   └── OptionList (单选)
│   │   │       ├── ResultCard (提交后)
│   │   │       │   ├── ScoreDisplay
│   │   │       │   └── AnswerReview
│   │   │       └── QuizProgress (1/N)
│   │   │
│   │   └── GraphPanel (右侧：知识图谱)
│   │       ├── GraphCanvas (vis-network)
│   │       │   ├── 力导向图
│   │       │   ├── 节点颜色 = 状态+掌握度
│   │       │   └── 双击 → 切换节点
│   │       ├── GraphLegend
│   │       └── GraphControls (缩放/重置/全屏)
│   │
│   └── SyllabusPage
│       ├── ModuleList (可拖拽排序)
│       │   ├── ModuleHeader (名称 + 展开折叠)
│       │   └── NodeSortableList (内部节点可拖拽)
│       └── ConfirmButton → 确认大纲后进入学习
│
└── SettingsPage
    ├── ModelConfigForm
    ├── DomainSettings
    └── AboutSection
```

---

## 三、状态管理（Zustand）

```typescript
// stores/useAuthStore.ts
interface AuthState {
  user: User | null;
  token: string | null;
  login: (email: string, password: string) => Promise<void>;
  register: (name: string, email: string, password: string) => Promise<void>;
  logout: () => void;
  loadUser: () => Promise<void>;
}

// stores/useLearningStore.ts
interface LearningState {
  currentPath: LearningPath | null;
  paths: LearningPath[];
  currentNode: KnowledgeNode | null;
  nodeProgress: NodeProgress | null;
  graphData: GraphData | null;
  chatMessages: ChatMessage[];

  // Actions
  fetchPaths: () => Promise<void>;
  createPath: (topic: string, domainId: string) => Promise<void>;
  loadNode: (nodeId: string) => Promise<void>;
  sendMessage: (content: string) => Promise<void>;
  completeNode: () => Promise<void>;
  requestQuiz: () => Promise<void>;
  submitQuiz: (answers: Answer[]) => Promise<QuizResult>;
  requestExtension: (direction: string) => Promise<void>;
}

// stores/useQuizStore.ts
interface QuizState {
  isOpen: boolean;
  questions: Question[];
  currentIndex: number;
  answers: Map<string, string>;
  result: QuizResult | null;
  open: () => void;
  close: () => void;
  selectAnswer: (questionId: string, option: string) => void;
  submit: () => Promise<void>;
}
```

---

## 四、WebSocket 通信

```typescript
// hooks/useChatSocket.ts
// 封装 WebSocket 连接管理

interface UseChatSocketOptions {
  pathId: string;
  nodeId: string;
  onMessage: (msg: ChatMessage) => void;
  onChunk: (text: string) => void;        // 流式增量
  onQuizRequest: (quiz: Quiz) => void;    // 当 AI 主动出题
  onError: (err: string) => void;
}

// 自动重连（指数退避）
// 连接生命周期：连接 → 认证 → 开始会话 → 消息交互 → 关闭
```

---

## 五、API 服务层

```typescript
// services/api.ts
// axios 实例 + JWT 拦截器

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1',
  timeout: 30000,
});

// 请求拦截器：自动注入 Token
api.interceptors.request.use((config) => {
  const token = useAuthStore.getState().token;
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// 响应拦截器：401 自动登出
api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      useAuthStore.getState().logout();
    }
    return Promise.reject(err);
  }
);

// API 函数（按模块导出）
export const authApi = { register, login, getMe };
export const pathApi = { create, list, get, update, remove };
export const nodeApi = { get, getGraph };
export const progressApi = { getProgress, startNode, completeNode };
export const quizApi = { generate, submit };
```

---

## 六、知识卡片组件设计

```typescript
// components/KnowledgeCard/KnowledgeCard.tsx

interface KnowledgeCardProps {
  node: KnowledgeNode;
  domainId: string;
  mastery: number;
  onPrev: () => void;
  onNext: () => void;
  onQuiz: () => void;
}

// 核心渲染逻辑
function KnowledgeCard(props: KnowledgeCardProps) {
  const { node, domainId } = props;

  // 按 domain_id 选择卡片模板
  const CardTemplate = CARD_TEMPLATES[domainId] || DefaultCard;

  return (
    <div className="card">
      <CardHeader title={node.title} difficulty={node.difficulty} />
      <CardBody>
        <CardTemplate content={node.content} examples={node.examples} code={node.codeSnippets} />
        <RelatedSection nodes={node.relatedNodes} />
      </CardBody>
      <CardFooter
        mastery={mastery}
        onPrev={onPrev}
        onNext={onNext}
        onQuiz={onQuiz}
      />
    </div>
  );
}

// 模板注册表
const CARD_TEMPLATES: Record<string, React.ComponentType<any>> = {
  math: MathCard,           // 含 KaTeX 渲染
  programming: ProgrammingCard, // 含 Monaco Editor
  general: DefaultCard,
};
```

---

## 七、知识图谱组件

```typescript
// components/KnowledgeGraph/KnowledgeGraph.tsx

interface GraphProps {
  nodes: GraphNode[];
  edges: GraphEdge[];
  currentNodeId: string;
  onNodeClick: (nodeId: string) => void;
}

// vis-network 配置要点：
const options = {
  nodes: {
    shape: 'dot',
    size: 20,
    font: { size: 14, color: '#333' },
    // 颜色由掌握度决定：
    // mastery >= 0.8 → green
    // mastery >= 0.4 → orange
    // mastery < 0.4  → red
    // not_started    → gray
  },
  edges: {
    arrows: { to: { enabled: true, scaleFactor: 0.5 } },
    // PREREQUISITE → 实线
    // RELATED     → 虚线
    // EXTENDS     → 点线
  },
  physics: {
    solver: 'forceAtlas2Based',
    stabilization: { iterations: 100 },
  },
  interaction: {
    hover: true,
    zoomView: true,
    dragView: true,
  },
};
```

---

## 八、依赖清单（package.json）

```json
{
  "dependencies": {
    "react": "^18.3",
    "react-dom": "^18.3",
    "react-router-dom": "^6.26",
    "axios": "^1.7",
    "zustand": "^4.5",
    "vis-network": "^9.1",
    "vis-data": "^7.1",
    "react-markdown": "^9.0",
    "react-syntax-highlighter": "^15.5",
    "katex": "^0.16",
    "monaco-editor": "^0.50",
    "@dnd-kit/core": "^6.1",
    "@dnd-kit/sortable": "^8.0",
    "lucide-react": "^0.441",
    "clsx": "^2.1",
    "tailwind-merge": "^2.5"
  },
  "devDependencies": {
    "typescript": "^5.5",
    "vite": "^5.4",
    "tailwindcss": "^3.4",
    "postcss": "^8.4",
    "autoprefixer": "^10.4",
    "@types/react": "^18.3",
    "eslint": "^9.0"
  }
}
```
