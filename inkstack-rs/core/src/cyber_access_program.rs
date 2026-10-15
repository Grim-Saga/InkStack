//! Forward explicit programs while leaving entitlement and model policy to the server.

use inkstack_api::AccessPrograms;
use inkstack_features::Feature;
use inkstack_login::InkStackAuth;
use inkstack_model_provider_info::OPENAI_PROVIDER_ID;
use inkstack_protocol::error::InkStackErr;
use inkstack_protocol::error::Result;
use inkstack_protocol::turn_input::CyberAccessProgram;

/// Configured support for explicit Cyber programs on API-key requests.
#[derive(Clone, Copy, Debug)]
pub enum ApiKeyCyberAccessPrograms {
    UnsupportedProvider,
    Disabled,
    Enabled,
}

impl ApiKeyCyberAccessPrograms {
    /// Captures the same provider and feature policy used by ordinary model requests.
    pub fn from_config(config: &crate::config::Config) -> Self {
        if config.model_provider_id != OPENAI_PROVIDER_ID {
            Self::UnsupportedProvider
        } else if config.features.enabled(Feature::ApiKeyCyberAccessPrograms) {
            Self::Enabled
        } else {
            Self::Disabled
        }
    }
}

pub(crate) fn for_provider(
    provider_id: &str,
    program: Option<CyberAccessProgram>,
) -> Option<CyberAccessProgram> {
    program.filter(|_| provider_id == OPENAI_PROVIDER_ID)
}

/// Resolves an explicit program using the request's current authentication.
pub fn for_auth(
    auth: Option<&InkStackAuth>,
    program: Option<CyberAccessProgram>,
    policy: ApiKeyCyberAccessPrograms,
) -> Result<Option<AccessPrograms>> {
    let Some(program) = program else {
        return Ok(None);
    };
    let Some(auth) = auth else {
        return Ok(None);
    };
    if auth.is_chatgpt_auth() {
        return Ok(Some(program.into()));
    }
    if !auth.is_api_key_auth() {
        return Ok(None);
    }
    match policy {
        ApiKeyCyberAccessPrograms::UnsupportedProvider => Ok(None),
        ApiKeyCyberAccessPrograms::Disabled => Err(InkStackErr::InvalidRequest(
            "Cyber access programs are disabled for this API-key session.".to_owned(),
        )),
        ApiKeyCyberAccessPrograms::Enabled => Ok(Some(program.into())),
    }
}
