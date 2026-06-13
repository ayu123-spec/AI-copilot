import { useCallback, useEffect, useMemo, useState } from "react";
import { Boxes, FileStack, Search, Sparkles } from "lucide-react";
import { api } from "../lib/api";
import { useAuth } from "../state/auth";
import { useToast } from "../state/toast";
import type { GraphData, GraphEntity } from "../lib/types";
import { ForceGraph, colorForType } from "../graph/ForceGraph";

const SAMPLE = [
  "Alice Johnson works for Acme Corp.",
  "Alice Johnson manages Bob Smith.",
  "Bob Smith reports to Alice Johnson.",
  "Bob Smith works on Project Atlas.",
  "Carol Lee works for Acme Corp.",
  "Carol Lee manages the Engineering department.",
  "Bob Smith is part of the Engineering department.",
  "Dave Park reports to Carol Lee.",
  "Dave Park works on Project Orion.",
  "Project Atlas is part of Acme Corp.",
  "Erin Maxwell works for Globex Ltd.",
  "Erin Maxwell manages Frank Turner.",
  "Frank Turner works on Project Orion.",
];

const LEGEND = ["Person", "Company", "Department", "Project", "Entity"];

export function GraphView() {
  const { currentWorkspace } = useAuth();
  const { push } = useToast();
  const ws = currentWorkspace!.id;

  const [data, setData] = useState<GraphData>({ entities: [], facts: [] });
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [query, setQuery] = useState("");
  const [highlight, setHighlight] = useState<Set<string> | null>(null);
  const [selected, setSelected] = useState<GraphEntity | null>(null);
  const [text, setText] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setData(await api.getGraph(ws));
    } catch (e: any) {
      push(e.message || "Couldn't load the graph", "error");
    } finally {
      setLoading(false);
    }
  }, [ws, push]);

  useEffect(() => {
    load();
  }, [load]);

  const build = async (texts?: string[]) => {
    setBusy(true);
    try {
      const res = await api.buildGraph(ws, texts);
      push(`Added ${res.entities} entities · ${res.relationships} relationships`, "success");
      setText("");
      await load();
    } catch (e: any) {
      push(e.message || "Build failed", "error");
    } finally {
      setBusy(false);
    }
  };

  const runQuery = async () => {
    if (!query.trim()) {
      setHighlight(null);
      return;
    }
    try {
      const res = await api.queryGraph(ws, query.trim());
      const ids = new Set<string>();
      res.entities.forEach((e) => ids.add(e.name.toLowerCase()));
      res.facts.forEach((f) => {
        ids.add(f.source.toLowerCase());
        ids.add(f.target.toLowerCase());
      });
      setHighlight(ids);
      if (res.entities[0]) setSelected(res.entities[0]);
      push(`${res.entities.length} entities · ${res.facts.length} facts matched`, "info");
    } catch (e: any) {
      push(e.message || "Query failed", "error");
    }
  };

  const relationships = useMemo(() => {
    if (!selected) return [];
    const name = selected.name.toLowerCase();
    return data.facts.filter(
      (f) => f.source.toLowerCase() === name || f.target.toLowerCase() === name,
    );
  }, [selected, data]);

  const empty = !loading && data.entities.length === 0;

  return (
    <div className="graph-wrap">
      <div className="graph-canvas" style={{ position: "relative", height: "100%" }}>
        <div className="graph-toolbar">
          <div className="graph-search">
            <Search size={16} className="dim" />
            <input
              placeholder="Trace a path — e.g. who reports to Alice Johnson?"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && runQuery()}
            />
            {highlight && (
              <button
                className="btn-ghost btn-sm"
                style={{ padding: "2px 8px" }}
                onClick={() => {
                  setHighlight(null);
                  setQuery("");
                }}
              >
                Clear
              </button>
            )}
          </div>
        </div>

        {loading ? (
          <div className="center-load">
            <div className="spinner" />
          </div>
        ) : empty ? (
          <div className="graph-empty">
            <div className="empty-inner" style={{ pointerEvents: "auto" }}>
              <div className="empty-orb">
                <Boxes size={32} />
              </div>
              <h1 style={{ fontSize: 22 }}>Your knowledge graph is empty</h1>
              <p>
                Extract entities and relationships from your documents, or drop in
                some text. Want to see it in action right now?
              </p>
              <button
                className="btn btn-primary"
                onClick={() => build(SAMPLE)}
                disabled={busy}
              >
                <Sparkles size={16} /> {busy ? "Building…" : "Load sample org graph"}
              </button>
            </div>
          </div>
        ) : (
          <ForceGraph
            data={data}
            highlightIds={highlight}
            selectedId={selected?.name || null}
            onSelect={setSelected}
          />
        )}
      </div>

      <aside className="graph-side">
        <div className="stat-row">
          <div className="stat">
            <div className="stat-n">{data.entities.length}</div>
            <div className="stat-l">Entities</div>
          </div>
          <div className="stat">
            <div className="stat-n">{data.facts.length}</div>
            <div className="stat-l">Relationships</div>
          </div>
        </div>

        <div className="build-box">
          <div className="label" style={{ margin: 0 }}>
            Build from text
          </div>
          <textarea
            className="textarea"
            rows={4}
            placeholder={"One statement per line, e.g.\nAlice manages Bob.\nBob works on Project Atlas."}
            value={text}
            onChange={(e) => setText(e.target.value)}
          />
          <div style={{ display: "flex", gap: 8 }}>
            <button
              className="btn btn-primary btn-sm"
              style={{ flex: 1, justifyContent: "center" }}
              disabled={busy || !text.trim()}
              onClick={() => build(text.split("\n").map((s) => s.trim()).filter(Boolean))}
            >
              Extract
            </button>
            <button
              className="btn btn-sm"
              disabled={busy}
              onClick={() => build(undefined)}
              title="Extract from this workspace's documents"
            >
              <FileStack size={15} /> Documents
            </button>
          </div>
          {data.entities.length > 0 && (
            <button
              className="btn btn-ghost btn-sm"
              style={{ justifyContent: "center" }}
              disabled={busy}
              onClick={() => build(SAMPLE)}
            >
              <Sparkles size={14} /> Add sample data
            </button>
          )}
        </div>

        <div>
          <div className="label">Legend</div>
          <div className="legend">
            {LEGEND.map((t) => (
              <span key={t} className="legend-item">
                <span className="legend-swatch" style={{ color: colorForType(t) }} />
                {t}
              </span>
            ))}
          </div>
        </div>

        {selected && (
          <div>
            <div className="label">Selected</div>
            <div className="inspector-name" style={{ color: colorForType(selected.type) }}>
              {selected.name}
            </div>
            <div className="chip" style={{ marginBottom: 12 }}>
              {selected.type}
            </div>
            <div className="rel-list">
              {relationships.length === 0 && (
                <div className="faint" style={{ fontSize: 13 }}>
                  No relationships recorded.
                </div>
              )}
              {relationships.map((f, i) => (
                <div className="rel-item" key={i}>
                  <b>{f.source}</b> <span className="rel">{f.relation}</span> <b>{f.target}</b>
                </div>
              ))}
            </div>
          </div>
        )}
      </aside>
    </div>
  );
}
