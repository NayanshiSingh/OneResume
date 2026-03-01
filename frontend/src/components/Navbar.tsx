"use client";

import Link from "next/link";
import { Github, Twitter, Linkedin } from "lucide-react";
import styles from "./Navbar.module.css";

export default function Navbar() {
    return (
        <nav className={styles.nav}>
            <div className={styles.left}>
                <Link href="/" className={styles.brand}>
                    ONERESUME
                </Link>
                <span className={styles.dot}></span>
                <span className={`mono-label ${styles.version}`}>BETA_V.01</span>
            </div>
            <div className={styles.right}>
                <a
                    href="https://github.com"
                    target="_blank"
                    rel="noopener"
                    className="btn-icon"
                    aria-label="GitHub"
                >
                    <Github size={16} />
                </a>
                <a
                    href="https://twitter.com"
                    target="_blank"
                    rel="noopener"
                    className="btn-icon"
                    aria-label="Twitter"
                >
                    <Twitter size={16} />
                </a>
                <a
                    href="https://linkedin.com"
                    target="_blank"
                    rel="noopener"
                    className="btn-icon"
                    aria-label="LinkedIn"
                >
                    <Linkedin size={16} />
                </a>
                <Link href="/dashboard" className="btn-primary btn-pill">
                    GET ACCESS
                </Link>
            </div>
        </nav>
    );
}
