#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]
use serde::Deserialize;
use std::{
    io::{BufRead, BufReader},
    process::{Child, Command, Stdio},
    sync::{mpsc, Mutex},
    time::Duration,
};
use tauri::{Manager, WebviewUrl, WebviewWindowBuilder};

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Ready {
    protocol: u32,
    url: String,
    title: String,
    width: u32,
    height: u32,
    native_features: Vec<String>,
}
struct Backend(Mutex<Child>);
impl Drop for Backend {
    fn drop(&mut self) {
        if let Ok(child) = self.0.get_mut() {
            let _ = child.kill();
            let _ = child.wait();
        }
    }
}
fn launch() -> Result<(Backend, Ready), Box<dyn std::error::Error>> {
    let mut command =
        if cfg!(debug_assertions) || std::env::args().any(|arg| arg == "--development") {
            let python = std::env::var("NATIVESTORE_PYTHON")?;
            let mut cmd = Command::new(python);
            cmd.args(["-m", "nativestore.host"]);
            cmd
        } else {
            let exe = std::env::current_exe()?;
            Command::new(
                exe.parent()
                    .ok_or("No executable directory")?
                    .join(if cfg!(windows) {
                        "nativestore-backend.exe"
                    } else {
                        "nativestore-backend"
                    }),
            )
        };
    command
        .stdout(Stdio::piped())
        .stderr(Stdio::inherit())
        .stdin(Stdio::piped())
        .env("NATIVESTORE_SUPERVISED", "1");
    #[cfg(windows)]
    {
        use std::os::windows::process::CommandExt;
        command.creation_flags(0x08000000);
    }
    let mut child = command.spawn()?;
    let stdout = child.stdout.take().ok_or("Backend stdout missing")?;
    let backend = Backend(Mutex::new(child));
    let (send, receive) = mpsc::channel();
    std::thread::spawn(move || {
        // Limit startup protocol bytes; discard later stdout without logging credentials.
        let mut reader = BufReader::new(stdout);
        let mut line = Vec::new();
        use std::io::Read;
        let read = reader.by_ref().take(8193).read_until(b'\n', &mut line);
        let _ = send.send(read.map(|_| line));
        let _ = std::io::copy(&mut reader, &mut std::io::sink());
    });
    let line = receive.recv_timeout(Duration::from_secs(30))??;
    if line.len() > 8192 {
        return Err("Startup message too large".into());
    }
    let ready: Ready = serde_json::from_slice(&line)?;
    if ready.protocol != 1
        || !(320..=7680).contains(&ready.width)
        || !(320..=7680).contains(&ready.height)
    {
        return Err("Invalid backend handshake".into());
    }
    let url = url::Url::parse(&ready.url)?;
    if url.scheme() != "http"
        || url.host_str() != Some("127.0.0.1")
        || url.port().is_none()
        || url.path() != "/__nativestore/bootstrap"
        || !url.username().is_empty()
    {
        return Err("Invalid backend origin".into());
    }
    Ok((backend, ready))
}
fn check_backend(startup_url: &str) -> Result<(), Box<dyn std::error::Error>> {
    let url = url::Url::parse(startup_url)?;
    let token = url
        .query_pairs()
        .find(|(key, _)| key == "token")
        .ok_or("Missing bootstrap token")?
        .1
        .into_owned();
    let origin = url.origin().ascii_serialization();
    let cookie = format!(
        "nativestore_{}={}",
        url.port().ok_or("Missing port")?,
        token
    );
    let client = reqwest::blocking::Client::builder()
        .no_proxy()
        .timeout(Duration::from_secs(10))
        .build()?;
    let page = client
        .get(format!("{origin}/"))
        .header("Cookie", &cookie)
        .send()?
        .error_for_status()?
        .text()?;
    if !page.contains("<!doctype html>") {
        return Err("Starter page did not render".into());
    }
    let reply: serde_json::Value = client
        .post(format!("{origin}/__nativestore/invoke"))
        .header("Cookie", &cookie)
        .header("Origin", &origin)
        .json(&serde_json::json!({"protocol": 1, "command": "list_expenses", "args": {}}))
        .send()?
        .error_for_status()?
        .json()?;
    if reply["ok"] != true || !reply["result"].is_array() {
        return Err("Starter command did not work".into());
    }
    Ok(())
}
fn diagnostic(message: &str) {
    eprintln!("{message}");
    if let Ok(path) = std::env::var("NATIVESTORE_DIAGNOSTICS") {
        use std::io::Write;
        if let Ok(mut file) = std::fs::OpenOptions::new()
            .create(true)
            .append(true)
            .open(path)
        {
            let _ = writeln!(file, "{message}");
        }
    }
}
fn run() -> Result<(), Box<dyn std::error::Error>> {
    let app = tauri::Builder::default()
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_clipboard_manager::init())
        .plugin(tauri_plugin_notification::init())
        .setup(|app| {
            let (backend, ready) = launch()?;
            let smoke = std::env::args().any(|arg| arg == "--smoke-test");
            let smoke_url = ready.url.clone();
            let (page_loaded, page_received) = mpsc::channel();
            let url = url::Url::parse(&ready.url)?;
            let origin = url.origin();
            let mut permissions = Vec::new();
            for feature in &ready.native_features {
                let allowed: &[&str] = match feature.as_str() {
                    "dialog" => &["dialog:allow-open", "dialog:allow-save"],
                    "clipboard" => &["clipboard-manager:allow-read-text", "clipboard-manager:allow-write-text"],
                    "notifications" => &["notification:allow-notify", "notification:allow-is-permission-granted", "notification:allow-request-permission"],
                    "window" => &["core:window:allow-set-title", "core:window:allow-minimize", "core:window:allow-maximize", "core:window:allow-unmaximize", "core:window:allow-close", "core:window:allow-is-maximized"],
                    _ => return Err("Unknown requested native feature".into()),
                };
                permissions.extend_from_slice(allowed);
            }
            if !permissions.is_empty() {
                let capability = serde_json::json!({
                    "identifier": "nativestore-session", "description": "Explicit application native features",
                    "windows": ["main"], "local": false,
                    "remote": {"urls": [format!("{}/*", origin.ascii_serialization())]},
                    "permissions": permissions,
                });
                app.add_capability(capability.to_string().as_str())?;
            }
            app.manage(backend);
            WebviewWindowBuilder::new(app, "main", WebviewUrl::External(url))
                .title(ready.title)
                .inner_size(ready.width as f64, ready.height as f64)
                .on_navigation(move |next| next.origin() == origin)
                .on_page_load(move |_window, payload| {
                    if smoke && payload.event() == tauri::webview::PageLoadEvent::Finished && payload.url().path() == "/" {
                        let _ = page_loaded.send(());
                    }
                })
                .build()?;
            if smoke {
                let handle = app.app_handle().clone();
                std::thread::spawn(move || {
                    let result = page_received.recv_timeout(Duration::from_secs(30))
                        .map_err(|_| "Native page did not finish loading".to_owned())
                        .and_then(|_| check_backend(&smoke_url).map_err(|error| error.to_string()));
                    if let Err(error) = &result { diagnostic(&format!("NativeStore smoke test failed: {error}")); }
                    handle.exit(if result.is_ok() { 0 } else { 1 });
                });
            }
            Ok(())
        })
        .build(tauri::generate_context!())?;
    app.run(|handle, event| {
        if let tauri::RunEvent::Exit = event {
            if let Some(backend) = handle.try_state::<Backend>() {
                if let Ok(mut child) = backend.0.lock() {
                    let _ = child.kill();
                    let _ = child.wait();
                }
            }
        }
    });
    Ok(())
}
fn main() {
    if let Err(error) = run() {
        diagnostic(&format!("NativeStore failed to initialize: {error}"));
        std::process::exit(1);
    }
}
