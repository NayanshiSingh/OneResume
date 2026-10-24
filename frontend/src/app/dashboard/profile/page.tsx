"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
    AlertTriangle,
    ArrowDown,
    ArrowUp,
    Check,
    ChevronDown,
    ChevronRight,
    Lightbulb,
    Pencil,
    Plus,
    Save,
    Trash2,
    X,
} from "lucide-react";
import {
    authApi,
    profileApi,
    type Bullet,
    type BulletParent,
    type FieldValues,
    type Profile,
    type ProfileCheck,
} from "@/lib/api";
import { MONTHS, SECTIONS, type FieldDef, type Item, type SectionDef } from "@/lib/profileFields";
import styles from "./page.module.css";

/** Runs a change and reports whether it succeeded; errors are shown by the page. */
type Runner = (action: () => Promise<unknown>) => Promise<boolean>;

/* ── Helpers ────────────────────────────────────────────────── */

function toFormValues(fields: FieldDef[], item?: Item): Record<string, string> {
    return Object.fromEntries(fields.map((f) => [f.name, item?.[f.name] == null ? "" : String(item[f.name])]));
}

function toPayload(fields: FieldDef[], values: Record<string, string>): FieldValues {
    return Object.fromEntries(fields.map((f) => {
        const raw = values[f.name].trim();
        if (raw === "") return [f.name, null];
        return [f.name, f.type === "number" || f.type === "month" ? parseInt(raw, 10) : raw];
    }));
}

function moved<T>(list: T[], index: number, delta: number): T[] {
    const next = [...list];
    const [item] = next.splice(index, 1);
    next.splice(index + delta, 0, item);
    return next;
}

/* ── Collapsible Section Shell ──────────────────────────────── */

function Section({ tag, title, count, children, defaultOpen = false }: {
    tag: string; title: string; count: number; children: React.ReactNode; defaultOpen?: boolean;
}) {
    const [open, setOpen] = useState(defaultOpen);
    return (
        <div className={styles.section}>
            <button className={styles.sectionHead} onClick={() => setOpen(!open)}>
                <span className={styles.sectionTag}>{tag}</span>
                <span className={styles.sectionTitle}>{title}</span>
                <span className={styles.sectionCount}>{count}</span>
                {open ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
            </button>
            {open && <div className={styles.sectionBody}>{children}</div>}
        </div>
    );
}

/* ── Item form (add and edit) ───────────────────────────────── */

function ItemForm({ fields, item, withBullets, label, onSubmit, onCancel }: {
    fields: FieldDef[];
    item?: Item;
    withBullets?: boolean;
    label: string;
    onSubmit: (values: FieldValues, bullets: string[]) => Promise<boolean>;
    onCancel?: () => void;
}) {
    const [values, setValues] = useState(() => toFormValues(fields, item));
    const [bullets, setBullets] = useState("");

    async function submit(e: FormEvent) {
        e.preventDefault();
        const saved = await onSubmit(toPayload(fields, values), bullets.split("\n").map((b) => b.trim()).filter(Boolean));
        if (saved && !item) {
            setValues(toFormValues(fields));
            setBullets("");
        }
    }

    return (
        <form onSubmit={submit} className={styles.addForm}>
            <span className="mono-label">{label}</span>
            <div className={styles.fieldGrid}>
                {fields.map((f) => (
                    <div key={f.name} className="form-group">
                        <label className="label">{f.label}</label>
                        {f.type === "month" ? (
                            <select className="input" value={values[f.name]} onChange={(e) => setValues({ ...values, [f.name]: e.target.value })}>
                                <option value="">—</option>
                                {MONTHS.map((m, i) => <option key={m} value={i + 1}>{m}</option>)}
                            </select>
                        ) : (
                            <input
                                className="input"
                                type={f.type === "number" ? "number" : "text"}
                                value={values[f.name]}
                                required={f.required}
                                placeholder={f.placeholder}
                                onChange={(e) => setValues({ ...values, [f.name]: e.target.value })}
                            />
                        )}
                    </div>
                ))}
            </div>
            {withBullets && !item && (
                <div className="form-group">
                    <label className="label">BULLETS (ONE_PER_LINE)</label>
                    <textarea className="textarea" value={bullets} onChange={(e) => setBullets(e.target.value)} />
                </div>
            )}
            <div className={styles.itemActions}>
                <button type="submit" className="btn-outline btn-sm">
                    {item ? <><Save size={12} /> SAVE</> : <><Plus size={12} /> ADD</>}
                </button>
                {onCancel && <button type="button" className="btn-outline btn-sm" onClick={onCancel}><X size={12} /> CANCEL</button>}
            </div>
        </form>
    );
}

/* ── Bullet editor ──────────────────────────────────────────── */

function BulletEditor({ parent, parentId, bullets, run }: {
    parent: BulletParent; parentId: string; bullets: Bullet[]; run: Runner;
}) {
    const [editing, setEditing] = useState<string | null>(null);
    const [draft, setDraft] = useState("");
    const [newText, setNewText] = useState("");

    return (
        <div className={styles.bulletEditor}>
            {bullets.map((b, i) => (
                <div key={b.id} className={styles.bulletRow}>
                    {editing === b.id ? (
                        <>
                            <input className="input" value={draft} onChange={(e) => setDraft(e.target.value)} />
                            <button className="btn-outline btn-sm" aria-label="Save bullet" disabled={!draft.trim()}
                                onClick={() => run(() => profileApi.updateBullet(parent, b.id, draft.trim())).then((ok) => ok && setEditing(null))}>
                                <Check size={12} />
                            </button>
                            <button className="btn-outline btn-sm" aria-label="Cancel" onClick={() => setEditing(null)}><X size={12} /></button>
                        </>
                    ) : (
                        <>
                            <span className={styles.bulletText}>{b.bullet_text}</span>
                            <button className="btn-outline btn-sm" aria-label="Move bullet up" disabled={i === 0}
                                onClick={() => run(() => profileApi.reorderBullets(parent, parentId, moved(bullets, i, -1).map((x) => x.id)))}>
                                <ArrowUp size={12} />
                            </button>
                            <button className="btn-outline btn-sm" aria-label="Move bullet down" disabled={i === bullets.length - 1}
                                onClick={() => run(() => profileApi.reorderBullets(parent, parentId, moved(bullets, i, 1).map((x) => x.id)))}>
                                <ArrowDown size={12} />
                            </button>
                            <button className="btn-outline btn-sm" aria-label="Edit bullet" onClick={() => { setEditing(b.id); setDraft(b.bullet_text); }}>
                                <Pencil size={12} />
                            </button>
                            <button className="btn-danger btn-sm" aria-label="Delete bullet" onClick={() => run(() => profileApi.deleteBullet(parent, b.id))}>
                                <Trash2 size={12} />
                            </button>
                        </>
                    )}
                </div>
            ))}
            <form className={styles.bulletRow} onSubmit={(e) => {
                e.preventDefault();
                run(() => profileApi.addBullet(parent, parentId, newText.trim())).then((ok) => ok && setNewText(""));
            }}>
                <input className="input" placeholder="Add a bullet" value={newText} onChange={(e) => setNewText(e.target.value)} />
                <button type="submit" className="btn-outline btn-sm" disabled={!newText.trim()}><Plus size={12} /></button>
            </form>
        </div>
    );
}

/* ── Section editor ─────────────────────────────────────────── */

function SectionEditor({ def, items, run }: {
    def: SectionDef; items: Item[]; run: Runner;
}) {
    const [editing, setEditing] = useState<string | null>(null);

    return (
        <Section tag={def.tag} title={def.title} count={items.length}>
            {items.map((item, i) => (
                <div key={item.id} className={styles.listItem}>
                    {editing === item.id ? (
                        <div className={styles.listContent}>
                            <ItemForm
                                fields={def.fields}
                                item={item}
                                label={`EDIT_${def.title}`}
                                onSubmit={async (values) => {
                                    const ok = await run(() => profileApi.updateItem(def.path, item.id, values));
                                    if (ok) setEditing(null);
                                    return ok;
                                }}
                                onCancel={() => setEditing(null)}
                            />
                        </div>
                    ) : (
                        <>
                            <div className={styles.listContent}>
                                <span className={styles.listTitle}>{def.heading(item)}</span>
                                {def.detail(item) && <span className={styles.listSub}>{def.detail(item)}</span>}
                                {def.bullets && (
                                    <BulletEditor parent={def.bullets} parentId={item.id} bullets={item.bullets ?? []} run={run} />
                                )}
                            </div>
                            <div className={styles.itemActions}>
                                <button className="btn-outline btn-sm" aria-label="Move up" disabled={i === 0}
                                    onClick={() => run(() => profileApi.reorderItems(def.path, moved(items, i, -1).map((x) => x.id)))}>
                                    <ArrowUp size={12} />
                                </button>
                                <button className="btn-outline btn-sm" aria-label="Move down" disabled={i === items.length - 1}
                                    onClick={() => run(() => profileApi.reorderItems(def.path, moved(items, i, 1).map((x) => x.id)))}>
                                    <ArrowDown size={12} />
                                </button>
                                <button className="btn-outline btn-sm" aria-label="Edit" onClick={() => setEditing(item.id)}>
                                    <Pencil size={12} />
                                </button>
                                <button className="btn-danger btn-sm" aria-label="Delete" onClick={() => run(() => profileApi.deleteItem(def.path, item.id))}>
                                    <Trash2 size={12} />
                                </button>
                            </div>
                        </>
                    )}
                </div>
            ))}
            <ItemForm
                fields={def.fields}
                withBullets={Boolean(def.bullets)}
                label={`ADD_${def.title}`}
                onSubmit={(values, bullets) => run(() => profileApi.createItem(def.path, {
                    ...values,
                    ...(def.bullets ? { bullets: bullets.map((bullet_text) => ({ bullet_text })) } : {}),
                }))}
            />
        </Section>
    );
}

/* ── Personal info ──────────────────────────────────────────── */

function PersonalInfoForm({ profile, run }: { profile: Profile; run: Runner }) {
    const [name, setName] = useState(profile.personal_info?.full_name ?? "");
    const [email, setEmail] = useState(profile.personal_info?.email ?? "");
    const [phone, setPhone] = useState(profile.personal_info?.phone_number ?? "");

    return (
        <Section tag="SEC_00" title="PERSONAL_INFO" count={profile.personal_info ? 1 : 0} defaultOpen={true}>
            <form className={styles.inlineForm} onSubmit={(e) => {
                e.preventDefault();
                run(() => profileApi.upsertPersonalInfo({ full_name: name, email: email || null, phone_number: phone || null }));
            }}>
                <div className="form-row">
                    <div className="form-group">
                        <label className="label">FULL_NAME</label>
                        <input className="input" value={name} onChange={(e) => setName(e.target.value)} required />
                    </div>
                    <div className="form-group">
                        <label className="label">EMAIL</label>
                        <input className="input" type="email" value={email} onChange={(e) => setEmail(e.target.value)} />
                    </div>
                </div>
                <div className="form-group">
                    <label className="label">PHONE (OPTIONAL)</label>
                    <input className="input" value={phone} onChange={(e) => setPhone(e.target.value)} />
                </div>
                <button type="submit" className="btn-primary btn-sm"><Save size={12} /> SAVE</button>
            </form>
        </Section>
    );
}

/* ── Profile checks ─────────────────────────────────────────── */

function ProfileChecks({ checks }: { checks: ProfileCheck[] }) {
    if (checks.length === 0) return null;
    return (
        <div className={styles.checks} role="status">
            <span className="mono-label">PROFILE_CHECKS: optional, these never block a draft</span>
            <ul className={styles.checkList}>
                {checks.map((c, i) => (
                    <li key={`${c.kind}-${c.bullet_id ?? c.item_id ?? i}`} className={c.severity === "warning" ? styles.checkWarning : undefined}>
                        <span>{c.severity === "warning" ? <AlertTriangle size={12} /> : <Lightbulb size={12} />} {c.message}</span>
                        {c.questions.length > 0 && (
                            <ul className={styles.checkQuestions}>
                                {c.questions.map((q) => <li key={q}>{q}</li>)}
                            </ul>
                        )}
                    </li>
                ))}
            </ul>
        </div>
    );
}

/* ── Page ───────────────────────────────────────────────────── */

export default function ProfilePage() {
    const router = useRouter();
    const [profile, setProfile] = useState<Profile | null>(null);
    const [checks, setChecks] = useState<ProfileCheck[]>([]);
    const [error, setError] = useState("");

    useEffect(() => {
        Promise.all([profileApi.get(), profileApi.checks()])
            .then(([p, c]) => { setProfile(p); setChecks(c); })
            .catch((err: unknown) => setError((err as Error).message));
    }, []);

    /** Run a change, then reload the profile so the page always shows saved data. */
    const run: Runner = async (action) => {
        setError("");
        try {
            await action();
            const [p, c] = await Promise.all([profileApi.get(), profileApi.checks()]);
            setProfile(p);
            setChecks(c);
            return true;
        } catch (err: unknown) {
            setError((err as Error).message);
            return false;
        }
    };

    async function deleteAccount() {
        if (!window.confirm("Delete your account, profile, and every generated resume? This cannot be undone.")) return;
        try {
            await authApi.deleteAccount();
            router.replace("/");
        } catch (err: unknown) {
            setError((err as Error).message);
        }
    }

    return (
        <div>
            <div className={styles.pageHeader}>
                <span className="mono-label">DASHBOARD / PROFILE</span>
                <h1 className={`headline ${styles.pageTitle}`}>USER PROFILE</h1>
            </div>

            {error && (
                <div className={styles.errorBar}>
                    <span className="mono-label" style={{ color: "#ef4444" }}>ERROR: {error}</span>
                </div>
            )}

            {!profile ? (
                <div className={styles.loadingState}>
                    <span className="mono-label loading-pulse">LOADING_PROFILE_DATA...</span>
                </div>
            ) : (
                <div className={styles.sections}>
                    <ProfileChecks checks={checks} />
                    <PersonalInfoForm profile={profile} run={run} />
                    {SECTIONS.map((def) => (
                        <SectionEditor
                            key={def.path}
                            def={def}
                            items={profile[def.key] as unknown as Item[]}
                            run={run}
                        />
                    ))}
                    <div className={styles.dangerZone}>
                        <span className="mono-label">DANGER_ZONE</span>
                        <p className="body-text">Deleting your account removes your profile, job descriptions, and every generated resume file.</p>
                        <button className="btn-danger btn-sm" onClick={deleteAccount}><Trash2 size={12} /> DELETE ACCOUNT</button>
                    </div>
                </div>
            )}
        </div>
    );
}
