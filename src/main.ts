import { invoke } from "@tauri-apps/api/core";
import { open } from "@tauri-apps/plugin-dialog";
import { openPath } from "@tauri-apps/plugin-opener";
import "./style.css";

type Backend = "basic" | "nougat" | "marker";

interface ConvertResult {
  out_path: string;
  assets_dir: string;
  block_count: number;
  asset_count: number;
}

interface Status {
  kind: "idle" | "running" | "done" | "error";
  message?: string;
  result?: ConvertResult;
}

const app = document.querySelector<HTMLDivElement>("#app")!;
let inputPath: string | null = null;
let backend: Backend = "basic";
let status: Status = { kind: "idle" };

function render() {
  app.innerHTML = `
    <header class="hero">
      <img src="/assets/logo.svg" alt="doc2latex" class="logo" />
    </header>

    <main class="card">
      <section class="row">
        <button id="pick" class="btn primary">Choose document</button>
        <span class="path" id="path">${
          inputPath ?? "no file selected"
        }</span>
      </section>

      <section class="row">
        <label for="backend" class="label">Backend</label>
        <select id="backend" class="select">
          <option value="basic"${backend === "basic" ? " selected" : ""}>
            basic (fastest)
          </option>
          <option value="nougat"${backend === "nougat" ? " selected" : ""}>
            nougat (academic PDFs)
          </option>
          <option value="marker"${backend === "marker" ? " selected" : ""}>
            marker (faster than nougat)
          </option>
        </select>
      </section>

      <section class="row">
        <button id="convert" class="btn primary" ${
          inputPath && status.kind !== "running" ? "" : "disabled"
        }>
          ${status.kind === "running" ? "Converting…" : "Convert to LaTeX"}
        </button>
      </section>

      ${renderStatus()}
    </main>

    <footer class="footer">
      <span>offline · no telemetry · v${import.meta.env.VITE_APP_VERSION ?? "dev"}</span>
    </footer>
  `;

  document.getElementById("pick")?.addEventListener("click", pickFile);
  document.getElementById("convert")?.addEventListener("click", runConvert);
  document
    .getElementById("backend")
    ?.addEventListener("change", (e) => {
      backend = (e.target as HTMLSelectElement).value as Backend;
    });
  document
    .getElementById("open-out")
    ?.addEventListener("click", () => {
      if (status.result) openPath(status.result.out_path);
    });
  document
    .getElementById("open-assets")
    ?.addEventListener("click", () => {
      if (status.result) openPath(status.result.assets_dir);
    });
}

function renderStatus(): string {
  if (status.kind === "idle") return "";
  if (status.kind === "running") {
    return `<div class="status running">${escape(status.message ?? "Working…")}</div>`;
  }
  if (status.kind === "error") {
    return `<div class="status error">${escape(status.message ?? "Conversion failed.")}</div>`;
  }
  if (status.kind === "done" && status.result) {
    const r = status.result;
    return `
      <div class="status done">
        <div class="status-title">Done — wrote ${r.block_count} blocks, ${r.asset_count} assets.</div>
        <div class="status-actions">
          <button id="open-out" class="btn">Open .tex</button>
          <button id="open-assets" class="btn">Open assets folder</button>
        </div>
        <div class="status-path">${escape(r.out_path)}</div>
      </div>
    `;
  }
  return "";
}

function escape(s: string): string {
  return s.replace(/[&<>"]/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c] ?? c),
  );
}

async function pickFile() {
  const selected = await open({
    multiple: false,
    directory: false,
    filters: [
      {
        name: "Documents",
        extensions: ["pdf", "docx", "jpg", "jpeg", "png"],
      },
    ],
  });
  if (typeof selected === "string") {
    inputPath = selected;
    status = { kind: "idle" };
    render();
  }
}

async function runConvert() {
  if (!inputPath) return;
  status = { kind: "running", message: `Converting ${inputPath}…` };
  render();
  try {
    const result = await invoke<ConvertResult>("convert_document", {
      input: inputPath,
      backend,
    });
    status = { kind: "done", result };
  } catch (e) {
    status = { kind: "error", message: String(e) };
  }
  render();
}

render();
