import type { LocaLLMConfig, ChatSession, Workspace, ModelInfo, SendOptions } from '../types';

let mockConfig: LocaLLMConfig = {
  systemPrompt: 'You are a helpful AI assistant running locally via LocaLLM.',
  temperature: 0.7,
  topP: 0.9,
  maxTokens: 2048,
  contextLength: 4096,
  model: 'llama3',
  provider: 'ollama',
  ollamaBaseUrl: 'http://localhost:11434',
  dynamicRouting: false,
};

// Mock catalog. A real backend would derive capabilities from the provider/model metadata.
const mockModels: ModelInfo[] = [
  { id: 'llama3', name: 'Llama 3', provider: 'ollama', capabilities: { files: true, webSearch: false, tools: false } },
  { id: 'qwen2.5-coder', name: 'Qwen 2.5 Coder', provider: 'ollama', capabilities: { files: true, webSearch: false, tools: true } },
  { id: 'gpt-4o', name: 'GPT-4o', provider: 'openai', capabilities: { files: true, webSearch: true, tools: true } },
  { id: 'claude-sonnet', name: 'Claude Sonnet', provider: 'anthropic', capabilities: { files: true, webSearch: true, tools: true } },
  { id: 'gemini-pro', name: 'Gemini Pro', provider: 'gemini', capabilities: { files: true, webSearch: true, tools: false } }
];

let mockWorkspaces: Workspace[] = [
  { name: 'default', description: 'Default general-purpose workspace', knowledgeCount: 1, skillsCount: 3 },
  { name: 'coding-agent', description: 'Autonomous coding & software development', knowledgeCount: 2, skillsCount: 5 },
  { name: 'generate-plan', description: 'Strategic architecture & planning', knowledgeCount: 1, skillsCount: 2 },
  { name: 'web_pentest', description: 'Web security & penetration testing', knowledgeCount: 3, skillsCount: 4 }
];

let mockSessions: ChatSession[] = [
  { id: '1', title: 'Welcome to LocaLLM', workspace: 'default', updatedAt: Date.now() - 3600000, messages: [] },
  { id: '2', title: 'React + Vite Architecture', workspace: 'coding-agent', updatedAt: Date.now() - 7200000, messages: [] },
  { id: '3', title: 'Vulnerability Analysis Plan', workspace: 'web_pentest', updatedAt: Date.now() - 10800000, messages: [] }
];

export const api = {
  getWorkspaces: async (): Promise<Workspace[]> => {
    await new Promise(resolve => setTimeout(resolve, 100));
    return [...mockWorkspaces];
  },
  createWorkspace: async (name: string, description: string = ''): Promise<Workspace> => {
    await new Promise(resolve => setTimeout(resolve, 150));
    const cleanName = name.trim().toLowerCase().replace(/[^a-zA-Z0-9_\-]/g, '-');
    const existing = mockWorkspaces.find(w => w.name.toLowerCase() === cleanName);
    if (existing) return existing;
    const newWs: Workspace = { name: cleanName, description, knowledgeCount: 0, skillsCount: 0 };
    mockWorkspaces.push(newWs);
    return newWs;
  },
  getModels: async (): Promise<ModelInfo[]> => {
    await new Promise(resolve => setTimeout(resolve, 100));
    return [...mockModels];
  },
  getConfig: async (): Promise<LocaLLMConfig> => {
    await new Promise(resolve => setTimeout(resolve, 100));
    return { ...mockConfig };
  },
  saveConfig: async (config: LocaLLMConfig): Promise<void> => {
    await new Promise(resolve => setTimeout(resolve, 100));
    mockConfig = { ...config };
  },
  getSessions: async (workspace?: string): Promise<ChatSession[]> => {
    await new Promise(resolve => setTimeout(resolve, 100));
    const filtered = workspace 
      ? mockSessions.filter(s => s.workspace === workspace)
      : mockSessions;
    return [...filtered].sort((a, b) => b.updatedAt - a.updatedAt);
  },
  saveSession: async (session: ChatSession): Promise<void> => {
    await new Promise(resolve => setTimeout(resolve, 100));
    const index = mockSessions.findIndex(s => s.id === session.id);
    if (index >= 0) {
      mockSessions[index] = session;
    } else {
      mockSessions.push(session);
    }
  },
  deleteSession: async (id: string): Promise<void> => {
    await new Promise(resolve => setTimeout(resolve, 100));
    mockSessions = mockSessions.filter(s => s.id !== id);
  },
  sendMessage: async (message: string, config: LocaLLMConfig, options: SendOptions, onChunk: (chunk: string) => void): Promise<string> => {
    return new Promise(resolve => {
      const extras = [
        options.files.length ? `files: ${options.files.map(f => f.name).join(', ')}` : '',
        options.webSearch ? 'web search on' : '',
        options.tools ? 'tools on' : ''
      ].filter(Boolean).join(' | ');
      const response = `This is a mock response to: "${message}".\n\nIn a real setup, this would stream from the local Python backend using \`${config.provider}\` and model \`${config.model}\`.${extras ? `\n\nRequest options: ${extras}` : ''}\n\n\`\`\`python\nprint("Hello from LocaLLM!")\n\`\`\``;
      let i = 0;
      const interval = setInterval(() => {
        if (i < response.length) {
          // Stream chunks of varying size for a more natural feel
          const chunkSize = Math.floor(Math.random() * 3) + 1;
          const chunk = response.slice(i, i + chunkSize);
          onChunk(chunk);
          i += chunkSize;
        } else {
          clearInterval(interval);
          resolve(response);
        }
      }, 30);
    });
  }
};
