"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
    ArrowDown,
    ArrowUp,
    Check,
    ChevronDown,
    ChevronRight,
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
    type SectionPath,
} from "@/lib/api";
import styles from "./page.module.css";

/* ── Section definitions ────────────────────────────────────── */

interface FieldDef {
    name: string;
    label: string;
    type?: "text" | "number" | "month";
    required?: boolean;
    placeholder?: string;
}

type Item = { id: string; bullets?: Bullet[] } & Record<string, unknown>;

/** Runs a change and reports whether it succeeded; errors are shown by the page. */
type Runner = (action: () => Promise<unknown>) => Promise<boolean>;

interface SectionDef {
    path: SectionPath;
    key: keyof Profile;
    tag: string;
    title: string;
    fields: FieldDef[];
    heading: (item: Item) => string;
    detail: (item: Item) => string;
    bullets?: BulletParent;
}

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

const join = (...parts: unknown[]) => parts.filter((p) => p !== null && p !== undefined && p !== "").join(" · ");

const SECTIONS: SectionDef[] = [
    {
        path: "education", key: "education", tag: "SEC_01", title: "EDUCATION",
        fields: [
            { name: "institution", label: "INSTITUTION", required: true },
            { name: "degree", label: "DEGREE", required: true },
            { name: "field_of_study", label: "FIELD_OF_STUDY" },
            { name: "grade", label: "GRADE" },
            { name: "start_year", label: "START_YEAR", type: "number" },
            { name: "end_year", label: "END_YEAR (OR EXPECTED)", type: "number" },
            { name: "end_month", label: "END_MONTH (OR EXPECTED)", type: "month" },
        ],
        heading: (e) => `${e.degree} — ${e.institution}`,
        detail: (e) => join(
            e.field_of_study,
            [e.start_year, [e.end_month ? MONTHS[(e.end_month as number) - 1] : null, e.end_year].filter(Boolean).join(" ")].filter(Boolean).join(" – "),
            e.grade && `GPA: ${e.grade}`,
        ),
    },
    {
        path: "skills", key: "skills", tag: "SEC_02", title: "SKILLS",
        fields: [
            { name: "skill_name", label: "SKILL_NAME", required: true },
            { name: "skill_category", label: "CATEGORY", placeholder: "OPTIONAL" },
        ],
        heading: (s) => String(s.skill_name),
        detail: (s) => join(s.skill_category),
    },
    {
        path: "experience", key: "experience", tag: "SEC_03", title: "EXPERIENCE", bullets: "experience",
        fields: [
            { name: "company", label: "COMPANY", required: true },
            { name: "role", label: "ROLE", required: true },
            { name: "start_date", label: "START_DATE", placeholder: "2023-01" },
            { name: "end_date", label: "END_DATE", placeholder: "Present" },
        ],
        heading: (e) => `${e.role} @ ${e.company}`,
        detail: (e) => [e.start_date, e.end_date].filter(Boolean).join(" — "),
    },
    {
        path: "projects", key: "projects", tag: "SEC_04", title: "PROJECTS", bullets: "projects",
        fields: [
            { name: "project_title", label: "PROJECT_TITLE", required: true },
            { name: "description", label: "DESCRIPTION" },
            { name: "tech_stack", label: "TECH_STACK", placeholder: "Python, React, Docker" },
        ],
        heading: (p) => String(p.project_title),
        detail: (p) => join(p.tech_stack && `Stack: ${p.tech_stack}`, p.description),
    },
    {
        path: "certifications", key: "certifications", tag: "SEC_05", title: "CERTIFICATIONS",
        fields: [
            { name: "name", label: "NAME", required: true },
            { name: "issuing_organization", label: "ISSUING_ORG" },
            { name: "year", label: "YEAR", type: "number" },
        ],
        heading: (c) => String(c.name),
        detail: (c) => join(c.issuing_organization, c.year),
    },
    {
        path: "achievements", key: "achievements", tag: "SEC_06", title: "ACHIEVEMENTS",
        fields: [
            { name: "title", label: "TITLE", required: true },
            { name: "description", label: "DESCRIPTION" },
            { name: "category", label: "CATEGORY" },
        ],
        heading: (a) => String(a.title),
        detail: (a) => join(a.description, a.category),
    },
    {
        path: "external-profiles", key: "external_profiles", tag: "SEC_07", title: "EXTERNAL_PROFILES",
        fields: [
            { name: "platform", label: "PLATFORM", required: true, placeholder: "GitHub" },
            { name: "profile_url", label: "URL", required: true, placeholder: "https://github.com/username" },
        ],
        heading: (ep) => String(ep.platform),
        detail: (ep) => String(ep.profile_url),
    },
];

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

/* ── Page ───────────────────────────────────────────────────── */

export default function ProfilePage() {
    const router = useRouter();
    const [profile, setProfile] = useState<Profile | null>(null);
    const [error, setError] = useState("");

    useEffect(() => {
        profileApi.get().then(setProfile).catch((err: unknown) => setError((err as Error).message));
    }, []);

    /** Run a change, then reload the profile so the page always shows saved data. */
    const run: Runner = async (action) => {
        setError("");
        try {
            await action();
            setProfile(await profileApi.get());
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
