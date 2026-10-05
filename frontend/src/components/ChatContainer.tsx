import { useEffect, useRef, useState, useCallback, useMemo } from 'react';
import type { Message, SourceItem, AttachedFile } from '../types';
import { motion, AnimatePresence } from 'motion/react';
import { Copy, Check, ArrowDown, FileDown, Compass, Sparkles, RotateCcw, FileText, Image as ImageIcon } from 'lucide-react';
import clsx from 'clsx';
import { MarkdownRenderer } from './MarkdownRenderer';
import { cleanAssistantContent, extractCurrentThinkingStep, extractSourcesFromText, isOnlyThinking } from '../utils/messageProcessor';
import { exportResponseToDoc } from '../utils/docExport';

interface ChatContainerProps {
  messages: Message[];
  isTyping: boolean;
  selectedSourceMessageId?: string | null;
  onToggleSources?: (message: Message) => void;
  sessionTitle?: string;
  onRegenerate?: (message: Message) => void;
}

export function ChatContainer({
  messages,
  isTyping,
  selectedSourceMessageId,
  onToggleSources,
  sessionTitle,
  onRegenerate
}: ChatContainerProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const [showScrollBottom, setShowScrollBottom] = useState(false);
  const isAutoScrollingRef = useRef(false);

  // Filter out any raw tool execution dumps or system messages to keep chat ultra-fast and clean
  const visibleMessages = useMemo(() => {
    return messages.filter(m => m.role === 'user' || m.role === 'assistant');
  }, [messages]);

  // Scroll to bottom helper
  const scrollToBottom = useCallback((smooth = true) => {
    isAutoScrollingRef.current = true;
    bottomRef.current?.scrollIntoView({ behavior: smooth ? 'smooth' : 'auto' });
    setTimeout(() => {
      isAutoScrollingRef.current = false;
      setShowScrollBottom(false);
    }, 350);
  }, []);

  // Check scroll position to toggle the scroll-to-bottom arrow button
  const handleScroll = () => {
    if (isAutoScrollingRef.current) return;
    const el = containerRef.current;
    if (!el) return;

    // Distance in pixels from the current scroll position to the bottom of the container
    const distanceFromBottom = el.scrollHeight - el.scrollTop - el.clientHeight;
    // Show button when user scrolls up more than 140px; hide when within 70px of the bottom
    if (distanceFromBottom > 140) {
      setShowScrollBottom(true);
    } else if (distanceFromBottom <= 70) {
      setShowScrollBottom(false);
    }
  };

  useEffect(() => {
    // Only auto-scroll on new messages if the user is not actively scrolled up reading history
    const el = containerRef.current;
    if (!el) return;
    const distanceFromBottom = el.scrollHeight - el.scrollTop - el.clientHeight;
    if (distanceFromBottom < 180 || isTyping) {
      scrollToBottom(true);
    }
  }, [visibleMessages, isTyping, scrollToBottom]);

  return (
    <div className="relative flex-1 flex flex-col min-h-0 overflow-hidden">
      {/* Scrollable chat messages container */}
      <div
        ref={containerRef}
        onScroll={handleScroll}
        className="flex-1 overflow-y-auto px-4 py-4 md:px-8 scroll-smooth"
      >
        <div className="max-w-3xl mx-auto space-y-6">
          <AnimatePresence initial={false}>
            {visibleMessages.map((msg) => (
              <ChatBubble
                key={msg.id}
                message={msg}
                isTyping={isTyping}
                isSelectedSource={selectedSourceMessageId === msg.id}
                onToggleSources={onToggleSources}
                sessionTitle={sessionTitle}
                onRegenerate={onRegenerate}
              />
            ))}
            {isTyping && (!visibleMessages.length || visibleMessages[visibleMessages.length - 1].role === 'user') && (
              <motion.div
                initial={{ opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                className="flex items-center gap-1.5 py-2 px-1"
              >
                <span className="w-2 h-2 rounded-full bg-blue-500 animate-bounce" style={{ animationDelay: '0ms' }} />
                <span className="w-2 h-2 rounded-full bg-blue-500 animate-bounce" style={{ animationDelay: '150ms' }} />
                <span className="w-2 h-2 rounded-full bg-blue-500 animate-bounce" style={{ animationDelay: '300ms' }} />
              </motion.div>
            )}
          </AnimatePresence>
          <div ref={bottomRef} className="h-4" />
        </div>
      </div>

      {/* Floating Scroll-to-Bottom Arrow Button (Centered at bottom, icon-only) */}
      <AnimatePresence>
        {showScrollBottom && (
          <motion.div
            initial={{ opacity: 0, scale: 0.8, y: 14 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.8, y: 14 }}
            transition={{ type: 'spring', stiffness: 380, damping: 24 }}
            className="absolute bottom-4 left-1/2 -translate-x-1/2 z-20 pointer-events-auto"
          >
            <button
              onClick={() => scrollToBottom(true)}
              className="w-10 h-10 rounded-full flex items-center justify-center liquid-glass-strong border border-white/40 dark:border-white/10 shadow-lg text-slate-800 dark:text-slate-100 hover:text-blue-600 dark:hover:text-blue-400 hover:shadow-xl active:scale-95 transition-all cursor-pointer backdrop-blur-md"
              aria-label="Scroll to bottom"
              title="Scroll to bottom"
            >
              <ArrowDown className="w-5 h-5 text-blue-600 dark:text-blue-400 animate-pulse" />
            </button>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

interface ChatBubbleProps {
  message: Message;
  isTyping: boolean;
  isSelectedSource?: boolean;
  onToggleSources?: (message: Message) => void;
  sessionTitle?: string;
  onRegenerate?: (message: Message) => void;
}

function formatFileSize(bytes: number): string {
  if (!bytes || bytes <= 0) return '0 B';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

const ChatBubble = ({
  message,
  isTyping,
  isSelectedSource,
  onToggleSources,
  sessionTitle,
  onRegenerate
}: ChatBubbleProps) => {
  const isUser = message.role === 'user';
  const [copied, setCopied] = useState(false);

  // Attached files and images
  const attachedFiles: AttachedFile[] = useMemo(() => {
    if (message.files && message.files.length > 0) {
      return message.files;
    }
    if (message.options?.files && message.options.files.length > 0) {
      return message.options.files.map(name => ({
        name,
        size: 0,
        type: 'application/octet-stream',
        url: undefined,
        content: undefined
      }));
    }
    return [];
  }, [message.files, message.options?.files]);

  const imageFiles = useMemo(() => {
    return attachedFiles.filter(f =>
      Boolean(f.url) ||
      f.type?.startsWith('image/') ||
      /\.(png|jpe?g|gif|webp|svg|bmp|avif|ico|heic|heif|tiff?)$/i.test(f.name)
    );
  }, [attachedFiles]);

  const docFiles = useMemo(() => {
    return attachedFiles.filter(f => !imageFiles.includes(f));
  }, [attachedFiles, imageFiles]);

  // Clean intermediate thinking/search trace from the final rendered output
  const cleanedContent = useMemo(() => {
    return isUser ? message.content : cleanAssistantContent(message.content);
  }, [isUser, message.content]);

  // Check if model is actively thinking and hasn't produced final text yet
  const currentlyThinking = useMemo(() => {
    return !isUser && isTyping && isOnlyThinking(message.content);
  }, [isUser, isTyping, message.content]);

  // Extract active dynamic reasoning or tool step
  const currentThinkingStep = useMemo(() => {
    return extractCurrentThinkingStep(message.content);
  }, [message.content]);

  // Calculate sources attached or extract from content
  const sources = useMemo<SourceItem[]>(() => {
    if (isUser) return [];
    return extractSourcesFromText(message.content, message.sources);
  }, [isUser, message.content, message.sources]);

  const handleCopy = () => {
    navigator.clipboard.writeText(cleanedContent || message.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleExportToDoc = () => {
    exportResponseToDoc({
      title: sessionTitle || 'LocaLLM Assistant Response',
      content: cleanedContent || message.content,
      sources,
      timestamp: message.timestamp
    });
  };

  return (
    <div className={`w-full flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      {isUser ? (
        /* User message: attached files & image previews rendered above the bubble */
        <div className="relative group flex flex-col items-end gap-1.5 max-w-[90%] sm:max-w-[80%]">
          {/* 1. Image Previews */}
          {imageFiles.length > 0 && (
            <div className="flex flex-wrap justify-end gap-2 max-w-full">
              {imageFiles.map((img, idx) => (
                <div
                  key={`${img.name}-${idx}`}
                  className="group/img relative rounded-2xl overflow-hidden border border-slate-200/80 dark:border-white/15 bg-black/5 dark:bg-black/30 shadow-sm max-w-xs transition-transform hover:scale-[1.01]"
                >
                  {img.url ? (
                    <img
                      src={img.url}
                      alt={img.name}
                      className="max-h-56 max-w-full object-cover rounded-2xl block"
                    />
                  ) : (
                    <div className="px-3 py-2 flex items-center gap-2 bg-slate-100 dark:bg-slate-800 text-xs text-slate-700 dark:text-slate-300">
                      <ImageIcon className="w-4 h-4 text-sky-500 shrink-0" />
                      <span className="truncate max-w-[160px] font-medium">{img.name}</span>
                    </div>
                  )}
                  <div className="absolute inset-x-0 bottom-0 px-2.5 py-1 bg-gradient-to-t from-black/80 via-black/40 to-transparent text-[11px] text-white/95 truncate opacity-0 group-hover/img:opacity-100 transition-opacity">
                    {img.name}
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* 2. Document & Code File Cards */}
          {docFiles.length > 0 && (
            <div className="flex flex-wrap justify-end gap-1.5 max-w-full">
              {docFiles.map((file, idx) => (
                <div
                  key={`${file.name}-${idx}`}
                  className="inline-flex items-center gap-2 px-3 py-1.5 rounded-2xl bg-white/90 dark:bg-[#151c28]/90 border border-slate-200/80 dark:border-white/15 shadow-xs text-xs text-slate-800 dark:text-slate-200 backdrop-blur-md"
                >
                  <div className="w-6 h-6 rounded-lg bg-blue-500/10 text-blue-600 dark:text-blue-400 flex items-center justify-center shrink-0">
                    <FileText className="w-3.5 h-3.5" />
                  </div>
                  <div className="min-w-0 max-w-[190px]">
                    <div className="font-medium truncate text-slate-800 dark:text-slate-100">{file.name}</div>
                    {file.size > 0 && (
                      <div className="text-[10px] text-slate-500 dark:text-slate-400">
                        {formatFileSize(file.size)}
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* 3. Text Message Bubble */}
          {(message.content && message.content.trim().length > 0) && (
            <div className="flex items-end justify-end gap-1.5 w-full">
              <div className="opacity-90 sm:opacity-0 sm:group-hover:opacity-100 transition-opacity pb-0.5 shrink-0">
                <ActionIconButton
                  icon={copied ? <Check className="w-3.5 h-3.5 text-emerald-500" /> : <Copy className="w-3.5 h-3.5" />}
                  tooltip={copied ? 'Copied to clipboard' : 'Copy message text'}
                  onClick={handleCopy}
                  ariaLabel="Copy message text"
                />
              </div>

              <div className="px-4.5 py-3 text-[15px]/relaxed md:text-[16px]/relaxed bg-blue-600 text-white rounded-[20px] shadow-[inset_0_1px_1px_rgba(255,255,255,0.35),0_8px_20px_-8px_rgba(37,99,235,0.5)]">
                <div className="whitespace-pre-wrap selection:bg-white/30">{message.content}</div>
              </div>
            </div>
          )}
        </div>
      ) : (
        /* AI Assistant response: rich Markdown rendering without background container */
        <div className="relative group w-full py-1 text-slate-800 dark:text-slate-100">
          {currentlyThinking ? (
            /* Dynamic animated thinking indicator showing the active reasoning / tool step */
            <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-xl bg-blue-500/10 text-blue-600 dark:text-blue-400 text-xs font-semibold animate-pulse border border-blue-500/20">
              <Sparkles className="w-3.5 h-3.5 animate-spin text-blue-500 shrink-0" />
              <span>{currentThinkingStep}</span>
            </div>
          ) : isTyping && !cleanedContent && !message.content ? (
            /* Active stream connection / initial response loading */
            <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-xl bg-blue-500/10 text-blue-600 dark:text-blue-400 text-xs font-semibold animate-pulse border border-blue-500/20">
              <Sparkles className="w-3.5 h-3.5 animate-spin text-blue-500 shrink-0" />
              <span>Refining user inquiry...</span>
            </div>
          ) : (!cleanedContent && !message.content) ? (
            /* Friendly fallback if response is empty */
            <div className="inline-flex items-center gap-2 px-3.5 py-2.5 rounded-2xl bg-amber-500/10 dark:bg-amber-500/15 border border-amber-500/30 text-amber-800 dark:text-amber-200 text-xs font-medium">
              <span className="w-2 h-2 rounded-full bg-amber-500 shrink-0" />
              <span>Model tidak memberikan respon teks. Anda dapat mengklik tombol <strong>Re-answer</strong> di bawah untuk mencoba kembali.</span>
            </div>
          ) : (
            <MarkdownRenderer content={cleanedContent || message.content} />
          )}

          {/* Action icon buttons row: icon-only with animated hover tooltips */}
          {(!isTyping || message.content) && (
            <div className="mt-3 flex items-center gap-1.5 opacity-90 sm:opacity-0 sm:group-hover:opacity-100 transition-opacity">
            {/* Copy button */}
            <ActionIconButton
              icon={copied ? <Check className="w-3.5 h-3.5 text-emerald-500" /> : <Copy className="w-3.5 h-3.5" />}
              tooltip={copied ? 'Copied to clipboard' : 'Copy response'}
              onClick={handleCopy}
              ariaLabel="Copy response"
            />

            {/* Re-answer button (placed between Copy and Export to docs) */}
            <ActionIconButton
              icon={<RotateCcw className={clsx("w-3.5 h-3.5", isTyping && "animate-spin")} />}
              tooltip={isTyping ? "Generating..." : "Re-answer"}
              onClick={() => onRegenerate?.(message)}
              disabled={isTyping}
              ariaLabel="Re-answer"
            />

            {/* Export to document button */}
            <ActionIconButton
              icon={<FileDown className="w-3.5 h-3.5" />}
              tooltip="Export to docs (.doc)"
              onClick={handleExportToDoc}
              ariaLabel="Export to document"
            />

            {/* View sources button */}
            <ActionIconButton
              icon={<Compass className="w-3.5 h-3.5" />}
              tooltip="View sources"
              onClick={() => onToggleSources?.(message)}
              isActive={isSelectedSource}
              badge={sources.length > 0 ? sources.length : undefined}
              ariaLabel="View sources"
            />
          </div>
          )}
        </div>
      )}
    </div>
  );
};

interface ActionIconButtonProps {
  icon: React.ReactNode;
  tooltip: string;
  onClick: () => void;
  ariaLabel: string;
  isActive?: boolean;
  badge?: number;
  disabled?: boolean;
}

function ActionIconButton({
  icon,
  tooltip,
  onClick,
  ariaLabel,
  isActive = false,
  badge,
  disabled = false
}: ActionIconButtonProps) {
  const [showTooltip, setShowTooltip] = useState(false);

  return (
    <div className="relative inline-flex items-center">
      <button
        type="button"
        disabled={disabled}
        onClick={onClick}
        onMouseEnter={() => !disabled && setShowTooltip(true)}
        onMouseLeave={() => setShowTooltip(false)}
        onFocus={() => !disabled && setShowTooltip(true)}
        onBlur={() => setShowTooltip(false)}
        aria-label={ariaLabel}
        className={clsx(
          'relative p-1.5 rounded-lg transition-all',
          disabled
            ? 'opacity-40 cursor-not-allowed text-slate-400'
            : 'cursor-pointer',
          !disabled && isActive
            ? 'bg-blue-500/15 text-blue-600 dark:text-blue-400 font-bold'
            : !disabled
            ? 'text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white hover:bg-black/[0.05] dark:hover:bg-white/[0.08]'
            : ''
        )}
      >
        {icon}
        {typeof badge === 'number' && badge > 0 && (
          <span className="absolute -top-1 -right-1 px-1 min-w-[14px] h-[14px] flex items-center justify-center text-[9px] font-bold rounded-full bg-blue-600 text-white leading-none">
            {badge > 99 ? '99+' : badge}
          </span>
        )}
      </button>

      {/* Floating tooltip on hover */}
      <AnimatePresence>
        {showTooltip && (
          <motion.div
            initial={{ opacity: 0, y: 4, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 2, scale: 0.95 }}
            transition={{ duration: 0.12 }}
            className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-2.5 py-1 bg-slate-900 dark:bg-zinc-800 text-white text-[11px] font-medium rounded-lg shadow-xl shadow-black/25 pointer-events-none whitespace-nowrap z-30 border border-white/10"
          >
            {tooltip}
            <div className="absolute top-full left-1/2 -translate-x-1/2 -mt-1 border-4 border-transparent border-t-slate-900 dark:border-t-zinc-800" />
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
