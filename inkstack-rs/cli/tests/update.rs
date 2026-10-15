use anyhow::Result;
use predicates::str::contains;
use std::path::Path;
use tempfile::TempDir;

fn inkstack_command(inkstack_home: &Path) -> Result<assert_cmd::Command> {
    let mut cmd = assert_cmd::Command::new(inkstack_utils_cargo_bin::cargo_bin("inkstack")?);
    cmd.env("INKSTACK_HOME", inkstack_home);
    Ok(cmd)
}

#[cfg(debug_assertions)]
#[tokio::test]
async fn update_does_not_start_interactive_prompt() -> Result<()> {
    let inkstack_home = TempDir::new()?;

    inkstack_command(inkstack_home.path())?
        .arg("update")
        .assert()
        .failure()
        .stderr(contains("`inkstack update` is not available in debug builds"));

    Ok(())
}
