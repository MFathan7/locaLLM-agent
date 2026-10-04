import { useState, useMemo, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { Search, X, MessageSquare, User, Bot, Calendar, ArrowRight, Loader2 } from 'lucide-react';
import type { ChatSession, Workspace } from '../types';

interface SearchOverlayProps {
  isOpen: boolean;
  onClose: () => void;
  sessions: ChatSession[];
  workspaces: Workspace[];
  activeWorkspace: string;
  onSelectSession: (sessionId: string, workspace?: string) => void;
}

interface MatchResult {
  sessionId: string;
  sessionTitle: string;
  workspace: string;
  messageId: string;
  role: 'user' | 'assistant' | 'system' | 'tool';
  snippet: string;
  timestamp: number;
}

export function SearchOverlay({
  isOpen,
  onClose,
  sessions,
  activeWorkspace,
  onSelectSession
}: SearchOverlayProps) {
  const [query, setQuery] = useState('');
  const [debouncedQuery, setDebouncedQuery] = useState('');
  const [isSearching, setIsSearching] = useState(false);
  const [scope, setScope] = useState<'current' | 'all'>('current');
  const inputRef = useRef<HTMLInputElement>(null);

  // Auto-focus input when opened
  useEffect(() => {
    if (isOpen) {
      setTimeout(() => inputRef.current?.focus(), 50);
    } else {
      setQuery('');
      setDebouncedQuery('');
    }
  }, [isOpen]);

  // Debounce search query (120ms) to ensure instantaneous keystrokes and zero lag
  useEffect(() => {
    if (!query) {
      setDebouncedQuery('');
      setIsSearching(false);
      return;
    }
    setIsSearching(true);
    const timer = setTimeout(() => {
      setDebouncedQuery(query);
      setIsSearching(false);
    }, 120);
    return () => clearTimeout(timer);
  }, [query]);

  // Handle ESC key to close
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  // Filter messages based on debouncedQuery and scope with snippet extraction & max 30 results
  const results = useMemo<MatchResult[]>(() => {
    const trimmed = debouncedQuery.trim().toLowerCase();
    if (!trimmed || trimmed.length < 2) return [];

    const targetSessions = scope === 'current'
      ? sessions.filter(s => s.workspace === activeWorkspace)
      : sessions;

    const matches: MatchResult[] = [];

    for (const session of targetSessions) {
      for (const msg of session.messages) {
        // Skip tool logs or empty messages to keep search focused and lightning fast
        if (!msg.content || msg.role === ('tool' as any)) continue;

        const contentLower = msg.content.toLowerCase();
        const matchIdx = contentLower.indexOf(trimmed);

        if (matchIdx !== -1) {
          // Extract a focused ~120 character snippet around the first match
          const start = Math.max(0, matchIdx - 45);
          const end = Math.min(msg.content.length, matchIdx + trimmed.length + 75);
          const rawSnippet = msg.content.slice(start, end).trim();
          const snippet = (start > 0 ? '...' : '') + rawSnippet + (end < msg.content.length ? '...' : '');

          matches.push({
            sessionId: session.id,
            sessionTitle: session.title,
            workspace: session.workspace,
            messageId: msg.id,
            role: msg.role,
            snippet,
            timestamp: msg.timestamp
          });

          // Limit to max 30 matches to keep DOM light and smooth
          if (matches.length >= 30) {
            break;
          }
        }
      }
      if (matches.length >= 30) break;
    }

    return matches.sort((a, b) => b.timestamp - a.timestamp);
  }, [debouncedQuery, scope, sessions, activeWorkspace]);

  if (!isOpen) return null;

  const handleSelectResult = (sessionId: string, workspace: string) => {
    // 1. Immediately trigger overlay close
    onClose();
    // 2. Schedule session selection in the next animation frame so the transition is instant and doesn't block the UI
    requestAnimationFrame(() => {
      onSelectSession(sessionId, workspace);
    });
  };

  const highlightMatches = (text: string, search: string) => {
    if (!search.trim()) return text;
    const regex = new RegExp(`(${search.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi');
    const parts = text.split(regex);
    return parts.map((part, i) =>
      regex.test(part) ? (
        <mark key={i} className="bg-amber-300 dark:bg-amber-400/40 text-slate-900 dark:text-amber-100 font-bold px-1 rounded-sm">
          {part}
        </mark>
      ) : (
        part
      )
    );
  };

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        transition={{ duration: 0.15 }}
        className="flex-1 flex flex-col h-full w-full overflow-hidden bg-white/80 dark:bg-zinc-950/80 backdrop-blur-xl relative z-20"
      >
        {/* Search Header Bar */}
        <div className="shrink-0 p-4 md:px-8 md:py-5 border-b border-black/[0.06] dark:border-white/[0.08]">
          <div className="max-w-3xl mx-auto flex items-center justify-between gap-3">
            <div className="flex-1 relative flex items-center">
              <Search className="w-5 h-5 text-slate-400 dark:text-slate-500 absolute left-3.5 pointer-events-none" />
              <input
                ref={inputRef}
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder={`Search messages in ${scope === 'current' ? `"${activeWorkspace}"` : 'all workspaces'}...`}
                className="w-full bg-black/[0.04] dark:bg-white/[0.06] border border-black/10 dark:border-white/10 rounded-2xl pl-11 pr-10 py-3 text-sm md:text-base text-slate-900 dark:text-slate-100 font-medium placeholder:text-slate-400 dark:placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500 transition-all shadow-xs"
              />
              {isSearching ? (
                <Loader2 className="w-4 h-4 text-blue-500 animate-spin absolute right-3.5" />
              ) : query ? (
                <button
                  onClick={() => setQuery('')}
                  className="absolute right-3.5 p-1 rounded-full text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 transition-colors cursor-pointer"
                  title="Clear search"
                >
                  <X className="w-4 h-4" />
                </button>
              ) : null}
            </div>

            {/* Close Search Mode Button (tanda silang) */}
            <button
              onClick={onClose}
              className="p-2.5 rounded-2xl text-slate-600 hover:text-slate-950 dark:text-slate-400 dark:hover:text-slate-100 bg-black/[0.04] dark:bg-white/[0.06] hover:bg-black/[0.08] dark:hover:bg-white/[0.1] border border-black/10 dark:border-white/10 transition-colors cursor-pointer shrink-0"
              title="Close search (Esc)"
              aria-label="Close search mode"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Scope selection pills */}
          <div className="max-w-3xl mx-auto mt-3 flex items-center gap-2 text-xs">
            <span className="text-slate-500 dark:text-slate-400 font-semibold">Scope:</span>
            <button
              onClick={() => setScope('current')}
              className={`px-3 py-1 rounded-xl font-bold transition-all cursor-pointer ${
                scope === 'current'
                  ? 'bg-blue-600 text-white shadow-xs'
                  : 'bg-black/[0.04] dark:bg-white/[0.05] text-slate-700 dark:text-slate-300 hover:bg-black/[0.08]'
              }`}
            >
              Current Workspace ({activeWorkspace})
            </button>
            <button
              onClick={() => setScope('all')}
              className={`px-3 py-1 rounded-xl font-bold transition-all cursor-pointer ${
                scope === 'all'
                  ? 'bg-blue-600 text-white shadow-xs'
                  : 'bg-black/[0.04] dark:bg-white/[0.05] text-slate-700 dark:text-slate-300 hover:bg-black/[0.08]'
              }`}
            >
              All Workspaces
            </button>
          </div>
        </div>

        {/* Search Results / Content Area */}
        <div className="flex-1 overflow-y-auto px-4 py-6 md:px-8">
          <div className="max-w-3xl mx-auto space-y-3">
            {/* When user hasn't typed anything */}
            {!query.trim() && (
              <div className="py-16 text-center space-y-3">
                <div className="inline-flex p-4 rounded-3xl bg-blue-500/10 text-blue-600 dark:text-blue-400">
                  <Search className="w-8 h-8" />
                </div>
                <h3 className="text-base font-bold text-slate-900 dark:text-slate-100">
                  Search Conversation History
                </h3>
                <p className="text-xs font-medium text-slate-600 dark:text-slate-400 max-w-md mx-auto">
                  Type any keyword, phrase, or code snippet to find exact matches across your chat messages.
                </p>
              </div>
            )}

            {/* When query is only 1 char */}
            {query.trim().length === 1 && (
              <div className="py-12 text-center text-xs text-slate-500 dark:text-slate-400 font-medium">
                Type at least 2 characters to search messages...
              </div>
            )}

            {/* When user has typed and no results found */}
            {debouncedQuery.trim().length >= 2 && !isSearching && results.length === 0 && (
              <div className="py-16 text-center space-y-3">
                <div className="inline-flex p-4 rounded-3xl bg-black/[0.03] dark:bg-white/[0.04] text-slate-400">
                  <MessageSquare className="w-8 h-8" />
                </div>
                <h3 className="text-base font-bold text-slate-900 dark:text-slate-100">
                  No matches found
                </h3>
                <p className="text-xs font-medium text-slate-600 dark:text-slate-400">
                  No messages contain &ldquo;{debouncedQuery}&rdquo; in this scope. Try changing your search query or switching to All Workspaces.
                </p>
              </div>
            )}

            {/* Results List */}
            {debouncedQuery.trim().length >= 2 && results.length > 0 && (
              <>
                <div className="text-xs font-bold text-slate-700 dark:text-slate-300 pb-1 flex items-center justify-between">
                  <span>Found {results.length}{results.length >= 30 ? '+' : ''} matching message{results.length > 1 ? 's' : ''}</span>
                  <span className="text-[11px] font-semibold text-slate-500 dark:text-slate-400">Click to open chat</span>
                </div>

                <div className="space-y-2.5">
                  {results.map((item, idx) => (
                    <div
                      key={`${item.sessionId}-${item.messageId}-${idx}`}
                      onClick={() => handleSelectResult(item.sessionId, item.workspace)}
                      className="p-4 rounded-2xl liquid-glass border border-black/[0.06] dark:border-white/[0.08] hover:border-blue-500/40 hover:shadow-lg transition-all cursor-pointer group"
                    >
                      {/* Result Card Header */}
                      <div className="flex items-center justify-between gap-2 mb-2 text-xs">
                        <div className="flex items-center gap-2">
                          <span className="font-bold text-slate-900 dark:text-slate-100 group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors flex items-center gap-1.5">
                            <MessageSquare className="w-3.5 h-3.5 shrink-0 text-blue-500" />
                            {item.sessionTitle}
                          </span>
                          <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-black/[0.06] dark:bg-white/[0.08] text-slate-700 dark:text-slate-300">
                            {item.workspace}
                          </span>
                        </div>

                        <div className="flex items-center gap-2 text-[11px] text-slate-500 dark:text-slate-400">
                          <span className="inline-flex items-center gap-1 font-bold">
                            {item.role === 'user' ? (
                              <>
                                <User className="w-3 h-3 text-blue-500" />
                                <span>You</span>
                              </>
                            ) : (
                              <>
                                <Bot className="w-3 h-3 text-emerald-500" />
                                <span>LocaLLM</span>
                              </>
                            )}
                          </span>
                          <span>•</span>
                          <span className="inline-flex items-center gap-1 font-medium">
                            <Calendar className="w-3 h-3" />
                            {new Date(item.timestamp).toLocaleDateString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}
                          </span>
                        </div>
                      </div>

                      {/* Content snippet with highlighted text */}
                      <p className="text-xs/relaxed text-slate-700 dark:text-slate-200 line-clamp-2 font-medium">
                        {highlightMatches(item.snippet, debouncedQuery)}
                      </p>

                      <div className="mt-2.5 flex items-center justify-end text-[11px] font-bold text-blue-600 dark:text-blue-400 opacity-0 group-hover:opacity-100 transition-opacity gap-1">
                        <span>Open in chat</span>
                        <ArrowRight className="w-3 h-3" />
                      </div>
                    </div>
                  ))}
                </div>
              </>
            )}
          </div>
        </div>
      </motion.div>
    </AnimatePresence>
  );
}
