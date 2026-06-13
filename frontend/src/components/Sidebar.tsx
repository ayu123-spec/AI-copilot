import { useState } from "react";
import {
  Brain,
  Check,
  ChevronsUpDown,
  Database,
  FileText,
  LogOut,
  MessagesSquare,
  Plus,
  Share2,
} from "lucide-react";
import type { View } from "../App";
import { useAuth } from "../state/auth";
import { useToast } from "../state/toast";
import { api } from "../lib/api";

const NAV: { id: View; label: string; icon: typeof Brain }[] = [
  { id: "chat", label: "Chat", icon: MessagesSquare },
  { id: "graph", label: "Knowledge Graph", icon: Share2 },
  { id: "library", label: "Library", icon: FileText },
  { id: "memory", label: "Memory", icon: Database },
];

export function Sidebar({
  view,
  onView,
}: {
  view: View;
  onView: (v: View) => void;
}) {
  const { user, workspaces, currentWorkspace, setCurrentWorkspace, logout, reloadWorkspaces } =
    useAuth();
  const { push } = useToast();
  const [open, setOpen] = useState(false);
  const [creating, setCreating] = useState(false);
  const [name, setName] = useState("");

  const initials = (user?.full_name || user?.email || "?")
    .split(" ")
    .map((s) => s[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();

  const create = async () => {
    if (!name.trim()) return;
    try {
      const ws = await api.createWorkspace(name.trim());
      await reloadWorkspaces();
      setCurrentWorkspace(ws);
      setName("");
      setCreating(false);
      setOpen(false);
      push("Workspace created", "success");
    } catch (e: any) {
      push(e.message || "Could not create workspace", "error");
    }
  };

  return (
    <aside className="sidebar">
      <div className="brand">
        <div className="brand-mark">
          <Brain size={19} />
        </div>
        <div>
          <div className="brand-name">Cortex</div>
          <div className="brand-sub">KNOWLEDGE COPILOT</div>
        </div>
      </div>

      <div className="ws-switch">
        <button className="ws-button" onClick={() => setOpen((o) => !o)}>
          <div style={{ minWidth: 0 }}>
            <div className="ws-label">WORKSPACE</div>
            <div className="ws-name">{currentWorkspace?.name || "Select…"}</div>
          </div>
          <ChevronsUpDown size={16} className="dim" />
        </button>
        {open && (
          <div className="ws-menu">
            {workspaces.map((w) => (
              <div
                key={w.id}
                className={`ws-item ${w.id === currentWorkspace?.id ? "active" : ""}`}
                onClick={() => {
                  setCurrentWorkspace(w);
                  setOpen(false);
                }}
              >
                <Share2 size={14} style={{ opacity: 0.6 }} />
                <span style={{ flex: 1, overflow: "hidden", textOverflow: "ellipsis" }}>
                  {w.name}
                </span>
                {w.id === currentWorkspace?.id && <Check size={15} />}
              </div>
            ))}
            <div style={{ height: 1, background: "var(--line)", margin: "6px 4px" }} />
            {creating ? (
              <div style={{ display: "flex", gap: 6, padding: 4 }}>
                <input
                  className="input"
                  style={{ padding: "8px 10px" }}
                  autoFocus
                  placeholder="Workspace name"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && create()}
                />
                <button className="btn btn-primary btn-sm" onClick={create}>
                  Add
                </button>
              </div>
            ) : (
              <div className="ws-item" onClick={() => setCreating(true)}>
                <Plus size={15} /> New workspace
              </div>
            )}
          </div>
        )}
      </div>

      <nav className="nav">
        <div className="nav-label">WORKSPACE</div>
        {NAV.map((n) => (
          <div
            key={n.id}
            className={`nav-item ${view === n.id ? "active" : ""}`}
            onClick={() => onView(n.id)}
          >
            <n.icon size={18} />
            {n.label}
          </div>
        ))}
      </nav>

      <div className="side-foot">
        <div className="user-card">
          <div className="avatar">{initials}</div>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div
              style={{
                fontWeight: 600,
                fontSize: 13.5,
                overflow: "hidden",
                textOverflow: "ellipsis",
                whiteSpace: "nowrap",
              }}
            >
              {user?.full_name}
            </div>
            <div className="brand-sub" style={{ textTransform: "none" }}>
              {user?.role}
            </div>
          </div>
          <button className="btn-icon btn-ghost" title="Sign out" onClick={logout}>
            <LogOut size={17} className="dim" />
          </button>
        </div>
      </div>
    </aside>
  );
}
