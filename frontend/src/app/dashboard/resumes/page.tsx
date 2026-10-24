"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Download, FileText, GitCompare, RotateCcw, Send, Trash2 } from "lucide-react";
import { resumesApi, type Resume, type VersionComparison } from "@/lib/api";
import styles from "./page.module.css";

const CHANGE_LABELS: Record<VersionComparison["changes"][number]["kind"], string> = {
    added_entry: "+ entry",
    removed_entry: "− entry",
    added_bullet: "+",
    removed_bullet: "−",
    added_skill: "+ skill",
    removed_skill: "− skill",
};

function formatDate(d: string) {
    return new Date(d).toLocaleDateString("en-US", { year: "numeric", month: "short", day: "numeric" });
}

function groupByRole(resumes: Resume[]): [string, Resume[]][] {
    const groups = new Map<string, Resume[]>();
    for (const r of resumes) groups.set(r.job_title, [...(groups.get(r.job_title) ?? []), r]);
    return [...groups.entries()].map(([title, versions]) => [title, versions.sort((a, b) => b.version - a.version)]);
}

function VersionRow({ resume, previous, onChange, onRemove, onError }: {
    resume: Resume;
    previous?: Resume;
    onChange: (r: Resume) => void;
    onRemove: (r: Resume) => void;
    onError: (message: string) => void;
}) {
    const router = useRouter();
    const [comparison, setComparison] = useState<VersionComparison | null>(null);
    const [sentDate, setSentDate] = useState(resume.sent_at?.slice(0, 10) ?? "");

    async function attempt(action: () => Promise<void>) {
        try {
            await action();
        } catch (err: unknown) {
            onError((err as Error).message);
        }
    }

    return (
        <div className={styles.version}>
            <div className={styles.versionHead}>
                <span className="badge badge-accent">V.{String(resume.version).padStart(2, "0")}</span>
                <span className="mono-label">{formatDate(resume.created_at)}</span>
                {resume.pdf_pages != null && <span className="mono-label">{resume.pdf_pages} PAGE(S)</span>}
                {resume.sent_at && <span className="badge">SENT {formatDate(resume.sent_at)}</span>}
                <span style={{ flex: 1 }} />
                {resume.formats.map((f) => (
                    <a key={f} href={resumesApi.downloadUrl(resume.id, f)} className={`${f === "pdf" ? "btn-primary" : "btn-outline"} btn-sm`}>
                        <Download size={12} /> {f.toUpperCase()}
                    </a>
                ))}
                {previous && previous.can_restore && resume.can_restore && (
                    <button className="btn-outline btn-sm" onClick={() => attempt(async () => {
                        setComparison(comparison ? null : await resumesApi.compare(previous.id, resume.id));
                    })}>
                        <GitCompare size={12} /> {comparison ? "HIDE CHANGES" : `CHANGES SINCE V.${String(previous.version).padStart(2, "0")}`}
                    </button>
                )}
                {resume.can_restore && (
                    <button className="btn-outline btn-sm" title="Start a new draft from this version"
                        onClick={() => attempt(async () => router.push(`/dashboard/drafts/${(await resumesApi.restore(resume.id)).id}`))}>
                        <RotateCcw size={12} /> RESTORE
                    </button>
                )}
                <button className="btn-danger btn-sm" aria-label="Delete version" onClick={() => onRemove(resume)}><Trash2 size={12} /></button>
            </div>

            {resume.warnings.map((w) => <span key={w} className={styles.warning}>⚠ {w}</span>)}

            <form className={styles.sentRow} onSubmit={(e) => {
                e.preventDefault();
                attempt(async () => onChange(await resumesApi.setSent(resume.id, sentDate ? `${sentDate}T00:00:00` : null)));
            }}>
                <label className="mono-label">SENT ON</label>
                <input type="date" className="input" value={sentDate} onChange={(e) => setSentDate(e.target.value)} />
                <button type="submit" className="btn-outline btn-sm"><Send size={12} /> SAVE</button>
            </form>

            {comparison && (
                <ul className={styles.changes}>
                    {comparison.changes.length === 0 && <li>No content changes.</li>}
                    {comparison.changes.map((c, i) => (
                        <li key={i} className={c.kind.startsWith("added") ? styles.added : styles.removed}>
                            <span className="mono-label">{CHANGE_LABELS[c.kind]}</span> {c.entry && c.kind.endsWith("bullet") ? `${c.entry}: ` : ""}{c.text}
                        </li>
                    ))}
                </ul>
            )}
        </div>
    );
}

export default function ResumesPage() {
    const [resumes, setResumes] = useState<Resume[] | null>(null);
    const [error, setError] = useState("");

    useEffect(() => {
        resumesApi.list().then(setResumes).catch((err: unknown) => setError((err as Error).message));
    }, []);

    async function remove(resume: Resume) {
        if (!window.confirm(`Delete ${resume.job_title} v${resume.version}? This removes its files.`)) return;
        try {
            await resumesApi.delete(resume.id);
            setResumes((current) => current?.filter((r) => r.id !== resume.id) ?? null);
        } catch (err: unknown) {
            setError((err as Error).message);
        }
    }

    const replace = (updated: Resume) => setResumes((current) => current?.map((r) => (r.id === updated.id ? updated : r)) ?? null);

    return (
        <div>
            <div className={styles.pageHeader}>
                <span className="mono-label">DASHBOARD / MY_RESUMES</span>
                <h1 className={`headline ${styles.pageTitle}`}>RESUME HISTORY</h1>
                <p className="body-text" style={{ marginTop: 8 }}>
                    Every export is kept as a version. Compare versions, record when you sent one, or restore one as a new draft.
                </p>
            </div>

            {error && <div className={styles.errorBar}><span className="mono-label" style={{ color: "#ef4444" }}>ERROR: {error}</span></div>}

            {resumes === null ? (
                <span className="mono-label loading-pulse">LOADING_RESUMES...</span>
            ) : resumes.length === 0 ? (
                <div className={styles.emptyState}>
                    <FileText size={32} opacity={0.15} />
                    <span className="mono-label" style={{ marginTop: 12 }}>NO_RESUMES_YET</span>
                    <p className="body-text" style={{ marginTop: 8 }}>Approve and export a draft to create your first version.</p>
                </div>
            ) : (
                groupByRole(resumes).map(([title, versions]) => (
                    <section key={title} className={styles.role}>
                        <h2 className={styles.jobTitle}>{title}</h2>
                        {versions.map((r, i) => (
                            <VersionRow key={r.id} resume={r} previous={versions[i + 1]} onChange={replace} onRemove={remove} onError={setError} />
                        ))}
                    </section>
                ))
            )}
        </div>
    );
}
