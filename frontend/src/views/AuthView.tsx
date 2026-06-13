import { useState } from "react";
import { Brain, Loader2 } from "lucide-react";
import { useAuth } from "../state/auth";

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
    <div className="auth-wrap">
      <div className="panel auth-card">
        <div className="auth-tag mono">v0.5 · local</div>
        <div className="auth-brand">
          <div className="brand-mark">
            <Brain size={20} />
          </div>
          <div>
            <div className="brand-name" style={{ fontSize: 20 }}>
              Cortex
            </div>
            <div className="brand-sub">KNOWLEDGE COPILOT</div>
          </div>
        </div>

        <h1 className="auth-title">
          {mode === "login" ? "Welcome back" : "Create your account"}
        </h1>
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

          <button
            className="btn btn-primary"
            style={{ width: "100%", justifyContent: "center", marginTop: 6, padding: "12px" }}
            disabled={busy}
          >
            {busy && <Loader2 size={16} className="spin-icon" />}
            {mode === "login" ? "Sign in" : "Create account"}
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
    </div>
  );
}
