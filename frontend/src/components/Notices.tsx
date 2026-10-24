import { AlertTriangle, CheckCircle, HelpCircle, XCircle } from "lucide-react";
import type { AIMode, EvidenceLabel } from "@/lib/api";
import styles from "./Notices.module.css";

/** Mode label plus warnings. Basic mode is always called out, never hidden. */
export function Notices({ mode, warnings }: { mode?: AIMode; warnings: string[] }) {
    if (mode !== "basic" && warnings.length === 0) return null;
    return (
        <div className={styles.notices} role="status">
            {mode === "basic" && <span className={styles.modeTag}>BASIC MODE</span>}
            <ul className={styles.list}>
                {warnings.map((w) => (
                    <li key={w}><AlertTriangle size={12} /> {w}</li>
                ))}
            </ul>
        </div>
    );
}

const LABELS: Record<EvidenceLabel, { text: string; className: string; Icon: typeof CheckCircle }> = {
    supported: { text: "SUPPORTED", className: styles.supported, Icon: CheckCircle },
    needs_confirmation: { text: "NEEDS CONFIRMATION", className: styles.confirm, Icon: HelpCircle },
    not_found: { text: "NOT FOUND", className: styles.missing, Icon: XCircle },
};

export function EvidenceBadge({ label }: { label: EvidenceLabel }) {
    const { text, className, Icon } = LABELS[label];
    return <span className={`${styles.badge} ${className}`}><Icon size={11} /> {text}</span>;
}
