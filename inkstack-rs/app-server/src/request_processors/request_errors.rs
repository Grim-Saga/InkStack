use super::*;
use inkstack_protocol::error::InkStackErrorDetails;

pub(super) fn environment_selection_error(err: InkStackErr) -> JSONRPCErrorError {
    match err.details() {
        InkStackErrorDetails::InvalidRequest(message) => invalid_request(message.clone()),
        _ => internal_error(format!("failed to validate environment selections: {err}")),
    }
}
