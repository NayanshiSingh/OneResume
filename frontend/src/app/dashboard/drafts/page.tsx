"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { FileText, Trash2 } from "lucide-react";
import { draftsApi, type DraftSummary } from "@/lib/api";
import styles from "./drafts.module.css";

export default function DraftsPage() {
    const [drafts, setDrafts] = useState<DraftSummary[] | null>(null);
    const [error, setError] = useState("");

    useEffect(() => {
        draftsApi.list().then(setDrafts).catch((err: unknown) => setError((err as Error).message));
    }, []);

    async function remove(draft: DraftSummary) {
        if (!window.confirm(`Delete the draft for ${draft.job_title}? Exported resumes are kept.`)) return;
        try {
            await draftsApi.delete(draft.id);
            setDrafts((current) => current?.filter((d) => d.id !== draft.id) ?? null);
        } catch (err: unknown) {
            setError((err as Error).message);
        }
    }

    return (
        <div>
            <div className={styles.pageHeader}>
                <span className="mono-label">DASHBOARD / DRAFTS</span>
                <h1 className={`headline ${styles.pageTitle}`}>DRAFTS</h1>
                <p className="body-text" style={{ marginTop: 8 }}>
                    Drafts are proposals. Review and approve one before exporting it. <Link href="/dashboard/analyze" className={styles.link}>Start a new draft</Link>.
                </p>
            </div>
            {error && <p className="mono-label" style={{ color: "#ef4444" }}>ERROR: {error}</p>}
            {drafts === null ? (
                <span className="mono-label loading-pulse">LOADING...</span>
            ) : drafts.length === 0 ? (
                <p className="body-text">No drafts yet.</p>
            ) : (
                <div className={styles.list}>
                    {drafts.map((d) => (
                        <div key={d.id} className={styles.row}>
                            <Link href={`/dashboard/drafts/${d.id}`} className={styles.rowMain}>
                                <FileText size={14} opacity={0.4} />
                                <span className={styles.rowTitle}>{d.job_title}</span>
                                <span className="badge">{d.status === "approved" ? "APPROVED" : "IN REVIEW"}</span>
                                {d.matching_mode === "basic" && <span className="badge">BASIC MATCHING</span>}
                                <span className="mono-label">REV {d.revision} · {new Date(d.updated_at).toLocaleString()}</span>
                            </Link>
                            <button className="btn-danger btn-sm" aria-label="Delete draft" onClick={() => remove(d)}><Trash2 size={12} /></button>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}
