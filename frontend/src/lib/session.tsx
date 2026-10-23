"use client";

import { createContext, useContext, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { ApiError, authApi, type User } from "@/lib/api";

interface Session {
    user: User;
    signOut: () => Promise<void>;
}

const SessionContext = createContext<Session | null>(null);

/** Loads the signed-in user; sends visitors without a session back to the sign-in page. */
export function SessionProvider({ children }: { children: React.ReactNode }) {
    const router = useRouter();
    const [user, setUser] = useState<User | null>(null);
    const [error, setError] = useState("");

    useEffect(() => {
        authApi.me().then(setUser).catch((err: unknown) => {
            if (err instanceof ApiError && err.status === 401) router.replace("/");
            else setError((err as Error).message);
        });
    }, [router]);

    async function signOut() {
        await authApi.logout();
        router.replace("/");
    }

    if (error) {
        return <div style={{ padding: 48 }}><span className="mono-label" style={{ color: "#ef4444" }}>ERROR: {error}</span></div>;
    }
    if (!user) {
        return <div style={{ padding: 48 }}><span className="mono-label loading-pulse">CHECKING_SESSION...</span></div>;
    }
    return <SessionContext.Provider value={{ user, signOut }}>{children}</SessionContext.Provider>;
}

export function useSession(): Session {
    const session = useContext(SessionContext);
    if (!session) throw new Error("useSession must be used inside SessionProvider");
    return session;
}
