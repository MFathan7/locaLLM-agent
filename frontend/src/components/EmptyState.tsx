import { useState } from 'react';
import { motion } from 'motion/react';

interface EmptyStateProps {
  workspace: string;
  userName?: string;
  onSelectPrompt?: (prompt: string) => void;
}

function getGreetingContext() {
  const now = new Date();
  const dayName = new Intl.DateTimeFormat('en-US', { weekday: 'long' }).format(now);
  const hour = now.getHours();

  let timePeriod = 'morning';
  if (hour >= 12 && hour < 17) {
    timePeriod = 'afternoon';
  } else if (hour >= 17) {
    timePeriod = 'evening';
  }

  return { dayName, timePeriod };
}

function generateGreetings(rawUserName?: string): string[] {
  const { dayName, timePeriod } = getGreetingContext();
  const user = (rawUserName || '').trim();

  if (user) {
    return [
      `Can I help you this ${dayName} ${timePeriod}, ${user}?`,
      `Good ${dayName} ${timePeriod}, ${user}. What are we working on?`,
      `Good ${dayName} ${timePeriod}, ${user}. How can I assist you today?`,
      `What are we building this ${dayName} ${timePeriod}, ${user}?`,
      `Ready when you are, ${user}. What is on your mind today?`
    ];
  }

  return [
    `Can I help you this ${dayName} ${timePeriod}?`,
    `Good ${dayName} ${timePeriod}. What are we working on today?`,
    `How can I help you this ${dayName}?`,
    `Ready when you are. Where should we begin?`,
    `What are we building today?`
  ];
}

export function EmptyState({ workspace, userName }: EmptyStateProps) {
  const [greeting] = useState(() => {
    const list = generateGreetings(userName);
    return list[Math.floor(Math.random() * list.length)];
  });

  return (
    <motion.div
      key={workspace}
      initial={{ opacity: 0, y: 12, scale: 0.98 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ type: 'spring', stiffness: 420, damping: 22 }}
      className="text-center px-4 mb-8 max-w-2xl mx-auto w-full select-none"
    >
      <motion.h1
        initial={{ opacity: 0, y: 6 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
        className="text-2xl sm:text-3xl md:text-4xl font-semibold tracking-tight text-slate-900 dark:text-white"
      >
        {greeting}
      </motion.h1>

      <p className="mt-2.5 text-sm text-slate-500 dark:text-slate-400 font-normal">
        New session in workspace <span className="font-semibold text-slate-700 dark:text-slate-300">{workspace}</span>
      </p>
    </motion.div>
  );
}
