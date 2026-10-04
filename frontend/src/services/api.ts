import type { LocaLLMConfig, ChatSession, Workspace, ModelInfo, SendOptions } from '../types';

const API_BASE = '/api';

export const api = {
  getWorkspaces: async (): Promise<Workspace[]> => {
    try {
      const res = await fetch(`${API_BASE}/workspaces`);
      if (res.ok) {
        return await res.json();
      }
    } catch (e) {
      console.warn('Failed to fetch workspaces from backend, using fallback:', e);
    }
    return [
      { name: 'default', description: 'Default general-purpose workspace', knowledgeCount: 1, skillsCount: 3 }
    ];
  },

  createWorkspace: async (data: Partial<Workspace> | string, description: string = ''): Promise<Workspace> => {
    const payload = typeof data === 'string' ? { name: data, description } : data;
    try {
      const res = await fetch(`${API_BASE}/workspaces`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      if (res.ok) {
        return await res.json();
      }
    } catch (e) {
      console.warn('Failed to create workspace on backend:', e);
    }
    return {
      name: payload.name || 'new-workspace',
      description: payload.description || '',
      icon: payload.icon || 'Folder',
      color: payload.color || '#3B82F6',
      custom_instructions: payload.custom_instructions || '',
      skills: payload.skills || [],
      knowledgeCount: 0,
      skillsCount: (payload.skills || []).length
    };
  },

  updateWorkspace: async (name: string, data: Partial<Workspace>): Promise<Workspace> => {
    try {
      const res = await fetch(`${API_BASE}/workspaces`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, ...data })
      });
      if (res.ok) {
        return await res.json();
      }
    } catch (e) {
      console.warn('Failed to update workspace on backend:', e);
    }
    return {
      name: data.name || name,
      ...data
    } as Workspace;
  },

  deleteWorkspace: async (name: string): Promise<boolean> => {
    try {
      const res = await fetch(`${API_BASE}/workspaces?name=${encodeURIComponent(name)}`, {
        method: 'DELETE'
      });
      return res.ok;
    } catch (e) {
      console.warn('Failed to delete workspace on backend:', e);
      return false;
    }
  },

  getModels: async (backend?: string): Promise<ModelInfo[]> => {
    try {
      const url = backend ? `${API_BASE}/models?backend=${encodeURIComponent(backend)}` : `${API_BASE}/models`;
      const res = await fetch(url);
      if (res.ok) {
        return await res.json();
      }
    } catch (e) {
      console.warn('Failed to fetch models from backend, using fallback:', e);
    }
    return [
      { id: 'nemotron3-super', name: 'nemotron3-super', provider: 'OpenAI', platform: 'OpenAI', capabilities: { files: true, webSearch: true, tools: true } },
      { id: 'auto', name: 'Auto Dynamic Router', provider: 'OpenAI', platform: 'OpenAI', capabilities: { files: true, webSearch: true, tools: true } }
    ];
  },

  getConfig: async (): Promise<LocaLLMConfig> => {
    try {
      const res = await fetch(`${API_BASE}/config`);
      if (res.ok) {
        return await res.json();
      }
    } catch (e) {
      console.warn('Failed to fetch config from backend, using fallback:', e);
    }
    return {
      active_backend: 'ollama',
      ollama_host: 'http://127.0.0.1:11434',
      ollama_model: 'gemma4:12b',
      custom_platforms: [],
      default_model: 'gemma4:12b',
      temperature: 0.7,
      context_window: 8192,
      system_prompt: 'You are locaLLM, a helpful, fast, and intelligent local AI assistant.',
      agent_permission_policy: 'ask',
      agent_max_steps: 25,
      active_workspace: 'default',
      search_provider: 'auto',
      search_api_url: '',
      ui_theme: 'cyber_neon',
      server_enabled: true,
      server_host: '127.0.0.1',
      server_port: 8080,
      server_api_key: ''
    };
  },

  saveConfig: async (config: LocaLLMConfig): Promise<void> => {
    try {
      const res = await fetch(`${API_BASE}/config`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config)
      });
      if (!res.ok) {
        console.error('Failed to save config on server:', await res.text());
      }
    } catch (e) {
      console.error('Network error saving config:', e);
    }
  },

  getSessions: async (workspace?: string): Promise<ChatSession[]> => {
    const ws = workspace || 'default';
    try {
      const res = await fetch(`${API_BASE}/sessions?workspace=${encodeURIComponent(ws)}`);
      if (res.ok) {
        return await res.json();
      }
    } catch (e) {
      console.warn('Failed to fetch sessions from backend:', e);
    }
    return [];
  },

  saveSession: async (session: ChatSession): Promise<void> => {
    try {
      await fetch(`${API_BASE}/sessions?workspace=${encodeURIComponent(session.workspace)}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(session)
      });
    } catch (e) {
      console.warn('Failed to save session to backend:', e);
    }
  },

  deleteSession: async (id: string, workspace?: string): Promise<void> => {
    try {
      await fetch(`${API_BASE}/sessions?id=${encodeURIComponent(id)}&workspace=${encodeURIComponent(workspace || 'default')}`, {
        method: 'DELETE'
      });
    } catch (e) {
      console.warn('Failed to delete session on backend:', e);
    }
  },

  sendMessage: async (
    message: string,
    config: LocaLLMConfig,
    options: SendOptions,
    onChunk: (chunk: string) => void
  ): Promise<string> => {
    const targetModel = config.default_model || config.model || 'nemotron3-super';
    const workspace = config.active_workspace || 'default';

    // Construct request payload
    const payload = {
      message,
      model: targetModel,
      workspace,
      temperature: config.temperature,
      options: {
        files: options.files.map(f => f.name),
        webSearch: options.webSearch,
        tools: options.tools
      }
    };

    try {
      const res = await fetch(`${API_BASE}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (!res.ok) {
        const errorData = await res.json().catch(() => ({ error: res.statusText }));
        const errMsg = errorData.error || 'Chat request failed';
        onChunk(`[Error: ${errMsg}]`);
        return errMsg;
      }

      if (!res.body) {
        const text = await res.text();
        onChunk(text);
        return text;
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let fullResponse = '';
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          const trimmed = line.trim();
          if (!trimmed || trimmed.startsWith(':')) continue;

          if (trimmed.startsWith('data: ')) {
            const dataStr = trimmed.slice(6);
            if (dataStr === '[DONE]') continue;

            try {
              const parsed = JSON.parse(dataStr);
              const delta = parsed.choices?.[0]?.delta;
              const content = delta?.content || delta?.reasoning_content || '';
              if (content) {
                fullResponse += content;
                onChunk(content);
              }
            } catch {
              // Raw text chunk fallback
              if (dataStr) {
                fullResponse += dataStr;
                onChunk(dataStr);
              }
            }
          } else {
            // Direct streaming text
            fullResponse += line + '\n';
            onChunk(line + '\n');
          }
        }
      }

      if (buffer.trim()) {
        try {
          const dataStr = buffer.trim().replace(/^data:\s*/, '');
          if (dataStr && dataStr !== '[DONE]') {
            const parsed = JSON.parse(dataStr);
            const content = parsed.choices?.[0]?.delta?.content || '';
            if (content) {
              fullResponse += content;
              onChunk(content);
            }
          }
        } catch {
          fullResponse += buffer;
          onChunk(buffer);
        }
      }

      return fullResponse || '(Empty response)';
    } catch (err: any) {
      console.warn('Direct chat stream failed, generating fallback response:', err);
      const fallback = `Could not connect to LocaLLM inference engine at port ${config.server_port || 8080}. Ensure locaLLM API server is running with 'server_enabled: true'.`;
      onChunk(fallback);
      return fallback;
    }
  },

  generateTitle: async (userPrompt: string, config: LocaLLMConfig): Promise<string> => {
    const targetModel = config.default_model || config.model || 'nemotron3-super';
    const workspace = config.active_workspace || 'default';
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 3500);

    const titlePrompt = `Summarize this user request into a 3 to 5 words title in the same language. Output ONLY the title without quotes, punctuation or extra words:\n"${userPrompt.slice(0, 250)}"`;

    try {
      const res = await fetch(`${API_BASE}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        signal: controller.signal,
        body: JSON.stringify({
          message: titlePrompt,
          model: targetModel,
          workspace,
          temperature: 0.3,
          options: {
            files: [],
            webSearch: false,
            tools: false
          }
        })
      });
      clearTimeout(timeoutId);

      if (!res.ok) return '';

      if (res.body) {
        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let full = '';
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          const chunk = decoder.decode(value, { stream: true });
          const lines = chunk.split('\n');
          for (const line of lines) {
            const trimmed = line.trim();
            if (trimmed.startsWith('data: ')) {
              const dataStr = trimmed.slice(6);
              if (dataStr === '[DONE]') continue;
              try {
                const parsed = JSON.parse(dataStr);
                const delta = parsed.choices?.[0]?.delta?.content || '';
                full += delta;
              } catch {
                full += dataStr;
              }
            } else if (trimmed && !trimmed.startsWith(':')) {
              full += trimmed + ' ';
            }
          }
          if (full.length > 60) break;
        }
        return full.replace(/<think>[\s\S]*?<\/think>/gi, '').trim();
      }
      const text = await res.text();
      return text.replace(/<think>[\s\S]*?<\/think>/gi, '').trim();
    } catch {
      return '';
    } finally {
      clearTimeout(timeoutId);
    }
  }
};
