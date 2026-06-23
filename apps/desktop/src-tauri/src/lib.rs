//! Tauri shell — dev Sidecar lifecycle via `uv run uvicorn` (M0-05).

use std::net::TcpStream;
use std::path::PathBuf;
use std::process::{Command, Stdio};
use std::sync::Mutex;
use std::time::{Duration, Instant};
use std::thread;

use tauri::Manager;

struct SidecarState(Mutex<Option<std::process::Child>>);

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .manage(SidecarState(Mutex::new(None)))
        .setup(|app| {
            let child = spawn_dev_sidecar()?;
            *app.state::<SidecarState>().0.lock().unwrap() = Some(child);
            wait_for_sidecar_port(Duration::from_secs(45))?;
            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}

fn orchestrator_dir() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../../services/orchestrator")
}

fn spawn_dev_sidecar() -> Result<std::process::Child, String> {
    let dir = orchestrator_dir();
    if !dir.join("src/main.py").is_file() {
        return Err(format!(
            "未找到 Sidecar 目录：{}。请从仓库根目录运行 pnpm tauri dev",
            dir.display()
        ));
    }

    Command::new("uv")
        .args([
            "run",
            "uvicorn",
            "src.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            "8123",
        ])
        .current_dir(&dir)
        .stdout(Stdio::null())
        .stderr(Stdio::null())
        .spawn()
        .map_err(|e| format!("无法启动 Sidecar（请确认已安装 uv）：{e}"))
}

fn wait_for_sidecar_port(timeout: Duration) -> Result<(), String> {
    let start = Instant::now();
    while start.elapsed() < timeout {
        if TcpStream::connect("127.0.0.1:8123").is_ok() {
            return Ok(());
        }
        thread::sleep(Duration::from_millis(400));
    }
    Err("Sidecar 启动超时：8123 端口不可达。请检查 uv 与 services/orchestrator".into())
}
