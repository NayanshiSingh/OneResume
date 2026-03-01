"use client";

import Link from "next/link";
import { usePathname, useSearchParams } from "next/navigation";
import {
    LayoutGrid,
    User,
    FileSearch,
    Sparkles,
    FileText,
    ArrowLeft,
} from "lucide-react";
import styles from "./layout.module.css";
import { Suspense } from "react";

const NAV_ITEMS = [
    { href: "/dashboard", label: "OVERVIEW", icon: LayoutGrid, tag: "SYS_00" },
    { href: "/dashboard/profile", label: "PROFILE", icon: User, tag: "SYS_01" },
    {
        href: "/dashboard/analyze",
        label: "ANALYZE_JD",
        icon: FileSearch,
        tag: "SYS_02",
    },
    {
        href: "/dashboard/generate",
        label: "GENERATE",
        icon: Sparkles,
        tag: "SYS_03",
    },
    {
        href: "/dashboard/resumes",
        label: "MY_RESUMES",
        icon: FileText,
        tag: "SYS_04",
    },
];

function DashboardShell({ children }: { children: React.ReactNode }) {
    const pathname = usePathname();
    const searchParams = useSearchParams();
    const userId = searchParams.get("user_id") || "";

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
                        const href = userId
                            ? `${item.href}?user_id=${userId}`
                            : item.href;
                        return (
                            <Link
                                key={item.href}
                                href={href}
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
                    <span className="mono-label">STATUS: OPERATIONAL</span>
                    <span className="mono-label" style={{ color: "#22c55e" }}>
                        ● SYSTEM_ONLINE
                    </span>
                </div>
            </aside>

            {/* ── Main Content ────────────────────────────────────── */}
            <main className={styles.main}>{children}</main>
        </div>
    );
}

export default function DashboardLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    return (
        <Suspense fallback={<div>Loading...</div>}>
            <DashboardShell>{children}</DashboardShell>
        </Suspense>
    );
}
