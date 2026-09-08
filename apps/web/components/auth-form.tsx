"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";

import { setAccessToken } from "@/lib/auth";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

type AuthFormProps = { mode: "login" | "signup" };

export function AuthForm({ mode }: AuthFormProps) {
  const isSignup = mode === "signup";
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [workspaceName, setWorkspaceName] = useState("My creator workspace");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`${API_URL}/v1/auth/${mode}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(
          isSignup
            ? { email, password, display_name: displayName, workspace_name: workspaceName }
            : { email, password },
        ),
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.detail ?? "Authentication failed");
      setAccessToken(payload.access_token);
      window.localStorage.setItem("reelpilot_user", JSON.stringify(payload.user));
      router.replace("/");
    } catch (authError) {
      setError(authError instanceof Error ? authError.message : "Authentication failed");
      setLoading(false);
    }
  }

  return (
    <main className="auth-shell">
      <section className="auth-card">
        <div className="auth-brand"><span>✦</span> ReelPilot <em>AI</em></div>
        <p className="auth-kicker">CREATOR WORKSPACE</p>
        <h1>{isSignup ? "Turn audience questions into your next Reel." : "Welcome back, creator."}</h1>
        <p className="auth-copy">{isSignup ? "Start with a free workspace. No Instagram connection required." : "Sign in to continue to your audience intelligence dashboard."}</p>
        <form onSubmit={submit}>
          {isSignup && <label>Your name<input required value={displayName} onChange={(event) => setDisplayName(event.target.value)} placeholder="Aarav Kapoor" /></label>}
          <label>Email<input required type="email" value={email} onChange={(event) => setEmail(event.target.value)} placeholder="you@example.com" /></label>
          <label>Password<input required minLength={8} type="password" value={password} onChange={(event) => setPassword(event.target.value)} placeholder={isSignup ? "At least 8 characters" : "Your password"} /></label>
          {isSignup && <label>Workspace name<input required value={workspaceName} onChange={(event) => setWorkspaceName(event.target.value)} /></label>}
          {error && <p className="auth-error" role="alert">{error}</p>}
          <button type="submit" disabled={loading}>{loading ? "Please wait…" : isSignup ? "Create workspace" : "Sign in"}</button>
        </form>
        <p className="auth-switch">{isSignup ? "Already have an account?" : "New to ReelPilot?"} <Link href={isSignup ? "/login" : "/signup"}>{isSignup ? "Sign in" : "Create an account"}</Link></p>
      </section>
      <aside className="auth-aside"><div className="aside-orbit">✦</div><p>“The best content ideas were already hiding in my comments.”</p><span>— early ReelPilot creator</span></aside>
    </main>
  );
}
