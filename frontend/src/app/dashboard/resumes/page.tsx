"use client";

import { useEffect, useState } from "react";
import { Download, FileText, Clock, Trash2 } from "lucide-react";
import { resumesApi, type Resume } from "@/lib/api";
import styles from "./page.module.css";

function ResumesContent() {
    const [resumes, setResumes] = useState<Resume[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");

    useEffect(() => {
        resumesApi.list().then(setResumes).catch((err: unknown) => setError((err as Error).message)).finally(() => setLoading(false));
    }, []);

    async function deleteResume(resume: Resume) {
        if (!window.confirm(`Delete ${resume.job_title} v${resume.version}? This removes its files.`)) return;
        try {
            await resumesApi.delete(resume.id);
            setResumes((current) => current.filter((r) => r.id !== resume.id));
        } catch (err: unknown) {
            setError((err as Error).message);
        }
    }

    function formatDate(d: string) {
        return new Date(d).toLocaleDateString("en-US", {
            year: "numeric",
            month: "short",
            day: "numeric",
            hour: "2-digit",
            minute: "2-digit",
        });
    }

    return (
        <div>
            <div className={styles.pageHeader}>
                <span className="mono-label">DASHBOARD / MY_RESUMES</span>
                <h1 className={`headline ${styles.pageTitle}`}>RESUME HISTORY</h1>
                <p className="body-text" style={{ marginTop: 8 }}>
                    View and download all your previously generated resumes.
                </p>
            </div>

            {loading ? (
                <div style={{ padding: "80px 0", textAlign: "center" }}>
                    <span className="mono-label loading-pulse">LOADING_RESUMES...</span>
                </div>
            ) : error ? (
                <div className={styles.errorBar}>
                    <span className="mono-label" style={{ color: "#ef4444" }}>
                        ERROR: {error}
                    </span>
                </div>
            ) : resumes.length === 0 ? (
                <div className={styles.emptyState}>
                    <FileText size={32} opacity={0.15} />
                    <span className="mono-label" style={{ marginTop: 12 }}>
                        NO_RESUMES_GENERATED
                    </span>
                    <p className="body-text" style={{ marginTop: 8 }}>
                        Generate your first resume from the Generate page.
                    </p>
                </div>
            ) : (
                <div className={styles.table}>
                    {/* Header */}
                    <div className={styles.tableHeader}>
                        <span className={styles.colTitle}>JOB_TITLE</span>
                        <span className={styles.colVersion}>VERSION</span>
                        <span className={styles.colDate}>CREATED_AT</span>
                        <span className={styles.colActions}>ACTIONS</span>
                    </div>

                    {/* Rows */}
                    {resumes.map((resume) => (
                        <div key={resume.id} className={styles.tableRow}>
                            <div className={styles.colTitle}>
                                <FileText size={14} opacity={0.3} />
                                <span className={styles.jobTitle}>{resume.job_title}</span>
                            </div>
                            <span className={styles.colVersion}>
                                <span className="badge badge-accent">
                                    V.{String(resume.version).padStart(2, "0")}
                                </span>
                            </span>
                            <span className={styles.colDate}>
                                <Clock size={12} opacity={0.3} />
                                <span className="mono-label">{formatDate(resume.created_at)}</span>
                            </span>
                            <div className={styles.colActions}>
                                {resume.formats.map((format) => (
                                    <a
                                        key={format}
                                        href={resumesApi.downloadUrl(resume.id, format)}
                                        className={`${format === "pdf" ? "btn-primary" : "btn-outline"} btn-sm`}
                                    >
                                        <Download size={12} /> {format.toUpperCase()}
                                    </a>
                                ))}
                                <button className="btn-danger btn-sm" onClick={() => deleteResume(resume)} aria-label="Delete resume">
                                    <Trash2 size={12} />
                                </button>
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}

export default function ResumesPage() {
    return <ResumesContent />;
}
