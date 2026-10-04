import { useEffect, useState } from 'react';
import clsx from 'clsx';
import { Sidebar } from './components/Sidebar';
import { ChatContainer } from './components/ChatContainer';
import { ChatInput } from './components/ChatInput';
import { SettingsModal } from './components/SettingsModal';
import { ThemeToggle } from './components/ThemeToggle';
import { AuroraBackground } from './components/AuroraBackground';
import { EmptyState } from './components/EmptyState';
import { useLocaLLM } from './hooks/useLocaLLM';
import { Menu, PanelLeftOpen } from 'lucide-react';
import { motion, AnimatePresence, LayoutGroup, useSpring, useTransform } from 'motion/react';
import type { ModelInfo } from './types';

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
    sessions,
    activeSessionId,
    setActiveSessionId,
    activeSession,
    createSession,
    deleteSession,
    sendMessage,
    isTyping
  } = useLocaLLM();

  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [isMobileSidebarOpen, setIsMobileSidebarOpen] = useState(false);
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);

  const isEmptyChat = (activeSession?.messages.length ?? 0) === 0;

  // Under-damped spring so the sidebar overshoots and settles (bounce) on both collapse and expand.
  // The width can never go negative, so the overshoot on collapse is clamped at 0.
  const SIDEBAR_WIDTH = 256;
  const sidebarSpring = useSpring(SIDEBAR_WIDTH, { stiffness: 320, damping: 15, mass: 0.9 });
  const sidebarWidth = useTransform(sidebarSpring, (v) => Math.max(0, v));
  useEffect(() => {
    sidebarSpring.set(isSidebarCollapsed ? 0 : SIDEBAR_WIDTH);
  }, [isSidebarCollapsed, sidebarSpring]);

  const handleChangeModel = (model: ModelInfo) => {
    if (!config) return;
    updateConfig({ ...config, model: model.id, provider: model.provider });
  };

  return (
    <div className="relative flex h-[100dvh] w-full overflow-hidden text-slate-800 dark:text-slate-100">
      <AuroraBackground intense={isEmptyChat} />

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
            onCreateWorkspace={createWorkspace}
            sessions={sessions}
            activeSessionId={activeSessionId}
            onSelectSession={setActiveSessionId}
            onNewSession={createSession}
            onDeleteSession={deleteSession}
            onOpenSettings={() => setIsSettingsOpen(true)}
            onCollapse={() => setIsSidebarCollapsed(true)}
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
                  onCreateWorkspace={createWorkspace}
                  sessions={sessions}
                  activeSessionId={activeSessionId}
                  onSelectSession={(id) => { setActiveSessionId(id); setIsMobileSidebarOpen(false); }}
                  onNewSession={() => { createSession(); setIsMobileSidebarOpen(false); }}
                  onDeleteSession={deleteSession}
                  onOpenSettings={() => { setIsSettingsOpen(true); setIsMobileSidebarOpen(false); }}
                  onCollapse={() => setIsMobileSidebarOpen(false)}
                />
              </LayoutGroup>
            </motion.div>
          </>
        )}
      </AnimatePresence>

      <main className="flex-1 flex flex-col min-w-0 relative h-[100dvh] z-10">
        {/* Floating header: no bar, no divider, only glass pills */}
        <header className="h-14 shrink-0 flex items-center justify-between px-3 md:px-4 pt-2">
          <div className="flex items-center gap-2 min-w-0">
            <AnimatePresence initial={false}>
              {isSidebarCollapsed && (
                <motion.button
                  key="expand"
                  initial={{ scale: 0, opacity: 0 }}
                  animate={{ scale: 1, opacity: 1 }}
                  exit={{ scale: 0, opacity: 0 }}
                  transition={{ type: 'spring', stiffness: 520, damping: 16 }}
                  onClick={() => setIsSidebarCollapsed(false)}
                  className="hidden md:flex w-9 h-9 items-center justify-center rounded-full liquid-glass text-slate-700 dark:text-slate-200 hover:bg-black/5 dark:hover:bg-white/10 cursor-pointer"
                  title="Expand sidebar"
                  aria-label="Expand sidebar"
                >
                  <PanelLeftOpen className="w-4 h-4" />
                </motion.button>
              )}
            </AnimatePresence>
            <button
              onClick={() => setIsMobileSidebarOpen(true)}
              className="md:hidden w-9 h-9 flex items-center justify-center rounded-full liquid-glass text-slate-700 dark:text-slate-200 cursor-pointer"
              aria-label="Open menu"
            >
              <Menu className="w-4 h-4" />
            </button>

            <div className="h-9 px-4 rounded-full liquid-glass flex items-center gap-2 min-w-0">
              <span className="hidden sm:inline text-xs font-medium text-blue-700 dark:text-blue-300">{activeWorkspace}</span>
              <span className="hidden sm:inline text-slate-400">/</span>
              <h2 className="text-xs font-medium truncate text-slate-800 dark:text-slate-100 max-w-[180px] sm:max-w-xs md:max-w-md">
                {activeSession?.title || 'New conversation'}
              </h2>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <ThemeToggle />
          </div>
        </header>

        {/* One shared layout: on a new chat the greeting + input sit centred, and once a message
            exists the input springs down to the bottom. The input stays mounted so it animates
            instead of re-rendering. */}
        <div className={clsx('flex-1 flex flex-col min-h-0', isEmptyChat && 'justify-center pb-10')}>
          {isEmptyChat ? (
            <EmptyState workspace={activeWorkspace} />
          ) : (
            <ChatContainer messages={activeSession?.messages || []} isTyping={isTyping} />
          )}

          <motion.div
            layout="position"
            transition={{ type: 'spring', stiffness: 220, damping: 20, mass: 0.9 }}
            className="shrink-0 w-full relative z-10"
          >
            <ChatInput
              onSend={sendMessage}
              disabled={!activeSessionId || isTyping}
              models={models}
              currentModelId={config?.model ?? ''}
              onChangeModel={handleChangeModel}
            />
          </motion.div>
        </div>
      </main>

      <SettingsModal
        isOpen={isSettingsOpen}
        onClose={() => setIsSettingsOpen(false)}
        config={config}
        onSave={updateConfig}
        isSyncing={isConfigSyncing}
      />
    </div>
  );
}

export default App;
