"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Save, Trash2, Upload } from "lucide-react";
import { Notices } from "@/components/Notices";
import { profileApi, type ImportPreview, type ProfileImport } from "@/lib/api";
import { MONTHS, SECTIONS, type FieldDef } from "@/lib/profileFields";
import styles from "./page.module.css";

type ImportItem = Record<string, unknown> & { bullets?: { bullet_text: string }[] };
type ImportListKey = Exclude<keyof ProfileImport, "personal_info">;

function FieldInput({ field, value, onChange }: { field: FieldDef; value: unknown; onChange: (v: string | number | null) => void }) {
    const text = value == null ? "" : String(value);
    const parse = (raw: string) => (raw === "" ? null : field.type === "number" || field.type === "month" ? parseInt(raw, 10) : raw);
    const flagged = text.includes("(check this)");
    return (
        <div className="form-group">
            <label className="label">{field.label}{flagged && <span className={styles.flag}> CHECK</span>}</label>
            {field.type === "month" ? (
                <select className="input" value={text} onChange={(e) => onChange(parse(e.target.value))}>
                    <option value="">—</option>
                    {MONTHS.map((m, i) => <option key={m} value={i + 1}>{m}</option>)}
                </select>
            ) : (
                <input className={`input ${flagged ? styles.flaggedInput : ""}`} type={field.type === "number" ? "number" : "text"}
                    value={text} required={field.required} onChange={(e) => onChange(parse(e.target.value))} />
            )}
        </div>
    );
}

export default function ImportPage() {
    const router = useRouter();
    const [file, setFile] = useState<File | null>(null);
    const [preview, setPreview] = useState<ImportPreview | null>(null);
    const [data, setData] = useState<ProfileImport | null>(null);
    const [error, setError] = useState("");
    const [busy, setBusy] = useState(false);

    async function upload() {
        if (!file) return;
        setBusy(true);
        setError("");
        try {
            const result = await profileApi.importResume(file);
            setPreview(result);
            setData(result.profile);
        } catch (err: unknown) {
            setError((err as Error).message);
        } finally {
            setBusy(false);
        }
    }

    async function save() {
        if (!data) return;
        setBusy(true);
        setError("");
        try {
            await profileApi.applyImport(data);
            router.push("/dashboard/profile");
        } catch (err: unknown) {
            setError((err as Error).message);
            setBusy(false);
        }
    }

    function updateItem(key: ImportListKey, index: number, changes: Partial<ImportItem>) {
        if (!data) return;
        const items = [...(data[key] as ImportItem[])];
        items[index] = { ...items[index], ...changes };
        setData({ ...data, [key]: items });
    }

    function removeItem(key: ImportListKey, index: number) {
        if (!data) return;
        setData({ ...data, [key]: (data[key] as ImportItem[]).filter((_, i) => i !== index) });
    }

    return (
        <div>
            <div className={styles.pageHeader}>
                <span className="mono-label">DASHBOARD / IMPORT_RESUME</span>
                <h1 className={`headline ${styles.pageTitle}`}>IMPORT A RESUME</h1>
                <p className="body-text" style={{ marginTop: 8 }}>
                    Upload a PDF or DOCX (up to 5 MB). Nothing is saved until you check the fields and press Save.
                </p>
            </div>

            <div className={styles.uploadRow}>
                <input type="file" accept=".pdf,.docx" onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
                <button className="btn-primary" onClick={upload} disabled={!file || busy}>
                    <Upload size={14} /> {busy && !preview ? "READING..." : "READ FILE"}
                </button>
            </div>

            {error && <div className={styles.errorBar}><span className="mono-label" style={{ color: "#ef4444" }}>ERROR: {error}</span></div>}

            {preview && data && (
                <>
                    <Notices mode={preview.mode} warnings={preview.warnings} />

                    {data.personal_info && (
                        <section className={styles.section}>
                            <h2 className="mono-label">PERSONAL_INFO</h2>
                            <div className={styles.fieldGrid}>
                                {(["full_name", "email", "phone_number"] as const).map((name) => (
                                    <FieldInput key={name} field={{ name, label: name.toUpperCase(), required: name === "full_name" }}
                                        value={data.personal_info?.[name]}
                                        onChange={(v) => setData({ ...data, personal_info: { ...data.personal_info!, [name]: v } })} />
                                ))}
                            </div>
                        </section>
                    )}

                    {SECTIONS.map((def) => {
                        const key = def.key as ImportListKey;
                        const items = data[key] as ImportItem[];
                        if (items.length === 0) return null;
                        return (
                            <section key={def.path} className={styles.section}>
                                <h2 className="mono-label">{def.title} ({items.length})</h2>
                                {items.map((item, i) => (
                                    <div key={i} className={styles.item}>
                                        <div className={styles.fieldGrid}>
                                            {def.fields.map((f) => (
                                                <FieldInput key={f.name} field={f} value={item[f.name]}
                                                    onChange={(v) => updateItem(key, i, { [f.name]: v })} />
                                            ))}
                                        </div>
                                        {def.bullets && (
                                            <div className="form-group">
                                                <label className="label">BULLETS (ONE_PER_LINE)</label>
                                                <textarea className="textarea"
                                                    value={(item.bullets ?? []).map((b) => b.bullet_text).join("\n")}
                                                    onChange={(e) => updateItem(key, i, {
                                                        bullets: e.target.value.split("\n").filter((l) => l.trim()).map((bullet_text) => ({ bullet_text })),
                                                    })} />
                                            </div>
                                        )}
                                        <button className="btn-danger btn-sm" onClick={() => removeItem(key, i)}><Trash2 size={12} /> REMOVE</button>
                                    </div>
                                ))}
                            </section>
                        );
                    })}

                    <button className="btn-primary" onClick={save} disabled={busy}>
                        <Save size={14} /> SAVE TO PROFILE
                    </button>
                </>
            )}
        </div>
    );
}
