use serde::{Deserialize, Serialize};
pub const VERSION: u32 = 1;
#[derive(Debug, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Invoke {
    pub protocol: u32,
    pub command: String,
    pub args: serde_json::Map<String, serde_json::Value>,
}
impl Invoke {
    pub fn validate(&self) -> Result<(), &'static str> {
        if self.protocol != VERSION {
            return Err("Unsupported protocol");
        }
        for segment in self.command.split('.') {
            let mut chars = segment.chars();
            if !chars
                .next()
                .is_some_and(|c| c.is_ascii_alphabetic() || c == '_')
                || !chars.all(|c| c.is_ascii_alphanumeric() || c == '_')
            {
                return Err("Invalid command");
            }
        }
        Ok(())
    }
}
#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn unknown_fields_rejected() {
        assert!(serde_json::from_str::<Invoke>(
            r#"{"protocol":1,"command":"x","args":{},"eval":"x"}"#
        )
        .is_err());
    }
    #[test]
    fn namespaces_are_validated() {
        for name in ["inventory.add_item", "inventory.tools.list"] {
            let value = Invoke {
                protocol: 1,
                command: name.into(),
                args: Default::default(),
            };
            assert!(value.validate().is_ok());
        }
        for name in ["inventory..item", ".item", "inventory.", "inventory.eval()"] {
            let value = Invoke {
                protocol: 1,
                command: name.into(),
                args: Default::default(),
            };
            assert!(value.validate().is_err());
        }
    }
    #[test]
    fn protocol_rejected() {
        let value: Invoke =
            serde_json::from_str(r#"{"protocol":2,"command":"x","args":{}}"#).unwrap();
        assert!(value.validate().is_err());
    }
    #[test]
    fn good_message() {
        let value: Invoke =
            serde_json::from_str(r#"{"protocol":1,"command":"hello","args":{"name":"Ada"}}"#)
                .unwrap();
        assert!(value.validate().is_ok());
    }
}
