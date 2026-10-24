"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import Navbar from "@/components/Navbar";
import GeometricCard from "@/components/GeometricCard";
import { authApi } from "@/lib/api";
import styles from "./page.module.css";

export default function LandingPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [mode, setMode] = useState<"signin" | "register">("signin");
  const router = useRouter();

  async function handleJoin() {
    if (!email || !password) {
      setError("Please enter both email and password.");
      return;
    }
    if (mode === "register" && password.length < 8) {
      setError("Password must be at least 8 characters.");
      return;
    }
    setError("");
    setLoading(true);
    try {
      await (mode === "register" ? authApi.register : authApi.login)({ email, password });
      router.push("/dashboard");
    } catch (err: unknown) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      <Navbar />

      {/* ── HERO — 2×2 Grid ──────────────────────────────────── */}
      <section className={styles.hero}>
        <div className={`${styles.cell} ${styles.cellTL}`}>
          <span className={styles.heroText}>ONE</span>
        </div>
        <div className={`${styles.cell} ${styles.cellTR}`}>
          <span className={styles.heroText}>RE</span>
        </div>
        <div className={`${styles.cell} ${styles.cellBL}`}>
          <span className={styles.heroText}>SU</span>
        </div>
        <div className={`${styles.cell} ${styles.cellBR}`}>
          <span className={styles.heroText}>ME</span>
        </div>

        {/* Center tagline overlaid */}
        <div className={styles.heroCenterOverlay}>
          <p className={styles.heroTagline}>
            AI-Powered, Role-Specific Resume Generation
          </p>
        </div>
      </section>

      {/* ── COMMAND BAR ──────────────────────────────────────── */}
      <section className={styles.commandBar}>
        <div className={styles.cmdCell}>
          <input
            type="email"
            placeholder="ENTER_YOUR_EMAIL"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className={styles.cmdInput}
          />
        </div>
        <div className={styles.cmdCell}>
          <input
            type="password"
            placeholder="ENTER_PASSWORD"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className={styles.cmdInput}
            onKeyDown={(e) => e.key === "Enter" && handleJoin()}
          />
        </div>
        <div className={`${styles.cmdCell} ${styles.cmdCellJoin}`}>
          <button
            className={styles.joinBtn}
            onClick={handleJoin}
            disabled={loading}
          >
            {loading ? "ACCESSING..." : mode === "register" ? "CREATE ACCOUNT" : "SIGN IN"}
          </button>
        </div>
      </section>

      <div className={styles.authLinks}>
        <button
          type="button"
          className={styles.authLink}
          onClick={() => { setMode(mode === "register" ? "signin" : "register"); setError(""); }}
        >
          {mode === "register" ? "Already have an account? Sign in" : "New here? Create an account"}
        </button>
        <Link href="/forgot-password" className={styles.authLink}>Forgot password?</Link>
      </div>

      {/* ── Error Message ────────────────────────────────────── */}
      {error && (
        <div className={styles.errorBar}>
          <span className={styles.errorText}>⚠ {error}</span>
        </div>
      )}

      {/* ── BENTO FEATURE GRID ───────────────────────────────── */}
      <section className={styles.bentoSection}>
        <div className={styles.bentoHeader}>
          <span className={styles.sectionLabel}>Features</span>
          <h2 className={`headline ${styles.bentoTitle}`}>
            BUILT FOR
            <br />
            PRECISION
          </h2>
        </div>
        <div className={styles.bentoGrid}>
          <GeometricCard
            tag="SYSTEM_01"
            title="JD ANALYSIS"
            subtitle="AI-powered job description parsing. Extract role titles, must-have skills, experience levels, and keywords automatically."
          />
          <GeometricCard
            tag="SYSTEM_02"
            title="SEMANTIC MATCH"
            subtitle="Hybrid embedding strategy with section-level and bullet-level semantic similarity scoring for precision relevance."
          />
          <GeometricCard
            tag="SYSTEM_03"
            title="ATS OPTIMIZED"
            subtitle="Rule-based ATS optimization engine ensures keyword alignment, formatting consistency, and one-page constraints."
          />
          <GeometricCard
            tag="SYSTEM_04"
            title="AI REWRITING"
            subtitle="LLM-powered bullet rewriting transforms your experience into clear, impact-driven, ATS-friendly language."
          />
          <GeometricCard
            tag="SYSTEM_05"
            title="ONE PROFILE"
            subtitle="Maintain a single, rich profile. Education, experience, projects, skills — all structured and ready for any role."
          />
          <GeometricCard
            tag="SYSTEM_06"
            title="INSTANT EXPORT"
            subtitle="Generate clean, single-column resumes that applicant tracking systems can read. Download as PDF or DOCX."
          />
        </div>
      </section>

      {/* ── FOOTER ───────────────────────────────────────────── */}
      <footer className={styles.footer}>
        <div className={styles.footerLeft}>
          <span className={styles.footerText}>© 2026 OneResume</span>
        </div>
        <div className={styles.footerRight}>
          <span className={styles.footerText}>Designed with Precision</span>
        </div>
      </footer>
    </>
  );
}
