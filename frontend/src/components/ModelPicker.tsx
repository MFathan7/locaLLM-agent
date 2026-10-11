import { useEffect, useRef, useState } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { ChevronDown, Check, Cpu, Brain } from 'lucide-react';
import clsx from 'clsx';
import type { ModelInfo } from '../types';

interface ModelPickerProps {
  models: ModelInfo[];
  currentId: string;
  onChange: (model: ModelInfo) => void;
  activePlatform?: string;
  placement?: 'down' | 'up';
  className?: string;
}

function getPlatformName(model: ModelInfo, activePlatform?: string): string {
  if (model.platform) {
    if (model.platform.toLowerCase() === 'ollama') return 'Ollama';
    return model.platform;
  }
  if (model.provider) {
    if (model.provider.toLowerCase() === 'ollama') return 'Ollama';
    if (model.provider.toLowerCase() === 'openai') {
      return activePlatform && activePlatform.toLowerCase() !== 'ollama' ? activePlatform : 'OpenAI';
    }
    return model.provider;
  }
  return activePlatform || 'Ollama';
}

export function ModelPicker({
  models,
  currentId,
  onChange,
  activePlatform,
  placement = 'down',
  className
}: ModelPickerProps) {
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);
  const current = models.find(m => m.id === currentId);

  useEffect(() => {
    if (!open) return;
    const onDown = (e: MouseEvent) => {
      if (!rootRef.current?.contains(e.target as Node)) setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setOpen(false);
    };
    document.addEventListener('mousedown', onDown);
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('mousedown', onDown);
      document.removeEventListener('keydown', onKey);
    };
  }, [open]);

  const isDownward = placement === 'down';

  return (
    <div ref={rootRef} className="relative shrink-0">
      <button
        type="button"
        onClick={() => setOpen(o => !o)}
        className={clsx(
          'h-9 px-3 rounded-full flex items-center gap-2 text-xs font-semibold text-slate-800 dark:text-slate-100 hover:bg-black/[0.06] dark:hover:bg-white/10 transition-colors cursor-pointer min-w-0 max-w-[200px] sm:max-w-xs focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500',
          className
        )}
        aria-haspopup="listbox"
        aria-expanded={open}
        title="Select model"
      >
        <Cpu className="w-3.5 h-3.5 text-blue-600 dark:text-blue-400 shrink-0" aria-hidden="true" />
        <span className="truncate">{current?.name ?? (currentId || 'Select Model')}</span>
        <motion.span
          animate={{ rotate: open ? (isDownward ? 180 : -180) : 0 }}
          transition={{ type: 'spring', stiffness: 400, damping: 22 }}
          className="shrink-0"
        >
          <ChevronDown className="w-3.5 h-3.5 opacity-60" aria-hidden="true" />
        </motion.span>
      </button>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: isDownward ? -6 : 6 }}
            animate={{ opacity: 1, scale: 1, y: 0, transition: { type: 'spring', stiffness: 450, damping: 24 } }}
            exit={{ opacity: 0, scale: 0.95, y: isDownward ? -4 : 4, transition: { duration: 0.12 } }}
            style={{ transformOrigin: isDownward ? 'top left' : 'bottom right' }}
            className={clsx(
              'absolute w-72 p-1.5 rounded-2xl bg-white dark:bg-[#141b2a] border border-slate-200 dark:border-slate-800 shadow-2xl shadow-black/25 z-50 max-h-80 overflow-y-auto',
              isDownward ? 'top-full left-0 mt-2' : 'bottom-full right-0 mb-3'
            )}
            role="listbox"
            aria-label="Available models"
          >
            {models.length === 0 ? (
              <div className="px-3 py-3 text-xs text-slate-500 dark:text-slate-400 text-center">
                No models discovered
              </div>
            ) : (
              models.map(m => {
                const selected = m.id === currentId;
                const platformLabel = getPlatformName(m, activePlatform);
                const hasThinking = Boolean(m.capabilities?.thinking);

                return (
                  <button
                    key={m.id}
                    type="button"
                    role="option"
                    aria-selected={selected}
                    onClick={() => {
                      onChange(m);
                      setOpen(false);
                    }}
                    className={clsx(
                      'w-full flex items-center gap-2 px-3 py-2 rounded-xl text-left cursor-pointer transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500',
                      selected
                        ? 'bg-blue-50 dark:bg-blue-950/50 text-blue-600 dark:text-blue-400 font-semibold'
                        : 'text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800/70 hover:text-slate-900 dark:hover:text-white'
                    )}
                  >
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-1.5">
                        <span className="text-[13px] font-semibold truncate leading-tight">{m.name}</span>
                        {hasThinking && (
                          <span
                            title="Compatible with Thinking mode"
                            className="inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded text-[10px] font-semibold bg-blue-100/80 dark:bg-blue-900/60 text-blue-700 dark:text-blue-300 shrink-0"
                          >
                            <Brain className="w-2.5 h-2.5" aria-hidden="true" />
                            <span>Thinking</span>
                          </span>
                        )}
                      </div>
                      <div className="text-[11px] text-slate-500 dark:text-slate-400 font-normal truncate mt-0.5">
                        {platformLabel}
                      </div>
                    </div>
                    {selected && <Check className="w-3.5 h-3.5 shrink-0 text-blue-600 dark:text-blue-400" aria-hidden="true" />}
                  </button>
                );
              })
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
