#[cfg(inkstack_bazel)]
pub use code_mode_proto::inkstack::code_mode::v1::*;

#[cfg(not(inkstack_bazel))]
tonic::include_proto!("inkstack.code_mode.v1");

pub const MAX_IDENTIFIER_BYTES: usize = 256;
