import { ArrowUp, X, Paperclip, Globe, Wrench } from 'lucide-react';
import { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import type { ModelInfo, SendOptions } from '../types';
import { PlusMenu } from './PlusMenu';
import { ModelPicker } from './ModelPicker';

interface ChatInputProps {
  onSend: (message: string, options: SendOptions) => void;
  disabled?: boolean;
  models: ModelInfo[];
  currentModelId: string;
  onChangeModel: (model: ModelInfo) => void;
}

const NO_CAPS = { files: true, webSearch: false, tools: false };

export function ChatInput({ onSend, disabled, models, currentModelId, onChangeModel }: ChatInputProps) {
  const [input, setInput] = useState('');
  const [files, setFiles] = useState<File[]>([]);
  const [webSearchPref, setWebSearchPref] = useState(false);
  const [toolsPref, setToolsPref] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const capabilities = models.find(m => m.id === currentModelId)?.capabilities ?? NO_CAPS;
  // A toggle only counts while the selected model actually supports it.
  const webSearch = webSearchPref && capabilities.webSearch;
  const tools = toolsPref && capabilities.tools;

  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = `${Math.min(el.scrollHeight, 160)}px`;
  }, [input]);

  const canSend = (input.trim().length > 0 || files.length > 0) && !disabled;

  const handleSend = () => {
    if (!canSend) return;
    onSend(input.trim(), { files, webSearch, tools });
    setInput('');
    setFiles([]);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleFiles = (e: React.ChangeEvent<HTMLInputElement>) => {
    const picked = Array.from(e.target.files ?? []);
    if (picked.length) setFiles(prev => [...prev, ...picked]);
    e.target.value = '';
  };

  const hasChips = files.length > 0 || webSearch || tools;

  return (
    <div className="px-4 pb-4 pt-1">
      <div className="max-w-3xl mx-auto">
        <div className="liquid-glass-input rounded-[28px] p-2">
          <AnimatePresence initial={false}>
            {hasChips && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: 'auto', opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                className="overflow-hidden"
              >
                <div className="flex flex-wrap gap-1.5 px-2 pt-1 pb-2">
                  {files.map((f, i) => (
                    <Chip key={`${f.name}-${i}`} icon={<Paperclip className="w-3 h-3" />} label={f.name}
                      onRemove={() => setFiles(prev => prev.filter((_, idx) => idx !== i))} />
                  ))}
                  {webSearch && <Chip icon={<Globe className="w-3 h-3" />} label="Web search" onRemove={() => setWebSearchPref(false)} />}
                  {tools && <Chip icon={<Wrench className="w-3 h-3" />} label="Tools" onRemove={() => setToolsPref(false)} />}
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          <div className="flex items-end gap-1.5">
            <PlusMenu
              capabilities={capabilities}
              webSearch={webSearch}
              tools={tools}
              onUploadClick={() => fileInputRef.current?.click()}
              onToggleWebSearch={() => setWebSearchPref(v => !v)}
              onToggleTools={() => setToolsPref(v => !v)}
            />
            <input ref={fileInputRef} type="file" multiple className="hidden" onChange={handleFiles} />

            {/* py-2 + leading-5 = 36px, same as the buttons, so a single line is optically centred */}
            <textarea
              ref={textareaRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Message LocaLLM"
              rows={1}
              disabled={disabled}
              className="flex-1 min-w-0 bg-transparent resize-none py-2 px-1 text-sm leading-5 text-slate-800 dark:text-slate-100 placeholder:text-slate-500 dark:placeholder:text-slate-400 focus:outline-none"
            />

            <ModelPicker models={models} currentId={currentModelId} onChange={onChangeModel} />

            <motion.button
              type="button"
              onClick={handleSend}
              disabled={!canSend}
              whileTap={{ scale: 0.88 }}
              animate={{ opacity: canSend ? 1 : 0.4 }}
              transition={{ type: 'spring', stiffness: 500, damping: 22 }}
              className="shrink-0 w-9 h-9 rounded-full flex items-center justify-center bg-blue-600 text-white shadow-[inset_0_1px_1px_rgba(255,255,255,0.45),0_6px_14px_-4px_rgba(37,99,235,0.6)] cursor-pointer disabled:cursor-not-allowed"
              aria-label="Send message"
            >
              <ArrowUp className="w-4 h-4" />
            </motion.button>
          </div>
        </div>
      </div>
    </div>
  );
}

function Chip({ icon, label, onRemove }: { icon: React.ReactNode; label: string; onRemove: () => void }) {
  return (
    <motion.span
      initial={{ opacity: 0, scale: 0.7 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ type: 'spring', stiffness: 520, damping: 18 }}
      className="inline-flex items-center gap-1.5 pl-2.5 pr-1.5 py-1 rounded-full text-[11px] font-medium bg-black/[0.07] dark:bg-white/10 text-slate-700 dark:text-slate-200 max-w-[200px]"
    >
      {icon}
      <span className="truncate">{label}</span>
      <button type="button" onClick={onRemove} className="p-0.5 rounded-full hover:bg-black/10 dark:hover:bg-white/15 cursor-pointer" aria-label={`Remove ${label}`}>
        <X className="w-3 h-3" />
      </button>
    </motion.span>
  );
}
