import { motion } from 'motion/react';

export function EmptyState({ workspace }: { workspace: string }) {
  return (
    <motion.div
      key={workspace}
      initial={{ opacity: 0, y: 14, scale: 0.97 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ type: 'spring', stiffness: 220, damping: 22 }}
      className="text-center px-4 mb-6"
    >
      <h1 className="text-3xl md:text-4xl font-semibold tracking-tight text-slate-900 dark:text-white">
        What are we working on?
      </h1>
      <p className="mt-2 text-sm text-slate-700 dark:text-slate-300">
        New chat in <span className="font-medium">{workspace}</span>
      </p>
    </motion.div>
  );
}
