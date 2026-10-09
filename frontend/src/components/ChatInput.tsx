import {
  ArrowUp,
  Square,
  X,
  Paperclip,
  Globe,
  Wrench,
  FileText,
  Image as ImageIcon
} from 'lucide-react';
import { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import type { ModelInfo, SendOptions } from '../types';
import { PlusMenu } from './PlusMenu';
import { ModelPicker } from './ModelPicker';

interface ChatInputProps {
  onSend: (message: string, options: SendOptions) => void;
  onStop?: () => void;
  disabled?: boolean;
  isTyping?: boolean;
  models: ModelInfo[];
  currentModelId: string;
  onChangeModel: (model: ModelInfo) => void;
  activePlatform?: string;
}

const DEFAULT_CAPS = { files: true, webSearch: true, tools: true };

const IMAGE_MIME_BY_EXT: Record<string, string> = {
  png: 'image/png',
  jpg: 'image/jpeg',
  jpeg: 'image/jpeg',
  gif: 'image/gif',
  webp: 'image/webp',
  svg: 'image/svg+xml',
  bmp: 'image/bmp',
  avif: 'image/avif',
  ico: 'image/x-icon',
  heic: 'image/heic',
  heif: 'image/heif',
  tiff: 'image/tiff',
  tif: 'image/tiff'
};

const IMAGE_EXTENSIONS_REGEX = /\.(png|jpe?g|gif|webp|svg|bmp|avif|ico|heic|heif|tiff?)$/i;

export function isImageFile(file: File): boolean {
  if (file.type && file.type.startsWith('image/')) {
    return true;
  }
  return IMAGE_EXTENSIONS_REGEX.test(file.name);
}

export function normalizeFile(file: File): File {
  if (file.type && file.type.startsWith('image/')) {
    return file;
  }
  const ext = file.name.split('.').pop()?.toLowerCase() || '';
  const inferredMime = IMAGE_MIME_BY_EXT[ext];
  if (inferredMime) {
    try {
      return new File([file], file.name, {
        type: inferredMime,
        lastModified: file.lastModified
      });
    } catch {
      return file;
    }
  }
  return file;
}

function extractFilesFromDataTransfer(dataTransfer: DataTransfer | null): File[] {
  if (!dataTransfer) return [];
  const result: File[] = [];

  if (dataTransfer.items && dataTransfer.items.length > 0) {
    for (let i = 0; i < dataTransfer.items.length; i++) {
      const item = dataTransfer.items[i];
      if (item.kind === 'file') {
        const file = item.getAsFile();
        if (file) result.push(normalizeFile(file));
      }
    }
  }

  if (result.length === 0 && dataTransfer.files && dataTransfer.files.length > 0) {
    for (let i = 0; i < dataTransfer.files.length; i++) {
      result.push(normalizeFile(dataTransfer.files[i]));
    }
  }

  return result;
}

export function ChatInput({
  onSend,
  onStop,
  disabled,
  isTyping,
  models,
  currentModelId,
  onChangeModel,
  activePlatform
}: ChatInputProps) {
  const [input, setInput] = useState('');
  const [files, setFiles] = useState<File[]>([]);
  const [webSearchPref, setWebSearchPref] = useState(false);
  const [toolsPref, setToolsPref] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const dragCounter = useRef(0);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (!disabled && textareaRef.current) {
      textareaRef.current.focus();
    }
  }, [disabled]);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const capabilities = models.find(m => m.id === currentModelId)?.capabilities ?? DEFAULT_CAPS;
  const webSearch = webSearchPref && (capabilities.webSearch ?? true);
  const tools = toolsPref && (capabilities.tools ?? true);

  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = `${Math.min(el.scrollHeight, 160)}px`;
  }, [input]);

  const appendFiles = (newFiles: File[]) => {
    setFiles(prev => {
      const remainingSlots = Math.max(0, 5 - prev.length);
      if (remainingSlots <= 0) return prev;
      return [...prev, ...newFiles.slice(0, remainingSlots)];
    });
  };

  // Window-level drag and drop so user can drop files anywhere
  useEffect(() => {
    const handleDragEnterWindow = (e: DragEvent) => {
      e.preventDefault();
      dragCounter.current++;
      if (e.dataTransfer && (e.dataTransfer.types.includes('Files') || e.dataTransfer.types.includes('application/x-moz-file'))) {
        setIsDragging(true);
      }
    };

    const handleDragLeaveWindow = (e: DragEvent) => {
      e.preventDefault();
      dragCounter.current--;
      if (dragCounter.current <= 0) {
        dragCounter.current = 0;
        setIsDragging(false);
      }
    };

    const handleDragOverWindow = (e: DragEvent) => {
      e.preventDefault();
      if (e.dataTransfer) {
        e.dataTransfer.dropEffect = 'copy';
      }
    };

    const handleDropWindow = (e: DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
      dragCounter.current = 0;
      setIsDragging(false);
      const dropped = extractFilesFromDataTransfer(e.dataTransfer);
      if (dropped.length > 0) {
        appendFiles(dropped);
      }
    };

    window.addEventListener('dragenter', handleDragEnterWindow);
    window.addEventListener('dragleave', handleDragLeaveWindow);
    window.addEventListener('dragover', handleDragOverWindow);
    window.addEventListener('drop', handleDropWindow);

    return () => {
      window.removeEventListener('dragenter', handleDragEnterWindow);
      window.removeEventListener('dragleave', handleDragLeaveWindow);
      window.removeEventListener('dragover', handleDragOverWindow);
      window.removeEventListener('drop', handleDropWindow);
    };
  }, []);

  const handleDropEvent = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    dragCounter.current = 0;
    setIsDragging(false);
    const dropped = extractFilesFromDataTransfer(e.dataTransfer);
    if (dropped.length > 0) {
      appendFiles(dropped);
    }
  };

  const handleDragOverEvent = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.dataTransfer) {
      e.dataTransfer.dropEffect = 'copy';
    }
  };

  const canSend = (input.trim().length > 0 || files.length > 0) && !disabled && !isTyping;

  const handleSend = () => {
    if (!canSend) return;
    onSend(input.trim(), { files, webSearch, tools });
    setInput('');
    setFiles([]);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (!isTyping) {
        handleSend();
      }
    }
  };

  const handleFiles = (e: React.ChangeEvent<HTMLInputElement>) => {
    const picked = Array.from(e.target.files ?? []).map(normalizeFile);
    if (picked.length) {
      setFiles(prev => {
        const remainingSlots = Math.max(0, 5 - prev.length);
        if (remainingSlots <= 0) return prev;
        return [...prev, ...picked.slice(0, remainingSlots)];
      });
    }
    e.target.value = '';
  };

  const imageFiles = files.filter(isImageFile);
  const docFiles = files.filter(f => !isImageFile(f));
  const hasChips = files.length > 0 || webSearch || tools;

  return (
    <div className="px-4 pb-4 pt-1">
      <div className="max-w-3xl mx-auto">
        {/* Slang disclaimer info above chat input box */}
        <div className="flex items-center justify-center gap-1.5 pb-1.5 select-none text-xs font-medium text-slate-500/80 dark:text-slate-400/80">
          <span>LocaLLM can trip. Stay sharp.</span>
        </div>

        <div
          onDragEnter={(e) => {
            e.preventDefault();
            if (e.dataTransfer?.types.includes('Files') || e.dataTransfer?.types.includes('application/x-moz-file')) {
              setIsDragging(true);
            }
          }}
          onDragOver={handleDragOverEvent}
          onDrop={handleDropEvent}
          className={`relative bg-white dark:bg-[#121826] border rounded-[28px] p-2 shadow-lg shadow-black/5 dark:shadow-black/40 transition-all ${
            isDragging
              ? 'border-blue-500 ring-2 ring-blue-500/40'
              : 'border-slate-300/80 dark:border-slate-700/80 focus-within:ring-2 focus-within:ring-blue-500/30 focus-within:border-blue-500/60'
          }`}
        >
          {/* Drag Overlay */}
          <AnimatePresence>
            {isDragging && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="absolute inset-0 z-40 rounded-[28px] border-2 border-dashed border-blue-500 bg-blue-500/10 dark:bg-blue-500/20 backdrop-blur-md flex items-center justify-center gap-2.5 text-blue-600 dark:text-blue-400 font-semibold text-sm pointer-events-none"
              >
                <Paperclip className="w-5 h-5 animate-bounce" />
                <span>Drop files here to attach</span>
              </motion.div>
            )}
          </AnimatePresence>

          {/* Attachments & Chips Tray */}
          <AnimatePresence initial={false}>
            {hasChips && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: 'auto', opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                className="overflow-hidden"
              >
                {/* 1. Image Previews Grid */}
                {imageFiles.length > 0 && (
                  <div className="flex flex-wrap gap-2 px-2 pt-1 pb-2">
                    {imageFiles.map((f, i) => (
                      <ImagePreviewCard
                        key={`${f.name}-${i}`}
                        file={f}
                        onRemove={() => setFiles(prev => prev.filter(item => item !== f))}
                      />
                    ))}
                  </div>
                )}

                {/* 2. Documents & Feature Chips */}
                <div className="flex flex-wrap gap-1.5 px-2 pt-0.5 pb-2">
                  {docFiles.map((f, i) => (
                    <DocumentChip
                      key={`${f.name}-${i}`}
                      file={f}
                      onRemove={() => setFiles(prev => prev.filter(item => item !== f))}
                    />
                  ))}
                  {files.length >= 5 && (
                    <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-medium bg-amber-500/15 text-amber-700 dark:text-amber-300 select-none">
                      Max 5 files
                    </span>
                  )}
                  {webSearch && (
                    <Chip
                      icon={<Globe className="w-3 h-3 text-emerald-500" />}
                      label="Web search"
                      onRemove={() => setWebSearchPref(false)}
                    />
                  )}
                  {tools && (
                    <Chip
                      icon={<Wrench className="w-3 h-3 text-purple-500" />}
                      label="Tools"
                      onRemove={() => setToolsPref(false)}
                    />
                  )}
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
            <input
              ref={fileInputRef}
              type="file"
              multiple
              className="hidden"
              onChange={handleFiles}
            />

            <textarea
              ref={textareaRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              onDragOver={handleDragOverEvent}
              onDrop={handleDropEvent}
              placeholder="Message LocaLLM (or drop files here)"
              rows={1}
              disabled={disabled}
              className="flex-1 min-w-0 bg-transparent resize-none py-2 px-2 text-sm md:text-base leading-5 text-slate-900 dark:text-slate-50 placeholder:text-slate-400 dark:placeholder:text-slate-500 focus:outline-none"
            />

            <ModelPicker
              models={models}
              currentId={currentModelId}
              onChange={onChangeModel}
              activePlatform={activePlatform}
            />

            {isTyping ? (
              <motion.button
                type="button"
                onClick={onStop}
                whileTap={{ scale: 0.88 }}
                initial={{ scale: 0.8, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                exit={{ scale: 0.8, opacity: 0 }}
                transition={{ type: 'spring', stiffness: 500, damping: 22 }}
                className="shrink-0 w-9 h-9 rounded-full flex items-center justify-center bg-slate-900 dark:bg-white text-white dark:text-slate-900 shadow-md hover:bg-slate-800 dark:hover:bg-slate-100 cursor-pointer transition-colors"
                aria-label="Stop generation"
                title="Stop generation"
              >
                <Square className="w-3.5 h-3.5 fill-current" />
              </motion.button>
            ) : (
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
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function ImagePreviewCard({ file, onRemove }: { file: File; onRemove: () => void }) {
  const [url, setUrl] = useState<string>('');

  useEffect(() => {
    const objectUrl = URL.createObjectURL(file);
    setUrl(objectUrl);
    return () => URL.revokeObjectURL(objectUrl);
  }, [file]);

  const sizeKb = Math.round(file.size / 1024);

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.8 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.8 }}
      transition={{ type: 'spring', stiffness: 450, damping: 22 }}
      className="relative group w-16 h-16 rounded-2xl overflow-hidden border border-slate-300/80 dark:border-slate-700/80 bg-slate-100 dark:bg-slate-800 shadow-sm shrink-0"
    >
      {url ? (
        <img
          src={url}
          alt={file.name}
          className="w-full h-full object-cover"
        />
      ) : (
        <div className="w-full h-full flex items-center justify-center text-slate-400">
          <ImageIcon className="w-5 h-5" />
        </div>
      )}
      <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
      <button
        type="button"
        onClick={onRemove}
        className="absolute top-1 right-1 w-5 h-5 rounded-full bg-black/70 hover:bg-red-500 text-white flex items-center justify-center shadow-xs cursor-pointer transition-colors"
        title={`Remove ${file.name}`}
        aria-label={`Remove ${file.name}`}
      >
        <X className="w-3 h-3" />
      </button>
      <div className="absolute bottom-1 left-1 right-1 text-[9px] text-white truncate font-medium drop-shadow-md opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none px-1">
        {sizeKb} KB
      </div>
    </motion.div>
  );
}

function DocumentChip({ file, onRemove }: { file: File; onRemove: () => void }) {
  const sizeKb = Math.round(file.size / 1024);
  return (
    <motion.span
      initial={{ opacity: 0, scale: 0.8 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.8 }}
      className="inline-flex items-center gap-1.5 pl-2.5 pr-1.5 py-1 rounded-full text-[11px] font-semibold bg-slate-100 dark:bg-slate-800 text-slate-800 dark:text-slate-200 border border-slate-200 dark:border-slate-700 max-w-[220px]"
    >
      <FileText className="w-3.5 h-3.5 text-blue-500 shrink-0" />
      <span className="truncate flex-1">{file.name}</span>
      <span className="text-[10px] text-slate-400 shrink-0">({sizeKb} KB)</span>
      <button
        type="button"
        onClick={onRemove}
        className="p-0.5 rounded-full hover:bg-slate-200 dark:hover:bg-slate-700 cursor-pointer"
        aria-label={`Remove ${file.name}`}
      >
        <X className="w-3 h-3" />
      </button>
    </motion.span>
  );
}

function Chip({
  icon,
  label,
  onRemove
}: {
  icon: React.ReactNode;
  label: string;
  onRemove: () => void;
}) {
  return (
    <motion.span
      initial={{ opacity: 0, scale: 0.7 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ type: 'spring', stiffness: 520, damping: 18 }}
      className="inline-flex items-center gap-1.5 pl-2.5 pr-1.5 py-1 rounded-full text-[11px] font-semibold bg-slate-100 dark:bg-slate-800 text-slate-800 dark:text-slate-200 border border-slate-200 dark:border-slate-700 max-w-[200px]"
    >
      {icon}
      <span className="truncate">{label}</span>
      <button
        type="button"
        onClick={onRemove}
        className="p-0.5 rounded-full hover:bg-slate-200 dark:hover:bg-slate-700 cursor-pointer"
        aria-label={`Remove ${label}`}
      >
        <X className="w-3 h-3" />
      </button>
    </motion.span>
  );
}
