import { useState } from "react";
import { Sparkles } from "lucide-react";
import { useAuth } from "./state/auth";
import { useToast } from "./state/toast";
import { api } from "./lib/api";
import { AuthView } from "./views/AuthView";
import { Sidebar } from "./components/Sidebar";
import { TopBar } from "./components/TopBar";
import { ChatView } from "./views/ChatView";
import { GraphView } from "./views/GraphView";
import { LibraryView } from "./views/LibraryView";
import { MemoryView } from "./views/MemoryView";
import { AnalyticsView } from "./views/AnalyticsView";

export type View = "chat" | "graph" | "library" | "memory" | "analytics";

export function App() {
  const { ready, user, currentWorkspace } = useAuth();
  const [view, setView] = useState<View>("chat");

  if (!ready) {
    return (
      <div className="center-load">
        <div className="spinner" />
      </div>
    );
  }
  if (!user) return <AuthView />;

  return (
    <div className="shell">
      <Sidebar view={view} onView={setView} />
      <div className="main">
        <TopBar view={view} />
        <div className="view">
          {!currentWorkspace ? (
            <NoWorkspace />
          ) : view === "chat" ? (
            <ChatView key={currentWorkspace.id} />
          ) : view === "graph" ? (
            <GraphView key={currentWorkspace.id} />
          ) : view === "library" ? (
            <LibraryView key={currentWorkspace.id} />
          ) : view === "analytics" ? (
            <AnalyticsView key={currentWorkspace.id} />
          ) : (
            <MemoryView key={currentWorkspace.id} />
          )}
        </div>
      </div>
    </div>
  );
}

function NoWorkspace() {
  const { reloadWorkspaces, setCurrentWorkspace } = useAuth();
  const { push } = useToast();
  const [busy, setBusy] = useState(false);

  const create = async () => {
    setBusy(true);
    try {
      const ws = await api.createWorkspace("General");
      await reloadWorkspaces();
      setCurrentWorkspace(ws);
      push("Workspace created", "success");
    } catch (e: any) {
      push(e.message || "Could not create workspace", "error");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="empty">
      <div className="empty-inner">
        <div className="empty-orb">
          <Sparkles size={34} />
        </div>
        <h1>Create your first workspace</h1>
        <p>
          Workspaces keep documents, conversations, and the knowledge graph
          scoped to a team — Finance, Legal, Engineering, anything you like.
        </p>
        <button className="btn btn-primary" onClick={create} disabled={busy}>
          {busy ? "Creating…" : "Create a workspace"}
        </button>
      </div>
    </div>
  );
}
