"use client";

import { useState } from "react";
import { Search, Zap, Tag, Star, Hash, Briefcase } from "lucide-react";
import { jdApi, type JDAnalysis } from "@/lib/api";
import styles from "./page.module.css";

export default function AnalyzePage() {
    const [rawText, setRawText] = useState("");
    const [loading, setLoading] = useState(false);
    const [result, setResult] = useState<JDAnalysis | null>(null);
    const [error, setError] = useState("");

    async function handleAnalyze() {
        if (rawText.trim().length < 20) {
            setError("JD text must be at least 20 characters.");
            return;
        }
        setLoading(true);
        setError("");
        setResult(null);
        try {
            const r = await jdApi.analyze(rawText);
            setResult(r);
        } catch (err: unknown) {
            setError((err as Error).message);
        } finally {
            setLoading(false);
        }
    }

    return (
        <div>
            <div className={styles.pageHeader}>
                <span className="mono-label">DASHBOARD / ANALYZE_JD</span>
                <h1 className={`headline ${styles.pageTitle}`}>JD ANALYSIS</h1>
                <p className="body-text" style={{ marginTop: 8 }}>
                    Paste a job description below to extract structured data using AI.
                </p>
            </div>

            {/* ── Input ────────────────────────────────────────────── */}
            <div className={styles.inputSection}>
                <label className="label">RAW_JOB_DESCRIPTION</label>
                <textarea
                    className="textarea"
                    style={{ minHeight: 240 }}
                    value={rawText}
                    onChange={(e) => setRawText(e.target.value)}
                    placeholder="Paste the full job description text here...&#10;&#10;Include role title, requirements, skills needed, etc."
                />
                <div className={styles.inputActions}>
                    <span className="mono-label">
                        {rawText.length} CHARS
                    </span>
                    <button
                        className="btn-primary"
                        onClick={handleAnalyze}
                        disabled={loading}
                    >
                        {loading ? (
                            <span className="loading-pulse">ANALYZING...</span>
                        ) : (
                            <>
                                <Search size={14} /> ANALYZE
                            </>
                        )}
                    </button>
                </div>
            </div>

            {error && (
                <div className={styles.errorBar}>
                    <span className="mono-label" style={{ color: "#ef4444" }}>
                        ERROR: {error}
                    </span>
                </div>
            )}

            {/* ── Results ──────────────────────────────────────────── */}
            {result && (
                <div className={styles.results}>
                    <div className={styles.resultsHeader}>
                        <span className="mono-label">ANALYSIS_RESULT</span>
                        <span className="badge badge-success">COMPLETE</span>
                    </div>

                    <div className={styles.resultGrid}>
                        <div className={styles.resultCard}>
                            <div className={styles.resultCardHead}>
                                <Briefcase size={14} />
                                <span className="mono-label">ROLE_TITLE</span>
                            </div>
                            <span className={styles.resultValue}>
                                {result.structured_data.role_title || "—"}
                            </span>
                        </div>

                        <div className={styles.resultCard}>
                            <div className={styles.resultCardHead}>
                                <Star size={14} />
                                <span className="mono-label">EXPERIENCE_LEVEL</span>
                            </div>
                            <span className={styles.resultValue}>
                                {result.structured_data.experience_level || "—"}
                            </span>
                        </div>

                        <div className={styles.resultCard}>
                            <div className={styles.resultCardHead}>
                                <Hash size={14} />
                                <span className="mono-label">ROLE_CATEGORY</span>
                            </div>
                            <span className={styles.resultValue}>
                                {result.structured_data.role_category || "—"}
                            </span>
                        </div>

                        <div className={styles.resultCard}>
                            <div className={styles.resultCardHead}>
                                <Zap size={14} />
                                <span className="mono-label">JD_ID</span>
                            </div>
                            <span className={styles.resultValue} style={{ fontSize: 11, letterSpacing: '0.05em' }}>
                                {result.id}
                            </span>
                        </div>
                    </div>

                    {/* Skills */}
                    <div className={styles.skillsSection}>
                        <div className={styles.skillBlock}>
                            <span className="mono-label">MUST_HAVE_SKILLS</span>
                            <div className={styles.tagGrid}>
                                {result.structured_data.must_have_skills.map((s, i) => (
                                    <span key={i} className={styles.mustTag}>
                                        {s}
                                    </span>
                                ))}
                                {result.structured_data.must_have_skills.length === 0 && (
                                    <span className="mono-label">NONE_DETECTED</span>
                                )}
                            </div>
                        </div>

                        <div className={styles.skillBlock}>
                            <span className="mono-label">NICE_TO_HAVE_SKILLS</span>
                            <div className={styles.tagGrid}>
                                {result.structured_data.nice_to_have_skills.map((s, i) => (
                                    <span key={i} className={styles.niceTag}>
                                        {s}
                                    </span>
                                ))}
                                {result.structured_data.nice_to_have_skills.length === 0 && (
                                    <span className="mono-label">NONE_DETECTED</span>
                                )}
                            </div>
                        </div>

                        <div className={styles.skillBlock}>
                            <span className="mono-label">KEYWORDS</span>
                            <div className={styles.tagGrid}>
                                {result.structured_data.keywords.map((k, i) => (
                                    <span key={i} className={styles.keyTag}>
                                        <Tag size={10} /> {k}
                                    </span>
                                ))}
                                {result.structured_data.keywords.length === 0 && (
                                    <span className="mono-label">NONE_DETECTED</span>
                                )}
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
