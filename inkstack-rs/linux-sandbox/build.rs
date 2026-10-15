fn main() {
    println!("cargo:rerun-if-env-changed=INKSTACK_BWRAP_SHA256");
}
