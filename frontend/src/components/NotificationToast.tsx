import { motion, AnimatePresence } from 'motion/react';
import { Bot, ArrowRight, X } from 'lucide-react';
import type { SessionNotification } from '../types';

interface NotificationToastProps {
  notification: SessionNotification | null;
  onOpenSession: (sessionId: string) => void;
  onDismiss: () => void;
}

export function NotificationToast({
  notification,
  onOpenSession,
  onDismiss
}: NotificationToastProps) {
  return (
    <AnimatePresence>
      {notification && (
        <motion.div
          key={notification.id}
          initial={{ opacity: 0, y: -20, scale: 0.95 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: -16, scale: 0.95 }}
          transition={{ type: 'spring', stiffness: 450, damping: 25 }}
          className="fixed top-4 right-4 sm:top-5 sm:right-6 z-50 pointer-events-auto max-w-sm w-full"
        >
          <div className="flex items-center gap-3 p-3.5 rounded-2xl liquid-glass-strong border border-white/40 dark:border-white/10 shadow-2xl backdrop-blur-xl text-slate-800 dark:text-slate-100">
            <div className="w-8 h-8 rounded-xl bg-blue-600/15 dark:bg-blue-400/20 text-blue-600 dark:text-blue-400 flex items-center justify-center shrink-0">
              <Bot className="w-4 h-4" />
            </div>

            <div className="min-w-0 flex-1">
              <div className="text-[11px] font-semibold tracking-wider uppercase text-blue-600 dark:text-blue-400">
                Response Ready
              </div>
              <div className="text-[13px] font-medium text-slate-800 dark:text-slate-100 truncate">
                {notification.sessionTitle}
              </div>
            </div>

            <div className="flex items-center gap-1.5 shrink-0">
              <button
                type="button"
                onClick={() => onOpenSession(notification.sessionId)}
                className="inline-flex items-center gap-1 px-2.5 py-1 rounded-xl text-xs font-semibold bg-blue-600 hover:bg-blue-700 text-white shadow-xs cursor-pointer active:scale-95 transition-all"
              >
                <span>Open</span>
                <ArrowRight className="w-3 h-3" />
              </button>

              <button
                type="button"
                onClick={onDismiss}
                className="p-1 rounded-lg text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 hover:bg-black/5 dark:hover:bg-white/10 transition-colors cursor-pointer"
                aria-label="Dismiss notification"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
