import type { LocaLLMConfig, ChatSession, Workspace, WorkspaceSkill, WorkspaceMemory, ModelInfo, SendOptions, Message, AttachedFile, StreamEvent } from '../types';
import { sanitizeChatTitle } from '../utils/messageProcessor';

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

  updateWorkspace: async (name: string, data: Partial<Workspace> & { oldName?: string; deletedSkills?: WorkspaceSkill[] }): Promise<Workspace> => {
    const origName = data.oldName || name;
    const targetName = data.name || name;
    try {
      const res = await fetch(`${API_BASE}/workspaces`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ...data,
          oldName: origName,
          name: targetName,
          newName: targetName
        })
      });
      if (res.ok) {
        return await res.json();
      }
    } catch (e) {
      console.warn('Failed to update workspace on backend:', e);
    }
    return {
      name: targetName,
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

  getWorkspaceMemory: async (name: string): Promise<WorkspaceMemory> => {
    try {
      const res = await fetch(`${API_BASE}/workspaces/${encodeURIComponent(name)}/memory`);
      if (res.ok) {
        return await res.json();
      }
    } catch (e) {
      console.warn('Failed to fetch workspace memory:', e);
    }
    return { workspace: name, auto_memory: true, facts: {} };
  },

  updateWorkspaceMemory: async (
    name: string,
    data: { auto_memory?: boolean; key?: string; value?: string; facts?: Record<string, string> }
  ): Promise<WorkspaceMemory> => {
    try {
      const res = await fetch(`${API_BASE}/workspaces/${encodeURIComponent(name)}/memory`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
      });
      if (res.ok) {
        return await res.json();
      }
    } catch (e) {
      console.warn('Failed to update workspace memory:', e);
    }
    return { workspace: name, auto_memory: data.auto_memory ?? true, facts: data.facts || {} };
  },

  deleteWorkspaceMemoryFact: async (name: string, key?: string): Promise<boolean> => {
    try {
      const url = key
        ? `${API_BASE}/workspaces/${encodeURIComponent(name)}/memory?key=${encodeURIComponent(key)}`
        : `${API_BASE}/workspaces/${encodeURIComponent(name)}/memory`;
      const res = await fetch(url, { method: 'DELETE' });
      return res.ok;
    } catch (e) {
      console.warn('Failed to delete workspace memory fact:', e);
      return false;
    }
  },

  inspectSkills: async (source: string): Promise<{ success: boolean; message: string; skills: string[]; count: number }> => {
    try {
      const res = await fetch(`${API_BASE}/skills/inspect`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ source })
      });
      if (res.ok) {
        return await res.json();
      }
      const err = await res.json().catch(() => ({ error: 'Failed to inspect skills' }));
      return { success: false, message: err.error || err.message || 'Inspection failed', skills: [], count: 0 };
    } catch (e: any) {
      return { success: false, message: e.message || 'Network error', skills: [], count: 0 };
    }
  },

  installSkills: async (workspace: string, source: string, skills?: string[]): Promise<{ success: boolean; message: string; installed: string[]; count: number }> => {
    try {
      const res = await fetch(`${API_BASE}/skills/install`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ workspace, source, skills })
      });
      if (res.ok) {
        return await res.json();
      }
      const err = await res.json().catch(() => ({ error: 'Failed to install skills' }));
      return { success: false, message: err.error || err.message || 'Installation failed', installed: [], count: 0 };
    } catch (e: any) {
      return { success: false, message: e.message || 'Network error', installed: [], count: 0 };
    }
  },

  getModels: async (backend?: string): Promise<ModelInfo[]> => {
    try {
      const url = backend ? `${API_BASE}/models?backend=${encodeURIComponent(backend)}` : `${API_BASE}/models`;
      const res = await fetch(url);
      if (res.ok) {
        const raw = await res.json();
        const list: any[] = Array.isArray(raw) ? raw : (raw.data || []);
        return list.map((m: any) => ({
          id: m.id || m.name,
          name: m.name || m.id,
          provider: m.provider || m.owned_by || 'Local',
          platform: m.platform || m.owned_by || 'Local',
          capabilities: {
            files: m.capabilities?.files ?? true,
            webSearch: m.capabilities?.webSearch ?? true,
            tools: m.capabilities?.tools ?? true
          }
        }));
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

  parseFile: async (filename: string, data: string): Promise<{ success: boolean; text: string; error?: string }> => {
    try {
      const res = await fetch(`${API_BASE}/parse-file`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ filename, data })
      });
      if (res.ok) {
        return await res.json();
      }
      const err = await res.json().catch(() => ({}));
      return { success: false, text: '', error: err.error || 'Failed to parse file' };
    } catch (e: any) {
      return { success: false, text: '', error: e.message || 'Network error parsing file' };
    }
  },

  sendMessage: async (
    message: string,
    config: LocaLLMConfig,
    options: SendOptions,
    onChunk: (chunk: string) => void,
    images?: string[],
    history?: Message[],
    onEvent?: (event: StreamEvent) => void
  ): Promise<string> => {
    const targetModel = config.default_model || config.model || 'nemotron3-super';
    const workspace = config.active_workspace || 'default';

    // Build multi-turn messages array ensuring full conversation context is preserved
    const conversationMessages: any[] = [];
    if (history && history.length > 0) {
      for (const m of history) {
        if (!m.content || !m.content.trim()) continue;
        let mContent = m.content.trim();
        // If prior message had attached text files, re-embed file context so model retains awareness
        if (m.role === 'user' && m.files && m.files.length > 0) {
          const fileBlocks = m.files
            .filter((f: AttachedFile) => f.content && f.content.trim().length > 0)
            .map((f: AttachedFile) => {
              const ext = f.name.split('.').pop() || 'txt';
              return `[Attached File: ${f.name}]\n\`\`\`${ext}\n${f.content}\n\`\`\``;
            })
            .join('\n\n');
          if (fileBlocks && !mContent.includes('[Attached File:')) {
            mContent = `${mContent}\n\n${fileBlocks}`;
          }
        }
        // Extract prior images attached to this message so vision models retain visual context
        const priorImages = (m.role === 'user' && m.files)
          ? m.files
              .filter((f: AttachedFile) => f.url && (f.type?.startsWith('image/') || f.url.startsWith('data:image') || /\.(png|jpe?g|gif|webp|svg|bmp|avif)$/i.test(f.name)))
              .map((f: AttachedFile) => {
                if (!f.url) return '';
                const commaIdx = f.url.indexOf(',');
                return commaIdx !== -1 ? f.url.slice(commaIdx + 1) : f.url;
              })
              .filter(Boolean)
          : [];

        conversationMessages.push({
          role: m.role,
          content: mContent,
          ...(priorImages.length > 0 ? { images: priorImages } : {})
        });
      }
    }

    conversationMessages.push({
      role: 'user',
      content: message,
      ...(images && images.length > 0 ? { images } : {})
    });

    // Construct request payload
    const payload = {
      message,
      messages: conversationMessages,
      model: targetModel,
      backend: config.active_backend || 'ollama',
      provider: config.active_backend || 'ollama',
      workspace,
      temperature: config.temperature,
      options: {
        files: options.files.map(f => f.name),
        webSearch: options.webSearch,
        tools: options.tools
      },
      ...(images && images.length > 0 ? { images } : {})
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
        onEvent?.({ event: 'error', data: { message: errMsg } });
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
            if (dataStr === '[DONE]') {
              onEvent?.({ event: 'done' });
              continue;
            }

            try {
              const parsed = JSON.parse(dataStr);

              // 1. Process modern high-level execution events
              if (parsed.event) {
                onEvent?.(parsed as StreamEvent);
                if (parsed.event === 'response_token' && typeof parsed.data === 'string') {
                  fullResponse += parsed.data;
                  onChunk(parsed.data);
                } else if (parsed.event === 'error') {
                  const errDetail = parsed.data?.message || 'Error occurred';
                  const errText = `\n[Gagal memproses respon: ${errDetail}]`;
                  fullResponse += errText;
                  onChunk(errText);
                }
                continue;
              }

              // 2. Compatibility fallback for standard OpenAI streaming chunk format
              const delta = parsed.choices?.[0]?.delta;
              if (delta?.content) {
                fullResponse += delta.content;
                onChunk(delta.content);
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
            if (parsed.event) {
              onEvent?.(parsed as StreamEvent);
              if (parsed.event === 'response_token' && typeof parsed.data === 'string') {
                fullResponse += parsed.data;
                onChunk(parsed.data);
              }
            } else {
              const content = parsed.choices?.[0]?.delta?.content || '';
              if (content) {
                fullResponse += content;
                onChunk(content);
              }
            }
          }
        } catch {
          fullResponse += buffer;
          onChunk(buffer);
        }
      }

      if (!fullResponse.trim()) {
        const emptyMsg = "Tidak ada respon teks yang diterima dari model. Pastikan model lokal aktif atau periksa apakah backend sedang memproses permintaan.";
        onChunk(emptyMsg);
        return emptyMsg;
      }

      return fullResponse;
    } catch (err: any) {
      console.warn('Direct chat stream failed, generating fallback response:', err);
      const fallback = `[Kendala Server]: Gagal terhubung ke engine locaLLM pada port ${config.server_port || 8080} (${err.message || 'Network error'}). Pastikan server locaLLM aktif.`;
      onChunk(fallback);
      return fallback;
    }
  },

  generateTitle: async (userPrompt: string, config: LocaLLMConfig): Promise<string> => {
    const targetModel = config.default_model || config.model || 'nemotron3-super';
    const workspace = config.active_workspace || 'default';
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 7000);

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

          // Strip completed thought blocks and currently unclosed thought block
          const candidate = full
            .replace(/<(?:think|thought)>[\s\S]*?<\/(?:think|thought)>/gi, '')
            .replace(/<(?:think|thought)>[\s\S]*$/gi, '')
            .trim();

          // Once we have actual non-thought title content
          if (candidate.length >= 4) {
            if (candidate.includes('\n') || candidate.length >= 35) {
              break;
            }
          }
        }
        return sanitizeChatTitle(full, '');
      }
      const text = await res.text();
      return sanitizeChatTitle(text, '');
    } catch {
      return '';
    } finally {
      clearTimeout(timeoutId);
    }
  }
};
