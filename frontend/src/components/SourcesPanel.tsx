import { useEffect, useMemo, useState } from 'react';
import { motion } from 'motion/react';
import { X, ExternalLink, Globe, BookOpen, Calendar, Compass } from 'lucide-react';
import type { Message, SourceItem } from '../types';
import { extractSourcesFromText } from '../utils/messageProcessor';

interface SourcesPanelProps {
  message: Message;
  onClose: () => void;
}

export function SourcesPanel({ message, onClose }: SourcesPanelProps) {
  // Extract sources from attached message.sources or parse from content
  const sources = useMemo<SourceItem[]>(() => {
    return extractSourcesFromText(message.content, message.sources);
  }, [message.content, message.sources]);

  // Handle ESC key to close
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onClose]);

  return (
    <motion.aside
      initial={{ x: '100%', opacity: 0 }}
      animate={{ x: 0, opacity: 1 }}
      exit={{ x: '100%', opacity: 0 }}
      transition={{ type: 'spring', stiffness: 420, damping: 28 }}
      className="fixed inset-y-0 right-0 md:static z-40 w-full sm:w-88 md:w-96 h-full flex flex-col bg-white/95 dark:bg-[#0c1017]/95 backdrop-blur-2xl border-l border-slate-200 dark:border-white/[0.08] shadow-2xl md:shadow-none shrink-0"
      aria-label="Sources and references"
    >
      {/* Header Bar */}
      <div className="flex items-center justify-between px-5 py-4 border-b border-slate-200 dark:border-white/[0.08] bg-slate-50/60 dark:bg-white/[0.02]">
        <div className="flex items-center gap-2.5">
          <div className="p-1.5 rounded-lg bg-blue-500/10 text-blue-600 dark:text-blue-400">
            <Compass className="w-4 h-4" />
          </div>
          <div>
            <h2 className="text-base font-bold text-slate-900 dark:text-slate-100 flex items-center gap-2">
              <span>Sources</span>
              {sources.length > 0 && (
                <span className="text-[11px] font-semibold px-2 py-0.5 rounded-full bg-black/[0.06] dark:bg-white/[0.08] text-slate-600 dark:text-slate-300">
                  {sources.length}
                </span>
              )}
            </h2>
          </div>
        </div>

        <button
          onClick={onClose}
          className="p-1.5 rounded-xl text-slate-500 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white hover:bg-black/[0.06] dark:hover:bg-white/[0.08] transition-colors cursor-pointer"
          aria-label="Close sources panel (Esc)"
          title="Close sources (Esc)"
        >
          <X className="w-5 h-5" />
        </button>
      </div>

      {/* Content Area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {sources.length === 0 ? (
          <div className="py-20 text-center px-4 space-y-3">
            <div className="inline-flex p-3.5 rounded-2xl bg-black/[0.04] dark:bg-white/[0.05] text-slate-400">
              <BookOpen className="w-7 h-7" />
            </div>
            <h3 className="text-sm font-bold text-slate-800 dark:text-slate-200">
              No External Sources Cited
            </h3>
            <p className="text-xs text-slate-500 dark:text-slate-400 max-w-xs mx-auto leading-relaxed">
              This response was synthesized directly using the model knowledge and instructions without external web search or citations.
            </p>
          </div>
        ) : (
          <div className="space-y-2.5">
            {sources.map((item, idx) => (
              <SourceCard key={item.id || `${item.url}-${idx}`} item={item} />
            ))}
          </div>
        )}
      </div>

      {/* Footer Info Strip */}
      <div className="px-5 py-3 border-t border-slate-200 dark:border-white/[0.08] text-[11px] font-medium text-slate-500 dark:text-slate-400 flex items-center justify-between bg-slate-50/50 dark:bg-transparent">
        <span>Linked to selected AI response</span>
        <button
          onClick={onClose}
          className="text-blue-600 dark:text-blue-400 hover:underline font-semibold cursor-pointer"
        >
          Done
        </button>
      </div>
    </motion.aside>
  );
}

function SourceCard({ item }: { item: SourceItem }) {
  const [imgError, setImgError] = useState(false);

  return (
    <a
      href={item.url}
      target="_blank"
      rel="noopener noreferrer"
      className="group block p-3.5 rounded-2xl bg-white dark:bg-[#121824] border border-slate-200/90 dark:border-white/[0.06] hover:border-blue-500/40 hover:shadow-md transition-all cursor-pointer"
    >
      {/* Publisher / Site Identity */}
      <div className="flex items-center justify-between gap-2 mb-1.5">
        <div className="flex items-center gap-2 min-w-0">
          {!imgError && item.favicon ? (
            <img
              src={item.favicon}
              alt=""
              onError={() => setImgError(true)}
              className="w-4 h-4 rounded-sm shrink-0 object-contain"
              loading="lazy"
            />
          ) : (
            <Globe className="w-3.5 h-3.5 text-blue-500 shrink-0" />
          )}
          <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 truncate">
            {item.domain || 'External Resource'}
          </span>
        </div>

        <ExternalLink className="w-3.5 h-3.5 text-slate-400 group-hover:text-blue-500 transition-colors shrink-0 opacity-70 group-hover:opacity-100" />
      </div>

      {/* Article Title */}
      <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100 group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors line-clamp-2 leading-snug">
        {item.title || item.url}
      </h3>

      {/* Date or Snippet Excerpt */}
      {item.snippet && item.snippet !== item.url && (
        <p className="mt-1 text-xs text-slate-500 dark:text-slate-400 line-clamp-2 leading-relaxed">
          {item.snippet}
        </p>
      )}

      {item.date && (
        <div className="mt-2 flex items-center gap-1.5 text-[11px] font-medium text-slate-400 dark:text-slate-500">
          <Calendar className="w-3 h-3" />
          <span>{item.date}</span>
        </div>
      )}
    </a>
  );
}
