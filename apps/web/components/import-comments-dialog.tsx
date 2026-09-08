"use client";

import { ChangeEvent, DragEvent, forwardRef, useImperativeHandle, useRef, useState } from "react";

import type { AnalysisResult } from "@/lib/api-types";
import { authHeaders } from "@/lib/auth";

type ImportResult = {
  import_id: string;
  filename: string;
  imported_count: number;
  skipped_count: number;
  detected_columns: string[];
  warnings: { row_number: number; message: string }[];
};

type ImportState =
  | { kind: "idle" }
  | { kind: "selected"; file: File }
  | { kind: "uploading"; file: File }
  | { kind: "success"; result: ImportResult }
  | { kind: "error"; message: string; file?: File };

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

type ImportCommentsDialogProps = {
  onAnalysisComplete?: (analysis: AnalysisResult) => void;
};

export type ImportCommentsDialogHandle = { open: () => void };

function UploadIcon() {
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24">
      <path d="M12 16V4m0 0L7 9m5-5 5 5M5 14v6h14v-6" />
    </svg>
  );
}

export const ImportCommentsDialog = forwardRef<ImportCommentsDialogHandle, ImportCommentsDialogProps>(function ImportCommentsDialog(
  { onAnalysisComplete },
  ref,
) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [isOpen, setIsOpen] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const [state, setState] = useState<ImportState>({ kind: "idle" });
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analysisError, setAnalysisError] = useState<string | null>(null);

  useImperativeHandle(ref, () => ({ open: () => setIsOpen(true) }), []);

  function selectFile(file?: File) {
    if (!file) return;
    if (!file.name.toLowerCase().endsWith(".csv")) {
      setState({ kind: "error", message: "Please choose a CSV file." });
      return;
    }
    if (file.size > 5 * 1024 * 1024) {
      setState({ kind: "error", message: "The CSV must be 5 MB or smaller." });
      return;
    }
    setState({ kind: "selected", file });
  }

  function handleInput(event: ChangeEvent<HTMLInputElement>) {
    selectFile(event.target.files?.[0]);
  }

  function handleDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();
    setIsDragging(false);
    selectFile(event.dataTransfer.files[0]);
  }

  async function upload() {
    if (state.kind !== "selected" && state.kind !== "error") return;
    const file = state.file;
    if (!file) return;

    setState({ kind: "uploading", file });
    const body = new FormData();
    body.append("file", file);

    try {
      const response = await fetch(`${API_URL}/v1/imports/comments-csv`, {
        method: "POST",
        headers: authHeaders(),
        body,
      });
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(typeof payload.detail === "string" ? payload.detail : "Import failed");
      }
      setState({ kind: "success", result: payload as ImportResult });
    } catch (error) {
      const message =
        error instanceof TypeError
          ? "Cannot reach the API. Start FastAPI on port 8000 and try again."
          : error instanceof Error
            ? error.message
            : "Import failed. Please try again.";
      setState({ kind: "error", message, file });
    }
  }

  function close() {
    setIsOpen(false);
    setIsDragging(false);
    setState({ kind: "idle" });
    setIsAnalyzing(false);
    setAnalysisError(null);
    if (inputRef.current) inputRef.current.value = "";
  }

  const selectedFile = state.kind === "selected" || state.kind === "uploading" || state.kind === "error" ? state.file : undefined;

  async function analyze(result: ImportResult) {
    setIsAnalyzing(true);
    setAnalysisError(null);
    try {
      const response = await fetch(`${API_URL}/v1/analysis-runs`, {
        method: "POST",
        headers: authHeaders(true),
        body: JSON.stringify({ import_id: result.import_id }),
      });
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(typeof payload.detail === "string" ? payload.detail : "Analysis failed");
      }
      onAnalysisComplete?.(payload as AnalysisResult);
      close();
    } catch (error) {
      setAnalysisError(error instanceof Error ? error.message : "Analysis failed. Please try again.");
      setIsAnalyzing(false);
    }
  }

  return (
    <>
      <button className="secondary-button" type="button" onClick={() => setIsOpen(true)}>
        <UploadIcon />Import comments
      </button>

      {isOpen && (
        <div className="dialog-backdrop" role="presentation" onMouseDown={close}>
          <section
            aria-labelledby="import-title"
            aria-modal="true"
            className="import-dialog"
            role="dialog"
            onMouseDown={(event) => event.stopPropagation()}
          >
            <button className="dialog-close" type="button" aria-label="Close import dialog" onClick={close}>×</button>

            {state.kind === "success" ? (
              <div className="import-success">
                <div className="success-mark">✓</div>
                <p className="dialog-kicker">IMPORT COMPLETE</p>
                <h2 id="import-title">{state.result.imported_count} comments are ready</h2>
                <p>
                  Imported from <strong>{state.result.filename}</strong>
                  {state.result.skipped_count > 0 && ` · ${state.result.skipped_count} rows skipped`}.
                </p>
                <div className="import-summary">
                  <span><b>{state.result.imported_count}</b>Valid comments</span>
                  <span><b>{state.result.detected_columns.length}</b>Columns detected</span>
                  <span><b>{state.result.warnings.length}</b>Warnings</span>
                </div>
                {analysisError && <p className="import-error" role="alert">{analysisError}</p>}
                <button
                  className="dialog-primary"
                  type="button"
                  disabled={isAnalyzing}
                  onClick={() => analyze(state.result)}
                >
                  {isAnalyzing ? "Finding audience signals…" : "Analyse comments →"}
                </button>
              </div>
            ) : (
              <>
                <p className="dialog-kicker">AUDIENCE DATA</p>
                <h2 id="import-title">Import Instagram comments</h2>
                <p className="dialog-copy">Upload a UTF-8 CSV export. We use it only to find recurring audience questions and content opportunities.</p>

                <div
                  className={`drop-zone ${isDragging ? "dragging" : ""}`}
                  onDragEnter={(event) => { event.preventDefault(); setIsDragging(true); }}
                  onDragOver={(event) => event.preventDefault()}
                  onDragLeave={() => setIsDragging(false)}
                  onDrop={handleDrop}
                >
                  <span className="upload-mark"><UploadIcon /></span>
                  <strong>{selectedFile?.name ?? "Drop your CSV here"}</strong>
                  <p>{selectedFile ? `${Math.max(1, Math.round(selectedFile.size / 1024))} KB selected` : "or choose a file from your computer"}</p>
                  <button type="button" onClick={() => inputRef.current?.click()}>{selectedFile ? "Choose another" : "Choose CSV"}</button>
                  <input ref={inputRef} type="file" accept=".csv,text/csv" onChange={handleInput} hidden />
                </div>

                <div className="format-note">
                  <strong>Required column</strong>
                  <code>comment</code> or <code>text</code>
                  <span>Optional: username, post_id, created_at, likes</span>
                </div>

                {state.kind === "error" && <p className="import-error" role="alert">{state.message}</p>}

                <div className="dialog-actions">
                  <a href="/comments.sample.csv" download>Download sample CSV</a>
                  <button
                    className="dialog-primary"
                    type="button"
                    disabled={!selectedFile || state.kind === "uploading"}
                    onClick={upload}
                  >
                    {state.kind === "uploading" ? "Importing…" : "Import comments"}
                  </button>
                </div>
              </>
            )}
          </section>
        </div>
      )}
    </>
  );
});
