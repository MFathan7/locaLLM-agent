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
        animate={{ opacity: intense ? 1 : 0 }}
        transition={{ duration: 0.6, ease: 'easeInOut' }}
      >
        <div className="aurora-blob aurora-a -top-[6%] -left-[4%] w-[24vw] h-[24vw] bg-sky-500/25 dark:bg-sky-500/18" />
        <div className="aurora-blob aurora-b top-[6%] -right-[6%] w-[22vw] h-[22vw] bg-teal-400/20 dark:bg-teal-500/15" />
        <div className="aurora-blob aurora-c -bottom-[8%] left-[10%] w-[24vw] h-[24vw] bg-emerald-400/20 dark:bg-emerald-500/15" />
        <div className="aurora-blob aurora-d -bottom-[6%] -right-[4%] w-[20vw] h-[20vw] bg-orange-300/20 dark:bg-orange-400/12" />
      </motion.div>
    </div>
  );
}
