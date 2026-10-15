//! Triggers local rollout maintenance without waiting for the background pass.

use super::ThreadRequestProcessor;
use super::thread_processor::unsupported_thread_store_operation;
use inkstack_app_server_protocol::ClientResponsePayload;
use inkstack_app_server_protocol::JSONRPCErrorError;
use inkstack_app_server_protocol::RolloutCompressResponse;
use inkstack_thread_store::LocalThreadStore;

impl ThreadRequestProcessor {
    pub(crate) fn rollout_compress(
        &self,
    ) -> Result<Option<ClientResponsePayload>, JSONRPCErrorError> {
        if !self.thread_store.as_any().is::<LocalThreadStore>() {
            return Err(unsupported_thread_store_operation("rollout/compress"));
        }

        inkstack_rollout::spawn_rollout_compression_worker(
            self.config.inkstack_home.to_path_buf(),
            inkstack_rollout::RolloutCompressionTrigger::Rpc,
        );
        Ok(Some(RolloutCompressResponse {}.into()))
    }
}
