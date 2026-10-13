use sha2::{Digest, Sha256};
use std::{fs, path::Path};
pub fn verify_bytes(data: &[u8], expected: &str) -> Result<(), String> {
    if expected.len() != 64
        || !expected
            .bytes()
            .all(|b| b.is_ascii_digit() || (b'a'..=b'f').contains(&b))
    {
        return Err("Invalid SHA-256".into());
    }
    let actual = format!("{:x}", Sha256::digest(data));
    if actual == expected {
        Ok(())
    } else {
        Err("Asset integrity check failed".into())
    }
}
pub fn verify(root: &Path, registry: &Path) -> Result<usize, String> {
    let lock_path = root.join("nativestore.lock");
    if !lock_path.is_file() {
        return Ok(0);
    }
    let lock: serde_json::Value =
        serde_json::from_slice(&fs::read(lock_path).map_err(|e| e.to_string())?)
            .map_err(|e| e.to_string())?;
    let registry: serde_json::Value =
        serde_json::from_slice(&fs::read(registry).map_err(|e| e.to_string())?)
            .map_err(|e| e.to_string())?;
    if lock["schema"] != 1 || registry["schema"] != 1 {
        return Err("Unsupported asset schema".into());
    }
    let trusted = registry["packages"].as_array().ok_or("Invalid registry")?;
    let entries = lock["packages"].as_array().ok_or("Invalid lock")?;
    let mut names = std::collections::HashSet::new();
    for entry in entries {
        if !trusted.contains(entry) {
            return Err("Untrusted lock entry".into());
        }
        if !names.insert(entry["name"].as_str().ok_or("Invalid package name")?) {
            return Err("Duplicate locked package".into());
        }
        let file = nativestore_config::safe_path(
            root,
            &format!(
                "static/vendor/{}",
                entry["path"].as_str().ok_or("Invalid asset path")?
            ),
        )?;
        if fs::metadata(&file).map_err(|e| e.to_string())?.len() > 20 * 1024 * 1024 {
            return Err("Asset too large".into());
        }
        verify_bytes(
            &fs::read(file).map_err(|e| e.to_string())?,
            entry["sha256"].as_str().ok_or("Missing hash")?,
        )?;
    }
    Ok(entries.len())
}
#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn valid_hash() {
        assert!(verify_bytes(
            b"abc",
            "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
        )
        .is_ok());
    }
    #[test]
    fn tampered() {
        assert!(verify_bytes(
            b"tampered",
            "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
        )
        .is_err());
    }
    #[test]
    fn malformed() {
        assert!(verify_bytes(b"abc", "unknown").is_err());
    }
}
