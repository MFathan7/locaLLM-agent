import { useEffect, useRef, useState } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { ChevronUp, Check } from 'lucide-react';
import clsx from 'clsx';
import type { ModelInfo } from '../types';

interface ModelPickerProps {
  models: ModelInfo[];
  currentId: string;
  onChange: (model: ModelInfo) => void;
  activePlatform?: string;
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

export function ModelPicker({ models, currentId, onChange, activePlatform }: ModelPickerProps) {
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

  return (
    <div ref={rootRef} className="relative shrink-0">
      <button
        type="button"
        onClick={() => setOpen(o => !o)}
        className="h-9 pl-3 pr-2.5 rounded-full flex items-center gap-1.5 text-xs font-semibold text-slate-800 dark:text-slate-100 hover:bg-black/[0.06] dark:hover:bg-white/10 transition-colors cursor-pointer max-w-[160px]"
        aria-haspopup="listbox"
        aria-expanded={open}
        title="Change model"
      >
        <span className="truncate">{current?.name ?? currentId}</span>
        <motion.span animate={{ rotate: open ? 0 : 180 }} transition={{ type: 'spring', stiffness: 400, damping: 22 }}>
          <ChevronUp className="w-3.5 h-3.5 opacity-60" />
        </motion.span>
      </button>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, scale: 0.4, y: 12 }}
            animate={{ opacity: 1, scale: 1, y: 0, transition: { type: 'spring', stiffness: 520, damping: 17, mass: 0.8 } }}
            exit={{ opacity: 0, scale: 0.6, y: 8, transition: { duration: 0.14 } }}
            style={{ transformOrigin: 'bottom right' }}
            className="absolute bottom-full right-0 mb-3 w-64 p-1.5 rounded-2xl bg-white dark:bg-[#141b2a] border border-slate-200 dark:border-slate-800 shadow-2xl shadow-black/25 z-30 max-h-72 overflow-y-auto"
            role="listbox"
          >
            {models.map(m => {
              const selected = m.id === currentId;
              const platformLabel = getPlatformName(m, activePlatform);
              return (
                <button
                  key={m.id}
                  type="button"
                  role="option"
                  aria-selected={selected}
                  onClick={() => { onChange(m); setOpen(false); }}
                  className={clsx(
                    'w-full flex items-center gap-2 px-3 py-2 rounded-xl text-left cursor-pointer transition-colors',
                    selected
                      ? 'bg-blue-50 dark:bg-blue-950/50 text-blue-600 dark:text-blue-400 font-semibold'
                      : 'text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800/70 hover:text-slate-900 dark:hover:text-white'
                  )}
                >
                  <div className="flex-1 min-w-0">
                    <div className="text-[13px] font-semibold truncate leading-tight">{m.name}</div>
                    <div className="text-[11px] text-slate-500 dark:text-slate-400 font-normal truncate mt-0.5">{platformLabel}</div>
                  </div>
                  {selected && <Check className="w-3.5 h-3.5 shrink-0" />}
                </button>
              );
            })}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
