//! Derives the enterprise credential owner from the active InkStack account.

use inkstack_config::McpEmaAuthScope;
use inkstack_login::InkStackAuth;

pub fn ema_auth_scope(auth: Option<&InkStackAuth>) -> Option<McpEmaAuthScope> {
    let auth = auth?;
    McpEmaAuthScope::new(auth.get_chatgpt_user_id()?, auth.get_account_id()?)
}
