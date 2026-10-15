use crate::bespoke_event_handling::apply_bespoke_event_handling;
use crate::command_exec::CommandExecManager;
use crate::command_exec::StartCommandExecParams;
use crate::config_manager::ConfigManager;
use crate::error_code::INPUT_TOO_LARGE_ERROR_CODE;
use crate::error_code::invalid_params;
use crate::models::supported_models;
use crate::outgoing_message::ConnectionId;
use crate::outgoing_message::ConnectionRequestId;
use crate::outgoing_message::OutgoingMessageSender;
use crate::outgoing_message::RequestContext;
use crate::outgoing_message::ThreadScopedOutgoingMessageSender;
use crate::skills_watcher::SkillsWatcher;
use crate::thread_status::ThreadWatchManager;
use crate::thread_status::resolve_thread_status;
use chrono::Duration as ChronoDuration;
use chrono::SecondsFormat;
use inkstack_analytics::AnalyticsEventsClient;
use inkstack_analytics::AnalyticsJsonRpcError;
use inkstack_analytics::InputError;
use inkstack_analytics::TurnSteerRequestError;
use inkstack_app_server_protocol::Account;
use inkstack_app_server_protocol::AccountLoginCompletedNotification;
use inkstack_app_server_protocol::AccountTokenUsageDailyBucket;
use inkstack_app_server_protocol::AccountTokenUsageSummary;
use inkstack_app_server_protocol::AccountUpdatedNotification;
use inkstack_app_server_protocol::AddCreditsNudgeCreditType;
use inkstack_app_server_protocol::AddCreditsNudgeEmailStatus;
use inkstack_app_server_protocol::AdditionalContextEntry;
use inkstack_app_server_protocol::AdditionalContextKind;
use inkstack_app_server_protocol::AppListUpdatedNotification;
use inkstack_app_server_protocol::AppSummary;
use inkstack_app_server_protocol::AppTemplateSummary;
use inkstack_app_server_protocol::AppTemplateUnavailableReason;
use inkstack_app_server_protocol::AppsInstalledParams;
use inkstack_app_server_protocol::AppsInstalledResponse;
use inkstack_app_server_protocol::AppsListParams;
use inkstack_app_server_protocol::AppsListResponse;
use inkstack_app_server_protocol::AppsReadParams;
use inkstack_app_server_protocol::AppsReadResponse;
use inkstack_app_server_protocol::AskForApproval;
use inkstack_app_server_protocol::AuthMode;
use inkstack_app_server_protocol::CancelLoginAccountParams;
use inkstack_app_server_protocol::CancelLoginAccountResponse;
use inkstack_app_server_protocol::CancelLoginAccountStatus;
use inkstack_app_server_protocol::ClientInfo;
use inkstack_app_server_protocol::ClientRequest;
use inkstack_app_server_protocol::ClientResponsePayload;
use inkstack_app_server_protocol::InkStackErrorInfo;
use inkstack_app_server_protocol::CollaborationModeListParams;
use inkstack_app_server_protocol::CollaborationModeListResponse;
use inkstack_app_server_protocol::CommandExecParams;
use inkstack_app_server_protocol::CommandExecResizeParams;
use inkstack_app_server_protocol::CommandExecTerminateParams;
use inkstack_app_server_protocol::CommandExecWriteParams;
use inkstack_app_server_protocol::ConfigWarningNotification;
use inkstack_app_server_protocol::ConsumeAccountRateLimitResetCreditOutcome;
use inkstack_app_server_protocol::ConsumeAccountRateLimitResetCreditParams;
use inkstack_app_server_protocol::ConsumeAccountRateLimitResetCreditResponse;
use inkstack_app_server_protocol::ConversationGitInfo;
use inkstack_app_server_protocol::ConversationSummary;
use inkstack_app_server_protocol::DeprecationNoticeNotification;
use inkstack_app_server_protocol::DynamicToolFunctionSpec;
use inkstack_app_server_protocol::DynamicToolNamespaceTool;
use inkstack_app_server_protocol::DynamicToolSpec;
use inkstack_app_server_protocol::EnvironmentAddParams;
use inkstack_app_server_protocol::EnvironmentAddResponse;
use inkstack_app_server_protocol::EnvironmentInfoParams;
use inkstack_app_server_protocol::EnvironmentInfoResponse;
use inkstack_app_server_protocol::EnvironmentShellInfo;
use inkstack_app_server_protocol::EnvironmentStatusKind;
use inkstack_app_server_protocol::EnvironmentStatusParams;
use inkstack_app_server_protocol::EnvironmentStatusResponse;
use inkstack_app_server_protocol::ExperimentalFeature as ApiExperimentalFeature;
use inkstack_app_server_protocol::ExperimentalFeatureListParams;
use inkstack_app_server_protocol::ExperimentalFeatureListResponse;
use inkstack_app_server_protocol::ExperimentalFeatureStage as ApiExperimentalFeatureStage;
use inkstack_app_server_protocol::FeedbackUploadParams;
use inkstack_app_server_protocol::FeedbackUploadResponse;
use inkstack_app_server_protocol::GetAccountParams;
use inkstack_app_server_protocol::GetAccountRateLimitsResponse;
use inkstack_app_server_protocol::GetAccountResponse;
use inkstack_app_server_protocol::GetAccountTokenUsageParams;
use inkstack_app_server_protocol::GetAccountTokenUsageResponse;
use inkstack_app_server_protocol::GetAuthStatusParams;
use inkstack_app_server_protocol::GetAuthStatusResponse;
use inkstack_app_server_protocol::GetConversationSummaryParams;
use inkstack_app_server_protocol::GetConversationSummaryResponse;
use inkstack_app_server_protocol::GetWorkspaceMessagesResponse;
use inkstack_app_server_protocol::GitDiffToRemoteParams;
use inkstack_app_server_protocol::GitDiffToRemoteResponse;
use inkstack_app_server_protocol::GitInfo as ApiGitInfo;
use inkstack_app_server_protocol::HookHandlerMetadata;
use inkstack_app_server_protocol::HookMetadata;
use inkstack_app_server_protocol::HooksListParams;
use inkstack_app_server_protocol::HooksListResponse;
use inkstack_app_server_protocol::InitializeParams;
use inkstack_app_server_protocol::InitializeResponse;
use inkstack_app_server_protocol::InstalledApp;
use inkstack_app_server_protocol::JSONRPCErrorError;
use inkstack_app_server_protocol::ListMcpServerStatusParams;
use inkstack_app_server_protocol::ListMcpServerStatusResponse;
use inkstack_app_server_protocol::LoginAccountParams;
use inkstack_app_server_protocol::LoginAccountResponse;
use inkstack_app_server_protocol::LoginApiKeyParams;
use inkstack_app_server_protocol::LoginAppBrand;
use inkstack_app_server_protocol::LogoutAccountResponse;
use inkstack_app_server_protocol::MarketplaceAddParams;
use inkstack_app_server_protocol::MarketplaceAddResponse;
use inkstack_app_server_protocol::MarketplaceInterface;
use inkstack_app_server_protocol::MarketplaceRemoveParams;
use inkstack_app_server_protocol::MarketplaceRemoveResponse;
use inkstack_app_server_protocol::MarketplaceUpgradeErrorInfo;
use inkstack_app_server_protocol::MarketplaceUpgradeParams;
use inkstack_app_server_protocol::MarketplaceUpgradeResponse;
use inkstack_app_server_protocol::McpResourceReadParams;
use inkstack_app_server_protocol::McpResourceReadResponse;
use inkstack_app_server_protocol::McpServerOauthClientRegistration;
use inkstack_app_server_protocol::McpServerOauthLoginCompletedNotification;
use inkstack_app_server_protocol::McpServerOauthLoginParams;
use inkstack_app_server_protocol::McpServerOauthLoginResponse;
use inkstack_app_server_protocol::McpServerRefreshResponse;
use inkstack_app_server_protocol::McpServerStatus;
use inkstack_app_server_protocol::McpServerStatusDetail;
use inkstack_app_server_protocol::McpServerToolCallParams;
use inkstack_app_server_protocol::McpServerToolCallResponse;
use inkstack_app_server_protocol::MemoryResetResponse;
use inkstack_app_server_protocol::MockExperimentalMethodParams;
use inkstack_app_server_protocol::MockExperimentalMethodResponse;
use inkstack_app_server_protocol::ModelListParams;
use inkstack_app_server_protocol::ModelListResponse;
use inkstack_app_server_protocol::PermissionProfileListParams;
use inkstack_app_server_protocol::PermissionProfileListResponse;
use inkstack_app_server_protocol::PermissionProfileSummary;
use inkstack_app_server_protocol::PluginDetail;
use inkstack_app_server_protocol::PluginInstallParams;
use inkstack_app_server_protocol::PluginInstallResponse;
use inkstack_app_server_protocol::PluginInstalledParams;
use inkstack_app_server_protocol::PluginInstalledResponse;
use inkstack_app_server_protocol::PluginInterface;
use inkstack_app_server_protocol::PluginListMarketplaceKind;
use inkstack_app_server_protocol::PluginListParams;
use inkstack_app_server_protocol::PluginListResponse;
use inkstack_app_server_protocol::PluginMarketplaceEntry;
use inkstack_app_server_protocol::PluginReadParams;
use inkstack_app_server_protocol::PluginReadResponse;
use inkstack_app_server_protocol::PluginShareCheckoutParams;
use inkstack_app_server_protocol::PluginShareCheckoutResponse;
use inkstack_app_server_protocol::PluginShareContext;
use inkstack_app_server_protocol::PluginShareDeleteParams;
use inkstack_app_server_protocol::PluginShareDeleteResponse;
use inkstack_app_server_protocol::PluginShareDiscoverability;
use inkstack_app_server_protocol::PluginShareListItem;
use inkstack_app_server_protocol::PluginShareListParams;
use inkstack_app_server_protocol::PluginShareListResponse;
use inkstack_app_server_protocol::PluginSharePrincipal;
use inkstack_app_server_protocol::PluginSharePrincipalType;
use inkstack_app_server_protocol::PluginShareSaveParams;
use inkstack_app_server_protocol::PluginShareSaveResponse;
use inkstack_app_server_protocol::PluginShareTarget;
use inkstack_app_server_protocol::PluginShareUpdateDiscoverability;
use inkstack_app_server_protocol::PluginShareUpdateTargetsParams;
use inkstack_app_server_protocol::PluginShareUpdateTargetsResponse;
use inkstack_app_server_protocol::PluginSkillReadParams;
use inkstack_app_server_protocol::PluginSkillReadResponse;
use inkstack_app_server_protocol::PluginSource;
use inkstack_app_server_protocol::PluginSummary;
use inkstack_app_server_protocol::PluginUninstallParams;
use inkstack_app_server_protocol::PluginUninstallResponse;
use inkstack_app_server_protocol::RateLimitResetCredit;
use inkstack_app_server_protocol::RateLimitResetCreditStatus;
use inkstack_app_server_protocol::RateLimitResetCreditsSummary;
use inkstack_app_server_protocol::RateLimitResetType;
use inkstack_app_server_protocol::RequestId;
use inkstack_app_server_protocol::ReviewDelivery as ApiReviewDelivery;
use inkstack_app_server_protocol::ReviewStartParams;
use inkstack_app_server_protocol::ReviewStartResponse;
use inkstack_app_server_protocol::ReviewTarget as ApiReviewTarget;
use inkstack_app_server_protocol::SandboxMode;
use inkstack_app_server_protocol::SendAddCreditsNudgeEmailParams;
use inkstack_app_server_protocol::SendAddCreditsNudgeEmailResponse;
use inkstack_app_server_protocol::ServerNotification;
use inkstack_app_server_protocol::ServerRequestResolvedNotification;
use inkstack_app_server_protocol::SkillSummary;
use inkstack_app_server_protocol::SkillsConfigWriteParams;
use inkstack_app_server_protocol::SkillsConfigWriteResponse;
use inkstack_app_server_protocol::SkillsExtraRootsSetParams;
use inkstack_app_server_protocol::SkillsExtraRootsSetResponse;
use inkstack_app_server_protocol::SkillsListParams;
use inkstack_app_server_protocol::SkillsListResponse;
use inkstack_app_server_protocol::SortDirection;
use inkstack_app_server_protocol::Thread;
use inkstack_app_server_protocol::ThreadApproveGuardianDeniedActionParams;
use inkstack_app_server_protocol::ThreadApproveGuardianDeniedActionResponse;
use inkstack_app_server_protocol::ThreadArchiveParams;
use inkstack_app_server_protocol::ThreadArchiveResponse;
use inkstack_app_server_protocol::ThreadArchivedNotification;
use inkstack_app_server_protocol::ThreadBackgroundTerminal;
use inkstack_app_server_protocol::ThreadBackgroundTerminalsCleanParams;
use inkstack_app_server_protocol::ThreadBackgroundTerminalsCleanResponse;
use inkstack_app_server_protocol::ThreadBackgroundTerminalsListParams;
use inkstack_app_server_protocol::ThreadBackgroundTerminalsListResponse;
use inkstack_app_server_protocol::ThreadBackgroundTerminalsTerminateParams;
use inkstack_app_server_protocol::ThreadBackgroundTerminalsTerminateResponse;
use inkstack_app_server_protocol::ThreadClosedNotification;
use inkstack_app_server_protocol::ThreadCompactStartParams;
use inkstack_app_server_protocol::ThreadCompactStartResponse;
use inkstack_app_server_protocol::ThreadDecrementElicitationParams;
use inkstack_app_server_protocol::ThreadDecrementElicitationResponse;
use inkstack_app_server_protocol::ThreadDeleteParams;
use inkstack_app_server_protocol::ThreadDeleteResponse;
use inkstack_app_server_protocol::ThreadDeletedNotification;
use inkstack_app_server_protocol::ThreadForkParams;
use inkstack_app_server_protocol::ThreadForkResponse;
use inkstack_app_server_protocol::ThreadGoal;
use inkstack_app_server_protocol::ThreadGoalClearParams;
use inkstack_app_server_protocol::ThreadGoalClearResponse;
use inkstack_app_server_protocol::ThreadGoalClearedNotification;
use inkstack_app_server_protocol::ThreadGoalGetParams;
use inkstack_app_server_protocol::ThreadGoalGetResponse;
use inkstack_app_server_protocol::ThreadGoalSetParams;
use inkstack_app_server_protocol::ThreadGoalSetResponse;
use inkstack_app_server_protocol::ThreadGoalStatus;
use inkstack_app_server_protocol::ThreadGoalUpdatedNotification;
use inkstack_app_server_protocol::ThreadHistoryBuilder;
#[cfg(test)]
use inkstack_app_server_protocol::ThreadHistoryMode;
use inkstack_app_server_protocol::ThreadIncrementElicitationParams;
use inkstack_app_server_protocol::ThreadIncrementElicitationResponse;
use inkstack_app_server_protocol::ThreadInjectItemsParams;
use inkstack_app_server_protocol::ThreadInjectItemsResponse;
use inkstack_app_server_protocol::ThreadItem;
use inkstack_app_server_protocol::ThreadItemEntry;
use inkstack_app_server_protocol::ThreadItemsListParams;
use inkstack_app_server_protocol::ThreadItemsListResponse;
use inkstack_app_server_protocol::ThreadItemsReadParams;
use inkstack_app_server_protocol::ThreadItemsReadResponse;
use inkstack_app_server_protocol::ThreadListCwdFilter;
use inkstack_app_server_protocol::ThreadListParams;
use inkstack_app_server_protocol::ThreadListResponse;
use inkstack_app_server_protocol::ThreadLoadedListParams;
use inkstack_app_server_protocol::ThreadLoadedListResponse;
use inkstack_app_server_protocol::ThreadMemoryModeSetParams;
use inkstack_app_server_protocol::ThreadMemoryModeSetResponse;
use inkstack_app_server_protocol::ThreadMetadataGitInfoUpdateParams;
use inkstack_app_server_protocol::ThreadMetadataUpdateParams;
use inkstack_app_server_protocol::ThreadMetadataUpdateResponse;
use inkstack_app_server_protocol::ThreadNameUpdatedNotification;
use inkstack_app_server_protocol::ThreadProjectUpdatedNotification;
use inkstack_app_server_protocol::ThreadReadParams;
use inkstack_app_server_protocol::ThreadReadResponse;
use inkstack_app_server_protocol::ThreadRealtimeAppendAudioParams;
use inkstack_app_server_protocol::ThreadRealtimeAppendAudioResponse;
use inkstack_app_server_protocol::ThreadRealtimeAppendSpeechParams;
use inkstack_app_server_protocol::ThreadRealtimeAppendSpeechResponse;
use inkstack_app_server_protocol::ThreadRealtimeAppendTextParams;
use inkstack_app_server_protocol::ThreadRealtimeAppendTextResponse;
use inkstack_app_server_protocol::ThreadRealtimeListVoicesResponse;
use inkstack_app_server_protocol::ThreadRealtimeStartParams;
use inkstack_app_server_protocol::ThreadRealtimeStartResponse;
use inkstack_app_server_protocol::ThreadRealtimeStartTransport;
use inkstack_app_server_protocol::ThreadRealtimeStopParams;
use inkstack_app_server_protocol::ThreadRealtimeStopResponse;
use inkstack_app_server_protocol::ThreadResumeInitialTurnsPageParams;
use inkstack_app_server_protocol::ThreadResumeParams;
use inkstack_app_server_protocol::ThreadResumeResponse;
use inkstack_app_server_protocol::ThreadSearchOccurrence;
use inkstack_app_server_protocol::ThreadSearchOccurrencesParams;
use inkstack_app_server_protocol::ThreadSearchOccurrencesResponse;
use inkstack_app_server_protocol::ThreadSearchParams;
use inkstack_app_server_protocol::ThreadSearchResponse;
use inkstack_app_server_protocol::ThreadSearchResult;
use inkstack_app_server_protocol::ThreadSearchSortKey;
use inkstack_app_server_protocol::ThreadSearchTextRange;
use inkstack_app_server_protocol::ThreadSetNameParams;
use inkstack_app_server_protocol::ThreadSetNameResponse;
use inkstack_app_server_protocol::ThreadSettings;
use inkstack_app_server_protocol::ThreadSettingsUpdateParams;
use inkstack_app_server_protocol::ThreadSettingsUpdateResponse;
use inkstack_app_server_protocol::ThreadShellCommandParams;
use inkstack_app_server_protocol::ThreadShellCommandResponse;
use inkstack_app_server_protocol::ThreadSortKey;
use inkstack_app_server_protocol::ThreadSourceKind;
use inkstack_app_server_protocol::ThreadStartParams;
use inkstack_app_server_protocol::ThreadStartResponse;
use inkstack_app_server_protocol::ThreadStartedNotification;
use inkstack_app_server_protocol::ThreadStatus;
use inkstack_app_server_protocol::ThreadTimelineListParams;
use inkstack_app_server_protocol::ThreadTimelineListResponse;
use inkstack_app_server_protocol::ThreadTurnsListParams;
use inkstack_app_server_protocol::ThreadTurnsListResponse;
use inkstack_app_server_protocol::ThreadUnarchiveParams;
use inkstack_app_server_protocol::ThreadUnarchiveResponse;
use inkstack_app_server_protocol::ThreadUnarchivedNotification;
use inkstack_app_server_protocol::ThreadUnsubscribeParams;
use inkstack_app_server_protocol::ThreadUnsubscribeResponse;
use inkstack_app_server_protocol::ThreadUnsubscribeStatus;
use inkstack_app_server_protocol::Turn;
use inkstack_app_server_protocol::TurnEnvironmentParams;
use inkstack_app_server_protocol::TurnError;
use inkstack_app_server_protocol::TurnInterruptParams;
use inkstack_app_server_protocol::TurnInterruptResponse;
use inkstack_app_server_protocol::TurnItemsView;
use inkstack_app_server_protocol::TurnSettingsUpdateParams;
use inkstack_app_server_protocol::TurnSettingsUpdateResponse;
use inkstack_app_server_protocol::TurnSettingsUpdateStatus;
use inkstack_app_server_protocol::TurnStartParams;
use inkstack_app_server_protocol::TurnStartResponse;
use inkstack_app_server_protocol::TurnStatus;
use inkstack_app_server_protocol::TurnSteerParams;
use inkstack_app_server_protocol::TurnSteerResponse;
use inkstack_app_server_protocol::UserInput as V2UserInput;
use inkstack_app_server_protocol::WindowsSandboxReadiness;
use inkstack_app_server_protocol::WindowsSandboxReadinessResponse;
use inkstack_app_server_protocol::WindowsSandboxSetupCompletedNotification;
use inkstack_app_server_protocol::WindowsSandboxSetupMode;
use inkstack_app_server_protocol::WindowsSandboxSetupStartParams;
use inkstack_app_server_protocol::WindowsSandboxSetupStartResponse;
use inkstack_app_server_protocol::WorkspaceMessage;
use inkstack_app_server_protocol::WorkspaceMessageType;
use inkstack_arg0::Arg0DispatchPaths;
use inkstack_backend_client::AddCreditsNudgeCreditType as BackendAddCreditsNudgeCreditType;
use inkstack_backend_client::Client as BackendClient;
use inkstack_backend_client::InkStackWorkspaceMessage as BackendWorkspaceMessage;
use inkstack_backend_client::InkStackWorkspaceMessageType as BackendWorkspaceMessageType;
use inkstack_backend_client::InkStackWorkspaceMessagesResponse as BackendWorkspaceMessagesResponse;
use inkstack_backend_client::ConsumeRateLimitResetCreditCode as BackendConsumeRateLimitResetCreditCode;
use inkstack_backend_client::RateLimitResetCreditDetails as BackendRateLimitResetCreditDetails;
use inkstack_backend_client::RateLimitResetCreditsDetails as BackendRateLimitResetCreditsDetails;
use inkstack_backend_client::RequestError as BackendRequestError;
use inkstack_backend_client::TokenUsageProfile;
use inkstack_chatgpt::connectors;
use inkstack_config::CloudConfigBundleLoadError;
use inkstack_config::CloudConfigBundleLoadErrorCode;
use inkstack_config::ConfigLayerStack;
use inkstack_config::loader::project_trust_key;
use inkstack_config::types::McpServerTransportConfig;
use inkstack_connectors::AppInfo;
use inkstack_core::InkStackThread;
use inkstack_core::InkStackThreadSettingsOverrides;
use inkstack_core::ForkSnapshot;
use inkstack_core::McpManager;
use inkstack_core::NewThread;
use inkstack_core::NotSubmittedReason;
#[cfg(test)]
use inkstack_core::SessionMeta;
use inkstack_core::StartThreadOptions;
use inkstack_core::SteerSubmission;
use inkstack_core::ThreadConfigSnapshot;
use inkstack_core::ThreadManager;
use inkstack_core::TurnInput;
use inkstack_core::TurnInputRequest;
use inkstack_core::TurnInputSubmission;
use inkstack_core::TurnStartOptions;
use inkstack_core::config::Config;
use inkstack_core::config::ConfigOverrides;
use inkstack_core::config::NetworkProxyAuditMetadata;
use inkstack_core::config::edit::ConfigEdit;
use inkstack_core::config::edit::ConfigEditsBuilder;
use inkstack_core::connectors::AccessibleConnectorsStatus;
use inkstack_core::exec::ExecCapturePolicy;
use inkstack_core::exec::ExecExpiration;
use inkstack_core::exec::ExecParams;
use inkstack_core::exec_env::create_env;
use inkstack_core::path_utils;
#[cfg(test)]
use inkstack_core::read_head_for_summary;
use inkstack_core::sandboxing::SandboxPermissions;
use inkstack_core::truncate_rollout_after_turn_id;
use inkstack_core::truncate_rollout_before_turn_id;
use inkstack_core::validate_environment_ids_and_cwds;
use inkstack_core::windows_sandbox::WindowsSandboxLevelExt;
use inkstack_core::windows_sandbox::WindowsSandboxSetupMode as CoreWindowsSandboxSetupMode;
use inkstack_core::windows_sandbox::WindowsSandboxSetupRequest;
use inkstack_core::windows_sandbox::sandbox_setup_is_complete;
use inkstack_core_plugins::PluginInstallError as CorePluginInstallError;
use inkstack_core_plugins::PluginInstallRequest;
use inkstack_core_plugins::PluginReadRequest;
use inkstack_core_plugins::PluginUninstallError as CorePluginUninstallError;
use inkstack_core_plugins::PluginsManager;
use inkstack_core_plugins::loader::load_plugin_apps;
use inkstack_core_plugins::manifest::PluginManifestInterface;
use inkstack_core_plugins::marketplace::MarketplaceError;
use inkstack_core_plugins::marketplace::MarketplacePluginSource;
use inkstack_core_plugins::marketplace_add::MarketplaceAddError;
use inkstack_core_plugins::marketplace_add::MarketplaceAddRequest;
use inkstack_core_plugins::marketplace_add::add_marketplace as add_marketplace_to_inkstack_home;
use inkstack_core_plugins::marketplace_remove::MarketplaceRemoveError;
use inkstack_core_plugins::marketplace_remove::MarketplaceRemoveRequest as CoreMarketplaceRemoveRequest;
use inkstack_core_plugins::marketplace_remove::remove_marketplace;
use inkstack_core_plugins::remote::RemoteMarketplace;
use inkstack_core_plugins::remote::RemoteMarketplaceSource;
use inkstack_core_plugins::remote::RemotePluginCatalogError;
use inkstack_core_plugins::remote::RemotePluginDetail as RemoteCatalogPluginDetail;
use inkstack_core_plugins::remote::RemotePluginServiceConfig;
use inkstack_core_plugins::remote::RemotePluginShareContext as RemoteCatalogPluginShareContext;
use inkstack_core_plugins::remote::RemotePluginShareSummary as RemoteCatalogPluginShareSummary;
use inkstack_core_plugins::remote::RemotePluginSummary as RemoteCatalogPluginSummary;
use inkstack_exec_server::EnvironmentManager;
use inkstack_exec_server::EnvironmentObservedStatus;
use inkstack_exec_server::LOCAL_ENVIRONMENT_ID;
use inkstack_exec_server::LOCAL_FS;
use inkstack_features::FEATURES;
use inkstack_features::Feature;
use inkstack_features::Stage;
use inkstack_feedback::InkStackFeedback;
use inkstack_feedback::FeedbackAttachmentPath;
use inkstack_feedback::FeedbackUploadOptions;
use inkstack_git_utils::git_diff_to_remote;
use inkstack_git_utils::resolve_root_git_project_for_trust;
use inkstack_login::AuthManager;
use inkstack_login::INKSTACK_OPEN_APP_URL;
use inkstack_login::InkStackAuth;
use inkstack_login::LoginSuccessPage;
use inkstack_login::LoginSuccessPageBrand;
use inkstack_login::ServerOptions as LoginServerOptions;
use inkstack_login::ShutdownHandle;
use inkstack_login::complete_device_code_login;
use inkstack_login::login_with_api_key;
use inkstack_login::login_with_bedrock_api_key;
use inkstack_login::oauth_client_id;
use inkstack_login::request_device_code;
use inkstack_login::run_login_server;
use inkstack_mcp::McpRuntimeContext;
use inkstack_mcp::McpServerStatusSnapshot;
use inkstack_mcp::McpSnapshotDetail;
use inkstack_mcp::collect_mcp_server_status_snapshot_with_detail;
use inkstack_mcp::discover_supported_scopes;
use inkstack_mcp::read_mcp_resource as read_mcp_resource_without_thread;
use inkstack_mcp::resolve_oauth_scopes;
use inkstack_memories_write::clear_memory_roots_contents;
use inkstack_model_provider::create_model_provider;
use inkstack_models_manager::collaboration_mode_presets::builtin_collaboration_mode_presets;
use inkstack_protocol::ThreadId;
use inkstack_protocol::config_types::CollaborationMode;
use inkstack_protocol::config_types::ForcedLoginMethod;
use inkstack_protocol::config_types::Personality;
use inkstack_protocol::config_types::ReasoningSummary;
use inkstack_protocol::config_types::TrustLevel;
use inkstack_protocol::config_types::WindowsSandboxLevel;
use inkstack_protocol::error::InkStackErr;
use inkstack_protocol::error::Result as InkStackResult;
#[cfg(test)]
use inkstack_protocol::items::TurnItem;
use inkstack_protocol::models::ResponseItem;
use inkstack_protocol::openai_models::ReasoningEffort;
use inkstack_protocol::protocol::AgentStatus;
use inkstack_protocol::protocol::ConversationAudioParams;
use inkstack_protocol::protocol::ConversationSpeechParams;
use inkstack_protocol::protocol::ConversationStartParams;
use inkstack_protocol::protocol::ConversationStartTransport;
use inkstack_protocol::protocol::ConversationTextParams;
use inkstack_protocol::protocol::EnvironmentConfigState;
use inkstack_protocol::protocol::EventMsg;
#[cfg(test)]
use inkstack_protocol::protocol::GitInfo as CoreGitInfo;
use inkstack_protocol::protocol::McpAuthStatus as CoreMcpAuthStatus;
use inkstack_protocol::protocol::Op;
use inkstack_protocol::protocol::RealtimeVoicesList;
use inkstack_protocol::protocol::ReviewDelivery as CoreReviewDelivery;
use inkstack_protocol::protocol::ReviewRequest;
use inkstack_protocol::protocol::ReviewTarget as CoreReviewTarget;
use inkstack_protocol::protocol::SessionConfiguredEvent;
#[cfg(test)]
use inkstack_protocol::protocol::SessionMetaLine;
use inkstack_protocol::protocol::TurnEnvironmentRequest;
use inkstack_protocol::protocol::W3cTraceContext;
use inkstack_protocol::protocol::strip_user_message_prefix;
use inkstack_protocol::user_input::MAX_USER_INPUT_TEXT_CHARS;
use inkstack_protocol::user_input::UserInput as CoreInputItem;
use inkstack_rmcp_client::McpOAuthClientRegistration;
use inkstack_rmcp_client::StreamableHttpRedirectMode;
use inkstack_rmcp_client::perform_oauth_login_return_url;
use inkstack_rollout::InitialHistory;
use inkstack_rollout::ResumedHistory;
use inkstack_rollout::RolloutItem;
use inkstack_rollout::persisted_rollout_item;
use inkstack_rollout::state_db::StateDbHandle;
use inkstack_rollout::state_db::reconcile_rollout;
use inkstack_state::ThreadMetadata;
use inkstack_state::log_db::LogDbLayer;
use inkstack_thread_store::ArchiveThreadParams as StoreArchiveThreadParams;
use inkstack_thread_store::ArchiveThreadsParams as StoreArchiveThreadsParams;
use inkstack_thread_store::ClearableField as StoreClearableField;
use inkstack_thread_store::DeleteThreadsParams as StoreDeleteThreadsParams;
use inkstack_thread_store::GitInfoPatch as StoreGitInfoPatch;
use inkstack_thread_store::ItemSortKey as StoreItemSortKey;
use inkstack_thread_store::ListItemsParams as StoreListItemsParams;
use inkstack_thread_store::ListItemsPosition as StoreListItemsPosition;
use inkstack_thread_store::ListThreadsParams as StoreListThreadsParams;
use inkstack_thread_store::ListTimelineParams as StoreListTimelineParams;
use inkstack_thread_store::ListTurnsParams as StoreListTurnsParams;
use inkstack_thread_store::LoadThreadHistoryParams as StoreLoadThreadHistoryParams;
use inkstack_thread_store::LocalThreadStore;
use inkstack_thread_store::ReadThreadByRolloutPathParams as StoreReadThreadByRolloutPathParams;
use inkstack_thread_store::ReadThreadParams as StoreReadThreadParams;
use inkstack_thread_store::SearchThreadOccurrencesParams as StoreSearchThreadOccurrencesParams;
use inkstack_thread_store::SearchThreadsParams as StoreSearchThreadsParams;
use inkstack_thread_store::SortDirection as StoreSortDirection;
use inkstack_thread_store::StoredThread;
use inkstack_thread_store::StoredTurn;
use inkstack_thread_store::StoredTurnItemsView;
use inkstack_thread_store::StoredTurnStatus;
use inkstack_thread_store::ThreadMetadataPatch as StoreThreadMetadataPatch;
use inkstack_thread_store::ThreadRelationFilter as StoreThreadRelationFilter;
use inkstack_thread_store::ThreadSortKey as StoreThreadSortKey;
use inkstack_thread_store::ThreadStore;
use inkstack_thread_store::ThreadStoreError;
use inkstack_utils_absolute_path::AbsolutePathBuf;
use inkstack_utils_pty::DEFAULT_OUTPUT_BYTES_CAP;
use std::collections::BTreeMap;
use std::collections::HashMap;
use std::collections::HashSet;
use std::io::Error as IoError;
use std::path::Path;
use std::path::PathBuf;
use std::result::Result;
use std::sync::Arc;
use std::time::Duration;
use std::time::Instant;
use tokio::sync::Mutex;
use tokio::sync::Semaphore;
use tokio::sync::SemaphorePermit;
use tokio::sync::broadcast;
use tokio::sync::oneshot;
use tokio::sync::watch;
use tokio_util::sync::CancellationToken;
use tokio_util::sync::DropGuard;
use tokio_util::task::TaskTracker;
use toml::Value as TomlValue;
use tracing::Instrument;
use tracing::error;
use tracing::info;
use tracing::warn;
use uuid::Uuid;

#[cfg(test)]
use inkstack_app_server_protocol::ServerRequest;

mod account_processor;
mod apps_processor;
mod bedrock_auth;
mod catalog_processor;
mod command_exec_processor;
mod config_processor;
#[cfg(test)]
#[path = "request_processors/config_reload_tests.rs"]
mod config_reload_tests;
mod diagnostics;
mod environment_processor;
mod feedback_doctor_report;
mod feedback_processor;
mod feedback_rollout_history;
mod feedback_thread_index;
mod fs_processor;
mod git_processor;
mod initialize_processor;
mod marketplace_processor;
mod mcp_event_stream;
mod mcp_processor;
mod memory_status;
mod persisted_resume_settings;
mod plugins;
mod process_exec_processor;
mod projects;
mod remote_control_processor;
mod rollout;
mod search;
mod thread_attachments;
mod thread_enrichment;
mod thread_fork_goal;
mod thread_input;
mod thread_processor;
mod thread_queue_processor;
mod thread_read_state;
mod thread_sections;
mod token_usage_replay;
mod turn_processor;
mod windows_sandbox_processor;

pub(crate) use account_processor::AccountRequestProcessor;
pub(crate) use apps_processor::AppsRequestProcessor;
pub(crate) use catalog_processor::CatalogRequestProcessor;
pub(crate) use command_exec_processor::CommandExecRequestProcessor;
pub(crate) use config_processor::ConfigRequestProcessor;
pub(crate) use diagnostics::read_server_diagnostics;
pub(crate) use environment_processor::EnvironmentRequestProcessor;
pub(crate) use feedback_processor::FeedbackRequestProcessor;
pub(crate) use fs_processor::FsRequestProcessor;
pub(crate) use git_processor::GitRequestProcessor;
pub(crate) use initialize_processor::InitializeRequestProcessor;
pub(crate) use marketplace_processor::MarketplaceRequestProcessor;
pub(crate) use mcp_event_stream::McpEventStreamReady;
pub(crate) use mcp_event_stream::McpEventStreams;
pub(crate) use mcp_processor::McpRequestProcessor;
pub(crate) use plugins::PluginRequestProcessor;
pub(crate) use process_exec_processor::ProcessExecRequestProcessor;
pub(crate) use projects::ProjectRequestProcessor;
pub(crate) use remote_control_processor::RemoteControlRequestProcessor;
pub(crate) use search::SearchRequestProcessor;
pub(crate) use thread_goal_processor::ThreadGoalRequestProcessor;
pub(crate) use thread_processor::ThreadRequestProcessor;
pub(crate) use thread_processor::ThreadResumeTarget;
pub(crate) use thread_queue_processor::ThreadQueueRequestProcessor;
pub(crate) use turn_processor::TurnRequestProcessor;
pub(crate) use windows_sandbox_processor::WindowsSandboxRequestProcessor;

use crate::error_code::internal_error;
use crate::error_code::invalid_request;
use crate::filters::compute_source_filters;
use crate::filters::source_kind_matches;
use crate::thread_state::ConnectionCapabilities;
use crate::thread_state::PendingThreadUnloads;
use crate::thread_state::ThreadListenerCommand;
use crate::thread_state::ThreadState;
use crate::thread_state::ThreadStateManager;
use token_usage_replay::restored_token_usage_turn_id;
use token_usage_replay::send_thread_token_usage_update_to_connection;

pub(crate) fn apply_live_thread_settings(
    thread: &mut Thread,
    config_snapshot: &ThreadConfigSnapshot,
) {
    thread.model = Some(config_snapshot.model.clone());
    thread.reasoning_effort = config_snapshot.reasoning_effort.clone();
    thread.environments = Some(
        config_snapshot
            .environment_selections()
            .iter()
            .map(Into::into)
            .collect(),
    );
}

fn resolve_request_cwd(cwd: Option<PathBuf>) -> Result<Option<AbsolutePathBuf>, JSONRPCErrorError> {
    cwd.map(|cwd| {
        AbsolutePathBuf::relative_to_current_dir(path_utils::normalize_for_native_workdir(cwd))
            .map_err(|err| invalid_request(format!("invalid cwd: {err}")))
    })
    .transpose()
}

fn resolve_turn_environment_requests(
    thread_manager: &ThreadManager,
    environments: Option<Vec<TurnEnvironmentParams>>,
) -> Result<Option<Vec<TurnEnvironmentRequest>>, JSONRPCErrorError> {
    let Some(environments) = environments else {
        return Ok(None);
    };
    let mut requests = Vec::with_capacity(environments.len());
    for environment in environments {
        let environment_id = environment.environment_id;
        let cwd = environment
            .cwd
            .to_inferred_path_uri()
            .ok_or_else(|| {
                invalid_request(format!(
                    "invalid cwd for environment `{environment_id}`: path `{}` does not use absolute POSIX or Windows path syntax",
                    environment.cwd
                ))
            })?;
        let workspace_roots = environment
            .runtime_workspace_roots
            .map(|roots| {
                let mut resolved_roots = Vec::new();
                for root in roots {
                    let root = root.to_inferred_path_uri().ok_or_else(|| {
                        invalid_request(format!(
                            "invalid runtime workspace root for environment `{environment_id}`: path `{root}` does not use absolute POSIX or Windows path syntax"
                        ))
                    })?;
                    if !resolved_roots.contains(&root) {
                        resolved_roots.push(root);
                    }
                }
                Ok::<_, JSONRPCErrorError>(resolved_roots)
            })
            .transpose()?
            .unwrap_or_else(|| vec![cwd.clone()]);
        requests.push(TurnEnvironmentRequest {
            environment_id,
            cwd,
            workspace_roots,
            config: EnvironmentConfigState::FromThread,
        });
    }
    validate_environment_ids_and_cwds(
        &thread_manager.environment_manager(),
        requests
            .iter()
            .map(|request| (request.environment_id.as_str(), &request.cwd)),
    )
    .map_err(environment_selection_error)?;
    Ok(Some(requests))
}

fn resolve_runtime_workspace_roots(workspace_roots: Vec<AbsolutePathBuf>) -> Vec<AbsolutePathBuf> {
    let mut resolved_roots = Vec::new();
    for root in workspace_roots {
        if !resolved_roots.iter().any(|existing| existing == &root) {
            resolved_roots.push(root);
        }
    }
    resolved_roots
}

mod config_errors;
mod request_errors;
mod thread_delete;
mod thread_goal_processor;
mod thread_lifecycle;
mod thread_resume_redaction;
mod thread_summary;

use self::config_errors::*;
use self::request_errors::*;
use self::thread_goal_processor::api_thread_goal_from_state;
use self::thread_lifecycle::*;
use self::thread_resume_redaction::*;
use self::thread_summary::*;

pub(crate) use self::thread_lifecycle::populate_thread_turns_from_history;
pub(crate) use self::thread_processor::thread_from_stored_thread;
#[cfg(test)]
pub(crate) use self::thread_summary::read_summary_from_rollout;
#[cfg(test)]
pub(crate) use self::thread_summary::summary_to_thread;
pub(crate) use self::thread_summary::thread_settings_from_config_snapshot;

pub(crate) fn build_legacy_api_turns_from_rollout_items(items: &[RolloutItem]) -> Vec<Turn> {
    let mut builder = ThreadHistoryBuilder::new();
    for item in items {
        if let Some(item) =
            persisted_rollout_item(item, inkstack_protocol::protocol::ThreadHistoryMode::Legacy)
        {
            builder.handle_rollout_item(item.as_ref());
        }
    }
    builder.finish()
}
