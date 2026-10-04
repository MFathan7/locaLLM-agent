import { useState, useRef, useEffect } from 'react';
import {
  MessageSquare,
  Plus,
  Settings,
  Trash2,
  PanelLeftClose,
  Check,
  X,
  Search,
  MoreVertical,
  Edit3
} from 'lucide-react';
import type { ChatSession, Workspace } from '../types';
import { motion, AnimatePresence } from 'motion/react';
import clsx from 'clsx';
import { WorkspaceIcon } from './WorkspaceIcon';

interface SidebarProps {
  workspaces: Workspace[];
  activeWorkspace: string;
  onSelectWorkspace: (name: string) => void;
  onCreateWorkspace: (name: string) => void;
  onEditWorkspace?: (workspace: Workspace) => void;
  onDeleteWorkspace?: (name: string) => void;
  sessions: ChatSession[];
  activeSessionId: string | null;
  onSelectSession: (id: string) => void;
  onNewSession: () => void;
  onDeleteSession: (id: string, title?: string) => void;
  onOpenSettings: () => void;
  onCollapse: () => void;
  onOpenSearch?: () => void;
}

// A slightly under-damped spring: the droplet overshoots and settles like iOS liquid glass.
const liquidSpring = { type: 'spring', stiffness: 380, damping: 24, mass: 0.9 } as const;

export function Sidebar({
  workspaces,
  activeWorkspace,
  onSelectWorkspace,
  onCreateWorkspace,
  onEditWorkspace,
  onDeleteWorkspace,
  sessions,
  activeSessionId,
  onSelectSession,
  onNewSession,
  onDeleteSession,
  onOpenSettings,
  onCollapse,
  onOpenSearch
}: SidebarProps) {
  const [isAddingWorkspace, setIsAddingWorkspace] = useState(false);
  const [newWsName, setNewWsName] = useState('');
  const [menuOpenWs, setMenuOpenWs] = useState<string | null>(null);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setMenuOpenWs(null);
      }
    };
    if (menuOpenWs) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [menuOpenWs]);

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
        <div className="flex items-center gap-0.5">
          {onOpenSearch && (
            <button
              onClick={onOpenSearch}
              className="p-1.5 rounded-full text-slate-600 hover:text-slate-900 dark:text-slate-300 dark:hover:text-white hover:bg-black/[0.06] dark:hover:bg-white/10 transition-colors cursor-pointer"
              title="Search messages"
              aria-label="Search messages"
            >
              <Search className="w-4 h-4" />
            </button>
          )}
          <button
            onClick={onCollapse}
            className="p-1.5 rounded-full text-slate-600 hover:text-slate-900 dark:text-slate-300 dark:hover:text-white hover:bg-black/[0.06] dark:hover:bg-white/10 transition-colors cursor-pointer"
            title="Collapse sidebar"
            aria-label="Collapse sidebar"
          >
            <PanelLeftClose className="w-4 h-4" />
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto px-2.5 pb-2 space-y-3">
        {/* Workspace */}
        <section className={clsx('relative', menuOpenWs ? 'z-30' : 'z-10')}>
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
              const isDefault = ws.name.toLowerCase() === 'default';
              const isMenuOpen = menuOpenWs === ws.name;

              return (
                <div
                  key={ws.name}
                  onClick={() => onSelectWorkspace(ws.name)}
                  onContextMenu={(e) => {
                    e.preventDefault();
                    setMenuOpenWs(ws.name);
                  }}
                  className={clsx(
                    'group relative w-full flex items-center justify-between px-2.5 py-1.5 rounded-2xl text-[13px] text-left cursor-pointer transition-colors',
                    isMenuOpen ? 'z-40' : 'z-0',
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

                  {/* Left: Custom Workspace Icon (click to edit) & Name */}
                  <div className="relative flex items-center gap-2 min-w-0 flex-1 mr-1">
                    <div
                      onClick={(e) => {
                        e.stopPropagation();
                        onEditWorkspace?.(ws);
                      }}
                      className="shrink-0 cursor-pointer hover:scale-110 active:scale-95 transition-transform"
                      title="Edit workspace"
                    >
                      <WorkspaceIcon
                        icon={ws.icon || 'Folder'}
                        color={ws.color || '#3B82F6'}
                        withContainer
                        containerClassName="w-5.5 h-5.5 rounded-lg flex items-center justify-center shrink-0 shadow-xs"
                        className="w-3 h-3"
                      />
                    </div>
                    <span className="truncate flex-1 font-medium">{ws.name}</span>
                  </div>

                  {/* Right: Quick Edit & Options Menu */}
                  <div className="relative flex items-center gap-0.5 shrink-0">
                    {/* Hover Quick Edit Icon */}
                    <button
                      type="button"
                      onMouseDown={(e) => e.stopPropagation()}
                      onClick={(e) => {
                        e.stopPropagation();
                        setMenuOpenWs(null);
                        onEditWorkspace?.(ws);
                      }}
                      className="opacity-0 group-hover:opacity-100 p-1.5 rounded-xl transition-all cursor-pointer text-slate-400 hover:text-blue-600 dark:hover:text-blue-400 hover:bg-black/10 dark:hover:bg-white/10 shrink-0"
                      title="Edit workspace"
                      aria-label="Edit workspace"
                    >
                      <Edit3 className="w-3.5 h-3.5" />
                    </button>

                    {/* Three Dots Menu Button */}
                    <button
                      type="button"
                      onMouseDown={(e) => e.stopPropagation()}
                      onClick={(e) => {
                        e.stopPropagation();
                        setMenuOpenWs(prev => prev === ws.name ? null : ws.name);
                      }}
                      className={clsx(
                        'relative p-1.5 rounded-xl transition-all cursor-pointer text-slate-400 hover:text-slate-900 dark:hover:text-white hover:bg-black/10 dark:hover:bg-white/10 shrink-0',
                        isMenuOpen ? 'opacity-100 bg-black/10 dark:bg-white/10 text-slate-900 dark:text-white' : 'opacity-40 group-hover:opacity-100'
                      )}
                      title="Workspace options"
                      aria-label="Workspace options"
                    >
                      <MoreVertical className="w-3.5 h-3.5" />
                    </button>

                    {/* Popover Action Menu */}
                    <AnimatePresence>
                      {isMenuOpen && (
                        <motion.div
                          ref={menuRef}
                          initial={{ opacity: 0, scale: 0.92, y: -4 }}
                          animate={{ opacity: 1, scale: 1, y: 0 }}
                          exit={{ opacity: 0, scale: 0.92, y: -4 }}
                          transition={{ type: 'spring', stiffness: 500, damping: 25 }}
                          onMouseDown={(e) => e.stopPropagation()}
                          onTouchStart={(e) => e.stopPropagation()}
                          onClick={(e) => e.stopPropagation()}
                          className="absolute right-0 top-full mt-1 w-44 p-1.5 rounded-2xl bg-white/95 dark:bg-[#151a26]/95 backdrop-blur-xl border border-slate-200 dark:border-white/15 shadow-2xl shadow-black/40 z-50 text-xs select-none"
                        >
                          <button
                            type="button"
                            onMouseDown={(e) => e.stopPropagation()}
                            onClick={(e) => {
                              e.stopPropagation();
                              setMenuOpenWs(null);
                              onEditWorkspace?.(ws);
                            }}
                            className="w-full flex items-center gap-2.5 px-3 py-2 rounded-xl hover:bg-black/5 dark:hover:bg-white/10 text-slate-700 dark:text-slate-200 transition-colors text-left cursor-pointer font-medium"
                          >
                            <Edit3 className="w-3.5 h-3.5 text-blue-500 shrink-0" />
                            <span>Edit workspace</span>
                          </button>

                          {!isDefault && onDeleteWorkspace && (
                            <button
                              type="button"
                              onMouseDown={(e) => e.stopPropagation()}
                              onClick={(e) => {
                                e.stopPropagation();
                                setMenuOpenWs(null);
                                onDeleteWorkspace(ws.name);
                              }}
                              className="w-full flex items-center gap-2.5 px-3 py-2 rounded-xl hover:bg-red-500/10 text-red-600 dark:text-red-400 transition-colors text-left cursor-pointer font-medium"
                            >
                              <Trash2 className="w-3.5 h-3.5 shrink-0" />
                              <span>Delete</span>
                            </button>
                          )}
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </div>
                </div>
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
            {sessions.filter(s => s.messages && s.messages.length > 0).length === 0 ? (
              <div className="px-3 py-3 text-center text-xs text-slate-500 dark:text-slate-400">
                No chats in this workspace.
              </div>
            ) : (
              sessions
                .filter(s => s.messages && s.messages.length > 0)
                .map((session) => {
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
                        type="button"
                        onClick={(e) => { e.stopPropagation(); onDeleteSession(session.id, session.title); }}
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
