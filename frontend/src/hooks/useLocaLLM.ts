import { useState, useEffect, useCallback } from 'react';
import type { LocaLLMConfig, ChatSession, Message, Workspace, ModelInfo, SendOptions } from '../types';
import { api } from '../services/api';

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
    };
    loadInit();
  }, []);

  // Load sessions whenever activeWorkspace changes
  const loadSessionsForWorkspace = useCallback(async (ws: string) => {
    const fetchedSessions = await api.getSessions(ws);
    setSessions(fetchedSessions);
    if (fetchedSessions.length > 0) {
      setActiveSessionId(fetchedSessions[0].id);
    } else {
      setActiveSessionId(null);
    }
  }, []);

  useEffect(() => {
    loadSessionsForWorkspace(activeWorkspace);
  }, [activeWorkspace, loadSessionsForWorkspace]);

  const selectWorkspace = (wsName: string) => {
    setActiveWorkspace(wsName);
  };

  const createWorkspace = async (name: string, description?: string) => {
    const newWs = await api.createWorkspace(name, description);
    setWorkspaces(prev => {
      if (prev.some(w => w.name === newWs.name)) return prev;
      return [...prev, newWs];
    });
    setActiveWorkspace(newWs.name);
  };

  const updateConfig = async (newConfig: LocaLLMConfig) => {
    setIsConfigSyncing(true);
    setConfig(newConfig);
    await api.saveConfig(newConfig);
    setIsConfigSyncing(false);
  };

  const activeSession = sessions.find(s => s.id === activeSessionId) || null;

  const createSession = async () => {
    const newSession: ChatSession = {
      id: Date.now().toString(),
      title: 'New Chat',
      workspace: activeWorkspace,
      updatedAt: Date.now(),
      messages: []
    };
    setSessions(prev => [newSession, ...prev]);
    setActiveSessionId(newSession.id);
    await api.saveSession(newSession);
  };

  const deleteSession = async (id: string) => {
    setSessions(prev => prev.filter(s => s.id !== id));
    if (activeSessionId === id) {
      setActiveSessionId(sessions.find(s => s.id !== id)?.id || null);
    }
    await api.deleteSession(id);
  };

  const sendMessage = async (content: string, options: SendOptions = { files: [], webSearch: false, tools: false }) => {
    if (!activeSessionId || !config) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content,
      timestamp: Date.now()
    };

    let sessionToUpdate = sessions.find(s => s.id === activeSessionId);
    if (!sessionToUpdate) return;
    
    let title = sessionToUpdate.title;
    if (sessionToUpdate.messages.length === 0) {
       title = content.slice(0, 30) + (content.length > 30 ? '...' : '');
    }

    sessionToUpdate = {
      ...sessionToUpdate,
      title,
      messages: [...sessionToUpdate.messages, userMessage],
      updatedAt: Date.now()
    };
    
    setSessions(prev => prev.map(s => s.id === activeSessionId ? sessionToUpdate! : s));
    setIsTyping(true);

    let assistantContent = '';
    const assistantMessageId = (Date.now() + 1).toString();
    
    setSessions(prev => prev.map(s => {
      if (s.id !== activeSessionId) return s;
      return {
        ...s,
        messages: [...s.messages, { id: assistantMessageId, role: 'assistant', content: '', timestamp: Date.now() }]
      };
    }));

    await api.sendMessage(content, config, options, (chunk) => {
      assistantContent += chunk;
      setSessions(prev => prev.map(s => {
        if (s.id !== activeSessionId) return s;
        const msgs = [...s.messages];
        const idx = msgs.findIndex(m => m.id === assistantMessageId);
        if (idx !== -1) msgs[idx] = { ...msgs[idx], content: assistantContent };
        return { ...s, messages: msgs };
      }));
    });

    setIsTyping(false);

    const updated: ChatSession = {
      ...sessionToUpdate,
      messages: [
        ...sessionToUpdate.messages,
        { id: assistantMessageId, role: 'assistant', content: assistantContent, timestamp: Date.now() }
      ],
      updatedAt: Date.now()
    };
    setSessions(prev => prev.map(s => s.id === updated.id ? updated : s));
    await api.saveSession(updated);
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
    sessions,
    activeSessionId,
    setActiveSessionId,
    activeSession,
    createSession,
    deleteSession,
    sendMessage,
    isTyping
  };
}
