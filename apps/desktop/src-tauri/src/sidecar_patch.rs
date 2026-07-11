//! Sidecar hotpatch (D37): Application Support binary + SHA256 meta.

use serde::{Deserialize, Serialize};
use std::fs;
use std::io::{BufRead, BufReader};
use std::path::{Path, PathBuf};
use std::process::Command;
use tauri::{AppHandle, Manager};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PatchMeta {
    pub patch_id: String,
    pub sha256: String,
    #[serde(default)]
    pub needs_restart: bool,
}

pub fn patches_dir(app: &AppHandle) -> Result<PathBuf, String> {
    let base = app
        .path()
        .app_data_dir()
        .map_err(|e| format!("app data dir: {e}"))?;
    let dir = base.join("patches");
    fs::create_dir_all(&dir).map_err(|e| format!("create patches dir: {e}"))?;
    Ok(dir)
}

fn meta_path(dir: &Path) -> PathBuf {
    dir.join("meta.json")
}

fn binary_path(dir: &Path) -> PathBuf {
    dir.join("orchestrator")
}

fn read_meta(dir: &Path) -> Option<PatchMeta> {
    let raw = fs::read_to_string(meta_path(dir)).ok()?;
    serde_json::from_str(&raw).ok()
}

fn write_meta(dir: &Path, meta: &PatchMeta) -> Result<(), String> {
    let json = serde_json::to_string_pretty(meta).map_err(|e| e.to_string())?;
    fs::write(meta_path(dir), json).map_err(|e| format!("write meta: {e}"))
}

fn sha256_hex(path: &Path) -> Result<String, String> {
    let output = Command::new("shasum")
        .args(["-a", "256"])
        .arg(path)
        .output()
        .map_err(|e| format!("shasum: {e}"))?;
    if !output.status.success() {
        return Err("shasum failed".into());
    }
    let line = BufReader::new(output.stdout.as_slice())
        .lines()
        .next()
        .transpose()
        .map_err(|e| e.to_string())?
        .ok_or_else(|| "empty shasum output".to_string())?;
    let hex = line
        .split_whitespace()
        .next()
        .ok_or_else(|| "bad shasum output".to_string())?
        .to_lowercase();
    Ok(hex)
}

fn verify_sha256(path: &Path, expected: &str) -> bool {
    match sha256_hex(path) {
        Ok(got) => got.eq_ignore_ascii_case(expected.trim()),
        Err(_) => false,
    }
}

/// Prefer verified Application Support patch over the bundle binary.
pub fn resolved_patch_binary(app: &AppHandle) -> Option<PathBuf> {
    let dir = patches_dir(app).ok()?;
    let bin = binary_path(&dir);
    let meta = read_meta(&dir)?;
    if !bin.is_file() {
        return None;
    }
    if !verify_sha256(&bin, &meta.sha256) {
        return None;
    }
    Some(bin)
}

pub fn installed_patch_id(app: &AppHandle) -> Option<String> {
    let dir = patches_dir(app).ok()?;
    let meta = read_meta(&dir)?;
    let bin = binary_path(&dir);
    if !bin.is_file() || !verify_sha256(&bin, &meta.sha256) {
        return None;
    }
    Some(meta.patch_id)
}

pub fn pending_restart_patch_id(app: &AppHandle) -> Option<String> {
    let dir = patches_dir(app).ok()?;
    let meta = read_meta(&dir)?;
    if meta.needs_restart {
        Some(meta.patch_id)
    } else {
        None
    }
}

#[cfg(target_os = "macos")]
pub fn download_and_install(
    app: &AppHandle,
    url: &str,
    patch_id: &str,
    sha256: &str,
) -> Result<(), String> {
    let dir = patches_dir(app)?;
    let staging = dir.join("orchestrator.partial");
    let dest = binary_path(&dir);

    let status = Command::new("curl")
        .args(["-fsSL", "--connect-timeout", "30", "-o"])
        .arg(&staging)
        .arg(url)
        .status()
        .map_err(|e| format!("curl: {e}"))?;
    if !status.success() {
        let _ = fs::remove_file(&staging);
        return Err("sidecar patch download failed".into());
    }

    if !verify_sha256(&staging, sha256) {
        let _ = fs::remove_file(&staging);
        return Err("sidecar patch sha256 mismatch".into());
    }

    #[cfg(unix)]
    {
        use std::os::unix::fs::PermissionsExt;
        let meta = fs::metadata(&staging).map_err(|e| e.to_string())?;
        let mut perms = meta.permissions();
        perms.set_mode(0o755);
        fs::set_permissions(&staging, perms).map_err(|e| e.to_string())?;
    }

    fs::rename(&staging, &dest).map_err(|e| format!("install patch: {e}"))?;
    write_meta(
        &dir,
        &PatchMeta {
            patch_id: patch_id.to_string(),
            sha256: sha256.trim().to_lowercase(),
            needs_restart: true,
        },
    )?;
    Ok(())
}

#[cfg(not(target_os = "macos"))]
pub fn download_and_install(
    _app: &AppHandle,
    _url: &str,
    _patch_id: &str,
    _sha256: &str,
) -> Result<(), String> {
    Err("Sidecar hotpatch is macOS-only".into())
}

pub fn clear_needs_restart(app: &AppHandle) -> Result<(), String> {
    let dir = patches_dir(app)?;
    let Some(mut meta) = read_meta(&dir) else {
        return Ok(());
    };
    meta.needs_restart = false;
    write_meta(&dir, &meta)
}

#[tauri::command]
pub fn clutch_sidecar_patch_status(app: AppHandle) -> Result<Option<String>, String> {
    Ok(installed_patch_id(&app))
}

#[tauri::command]
pub fn clutch_sidecar_patch_pending(app: AppHandle) -> Result<Option<String>, String> {
    Ok(pending_restart_patch_id(&app))
}

#[tauri::command]
pub fn clutch_download_sidecar_patch(
    app: AppHandle,
    url: String,
    patch_id: String,
    sha256: String,
) -> Result<(), String> {
    download_and_install(&app, &url, &patch_id, &sha256)
}
