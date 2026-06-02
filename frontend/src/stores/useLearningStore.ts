import { create } from 'zustand';

interface KnowledgeNode {
  id: string;
  title: string;
  summary: string;
  content: string;
  difficulty: string;
  domain_id: string;
  node_type: string;
  prerequisites: { id: string; title: string }[];
  related_nodes: { id: string; title: string }[];
}

interface NodeProgress {
  node_id: string;
  status: string;
  mastery: number;
  attempt_count: number;
}

interface Module {
  module_name: string;
  order: number;
  node_ids: string[];
  nodes: { id: string; status: string; mastery: number }[];
}

interface LearningPath {
  id: string;
  topic: string;
  domain_id: string;
  status: string;
  syllabus: Module[];
  created_at: string;
  node_count?: number;
  completed_count?: number;
  progress?: number;
}

interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  created_at?: string;
}

interface LearningState {
  // 数据
  currentPath: LearningPath | null;
  paths: LearningPath[];
  currentNode: KnowledgeNode | null;
  nodeProgress: NodeProgress | null;
  chatMessages: ChatMessage[];
  isChatLoading: boolean;

  // Actions
  setPaths: (paths: LearningPath[]) => void;
  setCurrentPath: (path: LearningPath) => void;
  setCurrentNode: (node: KnowledgeNode) => void;
  setNodeProgress: (progress: NodeProgress) => void;
  addChatMessage: (msg: ChatMessage) => void;
  appendChatChunk: (text: string) => void;
  setChatLoading: (v: boolean) => void;
  clearChat: () => void;
}

export const useLearningStore = create<LearningState>((set) => ({
  currentPath: null,
  paths: [],
  currentNode: null,
  nodeProgress: null,
  chatMessages: [],
  isChatLoading: false,

  setPaths: (paths) => set({ paths }),
  setCurrentPath: (path) => set({ currentPath: path }),
  setCurrentNode: (node) => set({ currentNode: node }),
  setNodeProgress: (progress) => set({ nodeProgress: progress }),
  addChatMessage: (msg) =>
    set((s) => ({ chatMessages: [...s.chatMessages, msg] })),
  appendChatChunk: (text) =>
    set((s) => {
      const msgs = [...s.chatMessages];
      const last = msgs[msgs.length - 1];
      if (last && last.role === 'assistant') {
        msgs[msgs.length - 1] = { ...last, content: last.content + text };
      } else {
        msgs.push({ id: `chunk-${Date.now()}`, role: 'assistant', content: text });
      }
      return { chatMessages: msgs };
    }),
  setChatLoading: (v) => set({ isChatLoading: v }),
  clearChat: () => set({ chatMessages: [] }),
}));
