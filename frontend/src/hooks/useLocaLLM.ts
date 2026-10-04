import { useState, useEffect, useCallback } from 'react';
import type { LocaLLMConfig, ChatSession, Message, Workspace, ModelInfo, SendOptions } from '../types';
import { api } from '../services/api';
import { extractSourcesFromText, generateSmartTitleFallback } from '../utils/messageProcessor';

export function useLocaLLM() {
  const [config, setConfig] = useState<LocaLLMConfig | null>(null);
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [activeWorkspace, setActiveWorkspace] = useState<string>('default');
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [isConfigSyncing, setIsConfigSyncing] = useState(false);
  const [isTyping, setIsTyping] = useState(false);
  const [models, setModels] = useState<ModelInfo[]>([]);

  // Load initial config, workspaces and model catalog
  useEffect(() => {
    const loadInit = async () => {
      const [fetchedConfig, fetchedWorkspaces, fetchedModels] = await Promise.all([
        api.getConfig(),
        api.getWorkspaces(),
        api.getModels()
      ]);
      setConfig(fetchedConfig);
      setWorkspaces(fetchedWorkspaces);
      setModels(fetchedModels);
      if (fetchedConfig.active_workspace) {
        setActiveWorkspace(fetchedConfig.active_workspace);
      }
    };
    loadInit();
  }, []);

  // Load sessions whenever activeWorkspace changes
  const loadSessionsForWorkspace = useCallback(async (ws: string) => {
    const fetchedSessions = await api.getSessions(ws);
    // Filter out empty sessions so ghost files do not clutter the sidebar
    const validSessions = fetchedSessions.filter(s => s.messages && s.messages.length > 0);
    setSessions(validSessions);
    if (validSessions.length > 0) {
      setActiveSessionId(validSessions[0].id);
    } else {
      setActiveSessionId(null);
    }
  }, []);

  useEffect(() => {
    loadSessionsForWorkspace(activeWorkspace);
  }, [activeWorkspace, loadSessionsForWorkspace]);

  const selectWorkspace = (wsName: string) => {
    setActiveWorkspace(wsName);
    if (config && config.active_workspace !== wsName) {
      const updated = { ...config, active_workspace: wsName };
      setConfig(updated);
      api.saveConfig(updated);
    }
  };

  const createWorkspace = async (data: Partial<Workspace> | string, description?: string) => {
    const newWs = await api.createWorkspace(data, description);
    setWorkspaces(prev => {
      if (prev.some(w => w.name === newWs.name)) {
        return prev.map(w => w.name === newWs.name ? { ...w, ...newWs } : w);
      }
      return [...prev, newWs];
    });
    setActiveWorkspace(newWs.name);
    if (config) {
      const updated = { ...config, active_workspace: newWs.name };
      setConfig(updated);
      api.saveConfig(updated);
    }
    return newWs;
  };

  const updateWorkspace = async (name: string, data: Partial<Workspace>) => {
    const updatedWs = await api.updateWorkspace(name, data);
    setWorkspaces(prev => prev.map(w => w.name === name ? { ...w, ...updatedWs } : w));
    if (data.name && data.name !== name && activeWorkspace === name) {
      setActiveWorkspace(data.name);
    }
    return updatedWs;
  };

  const deleteWorkspace = async (name: string) => {
    if (name.toLowerCase() === 'default') return;
    if (activeWorkspace.toLowerCase() === name.toLowerCase()) {
      selectWorkspace('default');
    }
    setWorkspaces(prev => prev.filter(w => w.name !== name));
    await api.deleteWorkspace(name);
  };

  const refreshModels = useCallback(async (backend?: string) => {
    const fetched = await api.getModels(backend);
    setModels(fetched);
    return fetched;
  }, []);

  const updateConfig = async (newConfig: LocaLLMConfig) => {
    setIsConfigSyncing(true);
    const backendChanged = config && newConfig.active_backend !== config.active_backend;
    setConfig(newConfig);
    await api.saveConfig(newConfig);
    if (backendChanged) {
      await refreshModels(newConfig.active_backend);
    }
    setIsConfigSyncing(false);
  };

  const activeSession = sessions.find(s => s.id === activeSessionId) || null;

  // Lazy new chat: switch to draft state without creating/saving empty session file
  const createSession = () => {
    setActiveSessionId(null);
  };

  const deleteSession = async (id: string) => {
    setSessions(prev => prev.filter(s => s.id !== id));
    if (activeSessionId === id) {
      const remaining = sessions.filter(s => s.id !== id);
      setActiveSessionId(remaining.length > 0 ? remaining[0].id : null);
    }
    await api.deleteSession(id, activeWorkspace);
  };

  const sendMessage = async (content: string, options: SendOptions = { files: [], webSearch: false, tools: false }) => {
    if (!config) return;
    const hasFiles = options.files && options.files.length > 0;
    if (!content.trim() && !hasFiles) return;

    const isImageAttached = hasFiles && options.files.some(f => /\.(png|jpe?g|gif|webp|svg|bmp|avif)$/i.test(f.name));
    const effectiveContent = content.trim() || (hasFiles ? (isImageAttached ? 'Analyze this image.' : 'Review the attached file.') : '');

    let currentSessionId = activeSessionId;
    let sessionToUpdate: ChatSession;
    let isBrandNewSession = false;

    // If in draft "New Chat" mode, initialize session on-the-fly when user sends their first message
    if (!currentSessionId) {
      isBrandNewSession = true;
      currentSessionId = Date.now().toString();
      const initialTitle = generateSmartTitleFallback(effectiveContent);
      sessionToUpdate = {
        id: currentSessionId,
        title: initialTitle,
        workspace: activeWorkspace,
        updatedAt: Date.now(),
        messages: []
      };
      setSessions(prev => [sessionToUpdate, ...prev]);
      setActiveSessionId(currentSessionId);
      await api.saveSession(sessionToUpdate);
    } else {
      const existing = sessions.find(s => s.id === currentSessionId);
      if (!existing) return;
      sessionToUpdate = existing;
    }

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: effectiveContent,
      timestamp: Date.now(),
      options: {
        files: options.files.map(f => f.name),
        webSearch: options.webSearch,
        tools: options.tools
      }
    };

    let title = sessionToUpdate.title;
    if (sessionToUpdate.messages.length === 0 && !isBrandNewSession) {
      title = generateSmartTitleFallback(effectiveContent);
    }

    sessionToUpdate = {
      ...sessionToUpdate,
      title,
      messages: [...sessionToUpdate.messages, userMessage],
      updatedAt: Date.now()
    };

    setSessions(prev => prev.map(s => s.id === currentSessionId ? sessionToUpdate : s));
    setIsTyping(true);

    let assistantContent = '';
    const assistantMessageId = (Date.now() + 1).toString();

    setSessions(prev => prev.map(s => {
      if (s.id !== currentSessionId) return s;
      return {
        ...s,
        messages: [...s.messages, { id: assistantMessageId, role: 'assistant', content: '', timestamp: Date.now() }]
      };
    }));

    await api.sendMessage(effectiveContent, config, options, (chunk) => {
      assistantContent += chunk;
      setSessions(prev => prev.map(s => {
        if (s.id !== currentSessionId) return s;
        const msgs = [...s.messages];
        const idx = msgs.findIndex(m => m.id === assistantMessageId);
        if (idx !== -1) msgs[idx] = { ...msgs[idx], content: assistantContent };
        return { ...s, messages: msgs };
      }));
    });

    setIsTyping(false);

    const sources = extractSourcesFromText(assistantContent);
    const updated: ChatSession = {
      ...sessionToUpdate,
      messages: [
        ...sessionToUpdate.messages,
        {
          id: assistantMessageId,
          role: 'assistant',
          content: assistantContent,
          timestamp: Date.now(),
          sources: sources.length > 0 ? sources : undefined
        }
      ],
      updatedAt: Date.now()
    };
    setSessions(prev => prev.map(s => s.id === updated.id ? updated : s));
    await api.saveSession(updated);

    // Asynchronously generate concise, goal-oriented AI chat title in background if first turn
    if (sessionToUpdate.messages.length <= 1) {
      api.generateTitle(content, config).then(aiTitle => {
        if (aiTitle && aiTitle.trim().length > 1) {
          const cleanTitle = aiTitle.trim().replace(/^["'«»“”]+|["'«»“”]+$/g, '').slice(0, 48);
          setSessions(prev => prev.map(s => s.id === currentSessionId ? { ...s, title: cleanTitle } : s));
          api.saveSession({ ...updated, title: cleanTitle });
        }
      }).catch(() => {
        // Fallback title is already active
      });
    }
  };

  const regenerateMessage = async (assistantMessageId: string) => {
    if (!config || isTyping) return;
    const currentSessionId = activeSessionId;
    if (!currentSessionId) return;

    const session = sessions.find(s => s.id === currentSessionId);
    if (!session) return;

    const msgIdx = session.messages.findIndex(m => m.id === assistantMessageId);
    if (msgIdx === -1) return;

    // Find the user prompt preceding this assistant message
    let userPrompt = '';
    let userOptions: SendOptions = { files: [], webSearch: false, tools: false };
    for (let i = msgIdx - 1; i >= 0; i--) {
      if (session.messages[i].role === 'user') {
        const uMsg = session.messages[i];
        userPrompt = uMsg.content;
        userOptions = {
          files: [],
          webSearch: Boolean(uMsg.options?.webSearch),
          tools: Boolean(uMsg.options?.tools)
        };
        break;
      }
    }

    if (!userPrompt) return;

    setIsTyping(true);

    let assistantContent = '';
    setSessions(prev => prev.map(s => {
      if (s.id !== currentSessionId) return s;
      const msgs = [...s.messages];
      const idx = msgs.findIndex(m => m.id === assistantMessageId);
      if (idx !== -1) {
        msgs[idx] = { ...msgs[idx], content: '', sources: undefined };
      }
      return { ...s, messages: msgs };
    }));

    await api.sendMessage(userPrompt, config, userOptions, (chunk) => {
      assistantContent += chunk;
      setSessions(prev => prev.map(s => {
        if (s.id !== currentSessionId) return s;
        const msgs = [...s.messages];
        const idx = msgs.findIndex(m => m.id === assistantMessageId);
        if (idx !== -1) {
          msgs[idx] = { ...msgs[idx], content: assistantContent };
        }
        return { ...s, messages: msgs };
      }));
    });

    setIsTyping(false);

    const sources = extractSourcesFromText(assistantContent);
    const updatedMsgs = session.messages.map(m => {
      if (m.id === assistantMessageId) {
        return {
          ...m,
          content: assistantContent,
          timestamp: Date.now(),
          sources: sources.length > 0 ? sources : undefined
        };
      }
      return m;
    });

    const updatedSession: ChatSession = {
      ...session,
      messages: updatedMsgs,
      updatedAt: Date.now()
    };

    setSessions(prev => prev.map(s => s.id === currentSessionId ? updatedSession : s));
    await api.saveSession(updatedSession);
  };

  return {
    config,
    models,
    updateConfig,
    isConfigSyncing,
    workspaces,
    activeWorkspace,
    selectWorkspace,
    createWorkspace,
    updateWorkspace,
    deleteWorkspace,
    sessions,
    activeSessionId,
    setActiveSessionId,
    activeSession,
    createSession,
    deleteSession,
    sendMessage,
    regenerateMessage,
    isTyping,
    refreshModels
  };
}
