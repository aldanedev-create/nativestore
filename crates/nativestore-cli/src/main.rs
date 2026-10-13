use std::{
    env,
    path::Path,
    process::{Command, ExitCode},
};
fn main() -> ExitCode {
    let args: Vec<String> = env::args().skip(1).collect();
    if let Some(command) = args.first() {
        let result = match command.as_str() {
            "routes" if args.len() == 1 => nativestore_router::discover(Path::new("."))
                .and_then(|value| serde_json::to_value(value).map_err(|e| e.to_string())),
            "config" if args.len() == 1 => nativestore_config::load(Path::new("."))
                .and_then(|value| serde_json::to_value(value).map_err(|e| e.to_string())),
            "snapshot" if args.len() == 1 => nativestore_dev::snapshot(Path::new("."))
                .and_then(|value| serde_json::to_value(value).map_err(|e| e.to_string())),
            "build-plan" if args.len() == 1 => {
                nativestore_builder::plan(Path::new("."), "windows-x86_64")
                    .and_then(|value| serde_json::to_value(value).map_err(|e| e.to_string()))
            }
            "verify-assets" if args.len() == 2 => {
                nativestore_assets::verify(Path::new("."), Path::new(&args[1]))
                    .map(|count| serde_json::json!({"verified": count}))
            }
            _ => {
                return forward(args);
            }
        };
        match result {
            Ok(value) => {
                println!("{}", serde_json::to_string_pretty(&value).unwrap());
                return ExitCode::SUCCESS;
            }
            Err(error) => {
                eprintln!("NativeStore: {error}");
                return ExitCode::FAILURE;
            }
        }
    }
    forward(args)
}
fn forward(args: Vec<String>) -> ExitCode {
    let python = env::var("NATIVESTORE_PYTHON").unwrap_or_else(|_| {
        if cfg!(windows) {
            "python".into()
        } else {
            "python3".into()
        }
    });
    match Command::new(python)
        .args(["-m", "nativestore"])
        .args(args)
        .status()
    {
        Ok(status) => ExitCode::from(status.code().unwrap_or(1).clamp(0, 255) as u8),
        Err(error) => {
            eprintln!("NativeStore Python runtime unavailable: {error}");
            ExitCode::FAILURE
        }
    }
}
