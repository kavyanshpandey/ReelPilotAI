"use client";

import { useEffect, useRef, useState, useSyncExternalStore } from "react";
import { useRouter } from "next/navigation";

import { ContentStudioDialog } from "@/components/content-studio-dialog";
import { ImportCommentsDialog, type ImportCommentsDialogHandle } from "@/components/import-comments-dialog";
import type { AnalysisCluster, AnalysisResult, InstagramAccount, UsageResponse } from "@/lib/api-types";
import { authHeaders, clearAccessToken, getAccessToken } from "@/lib/auth";

const sampleClusters = [
  {
    id: null,
    source: null,
    rank: "01",
    question: "How much should I budget for a 7-day Ladakh trip?",
    signal: "Strong signal",
    mentions: 27,
    growth: "+42%",
    languages: ["English", "Hinglish"],
    samples: [
      "Bhai total Ladakh trip ka budget kitna tha?",
      "Can you share a complete 7-day cost breakdown?",
    ],
    accent: "violet",
  },
  {
    id: null,
    source: null,
    rank: "02",
    question: "Which camera and settings do you use for travel Reels?",
    signal: "Rising",
    mentions: 18,
    growth: "+31%",
    languages: ["English"],
    samples: [
      "Which camera did you shoot this on?",
      "Please make a Reel about your export settings.",
    ],
    accent: "cyan",
  },
  {
    id: null,
    source: null,
    rank: "03",
    question: "Is Ladakh safe for a first solo trip?",
    signal: "Consistent",
    mentions: 14,
    growth: "+12%",
    languages: ["Hindi", "English"],
    samples: [
      "Solo jaana safe hai kya?",
      "Would you recommend this route for a first-time solo traveller?",
    ],
    accent: "orange",
  },
];

const noAuthSubscription = () => () => {};
const readClientAuth = () => Boolean(getAccessToken());
const readServerAuth = () => false;

function Icon({ name }: { name: "spark" | "grid" | "comments" | "ideas" | "studio" | "settings" | "upload" | "instagram" }) {
  const paths = {
    spark: "M12 2l1.8 6.2L20 10l-6.2 1.8L12 18l-1.8-6.2L4 10l6.2-1.8L12 2Z",
    grid: "M4 4h6v6H4V4Zm10 0h6v6h-6V4ZM4 14h6v6H4v-6Zm10 0h6v6h-6v-6Z",
    comments: "M4 5h16v11H9l-5 4V5Z",
    ideas: "M9 18h6M10 22h4M8.5 14.5A7 7 0 1 1 15.5 14.5C14.4 15.3 14 16 14 17h-4c0-1-.4-1.7-1.5-2.5Z",
    studio: "M4 4h16v16H4V4Zm4 4h8M8 12h5M8 16h7",
    settings: "M12 15.5a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7Zm0-12v2m0 13v2m8.5-8.5h-2m-13 0h-2m14.5-6-1.4 1.4M7.4 16.6 6 18m12 0-1.4-1.4M7.4 7.4 6 6",
    upload: "M12 16V4m0 0L7 9m5-5 5 5M5 14v6h14v-6",
    instagram: "M7 2h10a5 5 0 0 1 5 5v10a5 5 0 0 1-5 5H7a5 5 0 0 1-5-5V7a5 5 0 0 1 5-5Zm5 5a5 5 0 1 0 0 10 5 5 0 0 0 0-10Zm6.5-.8h.01",
  };
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24">
      <path d={paths[name]} />
    </svg>
  );
}

export default function Dashboard() {
  const [analysis, setAnalysis] = useState<AnalysisResult | null>(null);
  const [selectedCluster, setSelectedCluster] = useState<AnalysisCluster | null>(null);
  const [usage, setUsage] = useState<UsageResponse | null>(null);
  const [instagram, setInstagram] = useState<InstagramAccount | null>(null);
  const [syncingInstagram, setSyncingInstagram] = useState(false);
  const [instagramError, setInstagramError] = useState<string | null>(null);
  const [range, setRange] = useState<"30 days" | "90 days" | "All time">("30 days");
  const importDialogRef = useRef<ImportCommentsDialogHandle>(null);
  const [profileName] = useState(() => {
    if (typeof window === "undefined") return "Aarav Kapoor";
    try {
      const user = JSON.parse(window.localStorage.getItem("reelpilot_user") ?? "null") as { display_name?: string } | null;
      return user?.display_name || "Aarav Kapoor";
    } catch { return "Aarav Kapoor"; }
  });
  const router = useRouter();
  const authReady = useSyncExternalStore(noAuthSubscription, readClientAuth, readServerAuth);
  useEffect(() => {
    if (!authReady) {
      router.replace("/login");
      return;
    }
    fetch(`${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}/v1/usage`, { headers: authHeaders() })
      .then((response) => response.ok ? response.json() as Promise<UsageResponse> : null)
      .then((data) => data && setUsage(data))
      .catch(() => undefined);
    fetch(`${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}/v1/instagram/account`, { headers: authHeaders() })
      .then((response) => response.ok ? response.json() as Promise<InstagramAccount> : null)
      .then((data) => data && setInstagram(data))
      .catch(() => undefined);
  }, [authReady, router]);
  async function connectInstagram() {
    setInstagramError(null);
    const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}/v1/instagram/connect`, { headers: authHeaders() });
    const payload = await response.json();
    if (response.ok && payload.authorization_url) window.location.assign(payload.authorization_url);
    else setInstagramError(payload.detail ?? "Instagram connection failed");
  }

  async function syncInstagram() {
    setSyncingInstagram(true);
    setInstagramError(null);
    try {
      const syncResponse = await fetch(`${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}/v1/instagram/sync-comments`, {
        method: "POST",
        headers: authHeaders(),
      });
      const syncPayload = await syncResponse.json();
      if (!syncResponse.ok) throw new Error(syncPayload.detail ?? "Instagram sync failed");
      const analysisResponse = await fetch(`${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}/v1/analysis-runs`, {
        method: "POST",
        headers: authHeaders(true),
        body: JSON.stringify({ import_id: syncPayload.import_id }),
      });
      const analysisPayload = await analysisResponse.json();
      if (!analysisResponse.ok) throw new Error(analysisPayload.detail ?? "Analysis failed");
      setAnalysis(analysisPayload as AnalysisResult);
      scrollTo("comments");
    } catch (error) {
      setInstagramError(error instanceof Error ? error.message : "Instagram sync failed");
    } finally {
      setSyncingInstagram(false);
    }
  }
  async function disconnectInstagram() {
    if (!window.confirm("Disconnect Instagram from ReelPilot? You can reconnect it later.")) return;
    setInstagramError(null);
    const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}/v1/instagram/account`, {
      method: "DELETE",
      headers: authHeaders(),
    });
    if (response.ok) setInstagram({ connected: false, username: null, instagram_user_id: null, account_type: null, connected_at: null });
    else {
      const payload = await response.json().catch(() => ({}));
      setInstagramError(payload.detail ?? "Instagram disconnect failed");
    }
  }
  const clusters = analysis
      ? analysis.clusters.map((cluster, index) => ({
        id: cluster.id,
        source: cluster,
        rank: String(cluster.rank).padStart(2, "0"),
        question: cluster.canonical_question,
        signal: cluster.signal,
        mentions: cluster.mention_count,
        growth: `${cluster.opportunity_score} score`,
        languages: [analysis.provider === "openai" ? "AI semantic" : "Local analysis"],
        samples: cluster.comments.slice(0, 2).map((comment) => comment.text),
        accent: ["violet", "cyan", "orange"][index % 3],
      }))
    : sampleClusters;
  const commentCount = analysis?.comment_count ?? 482;
  const clusterCount = analysis?.clusters.length ?? clusters.length;

  function scrollTo(id: string) {
    document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  function openImport() {
    importDialogRef.current?.open();
    scrollTo("comments");
  }

  function openStudio() {
    const firstCluster = analysis?.clusters[0];
    if (firstCluster) setSelectedCluster(firstCluster);
    else scrollTo("comments");
  }

  if (!authReady) return <div className="auth-loading">Loading your workspace…</div>;

  return (
    <main className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <span className="brand-mark"><Icon name="spark" /></span>
          <span>ReelPilot</span>
          <em>AI</em>
        </div>

        <nav aria-label="Main navigation">
          <a className="nav-item active" href="#overview" onClick={(event) => { event.preventDefault(); scrollTo("overview"); }}><Icon name="grid" />Overview</a>
          <a className="nav-item" href="#comments" onClick={(event) => { event.preventDefault(); scrollTo("comments"); }}><Icon name="comments" />Audience signals</a>
          <a className="nav-item" href="#ideas" onClick={(event) => { event.preventDefault(); scrollTo("ideas"); }}><Icon name="ideas" />Reel ideas<span>{Math.min(10, clusterCount)}</span></a>
          <button className="nav-item" type="button" onClick={openStudio}><Icon name="studio" />Content studio</button>
        </nav>

        <div className="sidebar-bottom">
          <div className="usage-card">
            <p>Monthly analysis</p>
            <strong>{usage?.comments.used ?? 482} <small>/ {(usage?.comments.limit ?? 1000).toLocaleString()} comments</small></strong>
            <div className="progress"><i style={{ width: `${Math.min(100, ((usage?.comments.used ?? 482) / (usage?.comments.limit ?? 1000)) * 100)}%` }} /></div>
            <button type="button" onClick={() => scrollTo("settings")}>View usage</button>
          </div>
          <a className="nav-item" href="#settings" onClick={(event) => { event.preventDefault(); scrollTo("settings"); }}><Icon name="settings" />Settings</a>
            <div className="profile">
            <div className="avatar">AK</div>
            <div><strong>{profileName}</strong><span>Creator workspace</span></div>
            <button aria-label="Sign out" onClick={() => { clearAccessToken(); router.replace("/login"); }}>↪</button>
          </div>
        </div>
      </aside>

      <section className="workspace" id="overview">
        <header className="topbar">
          <button className="mobile-brand" aria-label="Open navigation"><Icon name="spark" /></button>
          <button className="account-chip" type="button" onClick={connectInstagram} title={instagram?.connected ? "Reconnect Instagram" : "Connect Instagram"}><span className="ig-icon"><Icon name="instagram" /></span><strong>{instagram?.connected ? `@${instagram.username}` : "Connect Instagram"}</strong><i />{instagram?.connected ? "Connected" : "Professional account"}</button>
          <div className="header-actions">
            <ImportCommentsDialog ref={importDialogRef} onAnalysisComplete={setAnalysis} />
            {instagram?.connected && <button className="secondary-button" type="button" onClick={syncInstagram} disabled={syncingInstagram}>{syncingInstagram ? "Syncing…" : "Sync comments"}</button>}
            {instagram?.connected && <button className="secondary-button" type="button" onClick={disconnectInstagram}>Disconnect Instagram</button>}
            <button className="primary-button" type="button" onClick={openImport}><Icon name="spark" />New analysis</button>
          </div>
        </header>

        {instagramError && <p className="integration-error" role="alert">{instagramError}</p>}

        <div className="content">
          <div className="eyebrow">AUDIENCE INTELLIGENCE</div>
          <div className="title-row">
            <div>
              <h1>Your audience is telling you<br />what to make next.</h1>
              <p>{analysis ? `We analysed ${commentCount} imported comments using ${analysis.provider} similarity.` : "We analysed 482 comments across your latest 12 posts."}</p>
            </div>
            <div className="range-control" aria-label="Analysis period">{(["30 days", "90 days", "All time"] as const).map((item) => <button className={range === item ? "selected" : ""} type="button" key={item} onClick={() => setRange(item)}>{item}</button>)}</div>
          </div>

          <div className="stats-grid">
            <article><span>COMMENTS ANALYSED</span><strong>{commentCount}</strong><small>{analysis ? "From your latest import" : <><b>↑ 18%</b> vs previous period</>}</small></article>
            <article><span>QUESTION SIGNALS</span><strong>{analysis ? commentCount : 96}</strong><small>{analysis ? "Questions and topic requests" : "20% of all comments"}</small></article>
            <article><span>TOPIC CLUSTERS</span><strong>{clusterCount}</strong><small>{clusters.filter((cluster) => cluster.signal === "Strong signal").length} strong opportunities</small></article>
            <article className="highlight-stat"><span>READY-TO-MAKE IDEAS</span><strong>{Math.min(10, clusterCount)}</strong><small>Generated from real demand</small></article>
          </div>

          <section className="signals" id="comments">
            <div className="section-heading">
              <div><h2>Top audience signals</h2><p>Ranked by frequency, recency and relevance to your niche.</p></div>
              <a href="#ideas">View all {clusterCount} clusters →</a>
            </div>

            <div className="cluster-list" id="ideas">
              {clusters.map((cluster) => (
                <article className="cluster-card" key={cluster.rank}>
                  <div className={`rank ${cluster.accent}`}>{cluster.rank}</div>
                  <div className="cluster-main">
                    <div className="cluster-meta"><span className={`signal ${cluster.accent}`}>● {cluster.signal}</span>{cluster.languages.map((language) => <span className="tag" key={language}>{language}</span>)}</div>
                    <h3>{cluster.question}</h3>
                    <div className="sample"><span>“</span><div>{cluster.samples.map((sample, sampleIndex) => <p key={`${cluster.rank}-${sampleIndex}`}>{sample}</p>)}</div></div>
                  </div>
                  <div className="cluster-numbers"><strong>{cluster.mentions}</strong><span>mentions</span><b>{cluster.growth}</b></div>
                  <button
                    className="make-reel"
                    type="button"
                    disabled={!cluster.source}
                    title={cluster.source ? "Open content studio" : "Import comments to unlock content studio"}
                    onClick={() => cluster.source && setSelectedCluster(cluster.source)}
                  >
                    {cluster.source ? "Create Reel pack" : "Import to create"} <span>→</span>
                  </button>
                </article>
              ))}
            </div>
          </section>

          <aside className="principle"><Icon name="spark" /><p><strong>Every idea is backed by real audience demand.</strong><br />Open a cluster to see all supporting comments before generating content.</p></aside>

          <section className="signals product-section" id="studio">
            <div className="section-heading">
              <div><h2>Content studio</h2><p>Turn a ranked audience signal into an editable Reel content pack.</p></div>
              <button className="secondary-button" type="button" onClick={openStudio}>Open studio →</button>
            </div>
            <div className="studio-summary"><span>1</span><p><strong>Choose a signal</strong><br />Select any imported cluster above to review its supporting comments and generate a pack.</p><span>2</span><p><strong>Edit and save</strong><br />Adjust the hook, script, caption, hashtags, and B-roll before copying it into your production workflow.</p></div>
          </section>

          <section className="signals product-section" id="settings">
            <div className="section-heading">
              <div><h2>Workspace settings</h2><p>Current workspace status and usage.</p></div>
            </div>
            <div className="settings-grid"><article><span>ANALYSIS PERIOD</span><strong>{range}</strong><small>Dashboard view</small></article><article><span>COMMENTS USED</span><strong>{usage?.comments.used ?? 0}</strong><small>{usage?.comments.limit ?? 1000} monthly limit</small></article><article><span>AI MODE</span><strong>{process.env.NEXT_PUBLIC_API_URL ? "Connected API" : "Local API"}</strong><small>Provider configured on the backend</small></article></div>
          </section>
        </div>
      </section>
      {selectedCluster && <ContentStudioDialog cluster={selectedCluster} onClose={() => setSelectedCluster(null)} />}
    </main>
  );
}
