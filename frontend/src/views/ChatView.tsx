import { useEffect, useRef, useState } from "react";
import {
  ArrowUp,
  ChevronRight,
  Database,
  FileText,
  GitBranch,
  Plus,
  Quote,
  Sparkles,
  Workflow,
} from "lucide-react";
import { api, streamChat } from "../lib/api";
import { useAuth } from "../state/auth";
import { useToast } from "../state/toast";
import type { AgentStep, Citation } from "../lib/types";

type Mode = "chat" | "agents";

interface ChatMsg {
  id: string;
  role: "user" | "assistant";
  content: string;
  citations?: Citation[];
  agent?: string;
  steps?: AgentStep[];
  facts?: string[];
  streaming?: boolean;
  error?: boolean;
}

const newId = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

const AGENT_COLOR: Record<string, string> = {
  research: "var(--c-research)",
  sql: "var(--c-sql)",
  graph: "var(--c-graph)",
};
const agentColor = (a?: string) => (a && AGENT_COLOR[a]) || "var(--dim)";

const SUGGESTIONS = [
  { k: "RETRIEVAL", t: "Summarize the key takeaways across my documents", c: "var(--teal)" },
  { k: "GRAPH AGENT", t: "Who reports to whom, and which teams own which projects?", c: "var(--violet)" },
  { k: "SQL AGENT", t: "What were total sales by region last quarter?", c: "var(--amber)" },
  { k: "MEMORY", t: "What do you know about my preferences so far?", c: "var(--green)" },
];

export function ChatView() {
  const { currentWorkspace } = useAuth();
  const { push } = useToast();
  const ws = currentWorkspace!.id;

  const [messages, setMessages] = useState<ChatMsg[]>([]);
  const [input, setInput] = useState("");
  const [mode, setMode] = useState<Mode>("chat");
  const [busy, setBusy] = useState(false);
  const [conversationId, setConversationId] = useState<string | null>(null);

  const scrollRef = useRef<HTMLDivElement>(null);
  const taRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages]);

  const grow = () => {
    const ta = taRef.current;
    if (!ta) return;
    ta.style.height = "auto";
    ta.style.height = Math.min(ta.scrollHeight, 180) + "px";
  };

  const reset = () => {
    setMessages([]);
    setConversationId(null);
  };

  const send = async (text: string) => {
    const q = text.trim();
    if (!q || busy) return;
    setInput("");
    requestAnimationFrame(grow);
    setMessages((m) => [...m, { id: newId(), role: "user", content: q }]);
    setBusy(true);

    if (mode === "chat") {
      const aid = newId();
      setMessages((m) => [...m, { id: aid, role: "assistant", content: "", streaming: true }]);
      await streamChat(ws, q, null, {
        onToken: (tok) =>
          setMessages((m) =>
            m.map((x) => (x.id === aid ? { ...x, content: x.content + tok } : x)),
          ),
        onDone: (citations) =>
          setMessages((m) =>
            m.map((x) => (x.id === aid ? { ...x, citations, streaming: false } : x)),
          ),
        onError: (msg) => {
          setMessages((m) =>
            m.map((x) =>
              x.id === aid
                ? {
                    ...x,
                    content:
                      x.content ||
                      "I couldn't reach the server. Make sure the backend is running on http://localhost:8000.",
                    streaming: false,
                    error: true,
                  }
                : x,
            ),
          );
          push(msg, "error");
        },
      });
      setBusy(false);
    } else {
      try {
        const res = await api.runAgent(ws, q, conversationId);
        if (res.conversation_id) setConversationId(res.conversation_id);
        const facts = Array.isArray((res.metadata as any)?.graph_facts)
          ? ((res.metadata as any).graph_facts as string[])
          : undefined;
        setMessages((m) => [
          ...m,
          {
            id: res.run_id || newId(),
            role: "assistant",
            content: res.answer,
            citations: res.citations,
            agent: res.agent,
            steps: res.steps,
            facts,
          },
        ]);
      } catch (e: any) {
        push(e.message || "Agent run failed", "error");
        setMessages((m) => [
          ...m,
          {
            id: newId(),
            role: "assistant",
            content: "That request failed. Check that the backend is running on :8000.",
            error: true,
          },
        ]);
      } finally {
        setBusy(false);
      }
    }
  };

  return (
    <div className="chat">
      <div className="chat-scroll" ref={scrollRef}>
        {messages.length === 0 ? (
          <Empty mode={mode} onPick={(t) => send(t)} />
        ) : (
          <div className="chat-inner">
            {messages.length > 0 && (
              <div style={{ display: "flex", justifyContent: "flex-end" }}>
                <button className="btn btn-ghost btn-sm" onClick={reset}>
                  <Plus size={15} /> New chat
                </button>
              </div>
            )}
            {messages.map((m) => (
              <Message key={m.id} msg={m} />
            ))}
          </div>
        )}
      </div>

      <div className="composer">
        <div className="composer-inner">
          <div className="composer-box">
            <textarea
              ref={taRef}
              rows={1}
              value={input}
              placeholder={
                mode === "chat"
                  ? "Ask anything about your knowledge base…"
                  : "Give the agent a task — it will route to research, SQL, or the graph…"
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
                className={`mode-opt ${mode === "agents" ? "active" : ""}`}
                onClick={() => setMode("agents")}
              >
                <Workflow size={13} /> Agents
              </button>
            </div>
            <span>
              {mode === "chat" ? "Streaming · grounded with citations" : "Auto-routed multi-step reasoning"}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}

function Empty({ mode, onPick }: { mode: Mode; onPick: (t: string) => void }) {
  return (
    <div className="empty">
      <div className="empty-inner">
        <div className="empty-orb">
          <Sparkles size={32} />
        </div>
        <h1>{mode === "chat" ? "Ask your knowledge base" : "Delegate to the agents"}</h1>
        <p>
          {mode === "chat"
            ? "Answers stream in real time, grounded in your documents with inline citations."
            : "One request is routed automatically to the right specialist — research, SQL, or the knowledge graph — with a full reasoning trace."}
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
        {isUser ? "You"[0] : <Sparkles size={15} />}
      </div>
      <div className="msg-body">
        <div className="msg-role">
          {isUser ? "You" : "Cortex"}
          {msg.agent && (
            <span className="agent-badge" style={{ color: agentColor(msg.agent) }}>
              <GitBranch size={11} /> {msg.agent}
            </span>
          )}
        </div>

        {msg.content || !msg.streaming ? (
          <div className={`msg-text ${isUser ? "user" : ""} ${msg.streaming ? "cursor-blink" : ""}`}>
            {msg.content}
          </div>
        ) : (
          <div className="typing">
            <span />
            <span />
            <span />
          </div>
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
        <div
          className="cite"
          key={c.index}
          title={c.snippet}
        >
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
