#[cfg(target_os = "windows")]
fn main() -> anyhow::Result<()> {
    inkstack_windows_sandbox::setup_helper_main()
}

#[cfg(not(target_os = "windows"))]
fn main() {
    panic!("inkstack-windows-sandbox-setup is Windows-only");
}
