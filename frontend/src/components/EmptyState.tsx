import { useState } from 'react';
import { motion } from 'motion/react';
import {
  Code2,
  Sparkles,
  PenTool,
  Layers,
  Lightbulb,
  CheckSquare,
  Wrench,
  ArrowUpRight
} from 'lucide-react';

interface EmptyStateProps {
  workspace: string;
  userName?: string;
  onSelectPrompt?: (prompt: string) => void;
}

interface StarterCard {
  id: string;
  title: string;
  desc: string;
  prompt: string;
  icon: React.ComponentType<{ className?: string }>;
  colorClass: string;
}

const GREETING_TEMPLATES = [
  // Classic & modern web AI chat greetings (ChatGPT, Claude, Cursor style)
  () => "What can I help with today?",
  () => "What are we working on?",
  () => "Where should we begin?",
  () => "What's on your mind today?",
  () => "Ready when you are.",
  () => "What are we building today?",
  () => "How can I help you today?",
  () => "Got an idea? Let's bring it to life.",
  () => "What do you want to explore today?",
  
  // Fresh, sleek & dev-slank prompts
  () => "What's cookin' today?",
  () => "Talk to me. What are we hacking on?",
  () => "What's the play for today?",
  () => "Ready to build something wild?",
  () => "Hit me with your best prompt.",
  () => "Drop a question or spark an idea.",
  () => "Let's make some magic happen.",
  () => "What's on your radar today?",

  // Subtle contextual greetings (only if user name is known, otherwise clean fallback)
  (u: string) => (u ? `Good to see you, ${u}. What are we working on?` : "What are we working on?"),
  (u: string) => (u ? `How can I help you today, ${u}?` : "How can I help you today?"),
  (u: string) => (u ? `Ready when you are, ${u}.` : "Ready when you are."),
  (u: string) => (u ? `What's cookin', ${u}?` : "What's cookin' today?")
];

const STARTER_POOL: StarterCard[] = [
  {
    id: 'code-review',
    title: 'Code review & optimize',
    desc: 'Audit algorithms, hunt bottlenecks, and polish structure',
    prompt: 'Help me review and optimize this code snippet for performance and clean structure: ',
    icon: Code2,
    colorClass: 'text-blue-500 bg-blue-500/10 dark:bg-blue-500/15'
  },
  {
    id: 'deep-explain',
    title: 'Break down a tough concept',
    desc: 'Explain complex systems with clarity and precision',
    prompt: 'Break down how modern LLM attention mechanisms and quantization work like I am 15.',
    icon: Sparkles,
    colorClass: 'text-purple-500 bg-purple-500/10 dark:bg-purple-500/15'
  },
  {
    id: 'write-pitch',
    title: 'Draft a punchy pitch',
    desc: 'Craft snappy proposals, docs, or high-conversion copy',
    prompt: 'Draft a short, persuasive project pitch highlighting our core capabilities and value prop.',
    icon: PenTool,
    colorClass: 'text-emerald-500 bg-emerald-500/10 dark:bg-emerald-500/15'
  },
  {
    id: 'arch-design',
    title: 'Architect backend system',
    desc: 'Design resilient microservices, pipelines, or schemas',
    prompt: 'Design a resilient, asynchronous worker architecture for high-throughput webhook processing.',
    icon: Layers,
    colorClass: 'text-amber-500 bg-amber-500/10 dark:bg-amber-500/15'
  },
  {
    id: 'brainstorm',
    title: 'Brainstorm creative angles',
    desc: 'Generate bold hypotheses and fresh strategies',
    prompt: 'Give me 5 unconventional, high-impact strategies to diagnose elusive software bugs.',
    icon: Lightbulb,
    colorClass: 'text-cyan-500 bg-cyan-500/10 dark:bg-cyan-500/15'
  },
  {
    id: 'action-items',
    title: 'Extract key takeaways',
    desc: 'Transform raw notes into structured action items',
    prompt: 'Extract structured action items, deadlines, and key decisions from these notes: ',
    icon: CheckSquare,
    colorClass: 'text-rose-500 bg-rose-500/10 dark:bg-rose-500/15'
  },
  {
    id: 'explore-skills',
    title: 'Explore workspace tools',
    desc: 'Check available agent skills in this workspace',
    prompt: 'What specialized tools and skills are available in this workspace? Walk me through what we can do.',
    icon: Wrench,
    colorClass: 'text-indigo-500 bg-indigo-500/10 dark:bg-indigo-500/15'
  }
];

function pickThreeRandom(): StarterCard[] {
  const shuffled = [...STARTER_POOL].sort(() => Math.random() - 0.5);
  return shuffled.slice(0, 3);
}

export function EmptyState({ workspace, userName, onSelectPrompt }: EmptyStateProps) {
  const [greeting] = useState(() => {
    const fn = GREETING_TEMPLATES[Math.floor(Math.random() * GREETING_TEMPLATES.length)];
    return fn(userName?.trim() || '');
  });

  const [starters] = useState<StarterCard[]>(() => pickThreeRandom());

  return (
    <motion.div
      key={workspace}
      initial={{ opacity: 0, y: 14, scale: 0.97 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ type: 'spring', stiffness: 220, damping: 22 }}
      className="text-center px-4 mb-6 max-w-3xl mx-auto w-full"
    >
      <h1 className="text-3xl md:text-4xl font-semibold tracking-tight text-slate-900 dark:text-white">
        {greeting}
      </h1>
      <p className="mt-2 text-sm text-slate-700 dark:text-slate-300">
        New chat in <span className="font-semibold text-slate-900 dark:text-slate-100">{workspace}</span>
      </p>

      {/* 3 Quick Starter Suggestion Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mt-8 text-left">
        {starters.map((item, idx) => {
          const IconComp = item.icon;
          return (
            <motion.button
              key={item.id}
              type="button"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.05 * idx, duration: 0.25 }}
              onClick={() => onSelectPrompt?.(item.prompt)}
              className="group relative p-3.5 rounded-2xl liquid-glass border border-black/[0.08] dark:border-white/10 hover:border-blue-500/40 dark:hover:border-blue-500/40 shadow-xs hover:shadow-md transition-all cursor-pointer flex flex-col justify-between text-left active:scale-[0.98]"
            >
              <div>
                <div className="flex items-center justify-between gap-2 mb-2">
                  <div className={`w-7 h-7 rounded-xl flex items-center justify-center ${item.colorClass}`}>
                    <IconComp className="w-4 h-4" />
                  </div>
                  <ArrowUpRight className="w-3.5 h-3.5 text-slate-400 group-hover:text-blue-500 group-hover:translate-x-0.5 group-hover:-translate-y-0.5 transition-transform" />
                </div>
                <h3 className="text-[13px] font-semibold text-slate-800 dark:text-slate-100 group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors line-clamp-1">
                  {item.title}
                </h3>
                <p className="mt-1 text-[12px] leading-relaxed text-slate-600 dark:text-slate-400 line-clamp-2">
                  {item.desc}
                </p>
              </div>
            </motion.button>
          );
        })}
      </div>
    </motion.div>
  );
}
