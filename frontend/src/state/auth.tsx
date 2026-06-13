import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import { api, clearToken, getToken, setToken } from "../lib/api";
import type { User, Workspace } from "../lib/types";

interface RegisterBody {
  email: string;
  password: string;
  full_name: string;
  organization_name: string;
}

interface AuthState {
  ready: boolean;
  user: User | null;
  workspaces: Workspace[];
  currentWorkspace: Workspace | null;
  setCurrentWorkspace: (w: Workspace) => void;
  login: (email: string, password: string) => Promise<void>;
  register: (body: RegisterBody) => Promise<void>;
  logout: () => void;
  reloadWorkspaces: () => Promise<Workspace[]>;
}

const AuthContext = createContext<AuthState>(null as unknown as AuthState);
export const useAuth = () => useContext(AuthContext);

const WS_KEY = "cortex_ws";

export function AuthProvider({ children }: { children: ReactNode }) {
  const [ready, setReady] = useState(false);
  const [user, setUser] = useState<User | null>(null);
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [currentWorkspace, setCurrent] = useState<Workspace | null>(null);

  const setCurrentWorkspace = useCallback((w: Workspace) => {
    setCurrent(w);
    localStorage.setItem(WS_KEY, w.id);
  }, []);

  const reloadWorkspaces = useCallback(async () => {
    const ws = await api.listWorkspaces();
    setWorkspaces(ws);
    setCurrent((cur) => {
      if (cur && ws.find((w) => w.id === cur.id)) return cur;
      const saved = localStorage.getItem(WS_KEY);
      return ws.find((w) => w.id === saved) || ws[0] || null;
    });
    return ws;
  }, []);

  const bootstrap = useCallback(async () => {
    if (!getToken()) {
      setReady(true);
      return;
    }
    try {
      setUser(await api.me());
      await reloadWorkspaces();
    } catch {
      clearToken();
      setUser(null);
    } finally {
      setReady(true);
    }
  }, [reloadWorkspaces]);

  useEffect(() => {
    bootstrap();
  }, [bootstrap]);

  const login = useCallback(
    async (email: string, password: string) => {
      const tok = await api.login(email, password);
      setToken(tok.access_token);
      setUser(await api.me());
      await reloadWorkspaces();
    },
    [reloadWorkspaces],
  );

  const register = useCallback(
    async (body: RegisterBody) => {
      await api.register(body);
      await login(body.email, body.password);
    },
    [login],
  );

  const logout = useCallback(() => {
    clearToken();
    localStorage.removeItem(WS_KEY);
    setUser(null);
    setWorkspaces([]);
    setCurrent(null);
  }, []);

  return (
    <AuthContext.Provider
      value={{
        ready,
        user,
        workspaces,
        currentWorkspace,
        setCurrentWorkspace,
        login,
        register,
        logout,
        reloadWorkspaces,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}
