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
  };
}

export interface ModelCapabilities {
  files: boolean;
  webSearch: boolean;
  tools: boolean;
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

