import { useEffect, useRef, useState } from "react";
import {
  BarChart3,
  Bell,
  CheckCheck,
  Database,
  FileText,
  Folder,
  type LucideIcon,
  MessagesSquare,
  Share2,
} from "lucide-react";
import type { View } from "../App";
import { useAuth } from "../state/auth";
import { api } from "../lib/api";
import type { AppNotification } from "../lib/types";

const TITLES: Record<View, { title: string; icon: LucideIcon }> = {
  chat: { title: "Chat", icon: MessagesSquare },
  graph: { title: "Knowledge Graph", icon: Share2 },
  library: { title: "Library", icon: FileText },
  memory: { title: "Memory", icon: Database },
  analytics: { title: "Analytics", icon: BarChart3 },
};

const LEVEL_COLOR: Record<string, string> = {
  success: "var(--green)",
  error: "var(--rose)",
  warning: "var(--amber)",
  info: "var(--dim)",
};

function timeAgo(iso: string): string {
  const then = new Date(iso).getTime();
  const secs = Math.max(0, Math.floor((Date.now() - then) / 1000));
  if (secs < 60) return "just now";
  const mins = Math.floor(secs / 60);
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return new Date(iso).toLocaleDateString();
}

export function TopBar({ view }: { view: View }) {
  const { currentWorkspace } = useAuth();
  const meta = TITLES[view];
  return (
    <header className="topbar">
      <div className="topbar-title">
        <meta.icon size={19} className="dim" />
        <h2>{meta.title}</h2>
      </div>
      <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
        <NotificationBell />
        {currentWorkspace && (
          <span className="chip">
            <Folder size={13} /> {currentWorkspace.name}
          </span>
        )}
        <span className="badge" style={{ color: "var(--green)" }}>
          <span className="badge-dot" /> Online
        </span>
      </div>
    </header>
  );
}

function NotificationBell() {
  const [open, setOpen] = useState(false);
  const [items, setItems] = useState<AppNotification[]>([]);
  const [unread, setUnread] = useState(0);
  const ref = useRef<HTMLDivElement>(null);

  const refreshCount = async () => {
    try {
      setUnread((await api.unreadCount()).unread);
    } catch {
      /* ignore */
    }
  };

  const loadList = async () => {
    try {
      setItems(await api.listNotifications());
    } catch {
      /* ignore */
    }
  };

  useEffect(() => {
    refreshCount();
    const t = setInterval(refreshCount, 20000);
    return () => clearInterval(t);
  }, []);

  // Close on outside click.
  useEffect(() => {
    if (!open) return;
    const onDoc = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, [open]);

  const toggle = async () => {
    const next = !open;
    setOpen(next);
    if (next) await loadList();
  };

  const markAll = async () => {
    try {
      await api.markAllNotificationsRead();
      setUnread(0);
      setItems((xs) => xs.map((x) => ({ ...x, read: true })));
    } catch {
      /* ignore */
    }
  };

  const openItem = async (n: AppNotification) => {
    if (n.read) return;
    try {
      await api.markNotificationRead(n.id);
      setItems((xs) => xs.map((x) => (x.id === n.id ? { ...x, read: true } : x)));
      setUnread((u) => Math.max(0, u - 1));
    } catch {
      /* ignore */
    }
  };

  return (
    <div className="notif" ref={ref}>
      <button className="notif-btn" onClick={toggle} title="Notifications">
        <Bell size={18} />
        {unread > 0 && <span className="notif-badge">{unread > 9 ? "9+" : unread}</span>}
      </button>
      {open && (
        <div className="notif-panel">
          <div className="notif-head">
            <span>Notifications</span>
            {items.some((i) => !i.read) && (
              <button className="notif-clear" onClick={markAll}>
                <CheckCheck size={14} /> Mark all read
              </button>
            )}
          </div>
          <div className="notif-list">
            {items.length === 0 ? (
              <div className="notif-empty">You're all caught up.</div>
            ) : (
              items.map((n) => (
                <button
                  key={n.id}
                  className={`notif-item ${n.read ? "" : "unread"}`}
                  onClick={() => openItem(n)}
                >
                  <span
                    className="notif-dot"
                    style={{ background: LEVEL_COLOR[n.level] || "var(--dim)" }}
                  />
                  <div className="notif-body">
                    <div className="notif-title">{n.title}</div>
                    {n.body && <div className="notif-text">{n.body}</div>}
                    <div className="notif-time">{timeAgo(n.created_at)}</div>
                  </div>
                </button>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}
