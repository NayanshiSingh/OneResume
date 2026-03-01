"use client";

import { useEffect, useState, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import {
    Sparkles,
    Download,
    CheckCircle,
    AlertTriangle,
    XCircle,
} from "lucide-react";
import {
    profilesApi,
    resumesApi,
    type Profile,
    type GenerateResult,
} from "@/lib/api";
import styles from "./page.module.css";

function GenerateContent() {
    const searchParams = useSearchParams();
    const router = useRouter();
    const userId = searchParams.get("user_id");

    const [profile, setProfile] = useState<Profile | null>(null);
    const [jdText, setJdText] = useState("");
    const [loading, setLoading] = useState(false);
    const [result, setResult] = useState<GenerateResult | null>(null);
    const [error, setError] = useState("");
    const [pageLoading, setPageLoading] = useState(true);

    useEffect(() => {
        if (!userId) {
            router.replace("/");
            return;
        }
        async function load() {
            try {
                const p = await profilesApi.getByUser(userId!);
                setProfile(p);
            } catch {
                // no profile
            } finally {
                setPageLoading(false);
            }
        }
        load();
    }, [userId, router]);

    async function handleGenerate() {
        if (!profile) {
            setError("No profile found. Please create one first.");
            return;
        }
        if (jdText.trim().length < 20) {
            setError("Job description must be at least 20 characters.");
            return;
        }
        setLoading(true);
        setError("");
        setResult(null);
        try {
            const r = await resumesApi.generate(profile.id, jdText);
            setResult(r);
        } catch (err: unknown) {
            setError((err as Error).message);
        } finally {
            setLoading(false);
        }
    }

    const confidenceIcon = (level: string) => {
        switch (level) {
            case "strong":
                return <CheckCircle size={12} color="#22c55e" />;
            case "inferred":
                return <AlertTriangle size={12} color="#eab308" />;
            default:
                return <XCircle size={12} color="#ef4444" />;
        }
    };

    return (
        <div>
            <div className={styles.pageHeader}>
                <span className="mono-label">DASHBOARD / GENERATE</span>
                <h1 className={`headline ${styles.pageTitle}`}>
                    RESUME GENERATOR
                </h1>
                <p className="body-text" style={{ marginTop: 8 }}>
                    Paste a job description to generate an AI-optimized, role-specific resume.
                </p>
            </div>

            {pageLoading ? (
                <div style={{ padding: "80px 0", textAlign: "center" }}>
                    <span className="mono-label loading-pulse">LOADING...</span>
                </div>
            ) : !profile ? (
                <div className={styles.noProfile}>
                    <span className="mono-label">NO_PROFILE_FOUND</span>
                    <p className="body-text" style={{ marginTop: 8 }}>
                        You need to create a profile and add your data before generating a resume.
                    </p>
                </div>
            ) : (
                <>
                    {/* ── Profile Status ────────────────────────────────── */}
                    <div className={styles.profileBar}>
                        <span className="mono-label">ACTIVE_PROFILE</span>
                        <div className={styles.profileStats}>
                            <span className="badge badge-accent">
                                {profile.experience.length} EXP
                            </span>
                            <span className="badge">
                                {profile.projects.length} PROJ
                            </span>
                            <span className="badge">
                                {profile.skills.length} SKILLS
                            </span>
                            <span className="badge">
                                {profile.education.length} EDU
                            </span>
                        </div>
                    </div>

                    {/* ── JD Input ──────────────────────────────────────── */}
                    <div className={styles.inputSection}>
                        <label className="label">JOB_DESCRIPTION</label>
                        <textarea
                            className="textarea"
                            style={{ minHeight: 200 }}
                            value={jdText}
                            onChange={(e) => setJdText(e.target.value)}
                            placeholder={"Paste the full job description here...\n\nThe AI pipeline will analyze, match, score, rewrite, and optimize your resume."}
                        />
                        <div className={styles.inputActions}>
                            <span className="mono-label">{jdText.length} CHARS</span>
                            <button
                                className="btn-primary btn-accent"
                                onClick={handleGenerate}
                                disabled={loading}
                            >
                                {loading ? (
                                    <span className="loading-pulse">GENERATING...</span>
                                ) : (
                                    <>
                                        <Sparkles size={14} /> GENERATE_RESUME
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

                    {/* ── Result ────────────────────────────────────────── */}
                    {result && (
                        <div className={styles.result}>
                            <div className={styles.resultHeader}>
                                <div>
                                    <span className="mono-label">GENERATION_COMPLETE</span>
                                    <h2 className={`headline ${styles.resultTitle}`}>
                                        {result.job_title}
                                    </h2>
                                    <span className="mono-label">
                                        VERSION_{String(result.version).padStart(2, "0")}
                                    </span>
                                </div>
                                <div className={styles.downloadBtns}>
                                    <a
                                        href={resumesApi.downloadUrl(result.resume_id, "pdf")}
                                        className="btn-primary"
                                        target="_blank"
                                        rel="noopener"
                                    >
                                        <Download size={14} /> PDF
                                    </a>
                                    <a
                                        href={resumesApi.downloadUrl(result.resume_id, "docx")}
                                        className="btn-outline"
                                        target="_blank"
                                        rel="noopener"
                                    >
                                        <Download size={14} /> DOCX
                                    </a>
                                </div>
                            </div>

                            {/* Skill Confidence */}
                            {result.skill_confidence && Object.keys(result.skill_confidence).length > 0 && (
                                <div className={styles.confSection}>
                                    <span className="mono-label">SKILL_CONFIDENCE</span>
                                    <div className={styles.confGrid}>
                                        {Object.entries(result.skill_confidence).map(
                                            ([skill, confidence]) => (
                                                <div key={skill} className={styles.confItem}>
                                                    {confidenceIcon(confidence)}
                                                    <span className={styles.confSkill}>{skill}</span>
                                                    <span className={styles.confLevel}>{confidence}</span>
                                                </div>
                                            )
                                        )}
                                    </div>
                                </div>
                            )}

                            {/* Keyword Coverage */}
                            {result.keyword_coverage && Object.keys(result.keyword_coverage).length > 0 && (
                                <div className={styles.confSection}>
                                    <span className="mono-label">KEYWORD_COVERAGE</span>
                                    <div className={styles.confGrid}>
                                        {Object.entries(result.keyword_coverage).map(
                                            ([keyword, covered]) => (
                                                <div key={keyword} className={styles.confItem}>
                                                    {covered ? (
                                                        <CheckCircle size={12} color="#22c55e" />
                                                    ) : (
                                                        <XCircle size={12} color="#ef4444" />
                                                    )}
                                                    <span className={styles.confSkill}>{keyword}</span>
                                                    <span className={styles.confLevel}>
                                                        {covered ? "COVERED" : "MISSING"}
                                                    </span>
                                                </div>
                                            )
                                        )}
                                    </div>
                                </div>
                            )}
                        </div>
                    )}
                </>
            )}
        </div>
    );
}

export default function GeneratePage() {
    return (
        <Suspense fallback={<div className="loading-pulse">LOADING...</div>}>
            <GenerateContent />
        </Suspense>
    );
}
