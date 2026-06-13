import { useCallback, useEffect, useState } from "react";
import { Brain, Plus, Sparkles } from "lucide-react";
import { api } from "../lib/api";
import { useAuth } from "../state/auth";
import { useToast } from "../state/toast";
import type { Memory, RecalledMemory } from "../lib/types";

const KINDS = ["note", "fact", "preference", "task"];

export function MemoryView() {
  const { currentWorkspace } = useAuth();
  const { push } = useToast();
  const ws = currentWorkspace!.id;

  const [memories, setMemories] = useState<Memory[]>([]);
  const [loading, setLoading] = useState(true);
  const [content, setContent] = useState("");
  const [kind, setKind] = useState("note");
  const [adding, setAdding] = useState(false);
  const [query, setQuery] = useState("");
  const [recalled, setRecalled] = useState<RecalledMemory[] | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setMemories(await api.listMemories(ws));
    } catch (e: any) {
      push(e.message || "Couldn't load memories", "error");
    } finally {
      setLoading(false);
    }
  }, [ws, push]);

  useEffect(() => {
    load();
  }, [load]);

  const add = async () => {
    if (!content.trim()) return;
    setAdding(true);
    try {
      await api.addMemory(ws, content.trim(), kind);
      setContent("");
      push("Memory saved", "success");
      load();
    } catch (e: any) {
      push(e.message || "Could not save", "error");
    } finally {
      setAdding(false);
    }
  };

  const recall = async () => {
    if (!query.trim()) {
      setRecalled(null);
      return;
    }
    try {
      setRecalled(await api.recallMemories(ws, query.trim(), 6));
    } catch (e: any) {
      push(e.message || "Recall failed", "error");
    }
  };

  return (
    <div className="page">
      <div className="page-narrow">
        <div className="panel" style={{ padding: 18, marginBottom: 24 }}>
          <div className="label">New memory</div>
          <textarea
            className="textarea"
            rows={2}
            placeholder="Something the copilot should remember — a preference, fact, or instruction…"
            value={content}
            onChange={(e) => setContent(e.target.value)}
          />
          <div style={{ display: "flex", gap: 10, marginTop: 11, alignItems: "center" }}>
            <div className="mode-toggle">
              {KINDS.map((k) => (
                <button
                  key={k}
                  className={`mode-opt ${kind === k ? "active" : ""}`}
                  onClick={() => setKind(k)}
                  style={{ textTransform: "capitalize" }}
                >
                  {k}
                </button>
              ))}
            </div>
            <button
              className="btn btn-primary btn-sm"
              style={{ marginLeft: "auto" }}
              disabled={adding || !content.trim()}
              onClick={add}
            >
              <Plus size={15} /> Save
            </button>
          </div>
        </div>

        <div className="panel" style={{ padding: 18, marginBottom: 24 }}>
          <div className="label">Recall by meaning</div>
          <div className="graph-search" style={{ background: "var(--panel-2)" }}>
            <Sparkles size={15} className="dim" />
            <input
              placeholder="What did I say about…?"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && recall()}
            />
            <button className="btn btn-sm" onClick={recall}>
              Recall
            </button>
          </div>
          {recalled && (
            <div className="doc-list" style={{ marginTop: 14 }}>
              {recalled.length === 0 && (
                <div className="dim" style={{ fontSize: 14 }}>
                  Nothing relevant found.
                </div>
              )}
              {recalled.map((r) => (
                <div className="doc-row" key={r.memory_id} style={{ alignItems: "flex-start" }}>
                  <div className="doc-icon" style={{ color: "var(--teal)" }}>
                    <Brain size={17} />
                  </div>
                  <div className="doc-meta">
                    <div className="msg-text" style={{ fontSize: 14 }}>
                      {r.content}
                    </div>
                    <div className="doc-sub">
                      {r.kind} · similarity {r.score.toFixed(3)}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="section-row">
          <h3>All memories</h3>
          <span className="chip">{memories.length} stored</span>
        </div>
        {loading ? (
          <div className="center-load" style={{ height: 140 }}>
            <div className="spinner" />
          </div>
        ) : memories.length === 0 ? (
          <div className="dim" style={{ fontSize: 14, padding: "8px 2px" }}>
            No memories yet. Anything you save here can be recalled by the agents later.
          </div>
        ) : (
          <div className="doc-list">
            {memories.map((m) => (
              <div className="doc-row" key={m.id} style={{ alignItems: "flex-start" }}>
                <div className="doc-icon">
                  <Brain size={17} />
                </div>
                <div className="doc-meta">
                  <div className="msg-text" style={{ fontSize: 14 }}>
                    {m.content}
                  </div>
                  <div className="doc-sub">
                    {m.kind}
                    {m.source ? ` · ${m.source}` : ""}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
