import { useEffect, useRef, useState } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { Plus, Paperclip, Globe, Wrench, Check } from 'lucide-react';
import clsx from 'clsx';
import type { ModelCapabilities } from '../types';

interface PlusMenuProps {
  capabilities: ModelCapabilities;
  webSearch: boolean;
  tools: boolean;
  onUploadClick: () => void;
  onToggleWebSearch: () => void;
  onToggleTools: () => void;
}

// Springs tuned to overshoot slightly, which gives the iOS "bounce" when the menu pops open.
const bounce = { type: 'spring', stiffness: 520, damping: 16, mass: 0.8 } as const;

const menuVariants = {
  hidden: { opacity: 0, scale: 0.35, y: 14 },
  show: {
    opacity: 1,
    scale: 1,
    y: 0,
    transition: { ...bounce, staggerChildren: 0.045, delayChildren: 0.03 }
  },
  exit: { opacity: 0, scale: 0.6, y: 8, transition: { duration: 0.14 } }
};

const itemVariants = {
  hidden: { opacity: 0, y: 12, scale: 0.9 },
  show: { opacity: 1, y: 0, scale: 1, transition: bounce }
};

export function PlusMenu({
  capabilities,
  webSearch,
  tools,
  onUploadClick,
  onToggleWebSearch,
  onToggleTools
}: PlusMenuProps) {
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);

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

  const hasDynamic = capabilities.webSearch || capabilities.tools;

  const selectedCount = (webSearch ? 1 : 0) + (tools ? 1 : 0);
  const activeLabels: string[] = [];
  if (webSearch) activeLabels.push('Web search');
  if (tools) activeLabels.push('Tools');
  const buttonTitle = activeLabels.length > 0
    ? `Add to message (${activeLabels.join(', ')})`
    : 'Add to message';

  return (
    <div ref={rootRef} className="relative shrink-0">
      <motion.button
        type="button"
        onClick={() => setOpen(o => !o)}
        whileTap={{ scale: 0.88 }}
        animate={{ rotate: open ? 45 : 0 }}
        transition={bounce}
        className={clsx(
          "w-8.5 h-8.5 rounded-full flex items-center justify-center transition-colors cursor-pointer relative",
          selectedCount > 0
            ? "text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-950/60 hover:bg-blue-100 dark:hover:bg-blue-900/60"
            : "text-slate-600 dark:text-slate-300 bg-transparent hover:bg-black/[0.05] dark:hover:bg-white/[0.08] hover:text-slate-900 dark:hover:text-white"
        )}
        aria-label={buttonTitle}
        title={buttonTitle}
        aria-expanded={open}
      >
        <Plus className="w-4 h-4" />
        {selectedCount > 0 && (
          <span
            className="absolute -top-1 -right-1 min-w-[17px] h-[17px] px-1 rounded-full bg-blue-600 dark:bg-blue-500 text-white text-[10px] font-bold flex items-center justify-center leading-none shadow-xs ring-2 ring-white dark:ring-[#121826] pointer-events-none select-none"
            aria-hidden="true"
          >
            {selectedCount}
          </span>
        )}
      </motion.button>

      <AnimatePresence>
        {open && (
          <motion.div
            variants={menuVariants}
            initial="hidden"
            animate="show"
            exit="exit"
            style={{ transformOrigin: 'bottom left' }}
            className="absolute bottom-full left-0 mb-3 w-52 p-1.5 rounded-2xl bg-white dark:bg-[#141b2a] border border-slate-200 dark:border-slate-800 shadow-2xl shadow-black/25 z-30"
            role="menu"
          >
            <MenuItem
              icon={<Paperclip className="w-4 h-4" />}
              label="Upload files"
              onClick={() => { onUploadClick(); setOpen(false); }}
            />

            {hasDynamic && (
              <motion.div variants={itemVariants} className="my-1 mx-2 h-px bg-slate-200 dark:bg-slate-800" />
            )}

            {capabilities.webSearch && (
              <MenuItem
                icon={<Globe className="w-4 h-4" />}
                label="Search web"
                active={webSearch}
                onClick={() => { onToggleWebSearch(); }}
              />
            )}
            {capabilities.tools && (
              <MenuItem
                icon={<Wrench className="w-4 h-4" />}
                label="Tools"
                active={tools}
                onClick={() => { onToggleTools(); }}
              />
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

function MenuItem({
  icon,
  label,
  onClick,
  active
}: {
  icon: React.ReactNode;
  label: string;
  onClick: () => void;
  active?: boolean;
}) {
  return (
    <motion.button
      type="button"
      variants={itemVariants}
      whileHover={{ scale: 1.02 }}
      whileTap={{ scale: 0.96 }}
      onClick={onClick}
      role="menuitem"
      className={clsx(
        'w-full flex items-center gap-2.5 px-3 py-2 rounded-xl text-[13px] font-medium text-left cursor-pointer transition-colors',
        active
          ? 'bg-blue-50 dark:bg-blue-950/50 text-blue-600 dark:text-blue-400 font-semibold'
          : 'text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800/70 hover:text-slate-900 dark:hover:text-white'
      )}
    >
      {icon}
      <span className="flex-1">{label}</span>
      {active && <Check className="w-3.5 h-3.5 shrink-0 text-blue-600 dark:text-blue-400" aria-hidden="true" />}
    </motion.button>
  );
}
