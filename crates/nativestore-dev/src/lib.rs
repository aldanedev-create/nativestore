use serde::Serialize;
use std::{fs, path::Path, time::UNIX_EPOCH};
#[derive(Debug, Serialize, PartialEq, Eq)]
pub struct FileState {
    pub path: String,
    pub modified_ns: u128,
    pub size: u64,
}
fn scan(directory: &Path, root: &Path, files: &mut Vec<FileState>) -> Result<(), String> {
    for entry in fs::read_dir(directory).map_err(|e| e.to_string())? {
        let entry = entry.map_err(|e| e.to_string())?;
        if entry.file_name() == "__pycache__" {
            continue;
        }
        let path = entry.path();
        if entry.file_type().map_err(|e| e.to_string())?.is_symlink() {
            return Err("Watched paths cannot be symlinks".into());
        }
        if path.is_dir() {
            scan(&path, root, files)?;
        } else if path.is_file() {
            record(&path, root, files)?;
        }
    }
    Ok(())
}
fn record(path: &Path, root: &Path, files: &mut Vec<FileState>) -> Result<(), String> {
    let metadata = fs::metadata(path).map_err(|e| e.to_string())?;
    files.push(FileState {
        path: path
            .strip_prefix(root)
            .map_err(|e| e.to_string())?
            .to_string_lossy()
            .replace('\\', "/"),
        modified_ns: metadata
            .modified()
            .map_err(|e| e.to_string())?
            .duration_since(UNIX_EPOCH)
            .map_err(|e| e.to_string())?
            .as_nanos(),
        size: metadata.len(),
    });
    Ok(())
}
pub fn snapshot(root: &Path) -> Result<Vec<FileState>, String> {
    let mut files = Vec::new();
    for item in fs::read_dir(root).map_err(|e| e.to_string())? {
        let path = item.map_err(|e| e.to_string())?.path();
        if path.extension().is_some_and(|e| e == "py")
            || path.file_name().is_some_and(|e| e == "nativestore.toml")
        {
            record(&path, root, &mut files)?;
        }
    }
    for directory in ["app", "pages", "api", "templates", "static"] {
        let path = root.join(directory);
        if path.exists() {
            scan(&path, root, &mut files)?;
        }
    }
    files.sort_by(|a, b| a.path.cmp(&b.path));
    Ok(files)
}
#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn missing_directory_fails() {
        assert!(snapshot(Path::new("__missing_nativestore_project__")).is_err());
    }
}
