import axios from 'axios';

const API_BASE = import.meta.env.VITE_API_URL || '/api/v1';
const WS_BASE = import.meta.env.VITE_WS_URL || `${location.protocol === 'https:' ? 'wss:' : 'ws:'}//${location.host}/api/v1`;

export const api = axios.create({
  baseURL: API_BASE,
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('token');
      window.location.href = '/login';
    }
    return Promise.reject(err);
  }
);

// ── WebSocket ──

let ws: WebSocket | null = null;
let wsReadyPromise: Promise<void> | null = null;
let wsReadyResolve: (() => void) | null = null;

export async function connectChatWS(
  onChunk: (text: string) => void,
  onDone: () => void,
  onError: (msg: string) => void
): Promise<void> {
  // 关闭旧连接
  ws?.close();
  ws = null;

  // 创建新的 Promise，连接成功后 resolve
  wsReadyPromise = new Promise((resolve) => {
    wsReadyResolve = resolve;
  });

  const token = localStorage.getItem('token');
  ws = new WebSocket(`${WS_BASE}/ws/chat?token=${token}`);

  ws.onopen = () => {
    console.log('🔗 WebSocket 已连接');
    wsReadyResolve?.();
  };

  ws.onmessage = (event) => {
    let data;
    try { data = JSON.parse(event.data); } catch { return; }
    switch (data.type) {
      case 'connected':
      case 'session_ready':
        break;
      case 'teaching_chunk':
        onChunk(data.content);
        break;
      case 'teaching_done':
        onDone();
        break;
      case 'error':
        onError(data.message);
        break;
      case 'audio_reply':
        playAudioReply(data.audio_data);
        break;
      case 'extension':
        onChunk(`\n\n--- 延伸 ---\n${data.content}`);
        break;
    }
  };

  ws.onclose = () => console.log('🔌 WebSocket 已断开');
  ws.onerror = () => {
    onError('连接错误');
    wsReadyResolve?.();
  };

  return wsReadyPromise;
}

export function sendChatMessage(nodeId: string, content: string, pathId?: string) {
  if (ws?.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ type: 'message', node_id: nodeId, content, path_id: pathId }));
  }
}

export function sendAudioMessage(base64Data: string, nodeId: string, pathId?: string) {
  if (ws?.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ type: 'audio', audio_data: base64Data, node_id: nodeId, path_id: pathId }));
  }
}

export function sendExtensionRequest(nodeId: string, direction = 'related') {
  if (ws?.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ type: 'extend', node_id: nodeId, direction }));
  }
}

export function playAudioReply(base64Data: string) {
  try {
    const binary = atob(base64Data);
    const bytes = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
    // 浏览器自动识别 WAV/MP3 格式，无需指定 MIME
    const blob = new Blob([bytes]);
    const url = URL.createObjectURL(blob);
    const audio = new Audio(url);
    audio.onended = () => URL.revokeObjectURL(url);
    audio.play().catch(() => {});
  } catch (_) { /* 音频播放失败不影响主功能 */ }
}

export function closeChatWS() {
  ws?.close();
  ws = null;
  wsReadyPromise = null;
  wsReadyResolve = null;
}
