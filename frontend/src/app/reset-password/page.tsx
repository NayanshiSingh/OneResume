"use client";

import { FormEvent, Suspense, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import Navbar from "@/components/Navbar";
import { authApi } from "@/lib/api";
import styles from "../auth.module.css";

function ResetPasswordForm() {
    const token = useSearchParams().get("token") ?? "";
    const [password, setPassword] = useState("");
    const [confirm, setConfirm] = useState("");
    const [done, setDone] = useState(false);
    const [error, setError] = useState("");
    const [loading, setLoading] = useState(false);

    async function submit(e: FormEvent) {
        e.preventDefault();
        if (password !== confirm) {
            setError("Passwords do not match.");
            return;
        }
        setLoading(true);
        setError("");
        try {
            await authApi.confirmPasswordReset(token, password);
            setDone(true);
        } catch (err: unknown) {
            setError((err as Error).message);
        } finally {
            setLoading(false);
        }
    }

    if (!token) {
        return <p className={`mono-label ${styles.error}`}>This reset link is missing its token.</p>;
    }
    if (done) {
        return <p className={`body-text ${styles.message}`}>Your password has been changed. Sign in with your new password.</p>;
    }
    return (
        <>
            <form onSubmit={submit} className={styles.form}>
                <div className="form-group">
                    <label className="label" htmlFor="password">NEW_PASSWORD (8+ CHARACTERS)</label>
                    <input id="password" className="input" type="password" minLength={8} required value={password} onChange={(e) => setPassword(e.target.value)} />
                </div>
                <div className="form-group">
                    <label className="label" htmlFor="confirm">CONFIRM_PASSWORD</label>
                    <input id="confirm" className="input" type="password" minLength={8} required value={confirm} onChange={(e) => setConfirm(e.target.value)} />
                </div>
                <button type="submit" className="btn-primary" disabled={loading}>
                    {loading ? "SAVING..." : "SET NEW PASSWORD"}
                </button>
            </form>
            {error && <p className={`mono-label ${styles.error}`}>ERROR: {error}</p>}
        </>
    );
}

export default function ResetPasswordPage() {
    return (
        <>
            <Navbar />
            <main className={styles.page}>
                <span className="mono-label">ACCOUNT / RECOVERY</span>
                <h1 className={`headline ${styles.title}`}>CHOOSE A NEW PASSWORD</h1>
                <Suspense fallback={<span className="mono-label loading-pulse">LOADING...</span>}>
                    <ResetPasswordForm />
                </Suspense>
                <Link href="/" className={styles.back}>Back to sign in</Link>
            </main>
        </>
    );
}
