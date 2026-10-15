use std::io::ErrorKind;
use std::path::Path;

use crate::rollout::SESSIONS_SUBDIR;
use inkstack_protocol::error::InkStackErr;
use inkstack_thread_store::ThreadStoreError;

pub(crate) fn map_session_init_error(err: &anyhow::Error, inkstack_home: &Path) -> InkStackErr {
    if let Some(store_error) = err
        .chain()
        .find_map(|cause| cause.downcast_ref::<ThreadStoreError>())
    {
        match store_error {
            ThreadStoreError::Unsupported { operation } => {
                return InkStackErr::UnsupportedOperation(format!("{operation} is not supported yet"));
            }
            ThreadStoreError::Conflict { message } => {
                return InkStackErr::InvalidRequest(message.clone());
            }
            ThreadStoreError::ThreadNotFound { .. }
            | ThreadStoreError::InvalidRequest { .. }
            | ThreadStoreError::Internal { .. } => {}
        }
    }

    if let Some(mapped) = err
        .chain()
        .filter_map(|cause| cause.downcast_ref::<std::io::Error>())
        .find_map(|io_err| map_rollout_io_error(io_err, inkstack_home))
    {
        return mapped;
    }

    InkStackErr::Fatal(format!("Failed to initialize session: {err:#}"))
}

fn map_rollout_io_error(io_err: &std::io::Error, inkstack_home: &Path) -> Option<InkStackErr> {
    let sessions_dir = inkstack_home.join(SESSIONS_SUBDIR);
    let hint = match io_err.kind() {
        ErrorKind::PermissionDenied => format!(
            "InkStack cannot access session files at {} (permission denied). If sessions were created using sudo, fix ownership: sudo chown -R $(whoami) {}",
            sessions_dir.display(),
            inkstack_home.display()
        ),
        ErrorKind::NotFound => format!(
            "Session storage missing at {}. Create the directory or choose a different InkStack home.",
            sessions_dir.display()
        ),
        ErrorKind::AlreadyExists => format!(
            "Session storage path {} is blocked by an existing file. Remove or rename it so InkStack can create sessions.",
            sessions_dir.display()
        ),
        ErrorKind::InvalidData => format!(
            "Session data under {} looks corrupt or unreadable. Clearing the sessions directory may help (this will remove saved threads).",
            sessions_dir.display()
        ),
        ErrorKind::IsADirectory | ErrorKind::NotADirectory => format!(
            "Session storage path {} has an unexpected type. Ensure it is a directory InkStack can use for session files.",
            sessions_dir.display()
        ),
        _ => return None,
    };

    Some(InkStackErr::Fatal(format!(
        "{hint} (underlying error: {io_err})"
    )))
}
