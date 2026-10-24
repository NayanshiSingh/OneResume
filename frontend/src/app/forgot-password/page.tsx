"use client";

import { FormEvent, useState } from "react";
import Link from "next/link";
import Navbar from "@/components/Navbar";
import { authApi } from "@/lib/api";
import styles from "../auth.module.css";

export default function ForgotPasswordPage() {
    const [email, setEmail] = useState("");
    const [message, setMessage] = useState("");
    const [error, setError] = useState("");
    const [loading, setLoading] = useState(false);

    async function submit(e: FormEvent) {
        e.preventDefault();
        setLoading(true);
        setError("");
        try {
            setMessage((await authApi.requestPasswordReset(email)).detail);
        } catch (err: unknown) {
            setError((err as Error).message);
        } finally {
            setLoading(false);
        }
    }

    return (
        <>
            <Navbar />
            <main className={styles.page}>
                <span className="mono-label">ACCOUNT / RECOVERY</span>
                <h1 className={`headline ${styles.title}`}>RESET PASSWORD</h1>
                <form onSubmit={submit} className={styles.form}>
                    <div className="form-group">
                        <label className="label" htmlFor="email">EMAIL</label>
                        <input id="email" className="input" type="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
                    </div>
                    <button type="submit" className="btn-primary" disabled={loading}>
                        {loading ? "SENDING..." : "SEND RESET LINK"}
                    </button>
                </form>
                {message && <p className={`body-text ${styles.message}`}>{message}</p>}
                {error && <p className={`mono-label ${styles.error}`}>ERROR: {error}</p>}
                <Link href="/" className={styles.back}>Back to sign in</Link>
            </main>
        </>
    );
}
