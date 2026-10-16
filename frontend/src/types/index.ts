export interface SourceItem {
  id: string;
  title: string;
  url: string;
  domain: string;
  snippet?: string;
  date?: string;
  favicon?: string;
}

export interface AttachedFile {
  name: string;
  size: number;
  type: string;
  url?: string; // base64 data url for images/preview
  content?: string; // text content for code/document files
}

export type ExecutionState =
  | 'idle'
  | 'routing'
  | 'thinking'
  | 'tool'
  | 'generating'
  | 'done'
  | 'error';

export interface StreamEvent {
  event:
    | 'routing'
    | 'thinking_start'
    | 'thinking_end'
    | 'tool_start'
    | 'tool_end'
    | 'response_start'
    | 'response_token'
    | 'done'
    | 'error';
  data?: any;
}

export interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system' | 'tool';
  content: string;
  timestamp: number;
  executionState?: ExecutionState;
  statusLabel?: string;
  sources?: SourceItem[];
  files?: AttachedFile[];
  options?: {
    files?: string[];
    webSearch?: boolean;
    tools?: boolean;
    thinking?: boolean;
  };
}

export interface ModelCapabilities {
  files: boolean;
  webSearch: boolean;
  tools: boolean;
  thinking?: boolean;
}

export interface ModelInfo {
  id: string;
  name: string;
  provider: string;
  platform?: string;
  capabilities: ModelCapabilities;
}

export interface SendOptions {
  files: File[];
  webSearch: boolean;
  tools: boolean;
  thinking?: boolean;
  sessionId?: string;
}

export interface WorkspaceSkill {
  id: string;
  name: string;
  description?: string;
  content: string;
  path?: string;
  enabled?: boolean;
}

export interface Workspace {
  name: string;
  description?: string;
  icon?: string;
  color?: string;
  custom_instructions?: string;
  auto_memory?: boolean;
  knowledgeCount?: number;
  skillsCount?: number;
  skills?: WorkspaceSkill[];
}

export interface WorkspaceMemory {
  workspace: string;
  auto_memory: boolean;
  facts: Record<string, string>;
}

export interface ChatSession {
  id: string;
  title: string;
  workspace: string;
  updatedAt: number;
  messages: Message[];
  folder?: string;
}

export interface CustomPlatformConfig {
  name: string;
  api_base: string;
  api_key?: string;
  default_model?: string;
}

export interface LocaLLMConfig {
  active_backend: string;
  ollama_host: string;
  ollama_model: string;
  custom_platforms: CustomPlatformConfig[];
  default_model: string;
  temperature: number;
  context_window: number;
  system_prompt: string;
  telegram_token?: string;
  telegram_allowed_users?: number[];
  whatsapp_enabled?: boolean;
  agent_auto_approve_commands?: boolean;
  agent_permission_policy: 'ask' | 'always_allow' | 'deny';
  agent_max_steps: number;
  active_workspace: string;
  search_provider: 'auto' | 'bing' | 'duckduckgo' | 'custom';
  search_api_url?: string;
  ui_theme?: string;
  server_enabled: boolean;
  server_host: string;
  server_port: number;
  server_api_key?: string;
  user_name?: string;

  // Compatibility aliases
  model?: string;
  provider?: string;
  contextLength?: number;
  maxTokens?: number;
  topP?: number;
  dynamicRouting?: boolean;
}

export interface SessionNotification {
  id: string;
  sessionId: string;
  sessionTitle: string;
  message: string;
}

export type PortSide = 'top' | 'bottom' | 'left' | 'right';
export type PortRole = 'main_in' | 'main_out' | 'sub_in' | 'sub_out';

export type ActivityCategory =
  | 'triggers'
  | 'orchestration'
  | 'specialists'
  | 'state_knowledge'
  | 'tools_plugins'
  | 'flow_control'
  | 'outputs';

export type WorkflowLane = 'ui' | 'agent' | 'policy' | 'tools' | 'evidence' | string;
export type SequenceColor = 'blue' | 'yellow' | 'red';

export interface WorkflowLaneConfig {
  id: string;
  num: string;
  label: string;
  description?: string;
  color?: SequenceColor;
  x?: number;
  y: number;
  width?: number;
  height: number;
  variant?: 'default' | 'exception';
}

export interface WorkflowNode {
  id: string;
  lane: WorkflowLane;
  category?: ActivityCategory;
  type: 'frontend' | 'backend' | 'security' | 'messagebus' | 'database' | 'cloud' | 'external';
  title: string;
  subtitle: string;
  tag?: string;
  x: number;
  y: number;
  status?: 'idle' | 'running' | 'success' | 'error';
  config: {
    workspace?: string;
    model?: string;
    directive?: string;
    tools?: string[];
    query?: string;
    condition?: string;
    command?: string;
    path?: string;
    endpoint?: string;
    timeout?: number;
    max_retries?: number;
    platform?: string;
    cron?: string;
    mode?: string;
    channel?: string;
    output_path?: string;
    [key: string]: any;
  };
  properties?: import('./workflowPropertySchema').NodeProperties;
}

export interface WorkflowEdge {
  id: string;
  from: string;
  to: string;
  fromSide?: PortSide;
  toSide?: PortSide;
  kind?: 'main' | 'sub' | 'conditional';
  conditionBranch?: 'true' | 'false' | 'loop' | 'done' | 'pass' | 'reject';
  label?: string;
  variant?: 'default' | 'emphasis' | 'security' | 'dashed';
}

export interface WorkflowNodePort {
  side: PortSide;
  role: PortRole;
  title: string;
  badgeLabel?: string;
  posClass: string;
}

export interface WorkflowStatePayload {
  objective: string;
  workspace: string;
  task_queue: string[];
  current_subtask?: string;
  findings: Array<{ topic: string; content: string; source?: string; timestamp?: string }>;
  artifacts: Array<{ path: string; type?: string; content?: string }>;
  modified_files: string[];
  test_results: Array<{ command: string; success: boolean; summary: string }>;
  verdict: { passed: boolean; score: number; feedback: string };
  retry_count: number;
  status: 'idle' | 'running' | 'success' | 'failed' | 'paused';
  context_variables: Record<string, any>;
  step_logs: Array<{ timestamp: string; agent: string; event_type: string; message: string }>;
}

export interface WorkflowDefinition {
  id: string;
  name: string;
  description?: string;
  isActive?: boolean;
  nodes: WorkflowNode[];
  edges: WorkflowEdge[];
  created_at?: string;
  updated_at?: string;
}

export interface WorkflowExecutionRecord {
  run_id: string;
  workflow_id: string;
  workflow_title?: string;
  trigger_source?: string;
  status: 'success' | 'failed' | 'running';
  started_at: string;
  ended_at?: string;
  duration_seconds: number;
  steps_executed: number;
  logs: Array<{
    timestamp: string;
    agent: string;
    event_type: string;
    message: string;
    node_id?: string;
  }>;
  artifacts?: Array<{ name?: string; path?: string; content?: string }>;
  state_summary?: Record<string, any>;
  error?: string;
}

export * from './workflowPropertySchema';

