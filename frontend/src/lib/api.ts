import type {
  AgentRunResponse,
  AnalyticsSummary,
  AppNotification,
  ChatResponse,
  Citation,
  Conversation,
  Doc,
  GraphBuildResult,
  GraphData,
  Memory,
  Message,
  RecalledMemory,
  SearchResult,
  TokenPair,
  User,
  Workspace,
} from "./types";

const BASE = (import.meta as any).env?.VITE_API_BASE || "/api/v1";
const TOKEN_KEY = "cortex_token";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}
export function setToken(token: string) {
  localStorage.setItem(TOKEN_KEY, token);
}
export function clearToken() {
  localStorage.removeItem(TOKEN_KEY);
}

function authHeaders(): Record<string, string> {
  const t = getToken();
  return t ? { Authorization: `Bearer ${t}` } : {};
}

async function request<T>(path: string, opts: RequestInit = {}): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    ...opts,
    headers: {
      ...(opts.body && !(opts.body instanceof FormData)
        ? { "Content-Type": "application/json" }
        : {}),
      ...authHeaders(),
      ...(opts.headers || {}),
    },
  });
  if (!res.ok) {
    let detail = `${res.status} ${res.statusText}`;
    try {
      const body = await res.json();
      if (body?.detail) detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
    } catch {
      /* keep status text */
    }
    throw new ApiError(res.status, detail);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export const api = {
  // ---- auth ----
  register(body: {
    email: string;
    password: string;
    full_name: string;
    organization_name: string;
  }) {
    return request<User>("/auth/register", {
      method: "POST",
      body: JSON.stringify(body),
    });
  },
  login(email: string, password: string) {
    return request<TokenPair>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
  },
  me() {
    return request<User>("/users/me");
  },

  // ---- workspaces ----
  listWorkspaces() {
    return request<Workspace[]>("/workspaces");
  },
  createWorkspace(name: string) {
    return request<Workspace>("/workspaces", {
      method: "POST",
      body: JSON.stringify({ name }),
    });
  },

  // ---- documents ----
  listDocuments(ws: string) {
    return request<Doc[]>(`/workspaces/${ws}/documents`);
  },
  uploadDocument(ws: string, file: File) {
    const form = new FormData();
    form.append("file", file);
    return request<Doc>(`/workspaces/${ws}/documents`, {
      method: "POST",
      body: form,
    });
  },
  deleteDocument(id: string) {
    return request<void>(`/documents/${id}`, { method: "DELETE" });
  },
  search(ws: string, query: string, limit = 5) {
    return request<SearchResult[]>(`/workspaces/${ws}/search`, {
      method: "POST",
      body: JSON.stringify({ query, limit }),
    });
  },

  // ---- chat ----
  chat(ws: string, query: string, conversationId?: string | null, deepResearch = false) {
    return request<ChatResponse>(`/workspaces/${ws}/chat`, {
      method: "POST",
      body: JSON.stringify({
        query,
        conversation_id: conversationId ?? null,
        deep_research: deepResearch,
      }),
    });
  },
  listConversations(ws: string) {
    return request<Conversation[]>(`/workspaces/${ws}/conversations`);
  },
  getMessages(conversationId: string) {
    return request<Message[]>(`/conversations/${conversationId}/messages`);
  },

  // ---- analytics ----
  getAnalytics(ws: string) {
    return request<AnalyticsSummary>(`/workspaces/${ws}/analytics`);
  },

  // ---- notifications ----
  listNotifications() {
    return request<AppNotification[]>(`/notifications`);
  },
  unreadCount() {
    return request<{ unread: number }>(`/notifications/unread_count`);
  },
  markNotificationRead(id: string) {
    return request<AppNotification>(`/notifications/${id}/read`, { method: "POST" });
  },
  markAllNotificationsRead() {
    return request<{ unread: number }>(`/notifications/read_all`, { method: "POST" });
  },

  // ---- agents ----
  runAgent(ws: string, query: string, conversationId?: string | null) {
    return request<AgentRunResponse>(`/workspaces/${ws}/agents/run`, {
      method: "POST",
      body: JSON.stringify({
        query,
        conversation_id: conversationId ?? null,
        persist_history: true,
      }),
    });
  },

  // ---- memory ----
  addMemory(ws: string, content: string, kind = "note") {
    return request<Memory>(`/workspaces/${ws}/memories`, {
      method: "POST",
      body: JSON.stringify({ content, kind }),
    });
  },
  listMemories(ws: string) {
    return request<Memory[]>(`/workspaces/${ws}/memories`);
  },
  recallMemories(ws: string, query: string, limit = 5) {
    return request<RecalledMemory[]>(`/workspaces/${ws}/memories/recall`, {
      method: "POST",
      body: JSON.stringify({ query, limit }),
    });
  },

  // ---- knowledge graph ----
  getGraph(ws: string) {
    return request<GraphData>(`/workspaces/${ws}/graph`);
  },
  buildGraph(ws: string, texts?: string[]) {
    return request<GraphBuildResult>(`/workspaces/${ws}/graph/build`, {
      method: "POST",
      body: JSON.stringify({ texts: texts ?? null }),
    });
  },
  queryGraph(ws: string, query: string, depth?: number) {
    return request<GraphData>(`/workspaces/${ws}/graph/query`, {
      method: "POST",
      body: JSON.stringify({ query, depth: depth ?? null }),
    });
  },
};

// Streaming chat over Server-Sent Events. EventSource only does GET, so we read
// the POST response body ourselves and parse the `data: {...}` frames.
export async function streamChat(
  ws: string,
  query: string,
  conversationId: string | null,
  handlers: {
    onToken: (t: string) => void;
    onDone: (citations: Citation[]) => void;
    onError: (message: string) => void;
  },
): Promise<void> {
  try {
    const res = await fetch(`${BASE}/workspaces/${ws}/chat/stream`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...authHeaders() },
      body: JSON.stringify({ query, conversation_id: conversationId }),
    });
    if (!res.ok || !res.body) {
      handlers.onError(`Stream failed (${res.status})`);
      return;
    }
    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const frames = buffer.split("\n\n");
      buffer = frames.pop() || "";
      for (const frame of frames) {
        const line = frame.trim();
        if (!line.startsWith("data:")) continue;
        const payload = line.slice(5).trim();
        try {
          const obj = JSON.parse(payload);
          if (obj.token) handlers.onToken(obj.token);
          if (obj.done) handlers.onDone(obj.citations || []);
        } catch {
          /* ignore malformed frame */
        }
      }
    }
  } catch (e: any) {
    handlers.onError(e?.message || "Stream error");
  }
}
