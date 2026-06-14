import { useCallback, useEffect, useRef, useState } from "react";
import type { ReactNode } from "react";
import {
  ArrowUp,
  ChevronRight,
  GitBranch,
  Layers,
  Loader2,
  MessageSquare,
  Paperclip,
  Plus,
  Quote,
  Search,
  Sparkles,
  Workflow,
} from "lucide-react";
import { api } from "../lib/api";
import { useAuth } from "../state/auth";
import { useToast } from "../state/toast";
import type { AgentStep, Citation, Conversation } from "../lib/types";

type Mode = "chat" | "research" | "agents";

interface ResearchStep {
  sub_question: string;
  sources_found: number;
}

interface ChatMsg {
  id: string;
  role: "user" | "assistant";
  content: string;
  citations?: Citation[];
  agent?: string;
  queryType?: string;
  grounding?: string;
  followUps?: string[];
  researchSteps?: ResearchStep[];
  steps?: AgentStep[];
  facts?: string[];
  streaming?: boolean;
  error?: boolean;
  system?: boolean;
}

const newId = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

const AGENT_COLOR: Record<string, string> = {
  research: "var(--c-research)",
  sql: "var(--c-sql)",
  graph: "var(--c-graph)",
  guardrail: "var(--rose)",
};
const agentColor = (a?: string) => (a && AGENT_COLOR[a]) || "var(--dim)";

const SUGGESTIONS = [
  { k: "DOCUMENTS", t: "Summarize the key points from my uploaded documents", c: "var(--teal)" },
  { k: "GRAPH AGENT", t: "Who reports to whom, and which teams own which projects?", c: "var(--amber)" },
  { k: "SQL AGENT", t: "What were total sales by region last quarter?", c: "var(--rose)" },
  { k: "MEMORY", t: "What do you know about my preferences so far?", c: "var(--green)" },
];

export function ChatView() {
  const { currentWorkspace, user } = useAuth();
  const { push } = useToast();
  const ws = currentWorkspace!.id;
  const firstName = (user?.full_name || "").trim().split(/\s+/)[0] || "there";

  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMsg[]>([]);
  const [input, setInput] = useState("");
  const [mode, setMode] = useState<Mode>("chat");
  const [busy, setBusy] = useState(false);
  const [uploading, setUploading] = useState(false);

  const scrollRef = useRef<HTMLDivElement>(null);
  const taRef = useRef<HTMLTextAreaElement>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const loadConversations = useCallback(async () => {
    try {
      setConversations(await api.listConversations(ws));
    } catch {
      /* non-fatal */
    }
  }, [ws]);

  useEffect(() => {
    loadConversations();
  }, [loadConversations]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages]);

  const grow = () => {
    const ta = taRef.current;
    if (!ta) return;
    ta.style.height = "auto";
    ta.style.height = Math.min(ta.scrollHeight, 180) + "px";
  };

  const newChat = () => {
    setMessages([]);
    setConversationId(null);
  };

  const openConversation = async (id: string) => {
    setConversationId(id);
    try {
      const msgs = await api.getMessages(id);
      setMessages(
        msgs.map((m) => ({
          id: m.id,
          role: m.role === "user" ? "user" : "assistant",
          content: m.content,
          citations: m.citations,
        })),
      );
    } catch (e: any) {
      push(e.message || "Couldn't load that conversation", "error");
    }
  };

  // Reveal an answer with a typewriter effect for a live feel.
  const reveal = (id: string, full: string) =>
    new Promise<void>((resolve) => {
      const parts = full.split(/(\s+)/);
      let i = 0;
      const step = () => {
        i += 2;
        const partial = parts.slice(0, i).join("");
        setMessages((m) => m.map((x) => (x.id === id ? { ...x, content: partial } : x)));
        if (i < parts.length) setTimeout(step, 16);
        else {
          setMessages((m) => m.map((x) => (x.id === id ? { ...x, content: full } : x)));
          resolve();
        }
      };
      step();
    });

  const send = async (text: string) => {
    const q = text.trim();
    if (!q || busy) return;
    setInput("");
    requestAnimationFrame(grow);
    setMessages((m) => [...m, { id: newId(), role: "user", content: q }]);
    setBusy(true);
    const aid = newId();
    setMessages((m) => [...m, { id: aid, role: "assistant", content: "", streaming: true }]);

    try {
      if (mode !== "agents") {
        const res = await api.chat(ws, q, conversationId, mode === "research");
        setConversationId(res.conversation_id);
        await reveal(aid, res.answer);
        setMessages((m) =>
          m.map((x) =>
            x.id === aid
              ? {
                  ...x,
                  citations: res.citations,
                  queryType: res.query_type,
                  followUps: res.follow_ups,
                  researchSteps: res.research_steps,
                  grounding: res.grounding,
                  streaming: false,
                }
              : x,
          ),
        );
      } else {
        const res = await api.runAgent(ws, q, conversationId);
        if (res.conversation_id) setConversationId(res.conversation_id);
        const facts = Array.isArray((res.metadata as any)?.graph_facts)
          ? ((res.metadata as any).graph_facts as string[])
          : undefined;
        await reveal(aid, res.answer);
        setMessages((m) =>
          m.map((x) =>
            x.id === aid
              ? {
                  ...x,
                  citations: res.citations,
                  agent: res.agent,
                  steps: res.steps,
                  facts,
                  streaming: false,
                }
              : x,
          ),
        );
      }
      loadConversations();
    } catch (e: any) {
      setMessages((m) =>
        m.map((x) =>
          x.id === aid
            ? {
                ...x,
                content:
                  "I couldn't reach the server. Make sure the backend is running on http://localhost:8000.",
                streaming: false,
                error: true,
              }
            : x,
        ),
      );
      push(e.message || "Request failed", "error");
    } finally {
      setBusy(false);
    }
  };

  const onAttach = async (files: FileList | null) => {
    const f = files?.[0];
    if (!f) return;
    setUploading(true);
    try {
      const doc = await api.uploadDocument(ws, f);
      push(`Uploaded ${doc.filename}`, "success");
      setMessages((m) => [
        ...m,
        {
          id: newId(),
          role: "assistant",
          system: true,
          content: `Added "${doc.filename}" to this workspace (${doc.num_chunks} chunks). Ask me anything about it.`,
        },
      ]);
    } catch (e: any) {
      push(e.message || "Upload failed", "error");
    } finally {
      setUploading(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  };

  return (
    <div className="chat-layout">
      <aside className="conv-rail">
        <button className="conv-new" onClick={newChat}>
          <Plus size={16} /> New chat
        </button>
        <div className="conv-list">
          {conversations.length === 0 ? (
            <div className="faint" style={{ fontSize: 12.5, padding: "10px 8px" }}>
              No conversations yet.
            </div>
          ) : (
            conversations.map((c) => (
              <button
                key={c.id}
                className={`conv-item ${c.id === conversationId ? "active" : ""}`}
                onClick={() => openConversation(c.id)}
                title={c.title}
              >
                <MessageSquare size={14} />
                <span>{c.title || "Untitled chat"}</span>
              </button>
            ))
          )}
        </div>
      </aside>

      <div className="chat">
        <div className="chat-scroll" ref={scrollRef}>
          {messages.length === 0 ? (
            <Empty mode={mode} name={firstName} onPick={(t) => send(t)} />
          ) : (
            <div className="chat-inner">
              {messages.map((m) =>
                m.system ? (
                  <div key={m.id} className="sys-note">
                    <Paperclip size={13} /> {m.content}
                  </div>
                ) : (
                  <Message key={m.id} msg={m} />
                ),
              )}
              <FollowUps messages={messages} onPick={(q) => send(q)} />
            </div>
          )}
        </div>

        <div className="composer">
          <div className="composer-inner">
            <div className="composer-box">
              <button
                className="attach-btn"
                onClick={() => fileRef.current?.click()}
                disabled={uploading}
                title="Attach a document from your computer"
              >
                {uploading ? <Loader2 size={18} className="spin-icon" /> : <Plus size={20} />}
              </button>
              <input ref={fileRef} type="file" hidden onChange={(e) => onAttach(e.target.files)} />
              <textarea
                ref={taRef}
                rows={1}
                value={input}
                placeholder={
                  mode === "agents"
                    ? "Give the agent a task — research, SQL, or the knowledge graph…"
                    : mode === "research"
                      ? "Ask a big question — I'll research it across your documents…"
                      : "Ask anything about your documents…  (＋ to attach a file)"
                }
                onChange={(e) => {
                  setInput(e.target.value);
                  grow();
                }}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    send(input);
                  }
                }}
              />
              <button
                className="send-btn"
                disabled={!input.trim() || busy}
                onClick={() => send(input)}
                title="Send"
              >
                <ArrowUp size={20} />
              </button>
            </div>
            <div className="composer-hint">
              <div className="mode-toggle">
                <button
                  className={`mode-opt ${mode === "chat" ? "active" : ""}`}
                  onClick={() => setMode("chat")}
                >
                  <Sparkles size={13} /> Chat
                </button>
                <button
                  className={`mode-opt ${mode === "research" ? "active" : ""}`}
                  onClick={() => setMode("research")}
                >
                  <Search size={13} /> Deep research
                </button>
                <button
                  className={`mode-opt ${mode === "agents" ? "active" : ""}`}
                  onClick={() => setMode("agents")}
                >
                  <Workflow size={13} /> Agents
                </button>
              </div>
              <span>
                {mode === "chat"
                  ? "Remembers the thread · grounded with citations"
                  : mode === "research"
                    ? "Decomposes · researches · synthesizes"
                    : "Auto-routed reasoning"}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function Empty({
  mode,
  name,
  onPick,
}: {
  mode: Mode;
  name: string;
  onPick: (t: string) => void;
}) {
  return (
    <div className="empty">
      <div className="empty-inner">
        <div className="empty-orb">
          <Sparkles size={32} />
        </div>
        <div className="welcome-eyebrow mono">WELCOME, DEAR</div>
        <h1 className="grad-text">{name}</h1>
        <p>
          {mode === "chat"
            ? "Ask anything about your documents — answers are grounded with citations, the thread is remembered, and ＋ adds a file right here."
            : mode === "research"
              ? "Pose a big question and I'll decompose it, research each part across your documents, and synthesize one structured report."
              : "Delegate a task — it's routed automatically to the right specialist (research, SQL, or the knowledge graph) with a full reasoning trace."}
        </p>
        <div className="suggest-grid">
          {SUGGESTIONS.map((s) => (
            <div key={s.t} className="suggest" onClick={() => onPick(s.t)}>
              <div className="suggest-k mono" style={{ color: s.c }}>
                {s.k}
              </div>
              <div className="suggest-t">{s.t}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function Message({ msg }: { msg: ChatMsg }) {
  const isUser = msg.role === "user";
  return (
    <div className="msg">
      <div className={`msg-avatar ${isUser ? "user" : "ai"}`}>
        {isUser ? "Y" : <Sparkles size={15} />}
      </div>
      <div className="msg-body">
        <div className="msg-role">
          {isUser ? "You" : "Cortex"}
          {msg.agent && (
            <span className="agent-badge" style={{ color: agentColor(msg.agent) }}>
              <GitBranch size={11} /> {msg.agent}
            </span>
          )}
          {!isUser && msg.queryType && msg.queryType !== "general" && (
            <span className="qtype-badge">{prettyType(msg.queryType)}</span>
          )}
          {!isUser && msg.grounding && !msg.streaming && (
            <span className={`ground-badge ${msg.grounding}`}>{msg.grounding}</span>
          )}
        </div>

        {msg.content || !msg.streaming ? (
          isUser ? (
            <div className="msg-text user">{msg.content}</div>
          ) : (
            <div className={`msg-text ${msg.streaming ? "cursor-blink" : ""}`}>
              <Markdown text={msg.content} />
            </div>
          )
        ) : (
          <div className="typing">
            <span />
            <span />
            <span />
          </div>
        )}

        {msg.researchSteps && msg.researchSteps.length > 0 && (
          <ResearchPlan steps={msg.researchSteps} />
        )}
        {msg.facts && msg.facts.length > 0 && <Facts facts={msg.facts} />}
        {msg.steps && msg.steps.length > 0 && <Trace steps={msg.steps} />}
        {msg.citations && msg.citations.length > 0 && <Citations citations={msg.citations} />}
      </div>
    </div>
  );
}

function Citations({ citations }: { citations: Citation[] }) {
  return (
    <div className="citations">
      {citations.map((c) => (
        <div className="cite" key={c.index} title={c.snippet}>
          <Quote size={12} className="dim" />
          <span className="cite-num">[{c.index}]</span>
          <span className="cite-src">
            {c.source}
            {c.page_number != null ? ` · p.${c.page_number}` : ""}
          </span>
        </div>
      ))}
    </div>
  );
}

function Facts({ facts }: { facts: string[] }) {
  return (
    <div className="facts">
      {facts.map((f, i) => (
        <div className="fact" key={i}>
          <GitBranch size={13} className="dim" />
          <span className="mono">{f}</span>
        </div>
      ))}
    </div>
  );
}

function Trace({ steps }: { steps: AgentStep[] }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="trace">
      <div className="trace-head" onClick={() => setOpen((o) => !o)}>
        <Workflow size={15} />
        <span>Reasoning trace</span>
        <span className="dim mono" style={{ fontSize: 11 }}>
          {steps.length} step{steps.length === 1 ? "" : "s"}
        </span>
        <ChevronRight
          size={15}
          style={{
            marginLeft: "auto",
            transform: open ? "rotate(90deg)" : "none",
            transition: "transform 0.2s",
          }}
        />
      </div>
      {open && (
        <div className="trace-body">
          {steps.map((s, i) => (
            <div className="trace-step" key={i}>
              <div className="trace-rail">
                <div className="trace-node" />
                {i < steps.length - 1 && <div className="trace-line" />}
              </div>
              <div>
                {s.tool && <div className="trace-tool">→ {s.tool}</div>}
                {s.thought && <div className="trace-thought">{s.thought}</div>}
                {s.observation && <div className="trace-obs">{s.observation}</div>}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function prettyType(t: string): string {
  return t
    .split("_")
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
}

// Minimal, dependency-free Markdown renderer for assistant answers:
// headings, bullet/numbered lists, paragraphs, **bold**, and `code`.
function inlineMd(text: string, keyBase: string): ReactNode[] {
  const nodes: ReactNode[] = [];
  const re = /(\*\*[^*]+\*\*|`[^`]+`)/g;
  let last = 0;
  let m: RegExpExecArray | null;
  let i = 0;
  while ((m = re.exec(text)) !== null) {
    if (m.index > last) nodes.push(text.slice(last, m.index));
    const tok = m[0];
    if (tok.startsWith("**")) nodes.push(<strong key={`${keyBase}-b${i}`}>{tok.slice(2, -2)}</strong>);
    else nodes.push(<code key={`${keyBase}-c${i}`}>{tok.slice(1, -1)}</code>);
    last = m.index + tok.length;
    i++;
  }
  if (last < text.length) nodes.push(text.slice(last));
  return nodes;
}

function Markdown({ text }: { text: string }) {
  const lines = text.replace(/\r/g, "").split("\n");
  const blocks: ReactNode[] = [];
  let i = 0;
  let key = 0;
  const isBullet = (l: string) => /^\s*[-*]\s+/.test(l);
  const isNum = (l: string) => /^\s*\d+\.\s+/.test(l);
  const isHeading = (l: string) => /^#{1,4}\s+/.test(l);

  while (i < lines.length) {
    const line = lines[i];
    if (line.trim() === "") {
      i++;
      continue;
    }
    const h = /^(#{1,4})\s+(.*)$/.exec(line);
    if (h) {
      const level = Math.min(h[1].length + 1, 6);
      const Tag = `h${level}` as keyof JSX.IntrinsicElements;
      blocks.push(
        <Tag key={key} className="md-h">
          {inlineMd(h[2], `h${key}`)}
        </Tag>,
      );
      key++;
      i++;
      continue;
    }
    if (isBullet(line)) {
      const items: ReactNode[] = [];
      while (i < lines.length && isBullet(lines[i])) {
        const item = lines[i].replace(/^\s*[-*]\s+/, "");
        items.push(<li key={items.length}>{inlineMd(item, `li${key}-${items.length}`)}</li>);
        i++;
      }
      blocks.push(
        <ul key={key} className="md-ul">
          {items}
        </ul>,
      );
      key++;
      continue;
    }
    if (isNum(line)) {
      const items: ReactNode[] = [];
      while (i < lines.length && isNum(lines[i])) {
        const item = lines[i].replace(/^\s*\d+\.\s+/, "");
        items.push(<li key={items.length}>{inlineMd(item, `ol${key}-${items.length}`)}</li>);
        i++;
      }
      blocks.push(
        <ol key={key} className="md-ol">
          {items}
        </ol>,
      );
      key++;
      continue;
    }
    const para: string[] = [];
    while (
      i < lines.length &&
      lines[i].trim() !== "" &&
      !isBullet(lines[i]) &&
      !isNum(lines[i]) &&
      !isHeading(lines[i])
    ) {
      para.push(lines[i]);
      i++;
    }
    blocks.push(
      <p key={key} className="md-p">
        {inlineMd(para.join(" "), `p${key}`)}
      </p>,
    );
    key++;
  }
  return <div className="md">{blocks}</div>;
}

function FollowUps({
  messages,
  onPick,
}: {
  messages: ChatMsg[];
  onPick: (q: string) => void;
}) {
  const last = messages[messages.length - 1];
  if (!last || last.role !== "assistant" || last.streaming || !last.followUps?.length) {
    return null;
  }
  return (
    <div className="followups">
      <span className="followups-label">Suggested follow-ups</span>
      <div className="followups-row">
        {last.followUps.map((f, i) => (
          <button key={i} className="followup-chip" onClick={() => onPick(f)}>
            {f}
          </button>
        ))}
      </div>
    </div>
  );
}

function ResearchPlan({ steps }: { steps: ResearchStep[] }) {
  const [open, setOpen] = useState(true);
  return (
    <div className="trace research-plan">
      <div className="trace-head" onClick={() => setOpen((o) => !o)}>
        <Layers size={15} />
        <span>Research plan</span>
        <span className="dim mono" style={{ fontSize: 11 }}>
          {steps.length} sub-question{steps.length === 1 ? "" : "s"}
        </span>
        <ChevronRight
          size={15}
          style={{
            marginLeft: "auto",
            transform: open ? "rotate(90deg)" : "none",
            transition: "transform 0.2s",
          }}
        />
      </div>
      {open && (
        <div className="trace-body">
          {steps.map((s, i) => (
            <div className="trace-step" key={i}>
              <div className="trace-rail">
                <div className="trace-node" />
                {i < steps.length - 1 && <div className="trace-line" />}
              </div>
              <div>
                <div className="trace-tool">{s.sub_question}</div>
                <div className="trace-obs">
                  {s.sources_found} source{s.sources_found === 1 ? "" : "s"} found
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
