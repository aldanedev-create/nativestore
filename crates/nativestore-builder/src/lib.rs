use serde::Serialize;
use std::path::Path;
#[derive(Debug, Serialize)]
pub struct Plan {
    pub platform: String,
    pub sidecar: String,
    pub installer: String,
    pub resources: Vec<String>,
}
pub fn plan(root: &Path, target: &str) -> Result<Plan, String> {
    if target != "windows-x86_64" {
        return Err("Only Windows x64 installer builds are supported".into());
    }
    let config = nativestore_config::load(root)?;
    let mut resources = vec![
        config.entry,
        "nativestore.toml".into(),
        "nativestore.lock".into(),
        "app".into(),
        "pages".into(),
        "api".into(),
        "templates".into(),
        "static".into(),
    ];
    resources.extend(config.extra_resources);
    resources.sort();
    resources.dedup();
    Ok(Plan {
        platform: target.into(),
        sidecar: "nativestore-backend-x86_64-pc-windows-msvc.exe".into(),
        installer: "nsis".into(),
        resources,
    })
}
#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn unsupported_platform() {
        assert!(plan(Path::new("."), "linux-x86_64")
            .unwrap_err()
            .contains("Windows"));
    }
}
