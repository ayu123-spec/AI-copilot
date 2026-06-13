// Types mirroring the FastAPI backend's response shapes.

export type Role = "owner" | "admin" | "manager" | "employee" | string;

export interface User {
  id: string;
  organization_id: string;
  email: string;
  full_name: string;
  role: Role;
  is_verified: boolean;
  created_at: string;
}

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface Workspace {
  id: string;
  organization_id: string;
  name: string;
  settings: Record<string, unknown>;
  created_at: string;
}

export type DocumentStatus = "pending" | "processing" | "ready" | "failed" | string;

export interface Doc {
  id: string;
  workspace_id: string;
  filename: string;
  content_type: string;
  status: DocumentStatus;
  num_chunks: number;
  error?: string | null;
  created_at: string;
}

export interface Citation {
  index: number;
  source: string;
  page_number?: number | null;
  snippet: string;
}

export interface ChatResponse {
  conversation_id: string;
  message_id: string;
  answer: string;
  citations: Citation[];
}

export interface AgentStep {
  thought?: string | null;
  tool?: string | null;
  tool_input?: Record<string, unknown> | null;
  observation?: string | null;
}

export interface AgentRunResponse {
  run_id: string;
  conversation_id?: string | null;
  agent: string;
  answer: string;
  citations: Citation[];
  steps: AgentStep[];
  metadata: Record<string, unknown>;
}

export interface SearchResult {
  score: number;
  text: string;
  document_id?: string | null;
  page_number?: number | null;
  source?: string | null;
}

export interface Memory {
  id: string;
  kind: string;
  content: string;
  source?: string | null;
  created_at: string;
}

export interface RecalledMemory {
  memory_id: string;
  content: string;
  kind: string;
  score: number;
}

export interface GraphEntity {
  id: string;
  name: string;
  type: string;
}

export interface GraphFact {
  source: string;
  relation: string;
  target: string;
}

export interface GraphData {
  entities: GraphEntity[];
  facts: GraphFact[];
}

export interface GraphBuildResult {
  entities: number;
  relationships: number;
}
