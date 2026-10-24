pub fn arg(args: &[String], name: &str, default: &str) -> String {
    args.iter()
        .position(|a| a == name)
        .and_then(|i| args.get(i + 1).cloned())
        .unwrap_or_else(|| default.to_string())
}

pub fn flag(args: &[String], name: &str) -> bool {
    args.iter().any(|a| a == name)
}
