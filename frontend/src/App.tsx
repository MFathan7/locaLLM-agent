import { useEffect, useState } from 'react';
import clsx from 'clsx';
import { Sidebar } from './components/Sidebar';
import { ChatContainer } from './components/ChatContainer';
import { ChatInput } from './components/ChatInput';
import { SettingsModal } from './components/SettingsModal';
import { ThemeToggle } from './components/ThemeToggle';
import { AuroraBackground } from './components/AuroraBackground';
import { EmptyState } from './components/EmptyState';
import { SearchOverlay } from './components/SearchOverlay';
import { SourcesPanel } from './components/SourcesPanel';
import { ConfirmModal } from './components/ConfirmModal';
import { WorkspaceModal } from './components/WorkspaceModal';
import { WorkspaceIcon } from './components/WorkspaceIcon';
import { useLocaLLM } from './hooks/useLocaLLM';
import { Menu, PanelLeftOpen, Search, Trash2 } from 'lucide-react';
import { motion, AnimatePresence, LayoutGroup, useSpring, useTransform } from 'motion/react';
import type { ModelInfo, Message, Workspace, WorkspaceSkill } from './types';

function App() {
  const {
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
    refreshModels,
    refreshWorkspaces
  } = useLocaLLM();

  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [isSearchOpen, setIsSearchOpen] = useState(false);
  const [isMobileSidebarOpen, setIsMobileSidebarOpen] = useState(false);
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
  const [selectedSourceMessage, setSelectedSourceMessage] = useState<Message | null>(null);
  const [pendingDelete, setPendingDelete] = useState<{
    type: 'session' | 'workspace';
    id: string;
    name: string;
  } | null>(null);

  // Workspace setup and edit modal state
  const [workspaceModalState, setWorkspaceModalState] = useState<{
    isOpen: boolean;
    mode: 'create' | 'edit';
    workspace?: Workspace | null;
  }>({ isOpen: false, mode: 'create', workspace: null });

  const handleOpenCreateWorkspace = (name: string) => {
    setWorkspaceModalState({
      isOpen: true,
      mode: 'create',
      workspace: {
        name,
        icon: 'Folder',
        color: '#3B82F6',
        custom_instructions: '',
        skills: []
      }
    });
  };

  const handleOpenEditWorkspace = (ws: Workspace) => {
    setWorkspaceModalState({
      isOpen: true,
      mode: 'edit',
      workspace: ws
    });
  };

  const handleSaveWorkspaceModal = async (data: {
    name: string;
    oldName?: string;
    description?: string;
    icon: string;
    color: string;
    custom_instructions: string;
    auto_memory?: boolean;
    skills: WorkspaceSkill[];
    deletedSkills?: WorkspaceSkill[];
  }) => {
    if (workspaceModalState.mode === 'create') {
      await createWorkspace(data);
    } else {
      await updateWorkspace(data.oldName || data.name, data);
    }
  };

  const handleConfirmDelete = async () => {
    if (!pendingDelete) return;
    if (pendingDelete.type === 'session') {
      await deleteSession(pendingDelete.id);
    } else if (pendingDelete.type === 'workspace') {
      await deleteWorkspace(pendingDelete.id);
    }
    setPendingDelete(null);
  };

  // Clear sources selection when active session switches
  useEffect(() => {
    setSelectedSourceMessage(null);
  }, [activeSessionId]);

  const isEmptyChat = (activeSession?.messages.length ?? 0) === 0;

  // Smooth, softly damped spring: provides a gentle, premium glide without aggressive oscillation
  const SIDEBAR_WIDTH = 256;
  const sidebarSpring = useSpring(SIDEBAR_WIDTH, { stiffness: 240, damping: 28, mass: 0.8 });
  const sidebarWidth = useTransform(sidebarSpring, (v) => Math.max(0, v));
  useEffect(() => {
    sidebarSpring.set(isSidebarCollapsed ? 0 : SIDEBAR_WIDTH);
  }, [isSidebarCollapsed, sidebarSpring]);

  // Keyboard shortcut listener: Cmd/Ctrl+K or Cmd/Ctrl+F to toggle search mode
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && (e.key === 'f' || e.key === 'k')) {
        e.preventDefault();
        setIsSearchOpen(prev => !prev);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  const handleChangeModel = (model: ModelInfo) => {
    if (!config) return;
    updateConfig({
      ...config,
      default_model: model.id,
      model: model.id,
      provider: model.provider,
      ...(model.provider === 'ollama' ? { ollama_model: model.id } : {})
    });
  };

  return (
    <div className="relative flex h-[100dvh] w-full overflow-hidden text-slate-800 dark:text-slate-100">
      <AuroraBackground intense={isEmptyChat && !isSearchOpen} />

      {/* Desktop sidebar. Always mounted; its width is driven by a bouncy spring.
          The panel is pinned to the right edge so it slides in/out from the left. */}
      <motion.aside
        style={{ width: sidebarWidth }}
        inert={isSidebarCollapsed}
        aria-hidden={isSidebarCollapsed}
        className="hidden md:block overflow-hidden relative z-20 shrink-0"
      >
        <div className="absolute inset-y-0 right-0 w-64">
          <Sidebar
            workspaces={workspaces}
            activeWorkspace={activeWorkspace}
            onSelectWorkspace={selectWorkspace}
            onCreateWorkspace={handleOpenCreateWorkspace}
            onEditWorkspace={handleOpenEditWorkspace}
            onDeleteWorkspace={(name) => setPendingDelete({ type: 'workspace', id: name, name })}
            sessions={sessions}
            activeSessionId={activeSessionId}
            onSelectSession={setActiveSessionId}
            onNewSession={createSession}
            onDeleteSession={(id, title) => setPendingDelete({ type: 'session', id, name: title || 'this chat' })}
            onOpenSettings={() => setIsSettingsOpen(true)}
            onCollapse={() => setIsSidebarCollapsed(true)}
            onOpenSearch={() => setIsSearchOpen(true)}
          />
        </div>
      </motion.aside>

      {/* Mobile sidebar overlay. LayoutGroup keeps its droplet separate from the desktop one. */}
      <AnimatePresence>
        {isMobileSidebarOpen && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setIsMobileSidebarOpen(false)}
              className="md:hidden fixed inset-0 bg-black/30 z-30"
            />
            <motion.div
              initial={{ x: '-110%' }}
              animate={{ x: 0 }}
              exit={{ x: '-110%' }}
              transition={{ type: 'spring', damping: 17, stiffness: 240 }}
              className="md:hidden fixed inset-y-0 left-0 z-40"
            >
              <LayoutGroup id="mobile-sidebar">
                <Sidebar
                  workspaces={workspaces}
                  activeWorkspace={activeWorkspace}
                  onSelectWorkspace={(ws) => { selectWorkspace(ws); setIsMobileSidebarOpen(false); }}
                  onCreateWorkspace={(name) => { handleOpenCreateWorkspace(name); setIsMobileSidebarOpen(false); }}
                  onEditWorkspace={(ws) => { handleOpenEditWorkspace(ws); setIsMobileSidebarOpen(false); }}
                  onDeleteWorkspace={(name) => { setPendingDelete({ type: 'workspace', id: name, name }); setIsMobileSidebarOpen(false); }}
                  sessions={sessions}
                  activeSessionId={activeSessionId}
                  onSelectSession={(id) => { setActiveSessionId(id); setIsMobileSidebarOpen(false); }}
                  onNewSession={() => { createSession(); setIsMobileSidebarOpen(false); }}
                  onDeleteSession={(id, title) => { setPendingDelete({ type: 'session', id, name: title || 'this chat' }); setIsMobileSidebarOpen(false); }}
                  onOpenSettings={() => { setIsSettingsOpen(true); setIsMobileSidebarOpen(false); }}
                  onCollapse={() => setIsMobileSidebarOpen(false)}
                  onOpenSearch={() => { setIsSearchOpen(true); setIsMobileSidebarOpen(false); }}
                />
              </LayoutGroup>
            </motion.div>
          </>
        )}
      </AnimatePresence>

      <main className="flex-1 flex flex-col min-w-0 relative h-[100dvh] z-10">
        {/* Floating header: no bar, no divider, only glass pills */}
        <header className="h-14 shrink-0 flex items-center justify-between px-3 md:px-4 pt-2">
          <div className="flex items-center gap-1.5 md:gap-2 min-w-0">
            {/* Desktop collapsed controls: Expand sidebar + Search icon appear ONLY when sidebar is closed */}
            <AnimatePresence initial={false}>
              {isSidebarCollapsed && (
                <motion.div
                  key="desktop-collapsed-controls"
                  initial={{ opacity: 0, width: 0 }}
                  animate={{ opacity: 1, width: 'auto' }}
                  exit={{ opacity: 0, width: 0 }}
                  transition={{ type: 'spring', stiffness: 280, damping: 26 }}
                  className="hidden md:flex items-center gap-1.5 overflow-hidden shrink-0"
                >
                  <button
                    onClick={() => setIsSidebarCollapsed(false)}
                    className="w-9 h-9 flex items-center justify-center rounded-full liquid-glass text-slate-700 dark:text-slate-200 hover:bg-black/5 dark:hover:bg-white/10 cursor-pointer shrink-0"
                    title="Expand sidebar"
                    aria-label="Expand sidebar"
                  >
                    <PanelLeftOpen className="w-4 h-4" />
                  </button>

                  <button
                    onClick={() => setIsSearchOpen(v => !v)}
                    className={clsx(
                      "w-9 h-9 flex items-center justify-center rounded-full liquid-glass cursor-pointer transition-colors shrink-0",
                      isSearchOpen
                        ? "bg-blue-600 text-white shadow-xs"
                        : "text-slate-700 dark:text-slate-200 hover:text-blue-600 dark:hover:text-blue-400 hover:bg-black/5 dark:hover:bg-white/10"
                    )}
                    title="Search conversation messages (Ctrl+F / ⌘K)"
                    aria-label="Search conversation messages"
                  >
                    <Search className="w-4 h-4" />
                  </button>
                </motion.div>
              )}
            </AnimatePresence>

            {/* Mobile controls */}
            <div className="md:hidden flex items-center gap-1.5 shrink-0">
              <button
                onClick={() => setIsMobileSidebarOpen(true)}
                className="w-9 h-9 flex items-center justify-center rounded-full liquid-glass text-slate-700 dark:text-slate-200 cursor-pointer"
                aria-label="Open menu"
              >
                <Menu className="w-4 h-4" />
              </button>
              <button
                onClick={() => setIsSearchOpen(v => !v)}
                className={clsx(
                  "w-9 h-9 flex items-center justify-center rounded-full liquid-glass cursor-pointer transition-colors",
                  isSearchOpen
                    ? "bg-blue-600 text-white shadow-xs"
                    : "text-slate-700 dark:text-slate-200 hover:text-blue-600 dark:hover:text-blue-400"
                )}
                title="Search conversation messages"
                aria-label="Search conversation messages"
              >
                <Search className="w-4 h-4" />
              </button>
            </div>

            {/* Current conversation title glass pill */}
            <div className="h-9 px-3.5 rounded-full liquid-glass flex items-center gap-2 min-w-0">
              <span className="hidden sm:inline-flex items-center gap-1.5 text-xs font-semibold text-slate-800 dark:text-slate-200">
                <WorkspaceIcon
                  icon={workspaces.find(w => w.name === activeWorkspace)?.icon || 'Folder'}
                  color={workspaces.find(w => w.name === activeWorkspace)?.color || '#3B82F6'}
                  className="w-4 h-4"
                />
                <span>{activeWorkspace}</span>
              </span>
              <span className="hidden sm:inline text-slate-400">/</span>
              <h2 className="text-xs font-medium truncate text-slate-800 dark:text-slate-100 max-w-[180px] sm:max-w-xs md:max-w-md">
                {activeSession?.title || 'New conversation'}
              </h2>
              {activeSession && activeSession.messages && activeSession.messages.length > 0 && (
                <button
                  type="button"
                  onClick={() => setPendingDelete({
                    type: 'session',
                    id: activeSession.id,
                    name: activeSession.title || 'this chat'
                  })}
                  className="p-1 -mr-1 rounded-full text-slate-400 hover:text-red-600 dark:hover:text-red-400 hover:bg-black/5 dark:hover:bg-white/10 transition-colors cursor-pointer shrink-0"
                  title="Delete current chat"
                  aria-label="Delete current chat"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              )}
            </div>
          </div>

          <div className="flex items-center gap-2">
            <ThemeToggle />
          </div>
        </header>

        {/* Center Area: Search mode replaces the active chat view when active */}
        {isSearchOpen ? (
          <SearchOverlay
            isOpen={isSearchOpen}
            onClose={() => setIsSearchOpen(false)}
            sessions={sessions}
            workspaces={workspaces}
            activeWorkspace={activeWorkspace}
            onSelectSession={(sessionId, ws) => {
              setIsSearchOpen(false);
              if (ws && ws !== activeWorkspace) {
                selectWorkspace(ws);
              }
              setActiveSessionId(sessionId);
            }}
          />
        ) : (
          /* One shared layout: on a new chat the greeting + input sit centred, and once a message
              exists the input springs down to the bottom. The input stays mounted so it animates
              instead of re-rendering. */
          <div className="flex-1 flex min-h-0 overflow-hidden relative">
            <div className={clsx('flex-1 flex flex-col min-h-0', isEmptyChat && 'justify-center pb-10')}>
              {isEmptyChat ? (
                <EmptyState
                  key={activeSession?.id || `new-${activeWorkspace}`}
                  workspace={activeWorkspace}
                  userName={config?.user_name}
                  onSelectPrompt={(prompt) => sendMessage(prompt)}
                />
              ) : (
                <ChatContainer
                  messages={activeSession?.messages || []}
                  isTyping={isTyping}
                  selectedSourceMessageId={selectedSourceMessage?.id}
                  onToggleSources={(msg) => setSelectedSourceMessage(curr => curr?.id === msg.id ? null : msg)}
                  sessionTitle={activeSession?.title}
                  onRegenerate={(msg) => regenerateMessage(msg.id)}
                />
              )}

              <motion.div
                layout="position"
                transition={{ type: 'spring', stiffness: 220, damping: 20, mass: 0.9 }}
                className="shrink-0 w-full relative z-10"
              >
                <ChatInput
                  onSend={sendMessage}
                  disabled={isTyping}
                  models={models}
                  currentModelId={config?.default_model || config?.model || ''}
                  onChangeModel={handleChangeModel}
                  activePlatform={config?.active_backend}
                />
              </motion.div>
            </div>

            {/* Sources Side Panel */}
            <AnimatePresence>
              {selectedSourceMessage && (
                <SourcesPanel
                  message={selectedSourceMessage}
                  onClose={() => setSelectedSourceMessage(null)}
                />
              )}
            </AnimatePresence>
          </div>
        )}
      </main>

      <SettingsModal
        isOpen={isSettingsOpen}
        onClose={() => setIsSettingsOpen(false)}
        config={config}
        onSave={updateConfig}
        isSyncing={isConfigSyncing}
        onRefreshModels={refreshModels}
      />

      <ConfirmModal
        isOpen={pendingDelete !== null}
        title={pendingDelete?.type === 'workspace' ? 'Delete Workspace' : 'Delete Chat'}
        description={
          pendingDelete?.type === 'workspace'
            ? `Are you sure you want to delete workspace "${pendingDelete?.name}"? All sessions and files in this workspace will be deleted.`
            : `Are you sure you want to delete "${pendingDelete?.name}"? This chat conversation will be permanently removed.`
        }
        confirmLabel="Confirm Delete"
        cancelLabel="Cancel"
        onConfirm={handleConfirmDelete}
        onClose={() => setPendingDelete(null)}
      />

      <WorkspaceModal
        isOpen={workspaceModalState.isOpen}
        mode={workspaceModalState.mode}
        workspace={workspaceModalState.workspace}
        onSave={handleSaveWorkspaceModal}
        onClose={() => setWorkspaceModalState(prev => ({ ...prev, isOpen: false }))}
        onReload={refreshWorkspaces}
      />
    </div>
  );
}

export default App;
