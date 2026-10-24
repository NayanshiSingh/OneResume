"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
    LayoutGrid,
    User,
    FileSearch,
    Sparkles,
    FileText,
    ArrowLeft,
    LogOut,
    Upload,
    Shield,
} from "lucide-react";
import styles from "./layout.module.css";
import { useEffect, useState } from "react";
import { SessionProvider, useSession } from "@/lib/session";
import { systemApi, type AIStatus } from "@/lib/api";

const NAV_ITEMS = [
    { href: "/dashboard", label: "OVERVIEW", icon: LayoutGrid, tag: "SYS_00" },
    { href: "/dashboard/profile", label: "PROFILE", icon: User, tag: "SYS_01" },
    { href: "/dashboard/import", label: "IMPORT_RESUME", icon: Upload, tag: "SYS_02" },
    { href: "/dashboard/analyze", label: "JOB_DESCRIPTION", icon: FileSearch, tag: "SYS_03" },
    { href: "/dashboard/drafts", label: "DRAFTS", icon: Sparkles, tag: "SYS_04" },
    { href: "/dashboard/resumes", label: "MY_RESUMES", icon: FileText, tag: "SYS_05" },
    { href: "/dashboard/data", label: "DATA_&_AI", icon: Shield, tag: "SYS_06" },
];

function AIStatusBanner() {
    const [status, setStatus] = useState<AIStatus | null>(null);
    useEffect(() => {
        systemApi.aiStatus().then(setStatus).catch(() => setStatus(null));
    }, []);
    if (!status || (status.llm && status.embeddings)) return null;
    const off = [!status.llm && "AI analysis and import (Gemini)", !status.embeddings && "semantic matching (Pinecone)"].filter(Boolean);
    return (
        <div className={styles.aiBanner} role="status">
            BASIC MODE: {off.join(" and ")} {off.length > 1 ? "are" : "is"} not configured. Features still work with simpler rules and are labelled.
        </div>
    );
}

function DashboardShell({ children }: { children: React.ReactNode }) {
    const pathname = usePathname();
    const { user, signOut } = useSession();

    return (
        <div className={styles.shell}>
            {/* ── Sidebar ─────────────────────────────────────────── */}
            <aside className={styles.sidebar}>
                <div className={styles.sidebarTop}>
                    <Link href="/" className={styles.backLink}>
                        <ArrowLeft size={14} />
                        <span>ONERESUME</span>
                    </Link>
                    <span className="mono-label" style={{ marginTop: 4 }}>
                        DASHBOARD_V.01
                    </span>
                </div>

                <nav className={styles.sideNav}>
                    {NAV_ITEMS.map((item) => {
                        const isActive =
                            pathname === item.href ||
                            (item.href !== "/dashboard" && pathname.startsWith(item.href));
                        return (
                            <Link
                                key={item.href}
                                href={item.href}
                                className={`${styles.navItem} ${isActive ? styles.navItemActive : ""}`}
                            >
                                <span className={styles.navTag}>{item.tag}</span>
                                <item.icon size={14} />
                                <span className={styles.navLabel}>{item.label}</span>
                            </Link>
                        );
                    })}
                </nav>

                <div className={styles.sidebarBottom}>
                    <span className="mono-label">{user.email}</span>
                    <button className="btn-outline btn-sm" onClick={signOut}>
                        <LogOut size={12} /> SIGN OUT
                    </button>
                </div>
            </aside>

            {/* ── Main Content ────────────────────────────────────── */}
            <main className={styles.main}><AIStatusBanner />{children}</main>
        </div>
    );
}

export default function DashboardLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    return (
        <SessionProvider>
            <DashboardShell>{children}</DashboardShell>
        </SessionProvider>
    );
}
