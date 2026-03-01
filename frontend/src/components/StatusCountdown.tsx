"use client";

import { useEffect, useMemo, useState } from "react";
import styles from "./StatusCountdown.module.css";

interface Props {
    targetDate?: Date;
}

export default function StatusCountdown({ targetDate }: Props) {
    const target = useMemo(
        () => targetDate || new Date(Date.now() + 7 * 24 * 60 * 60 * 1000),
        [targetDate]
    );

    const [time, setTime] = useState({ h: "00", m: "00", s: "00" });

    useEffect(() => {
        function update() {
            const diff = Math.max(0, target.getTime() - Date.now());
            const h = Math.floor(diff / 3600000);
            const m = Math.floor((diff % 3600000) / 60000);
            const s = Math.floor((diff % 60000) / 1000);
            setTime({
                h: String(h).padStart(2, "0"),
                m: String(m).padStart(2, "0"),
                s: String(s).padStart(2, "0"),
            });
        }
        update();
        const id = setInterval(update, 1000);
        return () => clearInterval(id);
    }, [target]);

    return (
        <div className={styles.timer}>
            <span className={styles.digit}>{time.h}</span>
            <span className={styles.sep}>:</span>
            <span className={styles.digit}>{time.m}</span>
            <span className={styles.sep}>:</span>
            <span className={styles.digit}>{time.s}</span>
        </div>
    );
}
