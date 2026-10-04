import { useState } from 'react';
import {
  MessageSquare,
  Plus,
  Settings,
  Trash2,
  PanelLeftClose,
  Check,
  X
} from 'lucide-react';
import type { ChatSession, Workspace } from '../types';
import { motion } from 'motion/react';
import clsx from 'clsx';

interface SidebarProps {
  workspaces: Workspace[];
  activeWorkspace: string;
  onSelectWorkspace: (name: string) => void;
  onCreateWorkspace: (name: string) => void;
  sessions: ChatSession[];
  activeSessionId: string | null;
  onSelectSession: (id: string) => void;
  onNewSession: () => void;
  onDeleteSession: (id: string) => void;
  onOpenSettings: () => void;
  onCollapse: () => void;
}

// A slightly under-damped spring: the droplet overshoots and settles like iOS liquid glass.
const liquidSpring = { type: 'spring', stiffness: 380, damping: 24, mass: 0.9 } as const;

export function Sidebar({
  workspaces,
  activeWorkspace,
  onSelectWorkspace,
  onCreateWorkspace,
  sessions,
  activeSessionId,
  onSelectSession,
  onNewSession,
  onDeleteSession,
  onOpenSettings,
  onCollapse
}: SidebarProps) {
  const [isAddingWorkspace, setIsAddingWorkspace] = useState(false);
  const [newWsName, setNewWsName] = useState('');

  const handleCreateWorkspace = () => {
    if (newWsName.trim()) {
      onCreateWorkspace(newWsName.trim());
      setNewWsName('');
      setIsAddingWorkspace(false);
    }
  };

  const handleKeyDownWs = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') handleCreateWorkspace();
    if (e.key === 'Escape') {
      setIsAddingWorkspace(false);
      setNewWsName('');
    }
  };

  return (
    <div className="w-60 h-[calc(100dvh-1rem)] m-2 rounded-[28px] liquid-glass flex flex-col select-none">
      {/* Header */}
      <div className="h-12 pl-4 pr-2.5 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 rounded-lg bg-gradient-to-br from-sky-500 to-blue-600 flex items-center justify-center text-white font-bold text-xs shadow-[inset_0_1px_1px_rgba(255,255,255,0.5)]">
            L
          </div>
          <span className="font-semibold text-sm tracking-tight text-slate-800 dark:text-slate-100">LocaLLM</span>
        </div>
        <button
          onClick={onCollapse}
          className="p-1.5 rounded-full text-slate-600 hover:text-slate-900 dark:text-slate-300 dark:hover:text-white hover:bg-black/[0.06] dark:hover:bg-white/10 transition-colors cursor-pointer"
          title="Collapse sidebar"
          aria-label="Collapse sidebar"
        >
          <PanelLeftClose className="w-4 h-4" />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto px-2.5 pb-2 space-y-3">
        {/* Workspace */}
        <section>
          <div className="px-2 py-1 flex items-center justify-between text-[11px] font-semibold tracking-wider text-slate-600 dark:text-slate-400 uppercase">
            <span>Workspace</span>
            <button
              onClick={() => setIsAddingWorkspace(v => !v)}
              className="p-1 rounded-full hover:bg-black/[0.06] dark:hover:bg-white/10 transition-colors cursor-pointer"
              title="Add workspace"
              aria-label="Add workspace"
            >
              <Plus className="w-3.5 h-3.5" />
            </button>
          </div>

          {isAddingWorkspace && (
            <motion.div
              initial={{ opacity: 0, scale: 0.92, y: -4 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              transition={liquidSpring}
              className="mt-1 mb-1.5"
            >
              <div className="flex items-center gap-1 pl-3 pr-1 py-1 rounded-full bg-black/[0.07] dark:bg-white/10">
                <input
                  type="text"
                  value={newWsName}
                  onChange={(e) => setNewWsName(e.target.value)}
                  onKeyDown={handleKeyDownWs}
                  placeholder="workspace-name"
                  autoFocus
                  className="w-full bg-transparent text-xs text-slate-800 dark:text-slate-100 placeholder:text-slate-500 focus:outline-none"
                />
                <button onClick={handleCreateWorkspace} className="p-1 rounded-full text-emerald-700 dark:text-emerald-400 hover:bg-black/[0.06] dark:hover:bg-white/10 cursor-pointer" aria-label="Create">
                  <Check className="w-3.5 h-3.5" />
                </button>
                <button onClick={() => { setIsAddingWorkspace(false); setNewWsName(''); }} className="p-1 rounded-full text-slate-500 hover:bg-black/[0.06] dark:hover:bg-white/10 cursor-pointer" aria-label="Cancel">
                  <X className="w-3.5 h-3.5" />
                </button>
              </div>
            </motion.div>
          )}

          {/* The liquid droplet (layoutId) slides between workspaces */}
          <div className="mt-0.5 space-y-0.5">
            {workspaces.map((ws) => {
              const isActive = activeWorkspace === ws.name;
              return (
                <button
                  key={ws.name}
                  onClick={() => onSelectWorkspace(ws.name)}
                  className={clsx(
                    'relative w-full flex items-center px-3 py-2 rounded-2xl text-[13px] text-left cursor-pointer transition-colors',
                    isActive
                      ? 'text-slate-900 dark:text-white font-medium'
                      : 'text-slate-700 dark:text-slate-300 hover:bg-black/[0.04] dark:hover:bg-white/[0.06]'
                  )}
                >
                  {isActive && (
                    <motion.span
                      layoutId="workspace-droplet"
                      transition={liquidSpring}
                      className="absolute inset-0 rounded-2xl liquid-pill"
                    />
                  )}
                  <span className="relative truncate">{ws.name}</span>
                </button>
              );
            })}
          </div>
        </section>

        <div className="mx-2 h-px bg-black/[0.08] dark:bg-white/[0.08]" />

        {/* Chats */}
        <section>
          <div className="px-2 py-1 flex items-center justify-between text-[11px] font-semibold tracking-wider text-slate-600 dark:text-slate-400 uppercase">
            <span>Chats</span>
            <button
              onClick={onNewSession}
              className="flex items-center gap-1 pl-1.5 pr-2 py-0.5 rounded-full normal-case tracking-normal text-[11px] font-medium text-blue-700 dark:text-blue-300 hover:bg-blue-500/15 transition-colors cursor-pointer"
              title="New chat"
            >
              <Plus className="w-3 h-3" />
              New
            </button>
          </div>

          <div className="mt-0.5 space-y-0.5">
            {sessions.length === 0 ? (
              <div className="px-3 py-3 text-center text-xs text-slate-500 dark:text-slate-400">
                No chats in this workspace.
              </div>
            ) : (
              sessions.map((session) => {
                const isActive = activeSessionId === session.id;
                return (
                  <div
                    key={session.id}
                    onClick={() => onSelectSession(session.id)}
                    className={clsx(
                      'group relative flex items-center gap-2 px-3 py-2 rounded-2xl cursor-pointer transition-colors text-[13px]',
                      isActive
                        ? 'text-slate-900 dark:text-white font-medium'
                        : 'text-slate-700 dark:text-slate-300 hover:bg-black/[0.04] dark:hover:bg-white/[0.06]'
                    )}
                  >
                    {isActive && (
                      <motion.span
                        layoutId="chat-droplet"
                        transition={liquidSpring}
                        className="absolute inset-0 rounded-2xl liquid-pill"
                      />
                    )}
                    <MessageSquare className="relative w-3.5 h-3.5 shrink-0 opacity-70" />
                    <span className="relative truncate flex-1">{session.title}</span>
                    <button
                      onClick={(e) => { e.stopPropagation(); onDeleteSession(session.id); }}
                      className="relative opacity-0 group-hover:opacity-100 p-1 rounded-full hover:text-red-600 dark:hover:text-red-400 text-slate-500 transition-opacity cursor-pointer"
                      title="Delete chat"
                      aria-label="Delete chat"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                );
              })
            )}
          </div>
        </section>
      </div>

      {/* Footer */}
      <div className="p-2.5">
        <button
          onClick={onOpenSettings}
          className="w-full flex items-center gap-2.5 px-3 py-2 rounded-2xl hover:bg-black/[0.06] dark:hover:bg-white/10 text-slate-700 dark:text-slate-300 transition-colors text-[13px] font-medium cursor-pointer"
        >
          <Settings className="w-4 h-4 opacity-70" />
          <span>Settings</span>
        </button>
      </div>
    </div>
  );
}
