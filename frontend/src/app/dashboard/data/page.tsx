"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { systemApi, type AIStatus } from "@/lib/api";
import styles from "./page.module.css";

function Status({ on }: { on: boolean | undefined }) {
    if (on === undefined) return null;
    return <span className={styles.status}>{on ? "[ON on this server]" : "[OFF: nothing is sent]"}</span>;
}

export default function DataPage() {
    const [status, setStatus] = useState<AIStatus | null>(null);
    useEffect(() => {
        systemApi.aiStatus().then(setStatus).catch(() => setStatus(null));
    }, []);

    return (
        <div>
            <div className={styles.pageHeader}>
                <span className="mono-label">DASHBOARD / DATA_&amp;_AI</span>
                <h1 className={`headline ${styles.pageTitle}`}>WHERE YOUR DATA GOES</h1>
            </div>

            <section className={styles.section}>
                <span className="mono-label">GOOGLE GEMINI <Status on={status?.llm} /></span>
                <ul className={styles.list}>
                    <li><strong>Importing a resume:</strong> the full text of the file you upload, including your name and contact details.</li>
                    <li><strong>Analysing a job description:</strong> the text you paste.</li>
                    <li><strong>Suggested wording:</strong> the role title and requirements, plus each selected bullet with its job or project title. A second request checks each suggestion against your original bullet. Your name, email, phone, and links are not sent.</li>
                </ul>
                <p className="body-text">
                    If the server&apos;s Gemini key is on Google&apos;s free tier, Google may use what is sent to improve its products.
                    Use a paid key before entering real resumes.
                </p>
            </section>

            <section className={styles.section}>
                <span className="mono-label">PINECONE <Status on={status?.embeddings} /></span>
                <ul className={styles.list}>
                    <li>The text of your experience and project bullets, and the job&apos;s title, requirements, and keywords, to measure how related they are. The results are stored with your profile so bullets are only sent again after you edit them.</li>
                    <li>Your name, contact details, and links are not sent.</li>
                </ul>
            </section>

            <section className={styles.section}>
                <span className="mono-label">STORED ON THIS SERVER</span>
                <ul className={styles.list}>
                    <li>Your profile, job descriptions, drafts, and exported PDF and DOCX files. Files are private to your account.</li>
                    <li>Counts of AI actions and failed sign-ins, used to enforce limits.</li>
                    <li>Uploaded resumes are read and then discarded; only the fields you apply are saved.</li>
                </ul>
                <p className="body-text">
                    Deleting your account on the <Link href="/dashboard/profile">profile page</Link> removes all of it.
                </p>
            </section>
        </div>
    );
}
