import { useState, useEffect, useCallback, useRef } from 'react';
import type { LocaLLMConfig, ChatSession, Message, Workspace, WorkspaceSkill, ModelInfo, SendOptions, AttachedFile, ExecutionState, SessionNotification } from '../types';
import { api } from '../services/api';
import { extractSourcesFromText, generateSmartTitleFallback, sanitizeChatTitle } from '../utils/messageProcessor';

function getUrlParams(): { session: string | null; workspace: string | null } {
  try {
    const params = new URLSearchParams(window.location.search);
    const session = params.get('c') || params.get('session') || null;
    const workspace = params.get('w') || params.get('workspace') || null;
    return { session, workspace };
  } catch {
    return { session: null, workspace: null };
  }
}

function updateUrlParams(workspace: string, sessionId: string | null) {
  try {
    const url = new URL(window.location.href);
    if (sessionId) {
      url.searchParams.set('c', sessionId);
      url.searchParams.delete('session');
    } else {
      url.searchParams.delete('c');
      url.searchParams.delete('session');
    }

    if (workspace && workspace.trim() && workspace.trim().toLowerCase() !== 'default') {
      url.searchParams.set('w', workspace.trim());
      url.searchParams.delete('workspace');
    } else {
      url.searchParams.delete('w');
      url.searchParams.delete('workspace');
    }

    const newPath = url.pathname + (url.search ? url.search : '') + url.hash;
    window.history.replaceState(null, '', newPath);
  } catch {}
}

export function useLocaLLM() {
  const initialParams = useRef(getUrlParams()).current;
  const [config, setConfig] = useState<LocaLLMConfig | null>(null);
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [activeWorkspace, setActiveWorkspace] = useState<string>(() => initialParams.workspace || 'default');
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(() => initialParams.session);
  const [isConfigSyncing, setIsConfigSyncing] = useState(false);
  const [typingSessionIds, setTypingSessionIds] = useState<string[]>([]);
  const [unreadSessionIds, setUnreadSessionIds] = useState<string[]>([]);
  const [sessionNotification, setSessionNotification] = useState<SessionNotification | null>(null);
  const abortControllersRef = useRef<Map<string, AbortController>>(new Map());
  const activeSessionIdRef = useRef<string | null>(activeSessionId);
  const [models, setModels] = useState<ModelInfo[]>([]);
  const sessionsCacheRef = useRef<Record<string, ChatSession[]>>({});
  const isInitialHydratedRef = useRef(false);
  const initialRequestedSessionIdRef = useRef<string | null>(initialParams.session);

  useEffect(() => {
    activeSessionIdRef.current = activeSessionId;
  }, [activeSessionId]);

  const isTyping = Boolean(activeSessionId && typingSessionIds.includes(activeSessionId));

  const clearUnreadSession = useCallback((sessionId: string) => {
    setUnreadSessionIds(prev => prev.filter(id => id !== sessionId));
    setSessionNotification(curr => curr?.sessionId === sessionId ? null : curr);
  }, []);

  const dismissNotification = useCallback(() => {
    setSessionNotification(null);
  }, []);

  const stopGeneration = useCallback((targetSessionId?: string) => {
    const sId = targetSessionId || activeSessionIdRef.current;
    if (!sId) return;
    const controller = abortControllersRef.current.get(sId);
    if (controller) {
      controller.abort();
      abortControllersRef.current.delete(sId);
    }
    setTypingSessionIds(prev => prev.filter(id => id !== sId));
  }, []);

  useEffect(() => {
    if (activeSessionId) {
      clearUnreadSession(activeSessionId);
    }
  }, [activeSessionId, clearUnreadSession]);

  // Sync active session and workspace with URL whenever activeSessionId or activeWorkspace changes
  useEffect(() => {
    if (isInitialHydratedRef.current) {
      updateUrlParams(activeWorkspace, activeSessionId);
    }
  }, [activeSessionId, activeWorkspace]);

  // Handle browser Back / Forward history navigation
  useEffect(() => {
    const handlePopState = () => {
      const { session, workspace } = getUrlParams();
      if (workspace && workspace !== activeWorkspace) {
        setActiveWorkspace(workspace);
      }
      setActiveSessionId(session);
    };
    window.addEventListener('popstate', handlePopState);
    return () => window.removeEventListener('popstate', handlePopState);
  }, [activeWorkspace]);

  const refreshWorkspaces = useCallback(async () => {
    try {
      const fetched = await api.getWorkspaces();
      setWorkspaces(fetched);
      return fetched;
    } catch (e) {
      console.warn('Failed to refresh workspaces:', e);
      return [];
    }
  }, []);

  // Load initial config, workspaces and model catalog with smart session and workspace resolution
  useEffect(() => {
    const loadInit = async () => {
      try {
        const [fetchedConfig, fetchedWorkspaces, fetchedModels] = await Promise.all([
          api.getConfig(),
          api.getWorkspaces(),
          api.getModels()
        ]);
        setConfig(fetchedConfig);
        setWorkspaces(fetchedWorkspaces);
        setModels(fetchedModels);

        const reqSessionId = initialRequestedSessionIdRef.current;
        const targetWs = initialParams.workspace || fetchedConfig.active_workspace || 'default';

        let foundSessions: ChatSession[] = [];
        let resolvedWs = targetWs;
        let sessionMatched = false;

        if (reqSessionId) {
          // 1. Try target workspace first
          try {
            const primarySessions = await api.getSessions(targetWs);
            if (primarySessions.some(s => s.id === reqSessionId)) {
              foundSessions = primarySessions;
              resolvedWs = targetWs;
              sessionMatched = true;
            }
          } catch {}

          // 2. If not found in target workspace, search across other workspaces
          if (!sessionMatched && fetchedWorkspaces && fetchedWorkspaces.length > 0) {
            for (const w of fetchedWorkspaces) {
              if (w.name.toLowerCase() === targetWs.toLowerCase()) continue;
              try {
                const wsSessions = await api.getSessions(w.name);
                if (wsSessions.some(s => s.id === reqSessionId)) {
                  foundSessions = wsSessions;
                  resolvedWs = w.name;
                  sessionMatched = true;
                  break;
                }
              } catch {}
            }
          }

          // 3. Fallback: if not found in any other workspace, load target workspace sessions
          if (!sessionMatched && foundSessions.length === 0) {
            try {
              foundSessions = await api.getSessions(targetWs);
            } catch {}
          }
        } else {
          // Normal load without session query
          try {
            foundSessions = await api.getSessions(targetWs);
          } catch {}
        }

        const validSessions = foundSessions
          .filter(s => s.messages && s.messages.length > 0)
          .map(s => ({ ...s, title: sanitizeChatTitle(s.title) }));
        sessionsCacheRef.current[resolvedWs] = validSessions;
        setActiveWorkspace(resolvedWs);
        setSessions(validSessions);

        if (reqSessionId && sessionMatched && validSessions.some(s => s.id === reqSessionId)) {
          setActiveSessionId(reqSessionId);
          updateUrlParams(resolvedWs, reqSessionId);
        } else {
          setActiveSessionId(null);
          updateUrlParams(resolvedWs, null);
        }

        if (resolvedWs !== fetchedConfig.active_workspace) {
          const updated = { ...fetchedConfig, active_workspace: resolvedWs };
          setConfig(updated);
          api.saveConfig(updated).catch(() => {});
        }
      } catch (err) {
        console.warn('Failed initial app hydration:', err);
      } finally {
        isInitialHydratedRef.current = true;
      }
    };
    loadInit();
  }, [initialParams]);

  // Keep in-memory cache updated with latest sessions
  useEffect(() => {
    if (activeWorkspace) {
      sessionsCacheRef.current[activeWorkspace] = sessions;
    }
  }, [activeWorkspace, sessions]);

  // Load sessions whenever activeWorkspace changes (after initial hydration)
  const loadSessionsForWorkspace = useCallback(async (ws: string) => {
    if (!isInitialHydratedRef.current) return;
    try {
      const fetchedSessions = await api.getSessions(ws);
      const validSessions = fetchedSessions
        .filter(s => s.messages && s.messages.length > 0)
        .map(s => ({ ...s, title: sanitizeChatTitle(s.title) }));
      sessionsCacheRef.current[ws] = validSessions;
      setSessions(validSessions);
    } catch (e) {
      console.warn('Failed to load sessions for workspace:', ws, e);
    }
  }, []);

  useEffect(() => {
    if (isInitialHydratedRef.current) {
      loadSessionsForWorkspace(activeWorkspace);
    }
  }, [activeWorkspace, loadSessionsForWorkspace]);

  const selectWorkspace = useCallback((wsName: string) => {
    if (wsName === activeWorkspace) return;

    // Clear session in URL so switching workspace always lands on clean New Chat
    setActiveSessionId(null);
    updateUrlParams(wsName, null);

    // 1. Instant optimistic switch from cache if already loaded
    const cached = sessionsCacheRef.current[wsName];
    if (cached) {
      setSessions(cached);
    }

    // 2. Set active workspace immediately
    setActiveWorkspace(wsName);

    // 3. Persist config asynchronously in background without blocking UI
    if (config && config.active_workspace !== wsName) {
      const updated = { ...config, active_workspace: wsName };
      setConfig(updated);
      api.saveConfig(updated).catch(e => console.warn('Failed to save active workspace config:', e));
    }
  }, [activeWorkspace, config]);

  const createWorkspace = async (data: Partial<Workspace> | string, description?: string) => {
    const newWs = await api.createWorkspace(data, description);
    setWorkspaces(prev => {
      if (prev.some(w => w.name === newWs.name)) {
        return prev.map(w => w.name === newWs.name ? { ...w, ...newWs } : w);
      }
      return [...prev, newWs];
    });
    setActiveWorkspace(newWs.name);
    setActiveSessionId(null);
    updateUrlParams(newWs.name, null);
    if (config) {
      const updated = { ...config, active_workspace: newWs.name };
      setConfig(updated);
      api.saveConfig(updated);
    }
    await refreshWorkspaces();
    return newWs;
  };

  const updateWorkspace = async (name: string, data: Partial<Workspace> & { oldName?: string; deletedSkills?: WorkspaceSkill[] }) => {
    const origName = data.oldName || name;
    const targetName = data.name || name;
    const updatedWs = await api.updateWorkspace(origName, data);
    setWorkspaces(prev => prev.map(w => w.name === origName ? { ...w, ...updatedWs } : w));
    if (targetName && targetName !== origName) {
      if (activeWorkspace.toLowerCase() === origName.toLowerCase()) {
        setActiveWorkspace(targetName);
        updateUrlParams(targetName, activeSessionId);
      }
      if (sessionsCacheRef.current[origName]) {
        sessionsCacheRef.current[targetName] = sessionsCacheRef.current[origName];
        delete sessionsCacheRef.current[origName];
      }
      if (config) {
        const updated = { ...config, active_workspace: targetName };
        setConfig(updated);
        api.saveConfig(updated).catch(() => {});
      }
    }
    await refreshWorkspaces();
    return updatedWs;
  };

  const deleteWorkspace = async (name: string) => {
    if (name.toLowerCase() === 'default') return;
    if (activeWorkspace.toLowerCase() === name.toLowerCase()) {
      selectWorkspace('default');
    }
    setWorkspaces(prev => prev.filter(w => w.name !== name));
    await api.deleteWorkspace(name);
    await refreshWorkspaces();
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
    updateUrlParams(activeWorkspace, null);
  };

  const deleteSession = async (id: string) => {
    setSessions(prev => prev.filter(s => s.id !== id));
    if (activeSessionId === id) {
      const remaining = sessions.filter(s => s.id !== id);
      const nextId = remaining.length > 0 ? remaining[0].id : null;
      setActiveSessionId(nextId);
      updateUrlParams(activeWorkspace, nextId);
    }
    await api.deleteSession(id, activeWorkspace);
  };

  const readAttachedFile = async (file: File): Promise<AttachedFile> => {
    const isImage = file.type?.startsWith('image/') || /\.(png|jpe?g|gif|webp|svg|bmp|avif|ico|heic|heif|tiff?)$/i.test(file.name);

    if (isImage) {
      return new Promise((resolve) => {
        const reader = new FileReader();
        reader.onload = () => {
          resolve({
            name: file.name,
            size: file.size,
            type: file.type || 'image/png',
            url: (reader.result as string) || undefined
          });
        };
        reader.onerror = () => {
          resolve({
            name: file.name,
            size: file.size,
            type: file.type || 'image/png'
          });
        };
        reader.readAsDataURL(file);
      });
    }

    const isRichDoc = /\.(docx|docm|dotx|pdf)$/i.test(file.name);
    if (isRichDoc) {
      try {
        const base64Data = await new Promise<string>((resolve, reject) => {
          const reader = new FileReader();
          reader.onload = () => resolve(reader.result as string);
          reader.onerror = () => reject(new Error('Failed to read file'));
          reader.readAsDataURL(file);
        });

        const res = await api.parseFile(file.name, base64Data);
        if (res.success && res.text) {
          return {
            name: file.name,
            size: file.size,
            type: file.type || (file.name.toLowerCase().endsWith('.pdf') ? 'application/pdf' : 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'),
            content: res.text
          };
        }
      } catch (err) {
        console.warn('Document parse request failed, falling back:', err);
      }
    }

    // Text / code / markdown files: read text contents safely up to 2MB
    return new Promise((resolve) => {
      const reader = new FileReader();
      reader.onload = () => {
        resolve({
          name: file.name,
          size: file.size,
          type: file.type || 'text/plain',
          content: (reader.result as string) || ''
        });
      };
      reader.onerror = () => {
        resolve({
          name: file.name,
          size: file.size,
          type: file.type || 'application/octet-stream',
          content: ''
        });
      };
      const slice = file.slice(0, 2 * 1024 * 1024);
      reader.readAsText(slice);
    });
  };

  const sendMessage = async (content: string, options: SendOptions = { files: [], webSearch: false, tools: false }) => {
    if (!config) return;
    const hasFiles = options.files && options.files.length > 0;
    if (!content.trim() && !hasFiles) return;

    // 1. Process attachments (max 5)
    const attachedToProcess = (options.files || []).slice(0, 5);
    const processedFiles: AttachedFile[] = await Promise.all(
      attachedToProcess.map(readAttachedFile)
    );

    // 2. Format prompt for the AI including file text contents
    let promptForAI = content.trim();
    const textAttachments = processedFiles.filter(f => f.content && f.content.trim().length > 0);
    const imageAttachments = processedFiles.filter(f => f.url && (f.type.startsWith('image/') || f.url.startsWith('data:image')));

    if (textAttachments.length > 0) {
      const fileBlocks = textAttachments.map(f => {
        const ext = f.name.split('.').pop() || 'txt';
        const sizeKb = (f.size / 1024).toFixed(1);
        return `[Attached File: ${f.name} (${sizeKb} KB)]\n\`\`\`${ext}\n${f.content}\n\`\`\``;
      }).join('\n\n');

      if (promptForAI) {
        promptForAI = `${promptForAI}\n\n${fileBlocks}`;
      } else {
        promptForAI = `Please analyze the following attached file(s):\n\n${fileBlocks}`;
      }
    } else if (!promptForAI && imageAttachments.length > 0) {
      promptForAI = 'Please inspect and analyze the attached image.';
    } else if (!promptForAI && processedFiles.length > 0) {
      promptForAI = `Attached file(s): ${processedFiles.map(f => f.name).join(', ')}`;
    }

    const titleSubject = content.trim() || (processedFiles.length > 0 ? processedFiles[0].name : 'Chat');

    let currentSessionId = activeSessionId;
    let sessionToUpdate: ChatSession;
    let isBrandNewSession = false;

    // If in draft "New Chat" mode, initialize session on-the-fly when user sends their first message
    if (!currentSessionId) {
      isBrandNewSession = true;
      currentSessionId = Date.now().toString();
      const initialTitle = generateSmartTitleFallback(titleSubject);
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
      content: content.trim(),
      timestamp: Date.now(),
      files: processedFiles.length > 0 ? processedFiles : undefined,
      options: {
        files: processedFiles.map(f => f.name),
        webSearch: options.webSearch,
        tools: options.tools
      }
    };

    let title = sessionToUpdate.title;
    if (sessionToUpdate.messages.length === 0 && !isBrandNewSession) {
      title = generateSmartTitleFallback(titleSubject);
    }

    sessionToUpdate = {
      ...sessionToUpdate,
      title,
      messages: [...sessionToUpdate.messages, userMessage],
      updatedAt: Date.now()
    };

    setSessions(prev => prev.map(s => s.id === currentSessionId ? sessionToUpdate : s));

    const abortController = new AbortController();
    abortControllersRef.current.set(currentSessionId, abortController);
    setTypingSessionIds(prev => Array.from(new Set([...prev, currentSessionId])));

    if (typeof window !== 'undefined' && 'Notification' in window && Notification.permission === 'default') {
      Notification.requestPermission().catch(() => {});
    }

    let assistantContent = '';
    const assistantMessageId = (Date.now() + 1).toString();

    setSessions(prev => prev.map(s => {
      if (s.id !== currentSessionId) return s;
      return {
        ...s,
        messages: [
          ...s.messages,
          {
            id: assistantMessageId,
            role: 'assistant',
            content: '',
            timestamp: Date.now(),
            executionState: 'thinking',
            statusLabel: 'Thinking...'
          }
        ]
      };
    }));

    const imagePayloads = imageAttachments
      .map(f => {
        if (!f.url) return '';
        const commaIdx = f.url.indexOf(',');
        return commaIdx !== -1 ? f.url.slice(commaIdx + 1) : f.url;
      })
      .filter(Boolean);

    // Extract existing session messages before the current turn for full multi-turn context
    const priorHistory = (sessionToUpdate.messages || [])
      .filter(m => m.id !== userMessage.id && m.id !== assistantMessageId);

    try {
      const res = await api.sendMessage(
        promptForAI,
        config,
        { ...options, sessionId: currentSessionId },
        (chunk) => {
          assistantContent += chunk;
          setSessions(prev => prev.map(s => {
            if (s.id !== currentSessionId) return s;
            const msgs = [...s.messages];
            const idx = msgs.findIndex(m => m.id === assistantMessageId);
            if (idx !== -1) {
              msgs[idx] = {
                ...msgs[idx],
                content: assistantContent,
                executionState: 'generating',
                statusLabel: 'Generating...'
              };
            }
            return { ...s, messages: msgs };
          }));
        },
        imagePayloads.length > 0 ? imagePayloads : undefined,
        priorHistory,
        (evt) => {
          setSessions(prev => prev.map(s => {
            if (s.id !== currentSessionId) return s;
            const msgs = [...s.messages];
            const idx = msgs.findIndex(m => m.id === assistantMessageId);
            if (idx === -1) return s;

            let nextState: ExecutionState = msgs[idx].executionState || 'idle';
            let nextLabel: string | undefined = msgs[idx].statusLabel;

            switch (evt.event) {
              case 'routing':
                nextState = 'thinking';
                nextLabel = 'Thinking...';
                break;
              case 'thinking_start':
                nextState = 'thinking';
                nextLabel = 'Thinking...';
                break;
              case 'thinking_end':
                if (nextState === 'thinking') {
                  nextState = 'generating';
                  nextLabel = 'Generating...';
                }
                break;
              case 'tool_start': {
                nextState = 'tool';
                const toolName = (evt.data?.tool || '').toLowerCase();
                if (toolName === 'web_search') {
                  nextLabel = 'Searching...';
                } else if (toolName.includes('python') || toolName.includes('code') || toolName.includes('terminal')) {
                  nextLabel = 'Running Python...';
                } else if (evt.data?.label) {
                  nextLabel = evt.data.label;
                } else {
                  nextLabel = `Running ${evt.data?.tool || 'tool'}...`;
                }
                break;
              }
              case 'tool_end':
                break;
              case 'response_start':
              case 'response_token':
                nextState = 'generating';
                nextLabel = 'Generating...';
                break;
              case 'done':
                nextState = 'done';
                nextLabel = undefined;
                break;
              case 'error':
                nextState = 'error';
                nextLabel = evt.data?.message || 'Error';
                break;
            }

            msgs[idx] = {
              ...msgs[idx],
              executionState: nextState,
              statusLabel: nextLabel
            };
            return { ...s, messages: msgs };
          }));
        },
        abortController.signal
      );

      if (!assistantContent.trim() && res && res.trim()) {
        assistantContent = res.trim();
        setSessions(prev => prev.map(s => {
          if (s.id !== currentSessionId) return s;
          const msgs = [...s.messages];
          const idx = msgs.findIndex(m => m.id === assistantMessageId);
          if (idx !== -1) msgs[idx] = { ...msgs[idx], content: assistantContent };
          return { ...s, messages: msgs };
        }));
      }

      // Check if user navigated to a different session while generating
      if (activeSessionIdRef.current !== currentSessionId) {
        setUnreadSessionIds(prev => Array.from(new Set([...prev, currentSessionId])));
        const notifTitle = sessionToUpdate.title || title || 'Chat';
        setSessionNotification({
          id: Date.now().toString(),
          sessionId: currentSessionId,
          sessionTitle: notifTitle,
          message: `AI finished responding in "${notifTitle}"`
        });
        if (typeof window !== 'undefined' && 'Notification' in window && Notification.permission === 'granted') {
          try {
            const notif = new Notification('LocaLLM', {
              body: `AI finished responding in "${notifTitle}"`,
              icon: '/favicon.ico'
            });
            notif.onclick = () => {
              window.focus();
              setActiveSessionId(currentSessionId);
            };
          } catch {}
        }
      }
    } catch (err: any) {
      if (err?.name === 'AbortError' || abortController.signal.aborted) {
        // User aborted/stopped generation: preserve partial content cleanly
      } else {
        const errMsg = `[Kendala Koneksi]: Gagal menghubungi model (${err?.message || 'Network error'}).`;
        assistantContent = errMsg;
        setSessions(prev => prev.map(s => {
          if (s.id !== currentSessionId) return s;
          const msgs = [...s.messages];
          const idx = msgs.findIndex(m => m.id === assistantMessageId);
          if (idx !== -1) msgs[idx] = { ...msgs[idx], content: errMsg, executionState: 'error', statusLabel: errMsg };
          return { ...s, messages: msgs };
        }));
      }
    } finally {
      abortControllersRef.current.delete(currentSessionId);
      setTypingSessionIds(prev => prev.filter(id => id !== currentSessionId));
    }

    if (!assistantContent.trim()) {
      assistantContent = 'Tidak ada respon yang diterima dari model. Silakan coba ajukan pertanyaan kembali atau gunakan model lain.';
      setSessions(prev => prev.map(s => {
        if (s.id !== currentSessionId) return s;
        const msgs = [...s.messages];
        const idx = msgs.findIndex(m => m.id === assistantMessageId);
        if (idx !== -1) msgs[idx] = { ...msgs[idx], content: assistantContent, executionState: 'done' };
        return { ...s, messages: msgs };
      }));
    }

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
          executionState: 'done',
          statusLabel: undefined,
          sources: sources.length > 0 ? sources : undefined
        }
      ],
      updatedAt: Date.now()
    };
    setSessions(prev => prev.map(s => s.id === updated.id ? updated : s));
    await api.saveSession(updated);

    // Asynchronously generate concise, goal-oriented AI chat title in background if first turn
    if (sessionToUpdate.messages.length <= 1) {
      api.generateTitle(titleSubject, config).then(aiTitle => {
        const cleanTitle = sanitizeChatTitle(aiTitle, '');
        if (cleanTitle && cleanTitle.length > 1) {
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

    const abortController = new AbortController();
    abortControllersRef.current.set(currentSessionId, abortController);
    setTypingSessionIds(prev => Array.from(new Set([...prev, currentSessionId])));

    let assistantContent = '';
    setSessions(prev => prev.map(s => {
      if (s.id !== currentSessionId) return s;
      const msgs = [...s.messages];
      const idx = msgs.findIndex(m => m.id === assistantMessageId);
      if (idx !== -1) {
        msgs[idx] = { ...msgs[idx], content: '', sources: undefined, executionState: 'thinking', statusLabel: 'Thinking...' };
      }
      return { ...s, messages: msgs };
    }));

    const targetIdx = session.messages.findIndex((m: Message) => m.id === assistantMessageId);
    const priorHistory = targetIdx > 1
      ? session.messages.slice(0, targetIdx - 1)
      : [];

    try {
      const res = await api.sendMessage(
        userPrompt,
        config,
        userOptions,
        (chunk) => {
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
        },
        undefined,
        priorHistory,
        (evt) => {
          setSessions(prev => prev.map(s => {
            if (s.id !== currentSessionId) return s;
            const msgs = [...s.messages];
            const idx = msgs.findIndex(m => m.id === assistantMessageId);
            if (idx === -1) return s;

            let nextState: ExecutionState = msgs[idx].executionState || 'idle';
            let nextLabel: string | undefined = msgs[idx].statusLabel;

            switch (evt.event) {
              case 'routing':
                nextState = 'thinking';
                nextLabel = 'Thinking...';
                break;
              case 'thinking_start':
                nextState = 'thinking';
                nextLabel = 'Thinking...';
                break;
              case 'thinking_end':
                if (nextState === 'thinking') {
                  nextState = 'generating';
                  nextLabel = 'Generating...';
                }
                break;
              case 'tool_start': {
                nextState = 'tool';
                const toolName = (evt.data?.tool || '').toLowerCase();
                if (toolName === 'web_search') {
                  nextLabel = 'Searching...';
                } else if (toolName.includes('python') || toolName.includes('code') || toolName.includes('terminal')) {
                  nextLabel = 'Running Python...';
                } else if (evt.data?.label) {
                  nextLabel = evt.data.label;
                } else {
                  nextLabel = `Running ${evt.data?.tool || 'tool'}...`;
                }
                break;
              }
              case 'tool_end':
                break;
              case 'response_start':
              case 'response_token':
                nextState = 'generating';
                nextLabel = 'Generating...';
                break;
              case 'done':
                nextState = 'done';
                nextLabel = undefined;
                break;
              case 'error':
                nextState = 'error';
                nextLabel = evt.data?.message || 'Error';
                break;
            }

            msgs[idx] = {
              ...msgs[idx],
              executionState: nextState,
              statusLabel: nextLabel
            };
            return { ...s, messages: msgs };
          }));
        },
        abortController.signal
      );

      if (!assistantContent.trim() && res && res.trim()) {
        assistantContent = res.trim();
      }

      if (activeSessionIdRef.current !== currentSessionId) {
        setUnreadSessionIds(prev => Array.from(new Set([...prev, currentSessionId])));
        const notifTitle = session.title || 'Chat';
        setSessionNotification({
          id: Date.now().toString(),
          sessionId: currentSessionId,
          sessionTitle: notifTitle,
          message: `AI finished responding in "${notifTitle}"`
        });
      }
    } catch (err: any) {
      if (err?.name === 'AbortError' || abortController.signal.aborted) {
        // User stopped generation
      } else {
        assistantContent = `[Kendala Koneksi]: Gagal menghubungi model (${err?.message || 'Network error'}).`;
      }
    } finally {
      abortControllersRef.current.delete(currentSessionId);
      setTypingSessionIds(prev => prev.filter(id => id !== currentSessionId));
    }

    if (!assistantContent.trim()) {
      assistantContent = 'Tidak ada respon yang diterima dari model. Silakan periksa koneksi atau coba klik kembali.';
    }

    setSessions(prev => prev.map(s => {
      if (s.id !== currentSessionId) return s;
      const msgs = [...s.messages];
      const idx = msgs.findIndex(m => m.id === assistantMessageId);
      if (idx !== -1) {
        msgs[idx] = { ...msgs[idx], content: assistantContent };
      }
      return { ...s, messages: msgs };
    }));

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
    typingSessionIds,
    unreadSessionIds,
    sessionNotification,
    clearUnreadSession,
    dismissNotification,
    stopGeneration,
    refreshModels,
    refreshWorkspaces
  };
}
