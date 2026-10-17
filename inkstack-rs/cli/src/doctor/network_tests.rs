use pretty_assertions::assert_eq;
use wiremock::Mock;
use wiremock::MockServer;
use wiremock::ResponseTemplate;
use wiremock::matchers::method;

use super::super::CheckStatus;
use super::super::ProviderAuthReachabilityMode;
use super::super::provider_reachability_check;
use super::super::provider_reachability_plan_from_parts;

#[tokio::test]
async fn provider_reachability_rejects_proxy_authentication_challenges() {
    let proxy = MockServer::start().await;
    Mock::given(method("HEAD"))
        .respond_with(ResponseTemplate::new(407))
        .mount(&proxy)
        .await;
    // The ChatGPT inference endpoint is now a fixed production URL, so probe
    // the provider-configured base URL instead. The proxy still returns 407,
    // so the reachability check must fail with a proxy-auth error.
    let plan = provider_reachability_plan_from_parts(
        ProviderAuthReachabilityMode::ApiKey,
        "openai",
        "OpenAI",
        Some(&proxy.uri()),
        /*provider_query_params*/ None,
        /*is_amazon_bedrock*/ false,
    );

    let check = provider_reachability_check(plan).await;
    assert_eq!(check.status, CheckStatus::Fail);
    assert!(
        check
            .details
            .join(" ")
            .contains("proxy authentication required (HTTP 407)")
    );
}
