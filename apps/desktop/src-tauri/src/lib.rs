//! Tauri shell — dev: `uv run uvicorn`; release: PyInstaller sidecar (M0-05 / M4-06).

use std::net::TcpStream;
use std::sync::Mutex;
use std::thread;
use std::time::{Duration, Instant};

use tauri::Manager;
use tauri_plugin_shell::ShellExt;

#[cfg(debug_assertions)]
use std::path::PathBuf;
#[cfg(debug_assertions)]
use std::process::{Command, Stdio};
#[cfg(not(debug_assertions))]
use tauri_plugin_shell::process::CommandChild;

#[cfg(debug_assertions)]
enum SidecarChild {
    Dev(std::process::Child),
}

#[cfg(not(debug_assertions))]
enum SidecarChild {
    Release(CommandChild),
}

struct SidecarState(Mutex<Option<SidecarChild>>);

fn free_sidecar_port() {
    #[cfg(all(not(debug_assertions), target_os = "macos"))]
    {
        let _ = std::process::Command::new("sh")
            .arg("-c")
            .arg("lsof -ti tcp:8123 | xargs kill -9 2>/dev/null || true")
            .status();
        thread::sleep(Duration::from_millis(400));
    }
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_dialog::init())
        .manage(SidecarState(Mutex::new(None)))
        .setup(|app| {
            free_sidecar_port();
            let child = spawn_sidecar(app.handle())?;
            *app.state::<SidecarState>().0.lock().unwrap() = Some(child);
            wait_for_sidecar_port(Duration::from_secs(60))?;
            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}

fn spawn_sidecar(app: &tauri::AppHandle) -> Result<SidecarChild, String> {
    #[cfg(debug_assertions)]
    {
        return spawn_dev_sidecar().map(SidecarChild::Dev);
    }

    #[cfg(not(debug_assertions))]
    {
        let (_rx, child) = app
            .shell()
            .sidecar("orchestrator")
            .map_err(|e| format!("无法加载 Sidecar 二进制：{e}"))?
            .spawn()
            .map_err(|e| format!("无法启动 Sidecar：{e}"))?;
        return Ok(SidecarChild::Release(child));
    }
}

#[cfg(debug_assertions)]
fn orchestrator_dir() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../../services/orchestrator")
}

#[cfg(debug_assertions)]
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
        if std::net::TcpStream::connect("127.0.0.1:8123").is_ok() {
            return Ok(());
        }
        thread::sleep(Duration::from_millis(400));
    }
    Err("Sidecar 启动超时：8123 端口不可达。请检查编排服务是否已内嵌或本机 uv 环境".into())
}
