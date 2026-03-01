"use client";

import { useEffect, useState, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { Download, FileText, Clock } from "lucide-react";
import { profilesApi, resumesApi, type Resume } from "@/lib/api";
import styles from "./page.module.css";

function ResumesContent() {
    const searchParams = useSearchParams();
    const router = useRouter();
    const userId = searchParams.get("user_id");

    const [resumes, setResumes] = useState<Resume[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");

    useEffect(() => {
        if (!userId) {
            router.replace("/");
            return;
        }
        async function load() {
            try {
                const profile = await profilesApi.getByUser(userId!);
                const r = await resumesApi.list(profile.id);
                setResumes(r);
            } catch {
                // no profile or resumes
            } finally {
                setLoading(false);
            }
        }
        load();
    }, [userId, router]);

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
                                <a
                                    href={resumesApi.downloadUrl(resume.id, "pdf")}
                                    className="btn-primary btn-sm"
                                    target="_blank"
                                    rel="noopener"
                                >
                                    <Download size={12} /> PDF
                                </a>
                                <a
                                    href={resumesApi.downloadUrl(resume.id, "docx")}
                                    className="btn-outline btn-sm"
                                    target="_blank"
                                    rel="noopener"
                                >
                                    <Download size={12} /> DOCX
                                </a>
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}

export default function ResumesPage() {
    return (
        <Suspense fallback={<div className="loading-pulse">LOADING...</div>}>
            <ResumesContent />
        </Suspense>
    );
}
