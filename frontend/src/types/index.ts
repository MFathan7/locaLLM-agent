export interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: number;
}

export interface ModelCapabilities {
  files: boolean;
  webSearch: boolean;
  tools: boolean;
}

export interface ModelInfo {
  id: string;
  name: string;
  provider: LocaLLMConfig['provider'];
  capabilities: ModelCapabilities;
}

export interface SendOptions {
  files: File[];
  webSearch: boolean;
  tools: boolean;
}

export interface Workspace {
  name: string;
  description?: string;
  knowledgeCount?: number;
  skillsCount?: number;
}

export interface ChatSession {
  id: string;
  title: string;
  workspace: string;
  updatedAt: number;
  messages: Message[];
  folder?: string;
}

export interface LocaLLMConfig {
  systemPrompt: string;
  temperature: number;
  topP: number;
  maxTokens: number;
  contextLength: number;
  model: string;
  provider: 'ollama' | 'openai' | 'anthropic' | 'gemini';
  ollamaBaseUrl: string;
  dynamicRouting: boolean;
}
