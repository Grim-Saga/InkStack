#![allow(clippy::expect_used)]

use std::process::Command;

use divan::Bencher;

fn main() {
    divan::main();
}

/// Exercises the Bazel-backed end-to-end benchmark path with a cheap,
/// deterministic InkStack invocation. Richer scenarios can add separate
/// benchmark binaries without making the shared harness depend on them.
#[divan::bench(sample_count = 20, sample_size = 1)]
fn inkstack_help(bencher: Bencher) {
    let inkstack = inkstack_utils_cargo_bin::cargo_bin("inkstack")
        .expect("inkstack binary should be available through Bazel runfiles");

    bencher.bench_local(move || {
        let output = Command::new(&inkstack)
            .arg("--help")
            .output()
            .expect("inkstack --help should run");
        assert!(output.status.success(), "inkstack --help should succeed");
    });
}
