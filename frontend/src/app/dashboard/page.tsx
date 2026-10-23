"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
    User,
    FileText,
    Sparkles,
    FileSearch,
    ArrowRight,
    Activity,
} from "lucide-react";
import { profileApi, type Profile } from "@/lib/api";
import { useSession } from "@/lib/session";
import styles from "./page.module.css";

function DashboardContent() {
    const { user } = useSession();
    const [profile, setProfile] = useState<Profile | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        profileApi.get().then(setProfile).catch(() => setProfile(null)).finally(() => setLoading(false));
    }, []);

    const sectionCount = profile
        ? [
            profile.personal_info ? 1 : 0,
            profile.education.length,
            profile.skills.length,
            profile.experience.length,
            profile.projects.length,
            profile.certifications.length,
            profile.achievements.length,
            profile.external_profiles.length,
        ].reduce((a, b) => a + b, 0)
        : 0;

    return (
        <div>
            {/* ── Page Header ──────────────────────────────────────── */}
            <div className={styles.pageHeader}>
                <span className="mono-label">DASHBOARD / OVERVIEW</span>
                <h1 className={`headline ${styles.pageTitle}`}>COMMAND CENTER</h1>
                <p className="body-text" style={{ marginTop: 8 }}>
                    {`Welcome back, ${user.email}. Your AI resume engine is ready.`}
                </p>
            </div>

            {/* ── Status Grid ──────────────────────────────────────── */}
            <div className={styles.statusGrid}>
                <div className={styles.statCard}>
                    <div className={styles.statTop}>
                        <span className="mono-label">PROFILE_ENTRIES</span>
                        <User size={16} opacity={0.3} />
                    </div>
                    <span className={styles.statValue}>
                        {loading ? "—" : sectionCount}
                    </span>
                    <span className={styles.statSub}>Total data points in your profile</span>
                </div>

                <div className={styles.statCard}>
                    <div className={styles.statTop}>
                        <span className="mono-label">SYSTEM_STATUS</span>
                        <Activity size={16} opacity={0.3} />
                    </div>
                    <span className={styles.statValue} style={{ color: "#22c55e" }}>
                        ONLINE
                    </span>
                    <span className={styles.statSub}>All services operational</span>
                </div>

                <div className={styles.statCard}>
                    <div className={styles.statTop}>
                        <span className="mono-label">AI_ENGINE</span>
                        <Sparkles size={16} opacity={0.3} />
                    </div>
                    <span className={styles.statValue}>GEMINI</span>
                    <span className={styles.statSub}>gemini-3-flash-preview active</span>
                </div>

                <div className={styles.statCard}>
                    <div className={styles.statTop}>
                        <span className="mono-label">EMBEDDINGS</span>
                        <FileText size={16} opacity={0.3} />
                    </div>
                    <span className={styles.statValue}>1024D</span>
                    <span className={styles.statSub}>multilingual-e5-large vector space</span>
                </div>
            </div>

            {/* ── Quick Actions ────────────────────────────────────── */}
            <div className={styles.actionsHeader}>
                <span className="mono-label">QUICK_ACTIONS</span>
            </div>
            <div className={styles.actionsGrid}>
                <Link href="/dashboard/profile" className={styles.actionCard}>
                    <div className={styles.actionIcon}>
                        <User size={20} />
                    </div>
                    <div>
                        <h3 className={styles.actionTitle}>EDIT_PROFILE</h3>
                        <p className={styles.actionSub}>
                            Add education, experience, skills, and more.
                        </p>
                    </div>
                    <ArrowRight size={16} opacity={0.3} />
                </Link>

                <Link href="/dashboard/analyze" className={styles.actionCard}>
                    <div className={styles.actionIcon}>
                        <FileSearch size={20} />
                    </div>
                    <div>
                        <h3 className={styles.actionTitle}>ANALYZE_JD</h3>
                        <p className={styles.actionSub}>
                            Parse a job description with AI analysis.
                        </p>
                    </div>
                    <ArrowRight size={16} opacity={0.3} />
                </Link>

                <Link href="/dashboard/generate" className={styles.actionCard}>
                    <div className={styles.actionIcon}>
                        <Sparkles size={20} />
                    </div>
                    <div>
                        <h3 className={styles.actionTitle}>GENERATE_RESUME</h3>
                        <p className={styles.actionSub}>
                            Create an AI-optimized, role-specific resume.
                        </p>
                    </div>
                    <ArrowRight size={16} opacity={0.3} />
                </Link>

                <Link href="/dashboard/resumes" className={styles.actionCard}>
                    <div className={styles.actionIcon}>
                        <FileText size={20} />
                    </div>
                    <div>
                        <h3 className={styles.actionTitle}>MY_RESUMES</h3>
                        <p className={styles.actionSub}>
                            View and download generated resumes.
                        </p>
                    </div>
                    <ArrowRight size={16} opacity={0.3} />
                </Link>
            </div>
        </div>
    );
}

export default function DashboardOverview() {
    return <DashboardContent />;
}
