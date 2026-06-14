import { useCallback, useEffect, useRef, useState } from "react";
import { FileText, Image as ImageIcon, Search, Trash2, UploadCloud } from "lucide-react";
import { api } from "../lib/api";
import { useAuth } from "../state/auth";
import { useToast } from "../state/toast";
import type { Doc, SearchResult } from "../lib/types";

export function LibraryView() {
  const { currentWorkspace } = useAuth();
  const { push } = useToast();
  const ws = currentWorkspace!.id;

  const [docs, setDocs] = useState<Doc[]>([]);
  const [loading, setLoading] = useState(true);
  const [drag, setDrag] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[] | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setDocs(await api.listDocuments(ws));
    } catch (e: any) {
      push(e.message || "Couldn't load documents", "error");
    } finally {
      setLoading(false);
    }
  }, [ws, push]);

  useEffect(() => {
    load();
  }, [load]);

  const upload = async (files: FileList | File[]) => {
    const list = Array.from(files);
    if (!list.length) return;
    setUploading(true);
    for (const f of list) {
      try {
        await api.uploadDocument(ws, f);
        push(`Uploaded ${f.name}`, "success");
      } catch (e: any) {
        push(`${f.name}: ${e.message}`, "error");
      }
    }
    setUploading(false);
    load();
  };

  const remove = async (d: Doc) => {
    try {
      await api.deleteDocument(d.id);
      setDocs((x) => x.filter((y) => y.id !== d.id));
      push("Document removed", "success");
    } catch (e: any) {
      push(e.message || "Delete failed", "error");
    }
  };

  const runSearch = async () => {
    if (!query.trim()) {
      setResults(null);
      return;
    }
    try {
      setResults(await api.search(ws, query.trim(), 8));
    } catch (e: any) {
      push(e.message || "Search failed", "error");
    }
  };

  return (
    <div className="page">
      <div className="page-narrow">
        <div
          className={`dropzone ${drag ? "drag" : ""}`}
          onClick={() => fileRef.current?.click()}
          onDragOver={(e) => {
            e.preventDefault();
            setDrag(true);
          }}
          onDragLeave={() => setDrag(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDrag(false);
            upload(e.dataTransfer.files);
          }}
        >
          <div className="dropzone-icon">
            <UploadCloud size={24} />
          </div>
          <div style={{ fontWeight: 600, fontSize: 15.5 }}>
            {uploading ? "Uploading…" : "Drop files or click to upload"}
          </div>
          <div className="dim" style={{ fontSize: 13, marginTop: 5 }}>
            PDF, DOCX, PPTX, TXT, Markdown, and images (PNG/JPG) — chunked,
            described, embedded, and made searchable
          </div>
          <input
            ref={fileRef}
            type="file"
            multiple
            hidden
            onChange={(e) => e.target.files && upload(e.target.files)}
          />
        </div>

        <div className="section-row" style={{ marginTop: 26 }}>
          <h3>Documents</h3>
          <div className="graph-search" style={{ maxWidth: 320, background: "var(--panel-2)" }}>
            <Search size={15} className="dim" />
            <input
              placeholder="Search this workspace…"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && runSearch()}
            />
          </div>
        </div>

        {results && (
          <div className="doc-list" style={{ marginBottom: 26 }}>
            {results.length === 0 && (
              <div className="dim" style={{ fontSize: 14 }}>
                No matching passages.
              </div>
            )}
            {results.map((r, i) => (
              <div className="doc-row" key={i} style={{ alignItems: "flex-start" }}>
                <div
                  className="doc-icon"
                  style={r.modality === "image" ? { color: "var(--violet)" } : undefined}
                >
                  {r.modality === "image" ? <ImageIcon size={16} /> : <FileText size={16} />}
                </div>
                <div className="doc-meta">
                  <div className="msg-text" style={{ fontSize: 13.5 }}>
                    {r.text}
                  </div>
                  <div className="doc-sub">
                    {r.source || "document"}
                    {r.page_number != null ? ` · p.${r.page_number}` : ""}
                    {r.modality === "image" ? " · image" : ""} · score{" "}
                    {r.score.toFixed(3)}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {loading ? (
          <div className="center-load" style={{ height: 160 }}>
            <div className="spinner" />
          </div>
        ) : docs.length === 0 ? (
          <div className="dim" style={{ fontSize: 14, padding: "20px 2px" }}>
            No documents yet. Upload a file to start building this workspace's knowledge.
          </div>
        ) : (
          <div className="doc-list">
            {docs.map((d) => (
              <div className="doc-row" key={d.id}>
                <div className="doc-icon">
                  <FileText size={18} />
                </div>
                <div className="doc-meta">
                  <div className="doc-name">{d.filename}</div>
                  <div className="doc-sub">
                    {d.num_chunks} chunk{d.num_chunks === 1 ? "" : "s"} · {d.content_type}
                  </div>
                </div>
                <span className={`status ${d.status}`}>{d.status}</span>
                <button className="btn-icon btn-ghost" title="Remove" onClick={() => remove(d)}>
                  <Trash2 size={16} className="dim" />
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
