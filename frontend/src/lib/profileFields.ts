import type { BulletParent, Bullet, Profile, SectionPath } from "@/lib/api";

/* ── Section definitions ────────────────────────────────────── */

export interface FieldDef {
    name: string;
    label: string;
    type?: "text" | "number" | "month";
    required?: boolean;
    placeholder?: string;
}

export type Item = { id: string; bullets?: Bullet[] } & Record<string, unknown>;

export interface SectionDef {
    path: SectionPath;
    key: keyof Profile;
    tag: string;
    title: string;
    fields: FieldDef[];
    heading: (item: Item) => string;
    detail: (item: Item) => string;
    bullets?: BulletParent;
}

export const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

const join = (...parts: unknown[]) => parts.filter((p) => p !== null && p !== undefined && p !== "").join(" · ");

export const SECTIONS: SectionDef[] = [
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

