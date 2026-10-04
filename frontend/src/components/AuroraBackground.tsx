import { motion } from 'motion/react';

interface AuroraBackgroundProps {
  /** Full intensity is used for the empty "new chat" state, a quiet version while chatting. */
  intense: boolean;
}

/**
 * Animated blurred gradient background. It also gives the liquid glass
 * surfaces something colourful to refract.
 */
export function AuroraBackground({ intense }: AuroraBackgroundProps) {
  return (
    <div className="fixed inset-0 pointer-events-none overflow-hidden z-0" aria-hidden="true">
      <motion.div
        className="absolute inset-0"
        initial={false}
        animate={{ opacity: intense ? 1 : 0.4 }}
        transition={{ duration: 0.9, ease: 'easeInOut' }}
      >
        <div className="aurora-blob aurora-a -top-[10%] -left-[8%] w-[46vw] h-[46vw] bg-sky-500/55 dark:bg-sky-500/35" />
        <div className="aurora-blob aurora-b top-[8%] -right-[10%] w-[42vw] h-[42vw] bg-teal-400/50 dark:bg-teal-500/30" />
        <div className="aurora-blob aurora-c -bottom-[14%] left-[14%] w-[44vw] h-[44vw] bg-emerald-400/40 dark:bg-emerald-500/25" />
        <div className="aurora-blob aurora-d -bottom-[10%] -right-[6%] w-[36vw] h-[36vw] bg-orange-300/50 dark:bg-orange-400/20" />
      </motion.div>
    </div>
  );
}
