use crate::config::Config;
pub use inkstack_rollout::ARCHIVED_SESSIONS_SUBDIR;
pub use inkstack_rollout::Cursor;
pub use inkstack_rollout::INTERACTIVE_SESSION_SOURCES;
pub use inkstack_rollout::RolloutRecorder;
pub use inkstack_rollout::RolloutRecorderParams;
pub use inkstack_rollout::SESSIONS_SUBDIR;
pub use inkstack_rollout::SessionMeta;
pub use inkstack_rollout::SortDirection;
pub use inkstack_rollout::ThreadItem;
pub use inkstack_rollout::ThreadSortKey;
pub use inkstack_rollout::ThreadsPage;
pub use inkstack_rollout::append_thread_name;
pub use inkstack_rollout::find_archived_thread_path_by_id_str;
#[deprecated(note = "use find_thread_path_by_id_str")]
pub use inkstack_rollout::find_conversation_path_by_id_str;
pub use inkstack_rollout::find_thread_meta_by_name_str;
pub use inkstack_rollout::find_thread_name_by_id;
pub use inkstack_rollout::find_thread_names_by_ids;
pub use inkstack_rollout::find_thread_path_by_id_str;
pub use inkstack_rollout::parse_cursor;
pub use inkstack_rollout::read_head_for_summary;
pub use inkstack_rollout::read_session_meta_line;
pub use inkstack_rollout::rollout_date_parts;

impl inkstack_rollout::RolloutConfigView for Config {
    fn inkstack_home(&self) -> &std::path::Path {
        self.inkstack_home.as_path()
    }

    fn sqlite_config(&self) -> &inkstack_state::SqliteConfig {
        self.sqlite_config()
    }

    fn cwd(&self) -> &std::path::Path {
        self.cwd.as_path()
    }

    fn model_provider_id(&self) -> &str {
        self.model_provider_id.as_str()
    }

    fn generate_memories(&self) -> bool {
        self.memories.generate_memories
    }
}

pub(crate) mod list {
    pub use inkstack_rollout::find_thread_path_by_id_str;
}

#[cfg(test)]
pub(crate) mod recorder {
    pub use inkstack_rollout::RolloutRecorder;
}

pub(crate) use crate::session_rollout_init_error::map_session_init_error;

pub(crate) mod truncation {
    pub(crate) use crate::thread_rollout_truncation::*;
}
