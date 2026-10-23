"use client";

import { use, useEffect, useState } from "react";
import { Check, Download, Eye, EyeOff, Pencil, Pin, PinOff, RotateCcw, X } from "lucide-react";
import { EvidenceBadge, Notices } from "@/components/Notices";
import {
    draftsApi,
    resumesApi,
    type Draft,
    type DraftBullet,
    type DraftEntry,
    type DraftOp,
    type DraftSection,
    type Resume,
    type ToggleItem,
} from "@/lib/api";
import styles from "../drafts.module.css";

type Apply = (...ops: DraftOp[]) => Promise<boolean>;

function BulletRow({ section, entry, bullet, apply }: { section: DraftSection; entry: DraftEntry; bullet: DraftBullet; apply: Apply }) {
    const [editing, setEditing] = useState(false);
    const [text, setText] = useState(bullet.text);
    const target = { section, item_id: entry.id, bullet_id: bullet.id };

    return (
        <div className={`${styles.bullet} ${bullet.included ? "" : styles.excluded}`}>
            <div className={styles.bulletBody}>
                {editing ? (
                    <input className="input" value={text} onChange={(e) => setText(e.target.value)} autoFocus />
                ) : (
                    <span>• {bullet.text}</span>
                )}
                {bullet.user_edited && (
                    <>
                        <span className={styles.editedTag}>EDITED BY YOU · YOU CONFIRM THIS AT APPROVAL</span>
                        <span className={styles.original}>{bullet.original_text}</span>
                    </>
                )}
            </div>
            <div className={styles.actions}>
                {editing ? (
                    <>
                        <button className="btn-outline btn-sm" aria-label="Save" disabled={!text.trim()}
                            onClick={() => apply({ op: "edit_bullet", ...target, text }).then((ok) => ok && setEditing(false))}><Check size={12} /></button>
                        <button className="btn-outline btn-sm" aria-label="Cancel" onClick={() => { setEditing(false); setText(bullet.text); }}><X size={12} /></button>
                    </>
                ) : (
                    <>
                        <button className="btn-outline btn-sm" aria-label={bullet.included ? "Hide" : "Include"}
                            onClick={() => apply({ op: "set_included", ...target, value: !bullet.included })}>
                            {bullet.included ? <EyeOff size={12} /> : <Eye size={12} />}
                        </button>
                        <button className="btn-outline btn-sm" aria-label="Edit for this resume" onClick={() => setEditing(true)}><Pencil size={12} /></button>
                        {bullet.user_edited && (
                            <button className="btn-outline btn-sm" aria-label="Revert to your profile wording"
                                onClick={() => apply({ op: "revert_bullet", ...target }).then((ok) => ok && setText(bullet.original_text))}><RotateCcw size={12} /></button>
                        )}
                    </>
                )}
            </div>
        </div>
    );
}

function EntrySection({ title, section, entries, apply }: { title: string; section: DraftSection; entries: DraftEntry[]; apply: Apply }) {
    if (entries.length === 0) return null;
    return (
        <div className={styles.section}>
            <span className="mono-label">{title}</span>
            {entries.map((entry) => (
                <div key={entry.id} className={`${styles.entry} ${entry.included ? "" : styles.excluded}`}>
                    <div className={styles.entryHead}>
                        <span className={styles.entryTitle}>{entry.title}</span>
                        <span className="mono-label">{entry.subtitle}</span>
                        {!entry.included && <span className="badge">LEFT OUT</span>}
                        {entry.pinned && <span className="badge badge-accent">PINNED</span>}
                        <span style={{ flex: 1 }} />
                        <button className="btn-outline btn-sm" aria-label={entry.included ? "Leave out" : "Include"}
                            onClick={() => apply({ op: "set_included", section, item_id: entry.id, value: !entry.included })}>
                            {entry.included ? <EyeOff size={12} /> : <Eye size={12} />}
                        </button>
                        <button className="btn-outline btn-sm" aria-label={entry.pinned ? "Unpin" : "Pin"}
                            onClick={() => apply({ op: "set_pinned", section, item_id: entry.id, value: !entry.pinned })}>
                            {entry.pinned ? <PinOff size={12} /> : <Pin size={12} />}
                        </button>
                    </div>
                    {entry.bullets.map((b) => (
                        <BulletRow key={`${b.id}-${b.text}`} section={section} entry={entry} bullet={b} apply={apply} />
                    ))}
                </div>
            ))}
        </div>
    );
}

function ToggleChips({ title, section, items, label, apply }: {
    title: string; section: DraftSection; items: ToggleItem[]; label: (item: ToggleItem) => string; apply: Apply;
}) {
    if (items.length === 0) return null;
    return (
        <div className={styles.section}>
            <span className="mono-label">{title}</span>
            <div className={styles.chips}>
                {items.map((item) => (
                    <button key={item.id} className={`${styles.chip} ${item.included ? "" : styles.excluded}`}
                        title={item.included ? "Click to leave out" : "Click to include"}
                        onClick={() => apply({ op: "set_included", section, item_id: item.id, value: !item.included })}>
                        {item.included ? "✓ " : "+ "}{label(item)}
                    </button>
                ))}
            </div>
        </div>
    );
}

export default function DraftReviewPage({ params }: { params: Promise<{ id: string }> }) {
    const { id } = use(params);
    const [draft, setDraft] = useState<Draft | null>(null);
    const [resume, setResume] = useState<Resume | null>(null);
    const [error, setError] = useState("");
    const [busy, setBusy] = useState(false);

    useEffect(() => {
        draftsApi.get(id).then(async (d) => {
            setDraft(d);
            if (d.exported_resume_id) setResume(await resumesApi.get(d.exported_resume_id));
        }).catch((err: unknown) => setError((err as Error).message));
    }, [id]);

    async function guarded(action: () => Promise<void>): Promise<boolean> {
        setBusy(true);
        setError("");
        try {
            await action();
            return true;
        } catch (err: unknown) {
            setError((err as Error).message);
            return false;
        } finally {
            setBusy(false);
        }
    }

    const apply: Apply = (...ops) => guarded(async () => {
        if (!draft) return;
        setDraft(await draftsApi.edit(draft.id, draft.revision, ops));
        setResume(null);
    });

    const approve = () => guarded(async () => {
        if (!draft) return;
        setDraft(await draftsApi.approve(draft.id, draft.revision));
    });

    const exportDraft = () => guarded(async () => {
        if (!draft) return;
        setResume(await draftsApi.export(draft.id));
        setDraft(await draftsApi.get(draft.id));
    });

    if (!draft) {
        return error
            ? <p className="mono-label" style={{ color: "#ef4444" }}>ERROR: {error}</p>
            : <span className="mono-label loading-pulse">LOADING_DRAFT...</span>;
    }

    const { content } = draft;
    const approvedCurrent = draft.status === "approved" && draft.approved_revision === draft.revision;
    const missingRequired = draft.coverage.filter((c) => c.importance === "required" && c.label === "not_found");

    return (
        <div>
            <div className={styles.pageHeader}>
                <span className="mono-label">DASHBOARD / DRAFTS / REVIEW</span>
                <h1 className={`headline ${styles.pageTitle}`}>{draft.job_title}</h1>
                <p className="body-text" style={{ marginTop: 8 }}>
                    Revision {draft.revision} · {draft.page_target} page target · wording is your own unless you edit it here.
                </p>
            </div>

            <Notices mode={draft.matching_mode} warnings={draft.warnings} />
            {error && <p className="mono-label" style={{ color: "#ef4444" }}>ERROR: {error}</p>}

            <div className={styles.layout}>
                <div>
                    {content.personal_info && (
                        <div className={styles.section}>
                            <span className={styles.entryTitle}>{content.personal_info.full_name}</span>
                            <span className="mono-label"> {[content.personal_info.email, content.personal_info.phone_number].filter(Boolean).join(" · ")}</span>
                        </div>
                    )}
                    <ToggleChips title="EDUCATION" section="education" items={content.education} apply={apply}
                        label={(e) => `${e.degree} — ${e.institution}`} />
                    <EntrySection title="EXPERIENCE" section="experience" entries={content.experience} apply={apply} />
                    <EntrySection title="PROJECTS" section="projects" entries={content.projects} apply={apply} />
                    <ToggleChips title="SKILLS" section="skills" items={content.skills} apply={apply} label={(s) => String(s.name)} />
                    <ToggleChips title="CERTIFICATIONS" section="certifications" items={content.certifications} apply={apply} label={(c) => String(c.name)} />
                    <ToggleChips title="ACHIEVEMENTS" section="achievements" items={content.achievements} apply={apply} label={(a) => String(a.title)} />
                    <ToggleChips title="LINKS" section="external_profiles" items={content.external_profiles} apply={apply} label={(p) => String(p.platform)} />
                </div>

                <aside className={styles.panel}>
                    <span className="mono-label">REQUIREMENTS</span>
                    {missingRequired.length > 0 && (
                        <p style={{ fontSize: 12 }}>{missingRequired.length} required item(s) have no evidence in your profile. The draft does not claim them.</p>
                    )}
                    <div>
                        {draft.coverage.map((c) => (
                            <div key={`${c.importance}-${c.requirement}`} className={styles.coverageRow}>
                                <div className={styles.coverageTop}>
                                    <span><strong>{c.requirement}</strong> {c.importance === "preferred" && <span className="mono-label">PREFERRED</span>}</span>
                                    <EvidenceBadge label={c.label} />
                                </div>
                                {c.label !== "not_found" && (
                                    <span style={{ opacity: 0.7 }}>{c.in_draft ? "In this draft" : "In your profile, but left out of this draft"}</span>
                                )}
                            </div>
                        ))}
                    </div>

                    {resume ? (
                        <div className={styles.approveBox}>
                            <span className="mono-label">EXPORTED AS VERSION {resume.version}</span>
                            {resume.formats.length === 0 && <span>No files could be rendered.</span>}
                            {resume.formats.map((f) => (
                                <a key={f} className="btn-primary btn-sm" href={resumesApi.downloadUrl(resume.id, f)}>
                                    <Download size={12} /> {f.toUpperCase()}
                                </a>
                            ))}
                        </div>
                    ) : approvedCurrent ? (
                        <button className="btn-primary" onClick={exportDraft} disabled={busy}><Download size={14} /> EXPORT PDF + DOCX</button>
                    ) : (
                        <div className={styles.approveBox}>
                            <span className="mono-label">APPROVE REVISION {draft.revision}</span>
                            <span>By approving, you confirm everything in this draft is accurate.</span>
                            {draft.edited_bullets.length > 0 && (
                                <span>You edited {draft.edited_bullets.length} bullet(s) for this resume; those are your own claims.</span>
                            )}
                            <button className="btn-primary btn-sm" onClick={approve} disabled={busy}><Check size={12} /> APPROVE</button>
                        </div>
                    )}
                </aside>
            </div>
        </div>
    );
}
