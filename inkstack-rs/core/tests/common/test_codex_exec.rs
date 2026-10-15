use inkstack_login::INKSTACK_API_KEY_ENV_VAR;
use std::path::Path;
use tempfile::TempDir;
use wiremock::MockServer;

pub struct TestInkStackExecBuilder {
    home: TempDir,
    cwd: TempDir,
}

impl TestInkStackExecBuilder {
    pub fn cmd(&self) -> assert_cmd::Command {
        let mut cmd = assert_cmd::Command::new(
            inkstack_utils_cargo_bin::cargo_bin("inkstack-exec")
                .expect("should find binary for inkstack-exec"),
        );
        cmd.current_dir(self.cwd.path())
            .env("INKSTACK_HOME", self.home.path())
            .env("INKSTACK_SQLITE_HOME", self.home.path())
            .env(INKSTACK_API_KEY_ENV_VAR, "dummy");
        cmd
    }
    pub fn cmd_with_server(&self, server: &MockServer) -> assert_cmd::Command {
        let mut cmd = self.cmd();
        let base = format!("{}/v1", server.uri());
        cmd.arg("-c")
            .arg(format!("openai_base_url={}", toml_string_literal(&base)));
        cmd
    }

    pub fn cwd_path(&self) -> &Path {
        self.cwd.path()
    }
    pub fn home_path(&self) -> &Path {
        self.home.path()
    }
}

fn toml_string_literal(value: &str) -> String {
    serde_json::to_string(value).expect("serialize TOML string literal")
}

pub fn test_inkstack_exec() -> TestInkStackExecBuilder {
    TestInkStackExecBuilder {
        home: TempDir::new().expect("create temp home"),
        cwd: TempDir::new().expect("create temp cwd"),
    }
}
