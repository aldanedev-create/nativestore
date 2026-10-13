use std::{
    fs,
    path::PathBuf,
    sync::atomic::{AtomicU64, Ordering},
};
static NEXT: AtomicU64 = AtomicU64::new(0);
pub struct Project {
    pub root: PathBuf,
}
impl Project {
    pub fn new() -> std::io::Result<Self> {
        let root = std::env::temp_dir().join(format!(
            "nativestore-test-{}-{}",
            std::process::id(),
            NEXT.fetch_add(1, Ordering::SeqCst)
        ));
        fs::create_dir(&root)?;
        Ok(Self { root })
    }
    pub fn write(&self, relative: &str, data: &str) -> std::io::Result<()> {
        let path = self.root.join(relative);
        if PathBuf::from(relative)
            .components()
            .any(|part| !matches!(part, std::path::Component::Normal(_)))
        {
            return Err(std::io::Error::new(
                std::io::ErrorKind::InvalidInput,
                "Unsafe test fixture path",
            ));
        }
        if let Some(parent) = path.parent() {
            fs::create_dir_all(parent)?;
        }
        fs::write(path, data)
    }
}
impl Drop for Project {
    fn drop(&mut self) {
        let _ = fs::remove_dir_all(&self.root);
    }
}
#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn lifetime() {
        let root;
        {
            let project = Project::new().unwrap();
            project.write("pages/index.py", "").unwrap();
            root = project.root.clone();
            assert!(root.join("pages/index.py").exists());
        }
        assert!(!root.exists());
    }
}
