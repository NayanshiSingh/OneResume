/* ════════════════════════════════════════════════════════════════
   API Client — wraps fetch for all FastAPI endpoints.
   Requests go to /api on the same origin (proxied by next.config.ts),
   so the httpOnly session cookie is sent automatically.
   ════════════════════════════════════════════════════════════════ */

export class ApiError extends Error {
    constructor(public status: number, message: string) {
        super(message);
    }
}

function detailMessage(body: unknown, fallback: string): string {
    const detail = (body as { detail?: unknown } | null)?.detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail) && detail.length > 0) {
        return detail.map((d: { msg?: string }) => d.msg ?? "Invalid value").join("; ");
    }
    return fallback;
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
    const res = await fetch(path, {
        ...options,
        credentials: "same-origin",
        headers: { "Content-Type": "application/json", ...options?.headers },
    });
    if (!res.ok) {
        const body = await res.json().catch(() => null);
        throw new ApiError(res.status, detailMessage(body, `Request failed (${res.status})`));
    }
    if (res.status === 204) return undefined as T;
    return res.json();
}

const send = <T>(method: string, path: string, body?: unknown) =>
    request<T>(path, { method, body: body === undefined ? undefined : JSON.stringify(body) });

/* ── Types ──────────────────────────────────────────────────── */

export interface User {
    id: string;
    email: string;
    created_at: string;
}

export interface PersonalInfo {
    id: string;
    full_name: string;
    email?: string | null;
    phone_number?: string | null;
}

export interface Bullet {
    id: string;
    bullet_text: string;
}

export interface Education {
    id: string;
    institution: string;
    degree: string;
    field_of_study?: string | null;
    start_year?: number | null;
    end_year?: number | null;
    end_month?: number | null;
    grade?: string | null;
}

export interface Skill {
    id: string;
    skill_name: string;
    skill_category?: string | null;
}

export interface Experience {
    id: string;
    company: string;
    role: string;
    start_date?: string | null;
    end_date?: string | null;
    bullets: Bullet[];
}

export interface Project {
    id: string;
    project_title: string;
    description?: string | null;
    tech_stack?: string | null;
    bullets: Bullet[];
}

export interface Certification {
    id: string;
    name: string;
    issuing_organization?: string | null;
    year?: number | null;
}

export interface Achievement {
    id: string;
    title: string;
    description?: string | null;
    category?: string | null;
}

export interface ExternalProfile {
    id: string;
    platform: string;
    profile_url: string;
}

export interface Profile {
    id: string;
    created_at: string;
    personal_info?: PersonalInfo | null;
    education: Education[];
    skills: Skill[];
    experience: Experience[];
    projects: Project[];
    certifications: Certification[];
    achievements: Achievement[];
    external_profiles: ExternalProfile[];
}

/** URL segment for each editable profile section. */
export type SectionPath =
    | "education" | "skills" | "experience" | "projects"
    | "certifications" | "achievements" | "external-profiles";

export type BulletParent = "experience" | "projects";

export type FieldValues = Record<string, string | number | null>;

export interface JDStructured {
    role_title: string;
    experience_level: string;
    must_have_skills: string[];
    nice_to_have_skills: string[];
    keywords: string[];
    role_category: string;
}

export interface JDAnalysis {
    id: string;
    structured_data: JDStructured;
    created_at: string;
}

export type ExportFormat = "pdf" | "docx";

export interface Resume {
    id: string;
    jd_id?: string | null;
    job_title: string;
    version: number;
    formats: ExportFormat[];
    created_at: string;
}

export interface GenerateResult {
    resume_id: string;
    job_title: string;
    version: number;
    formats: ExportFormat[];
    jd_analysis: JDStructured;
    skill_confidence: Record<string, string>;
    keyword_coverage: Record<string, boolean>;
}

/* ── Accounts ───────────────────────────────────────────────── */

type Credentials = { email: string; password: string };

export const authApi = {
    register: (data: Credentials) => send<User>("POST", "/api/auth/register", data),
    login: (data: Credentials) => send<User>("POST", "/api/auth/login", data),
    logout: () => send<void>("POST", "/api/auth/logout"),
    me: () => request<User>("/api/auth/me"),
    requestPasswordReset: (email: string) =>
        send<{ detail: string }>("POST", "/api/auth/password-reset/request", { email }),
    confirmPasswordReset: (token: string, newPassword: string) =>
        send<void>("POST", "/api/auth/password-reset/confirm", { token, new_password: newPassword }),
    deleteAccount: () => send<void>("DELETE", "/api/auth/account"),
};

/* ── Profile ────────────────────────────────────────────────── */

export const profileApi = {
    get: () => request<Profile>("/api/profile"),

    upsertPersonalInfo: (data: Omit<PersonalInfo, "id">) =>
        send<PersonalInfo>("PUT", "/api/profile/personal-info", data),

    createItem: (section: SectionPath, data: Record<string, unknown>) =>
        send<{ id: string }>("POST", `/api/profile/${section}`, data),
    updateItem: (section: SectionPath, id: string, changes: FieldValues) =>
        send<{ id: string }>("PATCH", `/api/profile/${section}/${id}`, changes),
    deleteItem: (section: SectionPath, id: string) =>
        send<void>("DELETE", `/api/profile/${section}/${id}`),
    reorderItems: (section: SectionPath, ids: string[]) =>
        send<void>("PUT", `/api/profile/${section}/order`, { ids }),

    addBullet: (parent: BulletParent, parentId: string, text: string) =>
        send<Bullet>("POST", `/api/profile/${parent}/${parentId}/bullets`, { bullet_text: text }),
    updateBullet: (parent: BulletParent, bulletId: string, text: string) =>
        send<Bullet>("PATCH", `/api/profile/${parent}/bullets/${bulletId}`, { bullet_text: text }),
    deleteBullet: (parent: BulletParent, bulletId: string) =>
        send<void>("DELETE", `/api/profile/${parent}/bullets/${bulletId}`),
    reorderBullets: (parent: BulletParent, parentId: string, ids: string[]) =>
        send<void>("PUT", `/api/profile/${parent}/${parentId}/bullets/order`, { ids }),
};

/* ── JD Analysis ────────────────────────────────────────────── */

export const jdApi = {
    analyze: (rawText: string) => send<JDAnalysis>("POST", "/api/jd/analyze", { raw_text: rawText }),
    get: (id: string) => request<JDAnalysis>(`/api/jd/${id}`),
};

/* ── Resumes ────────────────────────────────────────────────── */

export const resumesApi = {
    generate: (jdText: string) => send<GenerateResult>("POST", "/api/resumes/generate", { jd_text: jdText }),
    list: () => request<Resume[]>("/api/resumes"),
    get: (id: string) => request<Resume>(`/api/resumes/${id}`),
    delete: (id: string) => send<void>("DELETE", `/api/resumes/${id}`),
    downloadUrl: (id: string, format: ExportFormat) => `/api/resumes/${id}/download?format=${format}`,
};
