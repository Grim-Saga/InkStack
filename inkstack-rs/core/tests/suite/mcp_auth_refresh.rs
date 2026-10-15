#![allow(clippy::unwrap_used)]

use anyhow::Result;
use inkstack_config::McpServerTransportConfig;
use inkstack_core::config::ConfigBuilder;
use inkstack_core::config::Constrained;
use inkstack_core::plugins_manager_for_config;
use inkstack_exec_server_test_support::environment_manager_without_environments;
use inkstack_login::AuthManager;
use inkstack_login::InkStackAuth;
use inkstack_login::ExternalAuth;
use inkstack_login::ExternalAuthFuture;
use inkstack_login::ExternalAuthRefreshContext;
use inkstack_mcp::INKSTACK_APPS_MCP_SERVER_NAME;
use inkstack_mcp::InkStackAppsToolsCache;
use inkstack_mcp::EffectiveMcpServer;
use inkstack_mcp::McpRuntime;
use inkstack_mcp::McpRuntimeContext;
use inkstack_mcp::McpRuntimeInput;
use inkstack_mcp::McpStartupPolicy;
use inkstack_mcp::McpToolCatalogCache;
use inkstack_protocol::mcp::ClientMcpExtensions;
use inkstack_protocol::protocol::AskForApproval;
use core_test_support::apps_test_server::AppsTestServer;
use core_test_support::responses::start_mock_server;
use core_test_support::skip_if_no_network;
use pretty_assertions::assert_eq;
use serde_json::Value;
use serde_json::json;
use std::collections::HashMap;
use std::sync::Arc;
use tempfile::TempDir;
use tokio_util::sync::CancellationToken;

// Installs a known snapshot through AuthManager's public external-auth path.
struct StaticExternalAuth(InkStackAuth);

impl ExternalAuth for StaticExternalAuth {
    fn resolve(&self) -> ExternalAuthFuture<'_, InkStackAuth> {
        Box::pin(async { Ok(self.0.clone()) })
    }

    fn refresh(&self, _context: ExternalAuthRefreshContext) -> ExternalAuthFuture<'_, InkStackAuth> {
        Box::pin(async { Ok(self.0.clone()) })
    }
}

#[tokio::test(flavor = "multi_thread", worker_threads = 2)]
async fn hosted_plugin_runtime_ps_mcp_tool_calls_use_current_auth_manager_token() -> Result<()> {
    skip_if_no_network!(Ok(()));

    let server = start_mock_server().await;
    let apps_server = AppsTestServer::mount_hosted_plugin_runtime_searchable(&server).await?;
    let home = Arc::new(TempDir::new()?);
    let expected_auth = InkStackAuth::from_external_chatgpt_tokens(
        "header.e30.first",
        "test-account",
        /*chatgpt_plan_type*/ None,
    )?;
    let auth_manager = AuthManager::from_auth_for_testing_with_home(
        expected_auth.clone(),
        home.path().to_path_buf(),
    );
    // Build the hosted-plugin config directly so the local test origin can
    // exercise the connection-manager auth path. Effective server resolution
    // correctly strips ChatGPT auth from untrusted localhost origins.
    let mut hosted_plugin_runtime_config = inkstack_mcp::hosted_plugin_runtime_mcp_server_config(
        &apps_server.chatgpt_base_url,
        /*apps_mcp_product_sku*/ None,
        /*originator*/ None,
    );
    let McpServerTransportConfig::StreamableHttp {
        bearer_token_env_var,
        ..
    } = &mut hosted_plugin_runtime_config.transport
    else {
        panic!("hosted plugin runtime should use streamable HTTP");
    };
    // Keep the test on the AuthManager path even if the developer has the
    // debug bearer override in their environment.
    *bearer_token_env_var = None;
    let mcp_servers = HashMap::from([(
        INKSTACK_APPS_MCP_SERVER_NAME.to_string(),
        EffectiveMcpServer::from_host_config(hosted_plugin_runtime_config),
    )]);
    let mut config = ConfigBuilder::default()
        .inkstack_home(home.path().to_path_buf())
        .build()
        .await?;
    config.permissions.approval_policy = Constrained::allow_any(AskForApproval::Never);
    let plugins_manager = plugins_manager_for_config(&config, Arc::clone(&auth_manager));
    let mcp_config = Arc::new(config.to_mcp_config(&plugins_manager).await);
    let runtime = McpRuntime::new(McpRuntimeInput {
        startup_policy: McpStartupPolicy::Eager,
        config: mcp_config,
        plugins_available: false,
        ready_selected_capability_roots: Vec::new(),
        mcp_servers,
        submit_id: "test".to_string(),
        tx_event: None,
        startup_cancellation_token: CancellationToken::new(),
        runtime_context: McpRuntimeContext::new(
            Arc::new(environment_manager_without_environments()),
            home.path().to_path_buf(),
        ),
        inkstack_apps_tools_cache: InkStackAppsToolsCache::default(),
        tool_catalog_cache: McpToolCatalogCache::default(),
        inkstack_apps_tools_cache_key: inkstack_mcp::inkstack_apps_tools_cache_key(Some(&expected_auth)),
        client_mcp_extensions: ClientMcpExtensions::default(),
        auth: Some(expected_auth.clone()),
        auth_manager: Some(Arc::clone(&auth_manager)),
        elicitation_reviewer: None,
        elicitation_lifecycle: None,
    })
    .await;
    // The model-provider test covers AuthManager reload behavior. Keep this
    // regression focused on core MCP wiring by updating the same shared
    // manager after the MCP client has been created.
    auth_manager
        .set_external_auth(Arc::new(StaticExternalAuth(
            InkStackAuth::from_external_chatgpt_tokens(
                "header.e30.reloaded",
                "test-account",
                /*chatgpt_plan_type*/ None,
            )?,
        )))
        .await?;

    // The manager and its static fallback were created before the auth update,
    // so this tool call only sees the new token if the InkStack Apps provider
    // reads the shared AuthManager at request time.
    let tool_result = runtime
        .latest_call_tool(
            INKSTACK_APPS_MCP_SERVER_NAME,
            "calendar_create_event",
            /*environment_id*/ None,
            Some(json!({
                "title": "Lunch",
                "starts_at": "2026-06-18T12:00:00Z",
            })),
            /*meta*/ None,
            /*requested_timeout*/ None,
            /*wait_for_server*/ true,
        )
        .await?;
    assert_eq!(tool_result.result.is_error, Some(false));

    let requests = server
        .received_requests()
        .await
        .expect("mock server should capture tool-call requests");
    let tool_call_request = requests
        .iter()
        .find(|request| {
            request.url.path() == "/api/inkstack/ps/mcp"
                && serde_json::from_slice::<Value>(&request.body)
                    .ok()
                    .is_some_and(|body| {
                        body.get("method").and_then(Value::as_str) == Some("tools/call")
                    })
        })
        .expect("InkStack Apps should receive a tool call");
    assert_eq!(
        tool_call_request
            .headers
            .get("authorization")
            .and_then(|value| value.to_str().ok()),
        Some("Bearer header.e30.reloaded")
    );

    Ok(())
}
