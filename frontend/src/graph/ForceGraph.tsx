import { useEffect, useMemo, useRef, useState } from "react";
import {
  forceCenter,
  forceCollide,
  forceLink,
  forceManyBody,
  forceSimulation,
} from "d3-force";
import type { GraphData, GraphEntity } from "../lib/types";

const TYPE_COLOR: Record<string, string> = {
  Person: "#35e0ce",
  Company: "#8e86ff",
  Department: "#38bdf8",
  Project: "#58e1a0",
  Entity: "#7c89a8",
};
export const colorForType = (t: string) => TYPE_COLOR[t] || TYPE_COLOR.Entity;

interface SimNode {
  id: string;
  name: string;
  type: string;
  deg: number;
  x?: number;
  y?: number;
  fx?: number | null;
  fy?: number | null;
}
interface SimLink {
  source: any;
  target: any;
  relation: string;
}

export function ForceGraph({
  data,
  highlightIds,
  selectedId,
  onSelect,
}: {
  data: GraphData;
  highlightIds?: Set<string> | null;
  selectedId?: string | null;
  onSelect?: (e: GraphEntity | null) => void;
}) {
  const wrapRef = useRef<HTMLDivElement>(null);
  const [size, setSize] = useState({ w: 800, h: 600 });
  const [, setTick] = useState(0);
  const [hover, setHover] = useState<string | null>(null);
  const simRef = useRef<any>(null);
  const dragRef = useRef<{ id: string } | null>(null);

  useEffect(() => {
    const el = wrapRef.current;
    if (!el) return;
    const measure = () => setSize({ w: el.clientWidth, h: el.clientHeight });
    const ro = new ResizeObserver(measure);
    ro.observe(el);
    measure();
    return () => ro.disconnect();
  }, []);

  const { nodes, links } = useMemo(() => {
    const byName = new Map<string, SimNode>();
    const ns: SimNode[] = [];
    const ensure = (name: string, type = "Entity"): SimNode => {
      const key = name.toLowerCase();
      let n = byName.get(key);
      if (!n) {
        n = { id: name, name, type, deg: 0 };
        byName.set(key, n);
        ns.push(n);
      } else if (type !== "Entity" && n.type === "Entity") {
        n.type = type;
      }
      return n;
    };
    for (const e of data.entities) ensure(e.name, e.type);
    const ls: SimLink[] = [];
    for (const f of data.facts) {
      const s = ensure(f.source);
      const t = ensure(f.target);
      s.deg++;
      t.deg++;
      ls.push({ source: s.id, target: t.id, relation: f.relation });
    }
    return { nodes: ns, links: ls };
  }, [data]);

  useEffect(() => {
    if (!nodes.length) {
      setTick((t) => t + 1);
      return;
    }
    const sim = forceSimulation(nodes as any)
      .force("charge", forceManyBody().strength(-360))
      .force(
        "link",
        forceLink(links as any)
          .id((d: any) => d.id)
          .distance(98)
          .strength(0.45),
      )
      .force("center", forceCenter(size.w / 2, size.h / 2))
      .force("collide", forceCollide(34))
      .on("tick", () => setTick((t) => t + 1));
    simRef.current = sim;
    sim.alpha(1).restart();
    return () => sim.stop();
  }, [nodes, links, size.w, size.h]);

  const toSvg = (clientX: number, clientY: number) => {
    const rect = wrapRef.current!.getBoundingClientRect();
    return { x: clientX - rect.left, y: clientY - rect.top };
  };
  const onDown = (id: string) => (e: React.PointerEvent) => {
    (e.target as Element).setPointerCapture?.(e.pointerId);
    dragRef.current = { id };
    const n = nodes.find((x) => x.id === id);
    if (n) {
      n.fx = n.x;
      n.fy = n.y;
    }
    simRef.current?.alphaTarget(0.3).restart();
  };
  const onMove = (e: React.PointerEvent) => {
    if (!dragRef.current) return;
    const n = nodes.find((x) => x.id === dragRef.current!.id);
    if (!n) return;
    const p = toSvg(e.clientX, e.clientY);
    n.fx = p.x;
    n.fy = p.y;
  };
  const onUp = () => {
    if (!dragRef.current) return;
    const n = nodes.find((x) => x.id === dragRef.current!.id);
    if (n) {
      n.fx = null;
      n.fy = null;
    }
    dragRef.current = null;
    simRef.current?.alphaTarget(0);
  };

  const adj = useMemo(() => {
    const m = new Map<string, Set<string>>();
    for (const l of links) {
      const s = typeof l.source === "object" ? l.source.id : l.source;
      const t = typeof l.target === "object" ? l.target.id : l.target;
      if (!m.has(s)) m.set(s, new Set());
      if (!m.has(t)) m.set(t, new Set());
      m.get(s)!.add(t);
      m.get(t)!.add(s);
    }
    return m;
  }, [links]);

  const focus = hover || selectedId || null;
  const isDim = (id: string) =>
    !!focus && id !== focus && !adj.get(focus)?.has(id);
  const highlighted = (id: string) =>
    !!highlightIds && (highlightIds.has(id) || highlightIds.has(id.toLowerCase()));

  return (
    <div
      className="graph-canvas"
      ref={wrapRef}
      style={{ width: "100%", height: "100%" }}
      onPointerMove={onMove}
      onPointerUp={onUp}
      onPointerLeave={onUp}
      onClick={() => onSelect?.(null)}
    >
      <svg viewBox={`0 0 ${size.w} ${size.h}`} width={size.w} height={size.h}>
        <defs>
          <filter id="cx-glow" x="-60%" y="-60%" width="220%" height="220%">
            <feGaussianBlur stdDeviation="4" result="b" />
            <feMerge>
              <feMergeNode in="b" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>

        <g>
          {links.map((l, i) => {
            const s = typeof l.source === "object" ? l.source : nodes.find((n) => n.id === l.source);
            const t = typeof l.target === "object" ? l.target : nodes.find((n) => n.id === l.target);
            if (!s || !t) return null;
            const active = !!focus && (s.id === focus || t.id === focus);
            const dim = !!focus && !active;
            const mx = ((s.x || 0) + (t.x || 0)) / 2;
            const my = ((s.y || 0) + (t.y || 0)) / 2;
            return (
              <g key={i} opacity={dim ? 0.12 : 1}>
                <line
                  x1={s.x}
                  y1={s.y}
                  x2={t.x}
                  y2={t.y}
                  stroke={active ? "#35e0ce" : "rgba(255,255,255,0.16)"}
                  strokeWidth={active ? 1.6 : 1}
                />
                {(active || nodes.length <= 26) && (
                  <text className="edge-label" x={mx} y={my} textAnchor="middle">
                    {l.relation}
                  </text>
                )}
              </g>
            );
          })}
        </g>

        <g>
          {nodes.map((n) => {
            const c = colorForType(n.type);
            const r = 11 + Math.min(n.deg, 6) * 1.6;
            return (
              <g
                key={n.id}
                transform={`translate(${n.x || 0},${n.y || 0})`}
                opacity={isDim(n.id) ? 0.25 : 1}
                style={{ cursor: "grab" }}
                onPointerDown={onDown(n.id)}
                onClick={(e) => {
                  e.stopPropagation();
                  onSelect?.({ id: n.id, name: n.name, type: n.type });
                }}
                onPointerEnter={() => setHover(n.id)}
                onPointerLeave={() => setHover((h) => (h === n.id ? null : h))}
              >
                {highlighted(n.id) && (
                  <circle r={r + 7} fill="none" stroke={c} strokeWidth={2} opacity={0.55} />
                )}
                <circle
                  r={r}
                  fill={c}
                  filter="url(#cx-glow)"
                  stroke={selectedId === n.id ? "#fff" : "rgba(255,255,255,0.5)"}
                  strokeWidth={selectedId === n.id ? 2 : 1}
                />
                <text className="node-label" y={r + 15} textAnchor="middle">
                  {n.name}
                </text>
              </g>
            );
          })}
        </g>
      </svg>
    </div>
  );
}
