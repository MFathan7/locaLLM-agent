import { useEffect, useRef, useState } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { Plus, Paperclip, Globe, Wrench } from 'lucide-react';
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

  return (
    <div ref={rootRef} className="relative shrink-0">
      <motion.button
        type="button"
        onClick={() => setOpen(o => !o)}
        whileTap={{ scale: 0.88 }}
        animate={{ rotate: open ? 45 : 0 }}
        transition={bounce}
        className="w-9 h-9 rounded-full flex items-center justify-center text-slate-600 dark:text-slate-300 bg-black/[0.06] dark:bg-white/10 hover:bg-black/10 dark:hover:bg-white/15 transition-colors cursor-pointer"
        aria-label="Add to message"
        aria-expanded={open}
      >
        <Plus className="w-4 h-4" />
      </motion.button>

      <AnimatePresence>
        {open && (
          <motion.div
            variants={menuVariants}
            initial="hidden"
            animate="show"
            exit="exit"
            style={{ transformOrigin: 'bottom left' }}
            className="absolute bottom-full left-0 mb-3 w-52 p-1.5 rounded-3xl liquid-glass-strong z-30"
            role="menu"
          >
            <MenuItem
              icon={<Paperclip className="w-4 h-4" />}
              label="Upload files"
              onClick={() => { onUploadClick(); setOpen(false); }}
            />

            {hasDynamic && (
              <motion.div variants={itemVariants} className="my-1 mx-2 h-px bg-black/10 dark:bg-white/10" />
            )}

            {capabilities.webSearch && (
              <MenuItem
                icon={<Globe className="w-4 h-4" />}
                label="Search web"
                active={webSearch}
                onClick={() => { onToggleWebSearch(); setOpen(false); }}
              />
            )}
            {capabilities.tools && (
              <MenuItem
                icon={<Wrench className="w-4 h-4" />}
                label="Tools"
                active={tools}
                onClick={() => { onToggleTools(); setOpen(false); }}
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
      whileHover={{ scale: 1.03 }}
      whileTap={{ scale: 0.95 }}
      onClick={onClick}
      role="menuitem"
      className={clsx(
        'w-full flex items-center gap-2.5 px-3 py-2 rounded-2xl text-[13px] font-medium text-left cursor-pointer transition-colors',
        active
          ? 'bg-blue-500/15 text-blue-700 dark:text-blue-300'
          : 'text-slate-700 dark:text-slate-200 hover:bg-black/[0.06] dark:hover:bg-white/10'
      )}
    >
      {icon}
      <span className="flex-1">{label}</span>
      {active && <span className="w-1.5 h-1.5 rounded-full bg-blue-500" />}
    </motion.button>
  );
}
