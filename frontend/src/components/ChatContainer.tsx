import { useEffect, useRef } from 'react';
import type { Message } from '../types';
import { motion, AnimatePresence } from 'motion/react';
import clsx from 'clsx';
import { Copy, Check, User, Bot } from 'lucide-react';
import { useState } from 'react';

interface ChatContainerProps {
  messages: Message[];
  isTyping: boolean;
}

export function ChatContainer({ messages, isTyping }: ChatContainerProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isTyping]);

  return (
    <div className="flex-1 overflow-y-auto px-4 py-4 md:px-8">
      <div className="max-w-3xl mx-auto space-y-4">
        <AnimatePresence initial={false}>
          {messages.map((msg) => (
            <ChatBubble key={msg.id} message={msg} />
          ))}
          {isTyping && (
            <motion.div
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              className="flex items-start gap-2.5"
            >
              <div className="w-7 h-7 rounded-full liquid-glass flex items-center justify-center shrink-0 text-blue-600 dark:text-blue-400">
                <Bot className="w-3.5 h-3.5" />
              </div>
              <div className="liquid-glass-bubble rounded-[20px] px-4 py-3 flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 rounded-full bg-blue-500 animate-bounce" style={{ animationDelay: '0ms' }} />
                <span className="w-1.5 h-1.5 rounded-full bg-blue-500 animate-bounce" style={{ animationDelay: '150ms' }} />
                <span className="w-1.5 h-1.5 rounded-full bg-blue-500 animate-bounce" style={{ animationDelay: '300ms' }} />
              </div>
            </motion.div>
          )}
        </AnimatePresence>
        <div ref={bottomRef} className="h-2" />
      </div>
    </div>
  );
}

function ChatBubble({ message }: { message: Message }) {
  const isUser = message.role === 'user';
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(message.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 10, scale: 0.98 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ type: 'spring', stiffness: 300, damping: 24 }}
      className={clsx('flex items-start gap-2.5', isUser ? 'flex-row-reverse' : 'flex-row')}
    >
      <div
        className={clsx(
          'w-7 h-7 rounded-full flex items-center justify-center shrink-0',
          isUser ? 'bg-blue-600 text-white' : 'liquid-glass text-blue-600 dark:text-blue-400'
        )}
      >
        {isUser ? <User className="w-3.5 h-3.5" /> : <Bot className="w-3.5 h-3.5" />}
      </div>

      <div
        className={clsx(
          'relative group max-w-[85%] px-4 py-2.5 text-sm/relaxed',
          isUser
            ? 'bg-blue-600 text-white rounded-[20px] rounded-tr-md shadow-[inset_0_1px_1px_rgba(255,255,255,0.4),0_8px_20px_-8px_rgba(37,99,235,0.6)]'
            : 'liquid-glass-bubble text-slate-800 dark:text-slate-100 rounded-[20px] rounded-tl-md'
        )}
      >
        <div className="whitespace-pre-wrap">{message.content}</div>

        {!isUser && (
          <button
            onClick={handleCopy}
            className="absolute -right-9 top-1.5 opacity-0 group-hover:opacity-100 transition-opacity p-1.5 rounded-full hover:bg-black/[0.06] dark:hover:bg-white/10 text-slate-500 hover:text-slate-800 dark:hover:text-slate-200 cursor-pointer"
            title="Copy text"
            aria-label="Copy text"
          >
            {copied ? <Check className="w-3.5 h-3.5 text-emerald-600" /> : <Copy className="w-3.5 h-3.5" />}
          </button>
        )}
      </div>
    </motion.div>
  );
}
