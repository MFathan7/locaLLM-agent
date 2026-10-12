import {
  ArrowUp,
  Square,
  X,
  Paperclip,
  Brain,
  FileText,
  FileCode,
  FileSpreadsheet,
  File as FileGeneric,
  Image as ImageIcon
} from 'lucide-react';
import { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import clsx from 'clsx';
import type { ModelInfo, SendOptions, ModelCapabilities } from '../types';
import { PlusMenu } from './PlusMenu';

interface ChatInputProps {
  onSend: (message: string, options: SendOptions) => void;
  onStop?: () => void;
  disabled?: boolean;
  isTyping?: boolean;
  models?: ModelInfo[];
  currentModelId?: string;
  currentModel?: ModelInfo;
  isThinkingCompatible?: boolean;
  activeSessionId?: string | null;
}

const DEFAULT_CAPS: ModelCapabilities = { files: true, webSearch: true, tools: true, thinking: false };

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
  currentModel,
  isThinkingCompatible,
  activeSessionId
}: ChatInputProps) {
  const [input, setInput] = useState('');
  const [files, setFiles] = useState<File[]>([]);
  const [previewFile, setPreviewFile] = useState<File | null>(null);
  const [webSearchPref, setWebSearchPref] = useState(false);
  const [toolsPref, setToolsPref] = useState(false);
  const [thinkingPref, setThinkingPref] = useState(false);
  const [isExpanded, setIsExpanded] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const dragCounter = useRef(0);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    // Reset thinking mode to false on new chat / session change
    setThinkingPref(false);
  }, [activeSessionId]);

  useEffect(() => {
    if (!disabled && textareaRef.current) {
      textareaRef.current.focus();
    }
  }, [disabled]);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const capabilities = currentModel?.capabilities ?? (models?.find(m => m.id === currentModelId)?.capabilities ?? DEFAULT_CAPS);
  const isCompatible = typeof isThinkingCompatible === 'boolean'
    ? isThinkingCompatible
    : Boolean(capabilities.thinking);
  const webSearch = webSearchPref && (capabilities.webSearch ?? true);
  const tools = toolsPref && (capabilities.tools ?? true);
  const thinking = thinkingPref && isCompatible;

  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;

    // Reset height temporarily to accurately compute scrollHeight
    el.style.height = 'auto';
    const scrollH = el.scrollHeight;
    const maxHeight = 200;

    el.style.height = `${Math.min(scrollH, maxHeight)}px`;
    el.style.overflowY = scrollH > maxHeight ? 'auto' : 'hidden';

    // Prevent expansion hysteresis loop: keep expanded until cleared or deleted to single line
    const shouldExpand = Boolean(
      input.trim().length > 0 && (
        input.includes('\n') ||
        (isExpanded ? (scrollH > 44 || input.trim().length >= 40) : scrollH > 44)
      )
    );

    if (shouldExpand !== isExpanded) {
      setIsExpanded(shouldExpand);
    }
  }, [input, isExpanded]);

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
    onSend(input.trim(), { files, webSearch, tools, thinking });
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

  const handlePaste = (e: React.ClipboardEvent) => {
    const pasted = extractFilesFromDataTransfer(e.clipboardData);
    if (pasted.length > 0) {
      e.preventDefault();
      appendFiles(pasted);
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
  const hasChips = files.length > 0;

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
          onPaste={handlePaste}
          className={`relative bg-white dark:bg-[#121826] border rounded-[26px] py-1.5 px-2 shadow-lg shadow-black/5 dark:shadow-black/40 transition-all ${
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
                className="absolute inset-0 z-40 rounded-[26px] border-2 border-dashed border-blue-500 bg-blue-500/10 dark:bg-blue-500/20 backdrop-blur-md flex items-center justify-center gap-2.5 text-blue-600 dark:text-blue-400 font-semibold text-sm pointer-events-none"
              >
                <Paperclip className="w-5 h-5 animate-bounce" />
                <span>Drop files here to attach</span>
              </motion.div>
            )}
          </AnimatePresence>

          {/* Attachments Tray (Only shown when files are attached) */}
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
                        onPreview={() => setPreviewFile(f)}
                      />
                    ))}
                  </div>
                )}

                {/* 2. Documents */}
                {docFiles.length > 0 && (
                  <div className="flex flex-wrap gap-1.5 px-2 pt-0.5 pb-2">
                    {docFiles.map((f, i) => (
                      <DocumentChip
                        key={`${f.name}-${i}`}
                        file={f}
                        onRemove={() => setFiles(prev => prev.filter(item => item !== f))}
                        onPreview={() => setPreviewFile(f)}
                      />
                    ))}
                    {files.length >= 5 && (
                      <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-medium bg-amber-500/15 text-amber-700 dark:text-amber-300 select-none">
                        Max 5 files
                      </span>
                    )}
                  </div>
                )}
              </motion.div>
            )}
          </AnimatePresence>

          <div
            className={clsx(
              "grid transition-[gap,padding] duration-150",
              isExpanded
                ? "grid-cols-[1fr_auto] gap-y-2 pt-0.5"
                : "grid-cols-[auto_1fr_auto] items-center gap-1.5"
            )}
          >
            <div className={clsx("shrink-0", isExpanded ? "col-start-1 row-start-2 justify-self-start self-center" : "self-center")}>
              <PlusMenu
                capabilities={capabilities}
                webSearch={webSearch}
                tools={tools}
                onUploadClick={() => fileInputRef.current?.click()}
                onToggleWebSearch={() => setWebSearchPref(v => !v)}
                onToggleTools={() => setToolsPref(v => !v)}
              />
            </div>

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
              onPaste={handlePaste}
              placeholder="Message LocaLLM (or drop files here)"
              rows={1}
              disabled={disabled}
              className={clsx(
                "bg-transparent resize-none text-sm md:text-base text-slate-900 dark:text-slate-50 placeholder:text-slate-400 dark:placeholder:text-slate-500 focus:outline-none py-1 px-2 leading-6 overflow-y-hidden self-center",
                isExpanded
                  ? "col-span-2 row-start-1 w-full min-w-0 max-h-[200px]"
                  : "min-w-0"
              )}
            />

            <div
              className={clsx(
                "flex items-center gap-1.5 shrink-0 self-center",
                isExpanded && "col-start-2 row-start-2 justify-self-end"
              )}
            >
              <AnimatePresence>
                {isCompatible && (
                  <motion.button
                    type="button"
                    onClick={() => setThinkingPref(v => !v)}
                    whileTap={{ scale: 0.94 }}
                    initial={{ opacity: 0, scale: 0.88 }}
                    animate={{ opacity: 1, scale: 1 }}
                    exit={{ opacity: 0, scale: 0.88 }}
                    transition={{ type: 'spring', stiffness: 500, damping: 25 }}
                    aria-pressed={thinking}
                    aria-label={thinking ? "Thinking mode enabled" : "Thinking mode disabled"}
                    title={thinking ? "Thinking mode: ON" : "Thinking mode: OFF"}
                    className={clsx(
                      "h-8 px-3 rounded-full flex items-center gap-1.5 text-xs font-semibold cursor-pointer transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 shrink-0 select-none",
                      thinking
                        ? "bg-blue-100/90 dark:bg-blue-900/60 text-blue-700 dark:text-blue-300 border border-blue-300/90 dark:border-blue-700/80 shadow-xs"
                        : "text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200 hover:bg-black/[0.05] dark:hover:bg-white/[0.06] border border-transparent"
                    )}
                  >
                    <Brain className="w-3.5 h-3.5 shrink-0" aria-hidden="true" />
                    <span>Thinking</span>
                  </motion.button>
                )}
              </AnimatePresence>

              {isTyping ? (
                <motion.button
                  type="button"
                  onClick={(e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    onStop?.();
                  }}
                  whileTap={{ scale: 0.88 }}
                  initial={{ scale: 0.8, opacity: 0 }}
                  animate={{ scale: 1, opacity: 1 }}
                  exit={{ scale: 0.8, opacity: 0 }}
                  transition={{ type: 'spring', stiffness: 500, damping: 22 }}
                  className="shrink-0 w-8.5 h-8.5 rounded-full flex items-center justify-center bg-slate-900 dark:bg-white text-white dark:text-slate-900 shadow-md hover:bg-slate-800 dark:hover:bg-slate-100 cursor-pointer transition-colors z-20"
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
                  className="shrink-0 w-8.5 h-8.5 rounded-full flex items-center justify-center bg-blue-600 text-white shadow-[inset_0_1px_1px_rgba(255,255,255,0.45),0_6px_14px_-4px_rgba(37,99,235,0.6)] cursor-pointer disabled:cursor-not-allowed"
                  aria-label="Send message"
                >
                  <ArrowUp className="w-4 h-4" />
                </motion.button>
              )}
            </div>
          </div>
        </div>

        {/* File Preview Modal Pop-up */}
        <AnimatePresence>
          {previewFile && (
            <FilePreviewModal
              file={previewFile}
              onClose={() => setPreviewFile(null)}
            />
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}

function getFileIcon(fileName: string) {
  const ext = fileName.split('.').pop()?.toLowerCase() || '';
  if (ext === 'pdf') {
    return <FileText className="w-3.5 h-3.5 text-rose-500 shrink-0" />;
  }
  if (['py', 'js', 'ts', 'tsx', 'jsx', 'json', 'html', 'css', 'scss', 'sh', 'bash', 'sql', 'cpp', 'c', 'java', 'rs', 'go', 'yaml', 'yml'].includes(ext)) {
    return <FileCode className="w-3.5 h-3.5 text-amber-500 shrink-0" />;
  }
  if (['csv', 'xlsx', 'xls', 'tsv'].includes(ext)) {
    return <FileSpreadsheet className="w-3.5 h-3.5 text-emerald-500 shrink-0" />;
  }
  return <FileText className="w-3.5 h-3.5 text-blue-500 shrink-0" />;
}

function ImagePreviewCard({
  file,
  onRemove,
  onPreview
}: {
  file: File;
  onRemove: () => void;
  onPreview: () => void;
}) {
  const [url, setUrl] = useState<string>('');

  useEffect(() => {
    const objectUrl = URL.createObjectURL(file);
    setUrl(objectUrl);
    return () => URL.revokeObjectURL(objectUrl);
  }, [file]);

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.8 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.8 }}
      transition={{ type: 'spring', stiffness: 450, damping: 22 }}
      onClick={onPreview}
      title={file.name}
      className="relative group w-16 h-16 rounded-2xl overflow-hidden border border-slate-300/80 dark:border-slate-700/80 bg-slate-100 dark:bg-slate-800 shadow-sm shrink-0 cursor-pointer hover:ring-2 hover:ring-blue-500/40 transition-all select-none"
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
        onClick={(e) => {
          e.stopPropagation();
          onRemove();
        }}
        className="absolute top-1 right-1 w-5 h-5 rounded-full bg-black/70 hover:bg-red-500 text-white flex items-center justify-center shadow-xs cursor-pointer transition-colors z-10"
        title={`Remove ${file.name}`}
        aria-label={`Remove ${file.name}`}
      >
        <X className="w-3 h-3" />
      </button>
      {/* File name tooltip preview on hover (size is omitted as requested) */}
      <div className="absolute bottom-1 left-1 right-1 text-[9px] text-white truncate font-medium drop-shadow-md opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none px-0.5">
        {file.name}
      </div>
    </motion.div>
  );
}

function DocumentChip({
  file,
  onRemove,
  onPreview
}: {
  file: File;
  onRemove: () => void;
  onPreview: () => void;
}) {
  return (
    <motion.span
      initial={{ opacity: 0, scale: 0.8 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.8 }}
      onClick={onPreview}
      title={file.name}
      className="inline-flex items-center gap-1.5 pl-2.5 pr-1.5 py-1 rounded-full text-[11px] font-semibold bg-slate-100 hover:bg-slate-200/80 dark:bg-slate-800 dark:hover:bg-slate-700/80 text-slate-800 dark:text-slate-200 border border-slate-200 dark:border-slate-700 max-w-[220px] cursor-pointer transition-colors group/doc select-none"
    >
      {getFileIcon(file.name)}
      <span className="truncate flex-1 group-hover/doc:text-blue-600 dark:group-hover/doc:text-blue-400 transition-colors">
        {file.name}
      </span>
      {/* No file size displayed on hover, tooltip with name provided via title attribute */}
      <button
        type="button"
        onClick={(e) => {
          e.stopPropagation();
          onRemove();
        }}
        className="p-0.5 rounded-full hover:bg-slate-300 dark:hover:bg-slate-600 text-slate-500 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-100 cursor-pointer transition-colors"
        aria-label={`Remove ${file.name}`}
      >
        <X className="w-3 h-3" />
      </button>
    </motion.span>
  );
}

function FilePreviewModal({ file, onClose }: { file: File; onClose: () => void }) {
  const [url, setUrl] = useState<string>('');
  const [textContent, setTextContent] = useState<string>('');
  const [isLoadingText, setIsLoadingText] = useState(false);

  const isImage = isImageFile(file);
  const ext = file.name.split('.').pop()?.toLowerCase() || '';
  const isPdf = file.type === 'application/pdf' || ext === 'pdf';
  const isCodeOrText =
    file.type.startsWith('text/') ||
    [
      'txt', 'md', 'py', 'js', 'ts', 'tsx', 'jsx', 'json', 'html', 'css',
      'scss', 'sh', 'bash', 'zsh', 'sql', 'cpp', 'c', 'h', 'hpp', 'java',
      'rs', 'go', 'yaml', 'yml', 'toml', 'ini', 'env', 'xml', 'csv', 'log',
      'svg', 'dockerfile'
    ].includes(ext);

  useEffect(() => {
    const objectUrl = URL.createObjectURL(file);
    setUrl(objectUrl);
    return () => URL.revokeObjectURL(objectUrl);
  }, [file]);

  useEffect(() => {
    if (isCodeOrText && !isImage) {
      setIsLoadingText(true);
      let isMounted = true;
      file
        .text()
        .then(content => {
          if (isMounted) {
            // Cap preview length to avoid UI lag on massive files
            const maxLen = 200000;
            if (content.length > maxLen) {
              setTextContent(content.slice(0, maxLen) + '\n\n... [File content truncated for preview]');
            } else {
              setTextContent(content);
            }
            setIsLoadingText(false);
          }
        })
        .catch(() => {
          if (isMounted) {
            setTextContent('Unable to read text content from this file.');
            setIsLoadingText(false);
          }
        });
      return () => {
        isMounted = false;
      };
    }
  }, [file, isCodeOrText, isImage]);

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
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      onClick={onClose}
      className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-6 bg-black/60 backdrop-blur-sm"
    >
      <motion.div
        initial={{ scale: 0.94, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        exit={{ scale: 0.94, opacity: 0 }}
        transition={{ type: 'spring', stiffness: 450, damping: 25 }}
        onClick={(e) => e.stopPropagation()}
        className="relative w-full max-w-3xl max-h-[85vh] bg-white dark:bg-[#151c28] border border-slate-200/90 dark:border-white/10 rounded-2xl shadow-2xl flex flex-col overflow-hidden"
      >
        {/* Modal Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-slate-200/80 dark:border-white/10 bg-slate-50/50 dark:bg-black/20 shrink-0">
          <div className="flex items-center gap-2.5 min-w-0 pr-2">
            <div className="w-7 h-7 rounded-lg bg-blue-500/10 text-blue-600 dark:text-blue-400 flex items-center justify-center shrink-0">
              {isImage ? (
                <ImageIcon className="w-4 h-4 text-sky-500" />
              ) : (
                getFileIcon(file.name)
              )}
            </div>
            <div className="min-w-0">
              <h3 className="font-semibold text-sm sm:text-base text-slate-900 dark:text-slate-100 truncate" title={file.name}>
                {file.name}
              </h3>
            </div>
          </div>

          <button
            type="button"
            onClick={onClose}
            className="p-1.5 rounded-full hover:bg-slate-200/80 dark:hover:bg-slate-700/80 text-slate-500 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-100 cursor-pointer transition-colors"
            title="Close preview (Esc)"
            aria-label="Close preview"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="flex-1 overflow-auto p-4 flex items-center justify-center bg-slate-100/40 dark:bg-black/10 min-h-[220px]">
          {isImage ? (
            <div className="w-full flex items-center justify-center">
              <img
                src={url}
                alt={file.name}
                className="max-h-[68vh] max-w-full object-contain rounded-xl shadow-xs"
              />
            </div>
          ) : isPdf ? (
            <div className="w-full h-[65vh]">
              <iframe
                src={url}
                title={file.name}
                className="w-full h-full rounded-xl border border-slate-200 dark:border-slate-800 bg-white"
              />
            </div>
          ) : isCodeOrText ? (
            <div className="w-full max-h-[68vh] overflow-auto rounded-xl border border-slate-200/80 dark:border-white/10 bg-slate-50 dark:bg-[#0c1017]">
              {isLoadingText ? (
                <div className="p-8 text-center text-xs text-slate-400">Loading file content...</div>
              ) : (
                <pre className="p-4 text-xs font-mono text-slate-800 dark:text-slate-200 whitespace-pre-wrap leading-relaxed select-text scrollbar-thin">
                  <code>{textContent}</code>
                </pre>
              )}
            </div>
          ) : (
            <div className="p-8 flex flex-col items-center justify-center text-center gap-2.5">
              <div className="w-14 h-14 rounded-2xl bg-blue-500/10 text-blue-600 dark:text-blue-400 flex items-center justify-center">
                <FileGeneric className="w-7 h-7" />
              </div>
              <p className="font-semibold text-sm text-slate-800 dark:text-slate-200">{file.name}</p>
              <p className="text-xs text-slate-500 dark:text-slate-400">Pratinjau visual langsung tidak tersedia untuk format file biner ini.</p>
            </div>
          )}
        </div>
      </motion.div>
    </motion.div>
  );
}
