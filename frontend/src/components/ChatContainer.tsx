import { useEffect, useRef, useState, useCallback, useMemo } from 'react';
import type { Message, SourceItem } from '../types';
import { motion, AnimatePresence } from 'motion/react';
import { Copy, Check, ArrowDown, FileDown, Compass, Sparkles, RotateCcw } from 'lucide-react';
import clsx from 'clsx';
import { MarkdownRenderer } from './MarkdownRenderer';
import { cleanAssistantContent, extractSourcesFromText, isOnlyThinking } from '../utils/messageProcessor';
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
            {isTyping && (
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

  // Clean intermediate thinking/search trace from the final rendered output
  const cleanedContent = useMemo(() => {
    return isUser ? message.content : cleanAssistantContent(message.content);
  }, [isUser, message.content]);

  // Check if model is actively thinking and hasn't produced final text yet
  const currentlyThinking = useMemo(() => {
    return !isUser && isTyping && isOnlyThinking(message.content);
  }, [isUser, isTyping, message.content]);

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
        /* User message: clean rounded rectangle bubble with copy button on its left */
        <div className="relative group flex items-end justify-end gap-1.5 max-w-[90%] sm:max-w-[80%]">
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
      ) : (
        /* AI Assistant response: rich Markdown rendering without background container */
        <div className="relative group w-full py-1 text-slate-800 dark:text-slate-100">
          {currentlyThinking ? (
            /* Subtle thinking indicator while reasoning is underway */
            <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-xl bg-blue-500/10 text-blue-600 dark:text-blue-400 text-xs font-semibold animate-pulse">
              <Sparkles className="w-3.5 h-3.5 animate-spin" />
              <span>Thinking and reasoning...</span>
            </div>
          ) : (
            <MarkdownRenderer content={cleanedContent || message.content} />
          )}

          {/* Action icon buttons row: icon-only with animated hover tooltips */}
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
