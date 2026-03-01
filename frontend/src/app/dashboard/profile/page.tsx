"use client";

import { useEffect, useState, FormEvent, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import {
    Plus,
    Trash2,
    ChevronDown,
    ChevronRight,
    Save,
} from "lucide-react";
import {
    usersApi,
    profilesApi,
    type User,
    type Profile,
    type Education,
    type Skill,
    type Experience,
    type Project,
    type Certification,
    type Achievement,
    type ExternalProfile,
} from "@/lib/api";
import styles from "./page.module.css";

/* ── Collapsible Section Shell ──────────────────────────────── */
function Section({
    tag,
    title,
    count,
    children,
    defaultOpen = false,
}: {
    tag: string;
    title: string;
    count: number;
    children: React.ReactNode;
    defaultOpen?: boolean;
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

function ProfileContent() {
    const searchParams = useSearchParams();
    const router = useRouter();
    const userId = searchParams.get("user_id");

    const [user, setUser] = useState<User | null>(null);
    const [profile, setProfile] = useState<Profile | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");

    /* Personal Info form */
    const [piName, setPiName] = useState("");
    const [piEmail, setPiEmail] = useState("");
    const [piPhone, setPiPhone] = useState("");

    /* Education add form */
    const [eduInst, setEduInst] = useState("");
    const [eduDeg, setEduDeg] = useState("");
    const [eduField, setEduField] = useState("");
    const [eduStart, setEduStart] = useState("");
    const [eduEnd, setEduEnd] = useState("");
    const [eduGrade, setEduGrade] = useState("");

    /* Skills add form */
    const [skillName, setSkillName] = useState("");
    const [skillCat, setSkillCat] = useState("");

    /* Experience add form */
    const [expCompany, setExpCompany] = useState("");
    const [expRole, setExpRole] = useState("");
    const [expStart, setExpStart] = useState("");
    const [expEnd, setExpEnd] = useState("");
    const [expBullets, setExpBullets] = useState("");

    /* Project add form */
    const [projTitle, setProjTitle] = useState("");
    const [projDesc, setProjDesc] = useState("");
    const [projTech, setProjTech] = useState("");
    const [projBullets, setProjBullets] = useState("");

    /* Certification add form */
    const [certName, setCertName] = useState("");
    const [certOrg, setCertOrg] = useState("");
    const [certYear, setCertYear] = useState("");

    /* Achievement add form */
    const [achTitle, setAchTitle] = useState("");
    const [achDesc, setAchDesc] = useState("");
    const [achCat, setAchCat] = useState("");

    /* External Profile add form */
    const [epPlatform, setEpPlatform] = useState("");
    const [epUrl, setEpUrl] = useState("");

    /* ── Load data ───────────────────────────────────────────── */
    async function loadProfile() {
        if (!userId) return;
        try {
            const u = await usersApi.get(userId);
            setUser(u);
            try {
                const p = await profilesApi.getByUser(userId);
                setProfile(p);
                if (p.personal_info) {
                    setPiName(p.personal_info.full_name || "");
                    setPiEmail(p.personal_info.email || "");
                    setPiPhone(p.personal_info.phone_number || "");
                }
            } catch {
                // No profile yet
            }
        } catch {
            // API offline
        } finally {
            setLoading(false);
        }
    }

    useEffect(() => {
        if (!userId) {
            router.replace("/");
            return;
        }
        loadProfile();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [userId]);

    /* ── Handlers ────────────────────────────────────────────── */
    async function savePersonalInfo(e: FormEvent) {
        e.preventDefault();
        if (!profile) return;
        try {
            await profilesApi.upsertPersonalInfo(profile.id, {
                full_name: piName,
                email: piEmail || undefined,
                phone_number: piPhone || undefined,
            });
            await loadProfile();
        } catch (err: unknown) {
            setError((err as Error).message);
        }
    }

    async function addEducation(e: FormEvent) {
        e.preventDefault();
        if (!profile) return;
        try {
            await profilesApi.addEducation(profile.id, {
                institution: eduInst,
                degree: eduDeg,
                field_of_study: eduField || undefined,
                start_year: eduStart ? parseInt(eduStart) : undefined,
                end_year: eduEnd ? parseInt(eduEnd) : undefined,
                grade: eduGrade || undefined,
            });
            setEduInst(""); setEduDeg(""); setEduField(""); setEduStart(""); setEduEnd(""); setEduGrade("");
            await loadProfile();
        } catch (err: unknown) {
            setError((err as Error).message);
        }
    }

    async function addSkill(e: FormEvent) {
        e.preventDefault();
        if (!profile) return;
        try {
            await profilesApi.addSkill(profile.id, {
                skill_name: skillName,
                skill_category: skillCat || undefined,
            });
            setSkillName(""); setSkillCat("");
            await loadProfile();
        } catch (err: unknown) {
            setError((err as Error).message);
        }
    }

    async function addExperience(e: FormEvent) {
        e.preventDefault();
        if (!profile) return;
        try {
            const bullets = expBullets
                .split("\n")
                .filter((b) => b.trim())
                .map((b) => ({ bullet_text: b.trim() }));
            await profilesApi.addExperience(profile.id, {
                company: expCompany,
                role: expRole,
                start_date: expStart || undefined,
                end_date: expEnd || undefined,
                bullets,
            });
            setExpCompany(""); setExpRole(""); setExpStart(""); setExpEnd(""); setExpBullets("");
            await loadProfile();
        } catch (err: unknown) {
            setError((err as Error).message);
        }
    }

    async function addProject(e: FormEvent) {
        e.preventDefault();
        if (!profile) return;
        try {
            const bullets = projBullets
                .split("\n")
                .filter((b) => b.trim())
                .map((b) => ({ bullet_text: b.trim() }));
            await profilesApi.addProject(profile.id, {
                project_title: projTitle,
                description: projDesc || undefined,
                tech_stack: projTech || undefined,
                bullets,
            });
            setProjTitle(""); setProjDesc(""); setProjTech(""); setProjBullets("");
            await loadProfile();
        } catch (err: unknown) {
            setError((err as Error).message);
        }
    }

    async function addCertification(e: FormEvent) {
        e.preventDefault();
        if (!profile) return;
        try {
            await profilesApi.addCertification(profile.id, {
                name: certName,
                issuing_organization: certOrg || undefined,
                year: certYear ? parseInt(certYear) : undefined,
            });
            setCertName(""); setCertOrg(""); setCertYear("");
            await loadProfile();
        } catch (err: unknown) {
            setError((err as Error).message);
        }
    }

    async function addAchievement(e: FormEvent) {
        e.preventDefault();
        if (!profile) return;
        try {
            await profilesApi.addAchievement(profile.id, {
                title: achTitle,
                description: achDesc || undefined,
                category: achCat || undefined,
            });
            setAchTitle(""); setAchDesc(""); setAchCat("");
            await loadProfile();
        } catch (err: unknown) {
            setError((err as Error).message);
        }
    }

    async function addExtProfile(e: FormEvent) {
        e.preventDefault();
        if (!profile) return;
        try {
            await profilesApi.addExternalProfile(profile.id, {
                platform: epPlatform,
                profile_url: epUrl,
            });
            setEpPlatform(""); setEpUrl("");
            await loadProfile();
        } catch (err: unknown) {
            setError((err as Error).message);
        }
    }

    async function deleteItem(
        type: string,
        id: string
    ) {
        try {
            switch (type) {
                case "education": await profilesApi.deleteEducation(id); break;
                case "skill": await profilesApi.deleteSkill(id); break;
                case "experience": await profilesApi.deleteExperience(id); break;
                case "project": await profilesApi.deleteProject(id); break;
                case "certification": await profilesApi.deleteCertification(id); break;
                case "achievement": await profilesApi.deleteAchievement(id); break;
                case "external": await profilesApi.deleteExternalProfile(id); break;
            }
            await loadProfile();
        } catch (err: unknown) {
            setError((err as Error).message);
        }
    }

    /* ── Render ──────────────────────────────────────────────── */
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

            {loading ? (
                <div className={styles.loadingState}>
                    <span className="mono-label loading-pulse">LOADING_PROFILE_DATA...</span>
                </div>
            ) : !profile ? (
                <div className={styles.onboarding}>
                    <span className="mono-label">NO_PROFILE</span>
                    <p className="body-text" style={{ margin: "12px 0" }}>
                        Your account exists but no profile was found.
                    </p>
                    <button className="btn-primary" onClick={async () => {
                        if (!user) return;
                        const p = await profilesApi.create(user.id);
                        setProfile(p);
                    }}>
                        CREATE_PROFILE
                    </button>
                </div>
            ) : (
                /* ── Profile Sections ────────────────────────────────── */
                <div className={styles.sections}>
                    {/* Personal Info */}
                    <Section tag="SEC_00" title="PERSONAL_INFO" count={profile.personal_info ? 1 : 0} defaultOpen={true}>
                        <form onSubmit={savePersonalInfo} className={styles.inlineForm}>
                            <div className="form-row">
                                <div className="form-group">
                                    <label className="label">FULL_NAME</label>
                                    <input className="input" value={piName} onChange={(e) => setPiName(e.target.value)} required placeholder="JOHN_DOE" />
                                </div>
                                <div className="form-group">
                                    <label className="label">EMAIL</label>
                                    <input className="input" value={piEmail} onChange={(e) => setPiEmail(e.target.value)} placeholder="EMAIL@DOMAIN.COM" />
                                </div>
                            </div>
                            <div className="form-group">
                                <label className="label">PHONE</label>
                                <input className="input" value={piPhone} onChange={(e) => setPiPhone(e.target.value)} placeholder="+1_000_000_0000" />
                            </div>
                            <button type="submit" className="btn-primary btn-sm"><Save size={12} /> SAVE</button>
                        </form>
                    </Section>

                    {/* Education */}
                    <Section tag="SEC_01" title="EDUCATION" count={profile.education.length}>
                        {profile.education.map((edu: Education) => (
                            <div key={edu.id} className={styles.listItem}>
                                <div className={styles.listContent}>
                                    <span className={styles.listTitle}>{edu.degree} — {edu.institution}</span>
                                    <span className={styles.listSub}>
                                        {edu.field_of_study && `${edu.field_of_study} · `}
                                        {edu.start_year && `${edu.start_year}`}{edu.end_year && `–${edu.end_year}`}
                                        {edu.grade && ` · GPA: ${edu.grade}`}
                                    </span>
                                </div>
                                <button className="btn-danger btn-sm" onClick={() => deleteItem("education", edu.id)}><Trash2 size={12} /></button>
                            </div>
                        ))}
                        <form onSubmit={addEducation} className={styles.addForm}>
                            <span className="mono-label">ADD_EDUCATION</span>
                            <div className="form-row">
                                <div className="form-group"><label className="label">INSTITUTION</label><input className="input" value={eduInst} onChange={(e) => setEduInst(e.target.value)} required /></div>
                                <div className="form-group"><label className="label">DEGREE</label><input className="input" value={eduDeg} onChange={(e) => setEduDeg(e.target.value)} required /></div>
                            </div>
                            <div className="form-row">
                                <div className="form-group"><label className="label">FIELD_OF_STUDY</label><input className="input" value={eduField} onChange={(e) => setEduField(e.target.value)} /></div>
                                <div className="form-group"><label className="label">GRADE</label><input className="input" value={eduGrade} onChange={(e) => setEduGrade(e.target.value)} /></div>
                            </div>
                            <div className="form-row">
                                <div className="form-group"><label className="label">START_YEAR</label><input className="input" type="number" value={eduStart} onChange={(e) => setEduStart(e.target.value)} /></div>
                                <div className="form-group"><label className="label">END_YEAR</label><input className="input" type="number" value={eduEnd} onChange={(e) => setEduEnd(e.target.value)} /></div>
                            </div>
                            <button type="submit" className="btn-outline btn-sm"><Plus size={12} /> ADD</button>
                        </form>
                    </Section>

                    {/* Skills */}
                    <Section tag="SEC_02" title="SKILLS" count={profile.skills.length}>
                        <div className={styles.skillGrid}>
                            {profile.skills.map((sk: Skill) => (
                                <div key={sk.id} className={styles.skillChip}>
                                    <span>{sk.skill_name}</span>
                                    {sk.skill_category && <span className={styles.skillCat}>{sk.skill_category}</span>}
                                    <button className={styles.chipDelete} onClick={() => deleteItem("skill", sk.id)}><Trash2 size={10} /></button>
                                </div>
                            ))}
                        </div>
                        <form onSubmit={addSkill} className={styles.addForm}>
                            <span className="mono-label">ADD_SKILL</span>
                            <div className="form-row">
                                <div className="form-group"><label className="label">SKILL_NAME</label><input className="input" value={skillName} onChange={(e) => setSkillName(e.target.value)} required /></div>
                                <div className="form-group"><label className="label">CATEGORY</label><input className="input" value={skillCat} onChange={(e) => setSkillCat(e.target.value)} placeholder="OPTIONAL" /></div>
                            </div>
                            <button type="submit" className="btn-outline btn-sm"><Plus size={12} /> ADD</button>
                        </form>
                    </Section>

                    {/* Experience */}
                    <Section tag="SEC_03" title="EXPERIENCE" count={profile.experience.length}>
                        {profile.experience.map((exp: Experience) => (
                            <div key={exp.id} className={styles.listItem}>
                                <div className={styles.listContent}>
                                    <span className={styles.listTitle}>{exp.role} @ {exp.company}</span>
                                    <span className={styles.listSub}>{exp.start_date}{exp.end_date && ` — ${exp.end_date}`}</span>
                                    {exp.bullets.length > 0 && (
                                        <ul className={styles.bulletList}>
                                            {exp.bullets.map((b) => <li key={b.id}>{b.bullet_text}</li>)}
                                        </ul>
                                    )}
                                </div>
                                <button className="btn-danger btn-sm" onClick={() => deleteItem("experience", exp.id)}><Trash2 size={12} /></button>
                            </div>
                        ))}
                        <form onSubmit={addExperience} className={styles.addForm}>
                            <span className="mono-label">ADD_EXPERIENCE</span>
                            <div className="form-row">
                                <div className="form-group"><label className="label">COMPANY</label><input className="input" value={expCompany} onChange={(e) => setExpCompany(e.target.value)} required /></div>
                                <div className="form-group"><label className="label">ROLE</label><input className="input" value={expRole} onChange={(e) => setExpRole(e.target.value)} required /></div>
                            </div>
                            <div className="form-row">
                                <div className="form-group"><label className="label">START_DATE</label><input className="input" value={expStart} onChange={(e) => setExpStart(e.target.value)} placeholder="2023-01" /></div>
                                <div className="form-group"><label className="label">END_DATE</label><input className="input" value={expEnd} onChange={(e) => setExpEnd(e.target.value)} placeholder="PRESENT" /></div>
                            </div>
                            <div className="form-group"><label className="label">BULLETS (ONE_PER_LINE)</label><textarea className="textarea" value={expBullets} onChange={(e) => setExpBullets(e.target.value)} placeholder={"Designed and built...\nLed a team of...\nReduced latency by..."} /></div>
                            <button type="submit" className="btn-outline btn-sm"><Plus size={12} /> ADD</button>
                        </form>
                    </Section>

                    {/* Projects */}
                    <Section tag="SEC_04" title="PROJECTS" count={profile.projects.length}>
                        {profile.projects.map((proj: Project) => (
                            <div key={proj.id} className={styles.listItem}>
                                <div className={styles.listContent}>
                                    <span className={styles.listTitle}>{proj.project_title}</span>
                                    {proj.tech_stack && <span className={styles.listSub}>Stack: {proj.tech_stack}</span>}
                                    {proj.description && <span className={styles.listSub}>{proj.description}</span>}
                                    {proj.bullets.length > 0 && (
                                        <ul className={styles.bulletList}>
                                            {proj.bullets.map((b) => <li key={b.id}>{b.bullet_text}</li>)}
                                        </ul>
                                    )}
                                </div>
                                <button className="btn-danger btn-sm" onClick={() => deleteItem("project", proj.id)}><Trash2 size={12} /></button>
                            </div>
                        ))}
                        <form onSubmit={addProject} className={styles.addForm}>
                            <span className="mono-label">ADD_PROJECT</span>
                            <div className="form-group"><label className="label">PROJECT_TITLE</label><input className="input" value={projTitle} onChange={(e) => setProjTitle(e.target.value)} required /></div>
                            <div className="form-row">
                                <div className="form-group"><label className="label">DESCRIPTION</label><input className="input" value={projDesc} onChange={(e) => setProjDesc(e.target.value)} /></div>
                                <div className="form-group"><label className="label">TECH_STACK</label><input className="input" value={projTech} onChange={(e) => setProjTech(e.target.value)} placeholder="Python, React, Docker" /></div>
                            </div>
                            <div className="form-group"><label className="label">BULLETS (ONE_PER_LINE)</label><textarea className="textarea" value={projBullets} onChange={(e) => setProjBullets(e.target.value)} placeholder={"Implemented...\nAchieved..."} /></div>
                            <button type="submit" className="btn-outline btn-sm"><Plus size={12} /> ADD</button>
                        </form>
                    </Section>

                    {/* Certifications */}
                    <Section tag="SEC_05" title="CERTIFICATIONS" count={profile.certifications.length}>
                        {profile.certifications.map((cert: Certification) => (
                            <div key={cert.id} className={styles.listItem}>
                                <div className={styles.listContent}>
                                    <span className={styles.listTitle}>{cert.name}</span>
                                    <span className={styles.listSub}>{cert.issuing_organization}{cert.year && ` · ${cert.year}`}</span>
                                </div>
                                <button className="btn-danger btn-sm" onClick={() => deleteItem("certification", cert.id)}><Trash2 size={12} /></button>
                            </div>
                        ))}
                        <form onSubmit={addCertification} className={styles.addForm}>
                            <span className="mono-label">ADD_CERTIFICATION</span>
                            <div className="form-row">
                                <div className="form-group"><label className="label">NAME</label><input className="input" value={certName} onChange={(e) => setCertName(e.target.value)} required /></div>
                                <div className="form-group"><label className="label">ISSUING_ORG</label><input className="input" value={certOrg} onChange={(e) => setCertOrg(e.target.value)} /></div>
                            </div>
                            <div className="form-group"><label className="label">YEAR</label><input className="input" type="number" value={certYear} onChange={(e) => setCertYear(e.target.value)} /></div>
                            <button type="submit" className="btn-outline btn-sm"><Plus size={12} /> ADD</button>
                        </form>
                    </Section>

                    {/* Achievements */}
                    <Section tag="SEC_06" title="ACHIEVEMENTS" count={profile.achievements.length}>
                        {profile.achievements.map((ach: Achievement) => (
                            <div key={ach.id} className={styles.listItem}>
                                <div className={styles.listContent}>
                                    <span className={styles.listTitle}>{ach.title}</span>
                                    <span className={styles.listSub}>{ach.description}{ach.category && ` · ${ach.category}`}</span>
                                </div>
                                <button className="btn-danger btn-sm" onClick={() => deleteItem("achievement", ach.id)}><Trash2 size={12} /></button>
                            </div>
                        ))}
                        <form onSubmit={addAchievement} className={styles.addForm}>
                            <span className="mono-label">ADD_ACHIEVEMENT</span>
                            <div className="form-group"><label className="label">TITLE</label><input className="input" value={achTitle} onChange={(e) => setAchTitle(e.target.value)} required /></div>
                            <div className="form-row">
                                <div className="form-group"><label className="label">DESCRIPTION</label><input className="input" value={achDesc} onChange={(e) => setAchDesc(e.target.value)} /></div>
                                <div className="form-group"><label className="label">CATEGORY</label><input className="input" value={achCat} onChange={(e) => setAchCat(e.target.value)} /></div>
                            </div>
                            <button type="submit" className="btn-outline btn-sm"><Plus size={12} /> ADD</button>
                        </form>
                    </Section>

                    {/* External Profiles */}
                    <Section tag="SEC_07" title="EXTERNAL_PROFILES" count={profile.external_profiles.length}>
                        {profile.external_profiles.map((ep: ExternalProfile) => (
                            <div key={ep.id} className={styles.listItem}>
                                <div className={styles.listContent}>
                                    <span className={styles.listTitle}>{ep.platform}</span>
                                    <a href={ep.profile_url} target="_blank" rel="noopener" className={styles.listSub} style={{ color: "var(--accent)" }}>{ep.profile_url}</a>
                                </div>
                                <button className="btn-danger btn-sm" onClick={() => deleteItem("external", ep.id)}><Trash2 size={12} /></button>
                            </div>
                        ))}
                        <form onSubmit={addExtProfile} className={styles.addForm}>
                            <span className="mono-label">ADD_EXTERNAL_PROFILE</span>
                            <div className="form-row">
                                <div className="form-group"><label className="label">PLATFORM</label><input className="input" value={epPlatform} onChange={(e) => setEpPlatform(e.target.value)} required placeholder="GITHUB" /></div>
                                <div className="form-group"><label className="label">URL</label><input className="input" value={epUrl} onChange={(e) => setEpUrl(e.target.value)} required placeholder="https://github.com/username" /></div>
                            </div>
                            <button type="submit" className="btn-outline btn-sm"><Plus size={12} /> ADD</button>
                        </form>
                    </Section>
                </div>
            )}
        </div>
    );
}

export default function ProfilePage() {
    return (
        <Suspense fallback={<div className="loading-pulse">LOADING...</div>}>
            <ProfileContent />
        </Suspense>
    );
}
