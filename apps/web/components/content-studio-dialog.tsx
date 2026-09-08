"use client";

import { useEffect, useMemo, useState } from "react";

import type {
  AnalysisCluster,
  ContentLanguage,
  ContentPack,
  ContentTone,
} from "@/lib/api-types";
import { authHeaders } from "@/lib/auth";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const languages: ContentLanguage[] = ["Hinglish", "English", "Hindi"];
const tones: ContentTone[] = ["Conversational", "Educational", "Energetic", "Storytelling"];

type Duration = "15" | "30" | "60";

type ContentStudioDialogProps = {
  cluster: AnalysisCluster;
  onClose: () => void;
};

function copyText(pack: ContentPack) {
  return [
    `COVER\n${pack.cover_text}`,
    `HOOKS\n${pack.hooks.map((hook, index) => `${index + 1}. ${hook}`).join("\n")}`,
    `15-SECOND SCRIPT\n${pack.script_15}`,
    `30-SECOND SCRIPT\n${pack.script_30}`,
    `60-SECOND SCRIPT\n${pack.script_60}`,
    `CAPTION\n${pack.caption}`,
    `CTA\n${pack.cta}`,
    `HASHTAGS\n${pack.hashtags.join(" ")}`,
    `B-ROLL\n${pack.b_roll.map((shot) => `- ${shot}`).join("\n")}`,
  ].join("\n\n");
}

export function ContentStudioDialog({ cluster, onClose }: ContentStudioDialogProps) {
  const [language, setLanguage] = useState<ContentLanguage>("Hinglish");
  const [tone, setTone] = useState<ContentTone>("Conversational");
  const [pack, setPack] = useState<ContentPack | null>(null);
  const [draft, setDraft] = useState<ContentPack | null>(null);
  const [duration, setDuration] = useState<Duration>("30");
  const [status, setStatus] = useState<"idle" | "generating" | "saving" | "saved">("idle");
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    function escapeClose(event: KeyboardEvent) {
      if (event.key === "Escape") onClose();
    }
    window.addEventListener("keydown", escapeClose);
    return () => window.removeEventListener("keydown", escapeClose);
  }, [onClose]);

  const hasChanges = useMemo(
    () => Boolean(pack && draft && JSON.stringify(pack) !== JSON.stringify(draft)),
    [pack, draft],
  );

  async function generate() {
    setStatus("generating");
    setError(null);
    try {
      const response = await fetch(`${API_URL}/v1/clusters/${cluster.id}/content-packs`, {
        method: "POST",
        headers: authHeaders(true),
        body: JSON.stringify({ language, tone }),
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.detail ?? "Generation failed");
      setPack(payload as ContentPack);
      setDraft(payload as ContentPack);
      setStatus("idle");
    } catch (generationError) {
      setError(generationError instanceof Error ? generationError.message : "Generation failed");
      setStatus("idle");
    }
  }

  async function save() {
    if (!draft) return;
    setStatus("saving");
    setError(null);
    const fields = {
      hooks: draft.hooks,
      script_15: draft.script_15,
      script_30: draft.script_30,
      script_60: draft.script_60,
      caption: draft.caption,
      cta: draft.cta,
      hashtags: draft.hashtags,
      cover_text: draft.cover_text,
      b_roll: draft.b_roll,
    };
    try {
      const response = await fetch(`${API_URL}/v1/content-packs/${draft.id}`, {
        method: "PATCH",
        headers: authHeaders(true),
        body: JSON.stringify(fields),
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.detail?.[0]?.msg ?? payload.detail ?? "Save failed");
      setPack(payload as ContentPack);
      setDraft(payload as ContentPack);
      setStatus("saved");
      window.setTimeout(() => setStatus("idle"), 1600);
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : "Save failed");
      setStatus("idle");
    }
  }

  async function copyPack() {
    if (!draft) return;
    await navigator.clipboard.writeText(copyText(draft));
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1500);
  }

  function update<K extends keyof ContentPack>(key: K, value: ContentPack[K]) {
    setDraft((current) => (current ? { ...current, [key]: value } : current));
  }

  const scriptKey = `script_${duration}` as "script_15" | "script_30" | "script_60";

  return (
    <div className="studio-backdrop" role="presentation" onMouseDown={onClose}>
      <section className="studio-dialog" role="dialog" aria-modal="true" aria-labelledby="studio-title" onMouseDown={(event) => event.stopPropagation()}>
        <header className="studio-header">
          <div>
            <p className="dialog-kicker">CONTENT STUDIO</p>
            <h2 id="studio-title">{cluster.label}</h2>
            <span>{cluster.mention_count} audience mentions · {cluster.opportunity_score} opportunity score</span>
          </div>
          <button className="dialog-close" type="button" aria-label="Close content studio" onClick={onClose}>×</button>
        </header>

        {!draft ? (
          <div className="studio-start">
            <div className="studio-question"><span>AUDIENCE QUESTION</span><strong>{cluster.canonical_question}</strong></div>
            <div className="evidence-preview">
              <span>SOURCE EVIDENCE</span>
              {cluster.comments.slice(0, 3).map((comment) => <blockquote key={comment.id}>“{comment.text}”</blockquote>)}
            </div>
            <div className="generation-controls">
              <label>Language<select value={language} onChange={(event) => setLanguage(event.target.value as ContentLanguage)}>{languages.map((item) => <option key={item}>{item}</option>)}</select></label>
              <label>Tone<select value={tone} onChange={(event) => setTone(event.target.value as ContentTone)}>{tones.map((item) => <option key={item}>{item}</option>)}</select></label>
            </div>
            {error && <p className="studio-error" role="alert">{error}</p>}
            <button className="generate-pack" type="button" disabled={status === "generating"} onClick={generate}>
              <span>✦</span>{status === "generating" ? "Creating your Reel pack…" : "Generate Reel content pack"}
            </button>
            <p className="grounding-note">Generated only from the selected audience signal. Review before publishing.</p>
          </div>
        ) : (
          <div className="studio-editor">
            <aside className="editor-sidebar">
              <div className="pack-meta"><span>{draft.provider === "local" ? "Local preview" : `${draft.provider} generated`}</span><b>Version {draft.version}</b><small>{draft.language} · {draft.tone}</small></div>
              <nav>
                <a href="#cover">Cover</a><a href="#hooks">Hooks</a><a href="#script">Script</a><a href="#caption">Caption</a><a href="#broll">B-roll</a>
              </nav>
              <button type="button" onClick={generate}>↻ Generate new version</button>
            </aside>

            <div className="editor-content">
              <section id="cover" className="editor-section cover-editor">
                <label>Cover text <span>{draft.cover_text.length}/80</span></label>
                <input value={draft.cover_text} maxLength={80} onChange={(event) => update("cover_text", event.target.value)} />
              </section>

              <section id="hooks" className="editor-section">
                <div className="field-title"><h3>Three opening hooks</h3><span>Test different first 3 seconds</span></div>
                {draft.hooks.map((hook, index) => <label className="hook-field" key={index}><b>0{index + 1}</b><textarea value={hook} onChange={(event) => { const hooks = [...draft.hooks]; hooks[index] = event.target.value; update("hooks", hooks); }} /></label>)}
              </section>

              <section id="script" className="editor-section">
                <div className="field-title"><h3>Reel script</h3><div className="duration-tabs">{(["15", "30", "60"] as Duration[]).map((item) => <button className={duration === item ? "active" : ""} type="button" key={item} onClick={() => setDuration(item)}>{item}s</button>)}</div></div>
                <textarea className="script-field" value={draft[scriptKey]} onChange={(event) => update(scriptKey, event.target.value)} />
              </section>

              <section id="caption" className="editor-section">
                <div className="field-title"><h3>Caption and CTA</h3></div>
                <textarea className="caption-field" value={draft.caption} onChange={(event) => update("caption", event.target.value)} />
                <input value={draft.cta} onChange={(event) => update("cta", event.target.value)} />
                <input value={draft.hashtags.join(" ")} onChange={(event) => update("hashtags", event.target.value.split(/\s+/).filter(Boolean))} />
              </section>

              <section id="broll" className="editor-section">
                <div className="field-title"><h3>Suggested B-roll</h3><span>One shot per line</span></div>
                <textarea className="broll-field" value={draft.b_roll.join("\n")} onChange={(event) => update("b_roll", event.target.value.split("\n").filter(Boolean))} />
              </section>
              {error && <p className="studio-error" role="alert">{error}</p>}
            </div>

            <footer className="editor-footer">
              <span>{hasChanges ? "Unsaved changes" : status === "saved" ? "Saved ✓" : `Generated with ${draft.model}`}</span>
              <button className="copy-pack" type="button" onClick={copyPack}>{copied ? "Copied ✓" : "Copy all"}</button>
              <button className="save-pack" type="button" disabled={!hasChanges || status === "saving"} onClick={save}>{status === "saving" ? "Saving…" : "Save draft"}</button>
            </footer>
          </div>
        )}
      </section>
    </div>
  );
}
