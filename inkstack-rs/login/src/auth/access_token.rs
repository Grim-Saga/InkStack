const PERSONAL_ACCESS_TOKEN_PREFIX: &str = "at-";

pub(super) enum InkStackAccessToken<'a> {
    PersonalAccessToken(&'a str),
    AgentIdentityJwt(&'a str),
}

pub(super) fn classify_inkstack_access_token(access_token: &str) -> InkStackAccessToken<'_> {
    if access_token.starts_with(PERSONAL_ACCESS_TOKEN_PREFIX) {
        InkStackAccessToken::PersonalAccessToken(access_token)
    } else {
        InkStackAccessToken::AgentIdentityJwt(access_token)
    }
}

#[cfg(test)]
#[path = "access_token_tests.rs"]
mod tests;
