"use client";

import styles from "./GeometricCard.module.css";

interface Props {
    tag: string;
    title: string;
    subtitle: string;
}

export default function GeometricCard({ tag, title, subtitle }: Props) {
    return (
        <div className={styles.card}>
            <span className={`mono-label ${styles.tag}`}>{tag}</span>
            <div className={styles.center}>
                <div className={styles.diamond}></div>
            </div>
            <div className={styles.bottom}>
                <h3 className={styles.title}>{title}</h3>
                <p className={styles.sub}>{subtitle}</p>
            </div>
        </div>
    );
}
