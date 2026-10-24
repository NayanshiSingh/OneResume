"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Check, Plus, Search, Sparkles, X } from "lucide-react";
import { EvidenceBadge, Notices } from "@/components/Notices";
import { draftsApi, jdApi, jobsApi, type CoverageItem, type JDAnalysis, type JDStructured, type Job } from "@/lib/api";
import styles from "./page.module.css";

const POLL_MS = 1500;

function RequirementList({ title, items, onChange }: { title: string; items: string[]; onChange: (items: string[]) => void }) {
    const [draft, setDraft] = useState("");
    return (
        <div className={styles.skillBlock}>
            <span className="mono-label">{title}</span>
            <div className={styles.tagGrid}>
                {items.map((item) => (
                    <span key={item} className={styles.mustTag}>
                        {item}
                        <button className={styles.tagRemove} aria-label={`Remove ${item}`} onClick={() => onChange(items.filter((i) => i !== item))}>
                            <X size={10} />
                        </button>
                    </span>
                ))}
            </div>
            <form className={styles.addRow} onSubmit={(e) => {
                e.preventDefault();
                const value = draft.trim();
                if (value && !items.includes(value)) onChange([...items, value]);
                setDraft("");
            }}>
                <input className="input" placeholder='Add a requirement, e.g. "Python or Java"' value={draft} onChange={(e) => setDraft(e.target.value)} />
                <button type="submit" className="btn-outline btn-sm" disabled={!draft.trim()}><Plus size={12} /></button>
            </form>
        </div>
    );
}

export default function AnalyzePage() {
    const router = useRouter();
    const [rawText, setRawText] = useState("");
    const [analysis, setAnalysis] = useState<JDAnalysis | null>(null);
    const [review, setReview] = useState<JDStructured | null>(null);
    const [coverage, setCoverage] = useState<CoverageItem[] | null>(null);
    const [pageTarget, setPageTarget] = useState<1 | 2>(1);
    const [job, setJob] = useState<Job | null>(null);
    const [busy, setBusy] = useState(false);
    const [error, setError] = useState("");

    async function attempt(action: () => Promise<void>) {
        setBusy(true);
        setError("");
        try {
            await action();
        } catch (err: unknown) {
            setError((err as Error).message);
        } finally {
            setBusy(false);
        }
    }

    const analyze = () => attempt(async () => {
        const result = await jdApi.analyze(rawText);
        setAnalysis(result);
        setReview(result.structured_data);
        setCoverage(null);
        setJob(null);
    });

    const saveReview = () => attempt(async () => {
        if (!analysis || !review) return;
        const reviewed = { ...review, keywords: [...review.must_have_skills, ...review.nice_to_have_skills] };
        setAnalysis(await jdApi.saveReview(analysis.id, reviewed));
        setCoverage(await jdApi.coverage(analysis.id));
    });

    async function waitFor(current: Job): Promise<Job> {
        while (current.status === "queued" || current.status === "running") {
            setJob(current);
            await new Promise((resolve) => setTimeout(resolve, POLL_MS));
            current = await jobsApi.get(current.id);
        }
        setJob(current);
        return current;
    }

    const createDraft = (retryJob?: Job) => attempt(async () => {
        if (!analysis) return;
        const started = retryJob ? await jobsApi.retry(retryJob.id) : await draftsApi.request(analysis.id, pageTarget, crypto.randomUUID());
        const finished = await waitFor(started);
        if (finished.status === "succeeded" && finished.result_id) router.push(`/dashboard/drafts/${finished.result_id}`);
        else setError(finished.error ?? "Draft generation failed.");
    });

    return (
        <div>
            <div className={styles.pageHeader}>
                <span className="mono-label">DASHBOARD / JOB_DESCRIPTION</span>
                <h1 className={`headline ${styles.pageTitle}`}>JOB DESCRIPTION</h1>
                <p className="body-text" style={{ marginTop: 8 }}>
                    Paste a posting, check the requirements we found, then create a draft from your profile.
                </p>
            </div>

            <div className={styles.inputSection}>
                <label className="label">1 · PASTE_THE_POSTING</label>
                <textarea className="textarea" style={{ minHeight: 200 }} value={rawText} onChange={(e) => setRawText(e.target.value)}
                    placeholder="Paste the full job description, including requirements and nice-to-haves." />
                <div className={styles.inputActions}>
                    <span className="mono-label">{rawText.length} CHARS</span>
                    <button className="btn-primary" onClick={analyze} disabled={busy || rawText.trim().length < 20}>
                        <Search size={14} /> ANALYZE
                    </button>
                </div>
            </div>

            {error && <div className={styles.errorBar}><span className="mono-label" style={{ color: "#ef4444" }}>ERROR: {error}</span></div>}

            {analysis && review && (
                <div className={styles.results}>
                    <span className="label">2 · CHECK_THE_REQUIREMENTS</span>
                    <Notices mode={analysis.analysis_mode} warnings={analysis.warnings} />
                    <div className="form-group">
                        <label className="label">ROLE_TITLE</label>
                        <input className="input" value={review.role_title} onChange={(e) => setReview({ ...review, role_title: e.target.value })} />
                    </div>
                    <div className={styles.skillsSection}>
                        <RequirementList title="REQUIRED" items={review.must_have_skills}
                            onChange={(must_have_skills) => setReview({ ...review, must_have_skills })} />
                        <RequirementList title="NICE_TO_HAVE" items={review.nice_to_have_skills}
                            onChange={(nice_to_have_skills) => setReview({ ...review, nice_to_have_skills })} />
                    </div>
                    <button className="btn-primary" onClick={saveReview} disabled={busy}>
                        <Check size={14} /> {analysis.reviewed ? "SAVE CHANGES" : "CONFIRM REQUIREMENTS"}
                    </button>
                </div>
            )}

            {analysis && coverage && (
                <div className={styles.results}>
                    <span className="label">3 · HOW_YOUR_PROFILE_COVERS_IT</span>
                    <p className="body-text">These labels describe the evidence in your profile, not your real ability.</p>
                    <div className={styles.coverageTable}>
                        {coverage.map((item) => (
                            <div key={`${item.importance}-${item.requirement}`} className={styles.coverageRow}>
                                <span className={styles.coverageReq}>
                                    {item.requirement}
                                    <span className="mono-label"> {item.importance === "required" ? "REQUIRED" : "PREFERRED"}</span>
                                </span>
                                <EvidenceBadge label={item.label} />
                                <span className={styles.coverageEvidence}>
                                    {item.label === "needs_confirmation" ? "Only in your skills list." : item.evidence[0]?.text ?? "No evidence in your profile."}
                                </span>
                            </div>
                        ))}
                    </div>

                    <div className={styles.inputActions}>
                        <label className="label">
                            PAGE_TARGET{" "}
                            <select className="input" value={pageTarget} onChange={(e) => setPageTarget(Number(e.target.value) as 1 | 2)}>
                                <option value={1}>1 page</option>
                                <option value={2}>2 pages</option>
                            </select>
                        </label>
                        {job?.status === "failed" ? (
                            <button className="btn-primary btn-accent" onClick={() => createDraft(job)} disabled={busy}>RETRY</button>
                        ) : (
                            <button className="btn-primary btn-accent" onClick={() => createDraft()} disabled={busy}>
                                <Sparkles size={14} /> {job && busy ? `${job.status.toUpperCase()}...` : "CREATE DRAFT"}
                            </button>
                        )}
                    </div>
                </div>
            )}
        </div>
    );
}
