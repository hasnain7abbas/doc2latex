use std::path::PathBuf;

use serde::{Deserialize, Serialize};
use tauri::{Manager, path::BaseDirectory};
use tauri_plugin_shell::process::CommandEvent;
use tauri_plugin_shell::ShellExt;
use thiserror::Error;

#[derive(Debug, Error)]
enum AppError {
    #[error("sidecar invocation failed: {0}")]
    Sidecar(String),
    #[error("sidecar exited with code {code}: {stderr}")]
    SidecarExit { code: i32, stderr: String },
    #[error("sidecar produced no parseable result line")]
    NoResult,
    #[error("io error: {0}")]
    Io(String),
}

impl serde::Serialize for AppError {
    fn serialize<S>(&self, serializer: S) -> Result<S::Ok, S::Error>
    where
        S: serde::Serializer,
    {
        serializer.serialize_str(&self.to_string())
    }
}

#[derive(Debug, Clone, Deserialize)]
struct ConvertArgs {
    input: String,
    #[serde(default = "default_backend")]
    backend: String,
}

fn default_backend() -> String {
    "basic".to_string()
}

#[derive(Debug, Clone, Serialize, Deserialize)]
struct ConvertResult {
    out_path: String,
    assets_dir: String,
    block_count: u64,
    asset_count: u64,
}

#[tauri::command]
async fn convert_document(
    app: tauri::AppHandle,
    input: String,
    backend: Option<String>,
) -> Result<ConvertResult, AppError> {
    let backend = backend.unwrap_or_else(default_backend);
    let input_path = PathBuf::from(&input);
    if !input_path.exists() {
        return Err(AppError::Io(format!("input file not found: {}", input)));
    }

    // Output next to the input by default. Users can later expose this via
    // settings; for now, sane defaults.
    let out_path = input_path.with_extension("tex");
    let assets_dir = {
        let mut p = out_path.clone();
        let stem = p
            .file_stem()
            .map(|s| s.to_string_lossy().into_owned())
            .unwrap_or_else(|| "output".into());
        p.set_file_name(format!("{}_assets", stem));
        p
    };

    // Tauri 2 shell plugin: spawn the sidecar declared in tauri.conf.json
    // under `bundle.externalBin`.
    let cmd = app
        .shell()
        .sidecar("doc2latex")
        .map_err(|e| AppError::Sidecar(e.to_string()))?
        .args([
            "--emit-json",
            "convert",
            input_path.to_string_lossy().as_ref(),
            "--out",
            out_path.to_string_lossy().as_ref(),
            "--assets-dir",
            assets_dir.to_string_lossy().as_ref(),
            "--backend",
            &backend,
        ]);

    let (mut rx, _child) = cmd.spawn().map_err(|e| AppError::Sidecar(e.to_string()))?;

    let mut stdout_acc = String::new();
    let mut stderr_acc = String::new();
    let mut exit_code: Option<i32> = None;

    while let Some(event) = rx.recv().await {
        match event {
            CommandEvent::Stdout(line) => {
                let s = String::from_utf8_lossy(&line).into_owned();
                stdout_acc.push_str(&s);
                stdout_acc.push('\n');
            }
            CommandEvent::Stderr(line) => {
                stderr_acc.push_str(&String::from_utf8_lossy(&line));
                stderr_acc.push('\n');
            }
            CommandEvent::Terminated(payload) => {
                exit_code = payload.code;
            }
            _ => {}
        }
    }

    if let Some(code) = exit_code {
        if code != 0 {
            return Err(AppError::SidecarExit {
                code,
                stderr: stderr_acc.trim().to_string(),
            });
        }
    }

    // The CLI emits a single JSON object on its last stdout line when invoked
    // with --emit-json. Find it.
    let result_line = stdout_acc
        .lines()
        .rev()
        .find(|l| l.trim_start().starts_with('{'))
        .ok_or(AppError::NoResult)?;

    let parsed: ConvertResult = serde_json::from_str(result_line.trim())
        .map_err(|e| AppError::Sidecar(format!("bad JSON from sidecar: {e}")))?;
    Ok(parsed)
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_fs::init())
        .plugin(tauri_plugin_opener::init())
        .setup(|app| {
            // Touch BaseDirectory so the import is used; useful for future
            // resource resolution.
            let _ = app.path().resolve("", BaseDirectory::AppData);
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![convert_document])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
