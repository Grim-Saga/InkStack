use super::ContextualUserFragment;
use inkstack_hooks::HookContext;
use inkstack_protocol::models::ContentItemKind;
use inkstack_protocol::models::ContentItemMetadata;

#[derive(Debug, Clone, PartialEq)]
pub(crate) struct HookAdditionalContext {
    context: HookContext,
}

impl HookAdditionalContext {
    pub(crate) fn new(context: HookContext) -> Self {
        Self { context }
    }
}

impl ContextualUserFragment for HookAdditionalContext {
    fn content_kind(&self) -> ContentItemKind {
        ContentItemKind("hooks.additional_context".to_string())
    }

    fn role(&self) -> &'static str {
        "developer"
    }

    fn markers(&self) -> (&'static str, &'static str) {
        Self::type_markers()
    }

    fn type_markers() -> (&'static str, &'static str) {
        ("", "")
    }

    fn body(&self) -> String {
        self.context.text.clone()
    }

    fn content_metadata(&self) -> ContentItemMetadata {
        self.context.metadata.clone()
    }
}
