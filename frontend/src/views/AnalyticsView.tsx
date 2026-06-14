import { useEffect, useState } from "react";
import {
  Clock,
  Database,
  FileText,
  MessageSquare,
  ThumbsDown,
  ThumbsUp,
  TrendingUp,
} from "lucide-react";
import { api } from "../lib/api";
import { useAuth } from "../state/auth";
import type { AnalyticsSummary, CountItem, TimePoint } from "../lib/types";

const pretty = (s: string) =>
  s
    .split("_")
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");

export function AnalyticsView() {
  const { currentWorkspace } = useAuth();
  const ws = currentWorkspace!.id;
  const [data, setData] = useState<AnalyticsSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    setLoading(true);
    api
      .getAnalytics(ws)
      .then((d) => alive && setData(d))
      .catch((e) => alive && setErr(e.message || "Failed to load analytics"))
      .finally(() => alive && setLoading(false));
    return () => {
      alive = false;
    };
  }, [ws]);

  if (loading) {
    return (
      <div className="center-load">
        <div className="spinner" />
      </div>
    );
  }
  if (err || !data) {
    return <div className="dash-empty">{err || "No data."}</div>;
  }

  const latency =
    data.avg_latency_ms == null ? "—" : `${data.avg_latency_ms} ms`;

  return (
    <div className="dash">
      <div className="stat-grid">
        <Stat icon={<TrendingUp size={18} />} value={data.total_queries} label="Total queries" />
        <Stat icon={<Clock size={18} />} value={latency} label="Avg response time" />
        <Stat
          icon={<MessageSquare size={18} />}
          value={data.conversations}
          label="Conversations"
        />
        <Stat
          icon={<FileText size={18} />}
          value={data.documents}
          label={`Documents · ${data.chunks_total} chunks`}
        />
      </div>

      <div className="dash-card full">
        <h3>Queries over time</h3>
        <Bars activity={data.activity} />
      </div>

      <div className="dash-grid">
        <div className="dash-card">
          <h3>Query types detected</h3>
          {data.query_type_mix.length ? (
            <BarList items={data.query_type_mix} color="var(--teal)" labelFmt={pretty} />
          ) : (
            <div className="dash-empty">No chats classified yet — ask something in Chat.</div>
          )}
        </div>

        <div className="dash-card">
          <h3>Agent usage</h3>
          {data.agent_mix.length ? (
            <BarList items={data.agent_mix} color="var(--amber)" labelFmt={pretty} />
          ) : (
            <div className="dash-empty">No agent runs yet — try the Agents toggle in Chat.</div>
          )}
        </div>

        <div className="dash-card">
          <h3>Message volume</h3>
          <BarList
            items={[
              { label: "You", count: data.messages_user },
              { label: "Cortex", count: data.messages_assistant },
            ]}
            color="var(--teal)"
          />
        </div>

        <div className="dash-card">
          <h3>Answer feedback</h3>
          <div className="feedback-row">
            <div className="fb up">
              <ThumbsUp size={18} />
              <span>{data.feedback_up}</span>
            </div>
            <div className="fb down">
              <ThumbsDown size={18} />
              <span>{data.feedback_down}</span>
            </div>
            <div className="fb neutral">
              <Database size={16} />
              <span>{data.agent_runs} agent runs</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function Stat({
  icon,
  value,
  label,
}: {
  icon: React.ReactNode;
  value: number | string;
  label: string;
}) {
  return (
    <div className="stat-card">
      <div className="stat-ico">{icon}</div>
      <div className="stat-val">{value}</div>
      <div className="stat-lbl">{label}</div>
    </div>
  );
}

function BarList({
  items,
  color,
  labelFmt,
}: {
  items: CountItem[];
  color: string;
  labelFmt?: (s: string) => string;
}) {
  const max = Math.max(1, ...items.map((i) => i.count));
  return (
    <div className="barlist">
      {items.map((it) => (
        <div className="barrow" key={it.label}>
          <div className="barrow-label">{labelFmt ? labelFmt(it.label) : it.label}</div>
          <div className="barrow-track">
            <div
              className="barrow-fill"
              style={{ width: `${(it.count / max) * 100}%`, background: color }}
            />
          </div>
          <div className="barrow-count">{it.count}</div>
        </div>
      ))}
    </div>
  );
}

function Bars({ activity }: { activity: TimePoint[] }) {
  if (!activity.length) {
    return <div className="dash-empty">No activity yet. Start a chat to see your usage trend.</div>;
  }
  const max = Math.max(1, ...activity.map((a) => a.count));
  const show = activity.slice(-21); // last few weeks
  return (
    <div className="vbars">
      {show.map((a) => {
        const label = a.date.slice(5); // MM-DD
        return (
          <div className="vbar-col" key={a.date} title={`${a.date}: ${a.count}`}>
            <div className="vbar-wrap">
              <div className="vbar" style={{ height: `${(a.count / max) * 100}%` }} />
            </div>
            <div className="vbar-x">{label}</div>
          </div>
        );
      })}
    </div>
  );
}
