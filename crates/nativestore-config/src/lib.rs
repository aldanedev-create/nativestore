use serde::{Deserialize, Serialize};
use std::{
    fs,
    path::{Path, PathBuf},
};
#[derive(Debug, Deserialize, Serialize)]
#[serde(default, deny_unknown_fields)]
pub struct Config {
    pub name: String,
    pub title: String,
    pub entry: String,
    pub width: u32,
    pub height: u32,
    pub identifier: String,
    pub version: String,
    pub command_timeout: f64,
    pub max_result_bytes: u64,
    pub request_workers: u32,
    pub hidden_imports: Vec<String>,
    pub extra_resources: Vec<String>,
    pub native_features: Vec<String>,
}
impl Default for Config {
    fn default() -> Self {
        Self {
            name: "nativestore-app".into(),
            title: "NativeStore".into(),
            entry: "main.py".into(),
            width: 1100,
            height: 750,
            identifier: "dev.nativestore.app".into(),
            version: "0.1.0".into(),
            command_timeout: 30.0,
            max_result_bytes: 1_048_576,
            request_workers: 16,
            hidden_imports: vec![],
            extra_resources: vec![],
            native_features: vec![],
        }
    }
}
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Document {
    app: Config,
}
pub fn safe_path(root: &Path, relative: &str) -> Result<PathBuf, String> {
    if relative.is_empty()
        || relative.starts_with('/')
        || relative.contains(['\\', ':', '\0'])
        || relative
            .split('/')
            .any(|s| s.is_empty() || s == "." || s == "..")
    {
        return Err("Unsafe relative path".into());
    }
    let path = root.join(relative);
    let canonical_root = root.canonicalize().map_err(|e| e.to_string())?;
    let mut ancestor = path.clone();
    while !ancestor.exists() {
        if !ancestor.pop() {
            return Err("Invalid path".into());
        }
    }
    if !ancestor
        .canonicalize()
        .map_err(|e| e.to_string())?
        .starts_with(canonical_root)
    {
        return Err("Path escapes project".into());
    }
    Ok(path)
}
fn identifier(value: &str) -> bool {
    let mut chars = value.chars();
    chars
        .next()
        .is_some_and(|c| c.is_ascii_alphabetic() || c == '_')
        && chars.all(|c| c.is_ascii_alphanumeric() || c == '_')
}
pub fn load(root: &Path) -> Result<Config, String> {
    let text = fs::read_to_string(root.join("nativestore.toml")).map_err(|e| e.to_string())?;
    let config = toml::from_str::<Document>(&text)
        .map_err(|e| e.to_string())?
        .app;
    if config.name.is_empty()
        || config.name.len() > 64
        || !config.name.starts_with(|c: char| c.is_ascii_lowercase())
        || !config
            .name
            .chars()
            .all(|c| c.is_ascii_lowercase() || c.is_ascii_digit() || c == '-')
    {
        return Err("Invalid application name".into());
    }
    if config.title.is_empty()
        || config.title.chars().count() > 200
        || !(320..=7680).contains(&config.width)
        || !(320..=7680).contains(&config.height)
        || !(0.05..=600.0).contains(&config.command_timeout)
        || !(1024..=20_971_520).contains(&config.max_result_bytes)
        || !(1..=64).contains(&config.request_workers)
    {
        return Err("Invalid application limits".into());
    }
    let parts: Vec<_> = config.version.split('.').collect();
    if parts.len() != 3
        || parts
            .iter()
            .any(|p| p.is_empty() || !p.chars().all(|c| c.is_ascii_digit()))
    {
        return Err("Invalid application version".into());
    }
    let domain: Vec<_> = config.identifier.split('.').collect();
    if domain.len() < 2
        || domain.iter().any(|p| {
            p.is_empty()
                || !p.starts_with(|c: char| c.is_ascii_alphabetic())
                || !p.chars().all(|c| c.is_ascii_alphanumeric() || c == '-')
        })
    {
        return Err("Invalid application identifier".into());
    }
    if !config.entry.ends_with(".py") {
        return Err("Entry must be Python".into());
    }
    safe_path(root, &config.entry)?;
    for resource in &config.extra_resources {
        safe_path(root, resource)?;
    }
    for module in &config.hidden_imports {
        if !module.split('.').all(identifier) {
            return Err("Invalid hidden import".into());
        }
    }
    let mut features = std::collections::HashSet::new();
    for feature in &config.native_features {
        if !["dialog", "clipboard", "notifications", "window"].contains(&feature.as_str())
            || !features.insert(feature)
        {
            return Err("Invalid native feature".into());
        }
    }
    Ok(config)
}
#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn strict_fields() {
        assert!(toml::from_str::<Document>("[app]\nunknown=1").is_err());
    }
    #[test]
    fn defaults() {
        assert_eq!(Config::default().command_timeout, 30.0);
    }
    #[test]
    fn bad_import() {
        assert!(!identifier("bad-name"));
        assert!(identifier("good_name"));
    }
}
