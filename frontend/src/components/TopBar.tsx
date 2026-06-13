import {
  Database,
  Folder,
  type LucideIcon,
  MessagesSquare,
  Share2,
  FileText,
} from "lucide-react";
import type { View } from "../App";
import { useAuth } from "../state/auth";

const TITLES: Record<View, { title: string; icon: LucideIcon }> = {
  chat: { title: "Chat", icon: MessagesSquare },
  graph: { title: "Knowledge Graph", icon: Share2 },
  library: { title: "Library", icon: FileText },
  memory: { title: "Memory", icon: Database },
};

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
