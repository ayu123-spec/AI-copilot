import { useState } from "react";
import {
  ArrowRight,
  Brain,
  Database,
  Loader2,
  Network,
  Sparkles,
  Workflow,
} from "lucide-react";
import { useAuth } from "../state/auth";

const FEATURES = [
  { icon: Sparkles, label: "Retrieval-augmented answers" },
  { icon: Workflow, label: "Autonomous research agents" },
  { icon: Network, label: "Live knowledge graph" },
  { icon: Database, label: "Long-term memory" },
];

export function AuthView() {
  const { login, register } = useAuth();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [org, setOrg] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      if (mode === "login") {
        await login(email.trim(), password);
      } else {
        await register({
          email: email.trim(),
          password,
          full_name: fullName.trim(),
          organization_name: org.trim(),
        });
      }
    } catch (err: any) {
      setError(err?.message || "Something went wrong");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="auth-shell">
      <div className="auth-grid-bg" />
      <div className="auth-glow auth-glow-1" />
      <div className="auth-glow auth-glow-2" />

      {/* Left: brand hero */}
      <aside className="auth-hero">
        <div className="auth-hero-inner">
          <div className="auth-brand">
            <div className="brand-mark">
              <Brain size={22} />
            </div>
            <div>
              <div className="brand-name" style={{ fontSize: 21 }}>
                Cortex
              </div>
            </div>
          </div>

          <h1 className="auth-headline">
            Turn your documents into an <span className="grad-text">expert that thinks</span>.
          </h1>
          <p className="auth-hero-sub">
            An agentic knowledge platform — retrieval, reasoning, and a living graph
            of everything your team knows.
          </p>

          <ul className="auth-features">
            {FEATURES.map((f) => (
              <li key={f.label} className="auth-feature">
                <span className="auth-feature-ico">
                  <f.icon size={15} />
                </span>
                {f.label}
              </li>
            ))}
          </ul>

          <div className="auth-foot mono">Built for teams · Secure by design</div>
        </div>
      </aside>

      {/* Right: form */}
      <main className="auth-main">
        <div className="auth-glass">
          <div className="auth-tag mono">{mode === "login" ? "SIGN IN" : "GET STARTED"}</div>
          <h2 className="auth-title">
            {mode === "login" ? "Welcome back" : "Create your account"}
          </h2>
          <p className="auth-sub">
            {mode === "login"
              ? "Sign in to your organization's knowledge workspace."
              : "Spin up an organization and start building knowledge."}
          </p>

          {error && <div className="auth-error">{error}</div>}

          <form onSubmit={submit}>
            {mode === "register" && (
              <>
                <div className="field">
                  <label className="label">Full name</label>
                  <input
                    className="input"
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    placeholder="Ada Lovelace"
                    required
                  />
                </div>
                <div className="field">
                  <label className="label">Organization</label>
                  <input
                    className="input"
                    value={org}
                    onChange={(e) => setOrg(e.target.value)}
                    placeholder="Acme Inc."
                    required
                  />
                </div>
              </>
            )}
            <div className="field">
              <label className="label">Email</label>
              <input
                className="input"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@company.com"
                required
              />
            </div>
            <div className="field">
              <label className="label">Password</label>
              <input
                className="input"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder={mode === "register" ? "At least 8 characters" : "••••••••"}
                minLength={8}
                required
              />
            </div>

            <button className="btn btn-primary auth-submit" disabled={busy}>
              {busy ? (
                <Loader2 size={17} className="spin-icon" />
              ) : (
                <>
                  {mode === "login" ? "Sign in" : "Create account"}
                  <ArrowRight size={17} />
                </>
              )}
            </button>
          </form>

          <div className="auth-switch">
            {mode === "login" ? "New to Cortex?" : "Already have an account?"}{" "}
            <button
              onClick={() => {
                setMode(mode === "login" ? "register" : "login");
                setError("");
              }}
            >
              {mode === "login" ? "Create an account" : "Sign in"}
            </button>
          </div>
        </div>
      </main>
    </div>
  );
}
