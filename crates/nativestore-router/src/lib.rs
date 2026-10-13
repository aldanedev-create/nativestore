use serde::Serialize;
use std::{fs, path::Path};
#[derive(Debug, Serialize, PartialEq, Eq)]
pub struct Route {
    pub path: String,
    pub source: String,
    pub kind: String,
}
#[derive(Serialize)]
pub struct Manifest {
    pub protocol: u32,
    pub routes: Vec<Route>,
}
fn identifier(value: &str) -> bool {
    let mut chars = value.chars();
    chars
        .next()
        .is_some_and(|c| c.is_ascii_alphabetic() || c == '_')
        && chars.all(|c| c.is_ascii_alphanumeric() || c == '_')
}
fn segment(value: &str) -> Result<String, String> {
    if value.starts_with('[') && value.ends_with(']') && identifier(&value[1..value.len() - 1]) {
        Ok(format!("{{{}}}", &value[1..value.len() - 1]))
    } else if !value.is_empty()
        && value
            .chars()
            .all(|c| c.is_ascii_alphanumeric() || c == '_' || c == '-')
    {
        Ok(value.to_owned())
    } else {
        Err(format!("Invalid route segment: {value}"))
    }
}
fn overlap(a: &str, b: &str) -> bool {
    let a: Vec<_> = a.split('/').collect();
    let b: Vec<_> = b.split('/').collect();
    a.len() == b.len()
        && a.iter()
            .zip(b)
            .all(|(x, y)| *x == y || x.starts_with('{') || y.starts_with('{'))
}
fn visit(
    directory: &Path,
    project: &Path,
    base: &Path,
    kind: &str,
    routes: &mut Vec<Route>,
) -> Result<(), String> {
    for item in fs::read_dir(directory).map_err(|e| e.to_string())? {
        let item = item.map_err(|e| e.to_string())?;
        let path = item.path();
        if !path
            .canonicalize()
            .map_err(|e| e.to_string())?
            .starts_with(project)
        {
            return Err("Path escapes project".into());
        }
        if item.file_type().map_err(|e| e.to_string())?.is_symlink() {
            return Err("Symlink route is not allowed".into());
        }
        if path.is_dir() {
            visit(&path, project, base, kind, routes)?;
            continue;
        }
        if path.extension().and_then(|x| x.to_str()) != Some("py") {
            continue;
        }
        let local = path
            .strip_prefix(base)
            .map_err(|e| e.to_string())?
            .with_extension("");
        let parts: Vec<_> = local
            .iter()
            .map(|s| s.to_string_lossy().into_owned())
            .collect();
        if parts.iter().any(|p| p.starts_with('_')) {
            continue;
        }
        let mut output = if kind == "api" {
            vec!["api".to_owned()]
        } else {
            vec![]
        };
        for (index, part) in parts.iter().enumerate() {
            if index == parts.len() - 1 && part == "index" {
                continue;
            }
            output.push(segment(part)?);
        }
        let mut names = std::collections::HashSet::new();
        for part in &output {
            if part.starts_with('{') && !names.insert(part.clone()) {
                return Err("Repeated route parameter".into());
            }
        }
        if kind == "pages"
            && output
                .first()
                .is_some_and(|s| s == "static" || s == "__nativestore")
        {
            return Err("Reserved route".into());
        }
        let route = Route {
            path: format!("/{}", output.join("/")),
            source: path
                .strip_prefix(project)
                .map_err(|e| e.to_string())?
                .to_string_lossy()
                .replace('\\', "/"),
            kind: kind.to_owned(),
        };
        routes.push(route);
    }
    Ok(())
}
pub fn discover(root: &Path) -> Result<Manifest, String> {
    let project = root.canonicalize().map_err(|e| e.to_string())?;
    let mut routes = Vec::new();
    for kind in ["pages", "api"] {
        let base = project.join(kind);
        if base.exists() {
            visit(&base, &project, &base, kind, &mut routes)?;
        }
    }
    routes.sort_by(|a, b| (&a.path, &a.source).cmp(&(&b.path, &b.source)));
    for (index, route) in routes.iter().enumerate() {
        for other in &routes[index + 1..] {
            if overlap(&route.path, &other.path) {
                return Err(format!(
                    "Ambiguous routes: {} and {}",
                    route.source, other.source
                ));
            }
        }
    }
    Ok(Manifest {
        protocol: nativestore_protocol::VERSION,
        routes,
    })
}
#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn dynamic() {
        assert_eq!(segment("[id]").unwrap(), "{id}");
        assert!(segment("[bad-name]").is_err());
    }
    #[test]
    fn conflicts() {
        assert!(overlap("/posts/{id}", "/posts/new"));
        assert!(!overlap("/posts/{id}", "/users/{id}"));
    }
    #[test]
    fn traversal() {
        assert!(segment("..").is_err());
        assert!(segment("a.b").is_err());
    }
}

#[cfg(test)]
mod filesystem_tests {
    use super::*;
    use nativestore_test_support::Project;
    #[test]
    fn real_files_without_imports() {
        let project = Project::new().unwrap();
        project
            .write("pages/index.py", "raise Exception('do not import')")
            .unwrap();
        project.write("pages/users/[id].py", "").unwrap();
        let routes = discover(&project.root).unwrap().routes;
        assert_eq!(routes[0].path, "/");
        assert_eq!(routes[1].path, "/users/{id}");
        project.write("pages/users/new.py", "").unwrap();
        assert!(discover(&project.root).is_err());
    }
}
