/* ════════════════════════════════════════════════════════════════
   API Client — wraps fetch for all FastAPI endpoints
   ════════════════════════════════════════════════════════════════ */

const BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
    const res = await fetch(`${BASE}${path}`, {
        headers: { "Content-Type": "application/json", ...options?.headers },
        ...options,
    });
    if (!res.ok) {
        const text = await res.text();
        throw new Error(`API ${res.status}: ${text}`);
    }
    if (res.status === 204) return undefined as T;
    return res.json();
}

/* ── Types ──────────────────────────────────────────────────── */

export interface User {
    id: string;
    username: string;
    email: string;
    created_at: string;
}

export interface PersonalInfo {
    id: string;
    full_name: string;
    email?: string;
    phone_number?: string;
}

export interface Education {
    id: string;
    institution: string;
    degree: string;
    field_of_study?: string;
    start_year?: number;
    end_year?: number;
    grade?: string;
}

export interface Skill {
    id: string;
    skill_name: string;
    skill_category?: string;
}

export interface ExperienceBullet {
    id: string;
    bullet_text: string;
}

export interface Experience {
    id: string;
    company: string;
    role: string;
    start_date?: string;
    end_date?: string;
    bullets: ExperienceBullet[];
}

export interface ProjectBullet {
    id: string;
    bullet_text: string;
}

export interface Project {
    id: string;
    project_title: string;
    description?: string;
    tech_stack?: string;
    bullets: ProjectBullet[];
}

export interface Certification {
    id: string;
    name: string;
    issuing_organization?: string;
    year?: number;
}

export interface Achievement {
    id: string;
    title: string;
    description?: string;
    category?: string;
}

export interface ExternalProfile {
    id: string;
    platform: string;
    profile_url: string;
}

export interface Profile {
    id: string;
    user_id: string;
    created_at: string;
    personal_info?: PersonalInfo;
    education: Education[];
    skills: Skill[];
    experience: Experience[];
    projects: Project[];
    certifications: Certification[];
    achievements: Achievement[];
    external_profiles: ExternalProfile[];
}

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

export interface Resume {
    id: string;
    profile_id: string;
    jd_id?: string;
    job_title: string;
    version: number;
    file_path?: string;
    created_at: string;
}

export interface GenerateResult {
    resume_id: string;
    job_title: string;
    version: number;
    pdf_path: string;
    docx_path: string;
    jd_analysis: JDStructured;
    skill_confidence: Record<string, string>;
    keyword_coverage: Record<string, boolean>;
}

/* ── Users ──────────────────────────────────────────────────── */

export const usersApi = {
    loginOrRegister: (data: { email: string; password: string }) =>
        request<User>("/api/users/login-or-register", {
            method: "POST",
            body: JSON.stringify(data),
        }),

    create: (data: { username: string; email: string; password: string }) =>
        request<User>("/api/users/", { method: "POST", body: JSON.stringify(data) }),

    list: () => request<User[]>("/api/users/"),

    get: (id: string) => request<User>(`/api/users/${id}`),

    delete: (id: string) =>
        request<void>(`/api/users/${id}`, { method: "DELETE" }),
};

/* ── Profiles ───────────────────────────────────────────────── */

export const profilesApi = {
    create: (userId: string) =>
        request<Profile>(`/api/profiles/${userId}`, { method: "POST" }),

    get: (profileId: string) => request<Profile>(`/api/profiles/${profileId}`),

    getByUser: (userId: string) => request<Profile>(`/api/profiles/by-user/${userId}`),

    delete: (profileId: string) =>
        request<void>(`/api/profiles/${profileId}`, { method: "DELETE" }),

    /* Personal Info */
    upsertPersonalInfo: (profileId: string, data: Omit<PersonalInfo, "id">) =>
        request<PersonalInfo>(`/api/profiles/${profileId}/personal-info`, {
            method: "PUT",
            body: JSON.stringify(data),
        }),

    /* Education */
    addEducation: (profileId: string, data: Omit<Education, "id">) =>
        request<Education>(`/api/profiles/${profileId}/education`, {
            method: "POST",
            body: JSON.stringify(data),
        }),
    listEducation: (profileId: string) =>
        request<Education[]>(`/api/profiles/${profileId}/education`),
    deleteEducation: (id: string) =>
        request<void>(`/api/profiles/education/${id}`, { method: "DELETE" }),

    /* Skills */
    addSkill: (profileId: string, data: Omit<Skill, "id">) =>
        request<Skill>(`/api/profiles/${profileId}/skills`, {
            method: "POST",
            body: JSON.stringify(data),
        }),
    listSkills: (profileId: string) =>
        request<Skill[]>(`/api/profiles/${profileId}/skills`),
    deleteSkill: (id: string) =>
        request<void>(`/api/profiles/skills/${id}`, { method: "DELETE" }),

    /* Experience */
    addExperience: (
        profileId: string,
        data: {
            company: string;
            role: string;
            start_date?: string;
            end_date?: string;
            bullets: { bullet_text: string }[];
        }
    ) =>
        request<Experience>(`/api/profiles/${profileId}/experience`, {
            method: "POST",
            body: JSON.stringify(data),
        }),
    listExperience: (profileId: string) =>
        request<Experience[]>(`/api/profiles/${profileId}/experience`),
    deleteExperience: (id: string) =>
        request<void>(`/api/profiles/experience/${id}`, { method: "DELETE" }),

    /* Projects */
    addProject: (
        profileId: string,
        data: {
            project_title: string;
            description?: string;
            tech_stack?: string;
            bullets: { bullet_text: string }[];
        }
    ) =>
        request<Project>(`/api/profiles/${profileId}/projects`, {
            method: "POST",
            body: JSON.stringify(data),
        }),
    listProjects: (profileId: string) =>
        request<Project[]>(`/api/profiles/${profileId}/projects`),
    deleteProject: (id: string) =>
        request<void>(`/api/profiles/projects/${id}`, { method: "DELETE" }),

    /* Certifications */
    addCertification: (profileId: string, data: Omit<Certification, "id">) =>
        request<Certification>(`/api/profiles/${profileId}/certifications`, {
            method: "POST",
            body: JSON.stringify(data),
        }),
    listCertifications: (profileId: string) =>
        request<Certification[]>(`/api/profiles/${profileId}/certifications`),
    deleteCertification: (id: string) =>
        request<void>(`/api/profiles/certifications/${id}`, { method: "DELETE" }),

    /* Achievements */
    addAchievement: (profileId: string, data: Omit<Achievement, "id">) =>
        request<Achievement>(`/api/profiles/${profileId}/achievements`, {
            method: "POST",
            body: JSON.stringify(data),
        }),
    listAchievements: (profileId: string) =>
        request<Achievement[]>(`/api/profiles/${profileId}/achievements`),
    deleteAchievement: (id: string) =>
        request<void>(`/api/profiles/achievements/${id}`, { method: "DELETE" }),

    /* External Profiles */
    addExternalProfile: (profileId: string, data: Omit<ExternalProfile, "id">) =>
        request<ExternalProfile>(`/api/profiles/${profileId}/external-profiles`, {
            method: "POST",
            body: JSON.stringify(data),
        }),
    listExternalProfiles: (profileId: string) =>
        request<ExternalProfile[]>(`/api/profiles/${profileId}/external-profiles`),
    deleteExternalProfile: (id: string) =>
        request<void>(`/api/profiles/external-profiles/${id}`, {
            method: "DELETE",
        }),
};

/* ── JD Analysis ────────────────────────────────────────────── */

export const jdApi = {
    analyze: (rawText: string) =>
        request<JDAnalysis>("/api/jd/analyze", {
            method: "POST",
            body: JSON.stringify({ raw_text: rawText }),
        }),

    get: (id: string) => request<JDAnalysis>(`/api/jd/${id}`),
};

/* ── Resumes ────────────────────────────────────────────────── */

export const resumesApi = {
    generate: (profileId: string, jdText: string) =>
        request<GenerateResult>("/api/resumes/generate", {
            method: "POST",
            body: JSON.stringify({ profile_id: profileId, jd_text: jdText }),
        }),

    list: (profileId: string) =>
        request<Resume[]>(`/api/resumes/?profile_id=${profileId}`),

    get: (id: string) => request<Resume>(`/api/resumes/${id}`),

    downloadUrl: (id: string, format: "pdf" | "docx" = "pdf") =>
        `${BASE}/api/resumes/${id}/download?format=${format}`,
};
