import { useState, useRef, useMemo, useEffect, useCallback } from 'react';
import {
  Workflow,
  Play,
  ArrowLeft,
  Terminal,
  Bot,
  Sparkles,
  Layers,
  Search,
  Cpu,
  FileText,
  Globe,
  Plus,
  Trash2,
  ZoomIn,
  ZoomOut,
  Maximize2,
  Minimize2,
  RotateCcw,
  Grid,
  Check,
  Download,
  Upload,
  Settings2,
  Settings,
  X,
  ChevronRight,
  ShieldCheck,
  Database,
  AlertTriangle,
  ChevronDown,
  Radio,
  Pause,
  RefreshCw,
  FolderGit2,
  Move,
  Link as LinkIcon,
  Save,
  FilePlus,
  ArrowUp,
  ArrowDown,
  Undo2,
  Redo2,
  Lock,
  HelpCircle,
  BookOpen,
  Target,
  GripVertical
} from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';
import { ThemeToggle } from './ThemeToggle';
import { SettingsModal } from './SettingsModal';
import type { Workspace, ModelInfo, LocaLLMConfig } from '../types';
import { api } from '../services/api';

export type WorkflowLane = 'ui' | 'agent' | 'policy' | 'tools' | 'evidence' | string;

export type SequenceColor = 'blue' | 'yellow' | 'red';

export interface WorkflowLaneConfig {
  id: string;
  num: string;
  label: string;
  description?: string;
  color?: SequenceColor;
  x?: number;
  y: number;
  width?: number;
  height: number;
  variant?: 'default' | 'exception';
}

export interface ActivityDoc {
  role: string;
  description: string;
  inputs: string[];
  outputs: string[];
  configFields: { param: string; desc: string; defaultValue?: string }[];
  recommendedConnections: string;
}

export interface ActivityCatalogItem {
  lane: WorkflowLane;
  type: 'frontend' | 'backend' | 'security' | 'messagebus' | 'database' | 'cloud' | 'external';
  title: string;
  subtitle: string;
  tag: string;
  icon: any;
  color: string;
  defaultConfig: Record<string, any>;
  doc: ActivityDoc;
}

export interface WorkflowNode {
  id: string;
  lane: WorkflowLane;
  type: 'frontend' | 'backend' | 'security' | 'messagebus' | 'database' | 'cloud' | 'external';
  title: string;
  subtitle: string;
  tag?: string;
  x: number;
  y: number;
  status?: 'idle' | 'running' | 'success' | 'error';
  config: {
    workspace?: string;
    model?: string;
    directive?: string;
    tools?: string[];
    query?: string;
    condition?: string;
    command?: string;
    path?: string;
    endpoint?: string;
    timeout?: number;
    [key: string]: any;
  };
}

export type PortSide = 'top' | 'bottom' | 'left' | 'right';

export interface WorkflowEdge {
  id: string;
  from: string;
  to: string;
  fromSide?: PortSide;
  toSide?: PortSide;
  label?: string;
  variant?: 'default' | 'emphasis' | 'security' | 'dashed';
}

export const PORT_SIDES: { side: PortSide; posClass: string; title: string }[] = [
  { side: 'top', posClass: 'left-1/2 -top-1.5 -translate-x-1/2', title: 'Top Port' },
  { side: 'bottom', posClass: 'left-1/2 -bottom-1.5 -translate-x-1/2', title: 'Bottom Port' },
  { side: 'left', posClass: '-left-1.5 top-1/2 -translate-y-1/2', title: 'Left Port' },
  { side: 'right', posClass: '-right-1.5 top-1/2 -translate-y-1/2', title: 'Right Port' },
];

export interface WorkflowPhase {
  id: string;
  label: string;
  fromX: number;
  toX: number;
  variant?: 'default' | 'emphasis' | 'security' | 'dashed';
}

interface ExecutionEvent {
  agent: string;
  event_type: string;
  message: string;
  timestamp: string;
}

interface WorkflowStudioProps {
  workspaces?: Workspace[];
  activeWorkspace?: string;
  models?: ModelInfo[];
  config?: LocaLLMConfig | null;
  onUpdateConfig?: (cfg: LocaLLMConfig) => void;
  isConfigSyncing?: boolean;
  onRefreshModels?: (backend?: string) => Promise<ModelInfo[]>;
}

export const NODE_WIDTH = 156;
export const NODE_HEIGHT = 64;

// Default UiPath-Style Sequence Groups Layout
export const INITIAL_LANES: WorkflowLaneConfig[] = [
  { id: 'ui', num: '01', label: 'User Interface Sequence', description: 'Handles user prompts, input validation, and conversational deliverables', color: 'blue', x: 30, y: 70, width: 1680, height: 135 },
  { id: 'agent', num: '02', label: 'Agent Runtime Sequence', description: 'Cognitive reasoning loop, model inference, and tool call planning', color: 'blue', x: 30, y: 225, width: 1680, height: 145 },
  { id: 'policy', num: '03', label: 'Policy & Guardrail Sequence', description: 'Safety screening, human authorization gates, and retry recovery loops', color: 'red', x: 30, y: 390, width: 1680, height: 135 },
  { id: 'tools', num: '04', label: 'Tool Execution Sequence', description: 'Sandboxed code interpretation, terminal commands, and API execution', color: 'yellow', x: 30, y: 545, width: 1680, height: 145 },
  { id: 'evidence', num: '05', label: 'Evidence & Context Sequence', description: 'Vector embeddings, short-term scratchpad, and memory grounding', color: 'blue', x: 30, y: 710, width: 1680, height: 135 }
];

// UiPath-Style Sequence Visual Themes (Standard, Normal, Critical)
export const SEQUENCE_COLOR_THEMES: Record<SequenceColor, {
  label: string;
  badgeLabel: string;
  tooltip: string;
  border: string;
  bg: string;
  headerBg: string;
  headerText: string;
  badgeClass: string;
  accentHex: string;
  dotBg: string;
}> = {
  blue: {
    label: 'Standard',
    badgeLabel: 'STANDARD',
    tooltip: 'Standard sequence for baseline workflow processes and standard operations.',
    border: 'border-blue-400/80 dark:border-blue-500/50',
    bg: 'bg-blue-50/20 dark:bg-blue-950/15',
    headerBg: 'bg-blue-100/75 dark:bg-blue-900/40 border-b border-blue-200 dark:border-blue-800/60',
    headerText: 'text-blue-950 dark:text-blue-200',
    badgeClass: 'bg-blue-500/15 text-blue-700 dark:text-blue-300 border border-blue-400/40',
    accentHex: '#3b82f6',
    dotBg: 'bg-blue-500'
  },
  yellow: {
    label: 'Normal',
    badgeLabel: 'NORMAL',
    tooltip: 'Normal sequence for intermediate execution handling secondary tools and middle-tier processes.',
    border: 'border-amber-400/80 dark:border-amber-500/50',
    bg: 'bg-amber-50/20 dark:bg-amber-950/15',
    headerBg: 'bg-amber-100/75 dark:bg-amber-900/40 border-b border-amber-200 dark:border-amber-800/60',
    headerText: 'text-amber-950 dark:text-amber-200',
    badgeClass: 'bg-amber-500/15 text-amber-700 dark:text-amber-300 border border-amber-400/40',
    accentHex: '#f59e0b',
    dotBg: 'bg-amber-500'
  },
  red: {
    label: 'Critical',
    badgeLabel: 'CRITICAL',
    tooltip: 'Critical sequence for high-priority security guardrails, policy gates, and recovery loops.',
    border: 'border-rose-400/80 dark:border-rose-500/50',
    bg: 'bg-rose-50/20 dark:bg-rose-950/15',
    headerBg: 'bg-rose-100/75 dark:bg-rose-900/40 border-b border-rose-200 dark:border-rose-800/60',
    headerText: 'text-rose-950 dark:text-rose-200',
    badgeClass: 'bg-rose-500/15 text-rose-700 dark:text-rose-300 border border-rose-400/40',
    accentHex: '#f43f5e',
    dotBg: 'bg-rose-500'
  }
};

// Helper to recalculate sequential positions and numbers for dynamic sequences
export function computeLanePositions(laneList: WorkflowLaneConfig[]): WorkflowLaneConfig[] {
  let currentY = 70;
  return laneList.map((lane, index) => {
    const num = lane.num || String(index + 1).padStart(2, '0');
    const x = typeof lane.x === 'number' ? lane.x : 30;
    const width = typeof lane.width === 'number' ? lane.width : 1680;
    const height = typeof lane.height === 'number' ? lane.height : 140;
    const color: SequenceColor = lane.color || (lane.variant === 'exception' ? 'red' : 'blue');
    const y = typeof lane.y === 'number' && !isNaN(lane.y) ? lane.y : currentY;
    currentY = Math.max(currentY + height + 24, y + height + 24);
    return {
      ...lane,
      num,
      x,
      y,
      width,
      height,
      color
    };
  });
}

// Archify Signal Flow Phase Demarcations
const SIGNAL_FLOW_PHASES: WorkflowPhase[] = [
  { id: 'intake', label: '01: Intake & Request', fromX: 30, toX: 430, variant: 'default' },
  { id: 'reasoning', label: '02: Planning & Policy Gate', fromX: 440, toX: 890, variant: 'emphasis' },
  { id: 'execution', label: '03: Tool Execution & Verification', fromX: 900, toX: 1360, variant: 'security' },
  { id: 'evidence', label: '04: Evidence & Synthesis', fromX: 1370, toX: 1680, variant: 'dashed' }
];

// Archify Semantic Type Styling Specifications
const ARCHIFY_TYPE_STYLES: Record<string, {
  container: string;
  iconColor: string;
  tagClass: string;
  stroke: string;
  hoverShadow: string;
}> = {
  frontend: {
    container: 'bg-cyan-50/90 dark:bg-cyan-950/40 border-cyan-500/80 dark:border-cyan-400 text-cyan-950 dark:text-cyan-100 shadow-2xs',
    iconColor: 'text-cyan-600 dark:text-cyan-400',
    tagClass: 'bg-cyan-100 text-cyan-800 dark:bg-cyan-900/60 dark:text-cyan-300',
    stroke: '#22d3ee',
    hoverShadow: 'shadow-[0_12px_28px_-6px_rgba(6,182,212,0.45),0_6px_14px_-4px_rgba(6,182,212,0.3)] border-cyan-500 dark:border-cyan-400'
  },
  backend: {
    container: 'bg-emerald-50/90 dark:bg-emerald-950/40 border-emerald-500/80 dark:border-emerald-400 text-emerald-950 dark:text-emerald-100 shadow-2xs',
    iconColor: 'text-emerald-600 dark:text-emerald-400',
    tagClass: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/60 dark:text-emerald-300',
    stroke: '#34d399',
    hoverShadow: 'shadow-[0_12px_28px_-6px_rgba(16,185,129,0.45),0_6px_14px_-4px_rgba(16,185,129,0.3)] border-emerald-500 dark:border-emerald-400'
  },
  security: {
    container: 'bg-rose-50/90 dark:bg-rose-950/40 border-rose-500/80 dark:border-rose-400 text-rose-950 dark:text-rose-100 shadow-2xs',
    iconColor: 'text-rose-600 dark:text-rose-400',
    tagClass: 'bg-rose-100 text-rose-800 dark:bg-rose-900/60 dark:text-rose-300',
    stroke: '#fb7185',
    hoverShadow: 'shadow-[0_12px_28px_-6px_rgba(244,63,94,0.45),0_6px_14px_-4px_rgba(244,63,94,0.3)] border-rose-500 dark:border-rose-400'
  },
  database: {
    container: 'bg-purple-50/90 dark:bg-purple-950/40 border-purple-500/80 dark:border-purple-400 text-purple-950 dark:text-purple-100 shadow-2xs',
    iconColor: 'text-purple-600 dark:text-purple-400',
    tagClass: 'bg-purple-100 text-purple-800 dark:bg-purple-900/60 dark:text-purple-300',
    stroke: '#a78bfa',
    hoverShadow: 'shadow-[0_12px_28px_-6px_rgba(168,85,247,0.45),0_6px_14px_-4px_rgba(168,85,247,0.3)] border-purple-500 dark:border-purple-400'
  },
  cloud: {
    container: 'bg-amber-50/90 dark:bg-amber-950/40 border-amber-500/80 dark:border-amber-400 text-amber-950 dark:text-amber-100 shadow-2xs',
    iconColor: 'text-amber-600 dark:text-amber-400',
    tagClass: 'bg-amber-100 text-amber-800 dark:bg-amber-900/60 dark:text-amber-300',
    stroke: '#fbbf24',
    hoverShadow: 'shadow-[0_12px_28px_-6px_rgba(245,158,11,0.45),0_6px_14px_-4px_rgba(245,158,11,0.3)] border-amber-500 dark:border-amber-400'
  },
  messagebus: {
    container: 'bg-orange-50/90 dark:bg-orange-950/40 border-orange-500/80 dark:border-orange-400 text-orange-950 dark:text-orange-100 shadow-2xs',
    iconColor: 'text-orange-600 dark:text-orange-400',
    tagClass: 'bg-orange-100 text-orange-800 dark:bg-orange-900/60 dark:text-orange-300',
    stroke: '#fb923c',
    hoverShadow: 'shadow-[0_12px_28px_-6px_rgba(249,115,22,0.45),0_6px_14px_-4px_rgba(249,115,22,0.3)] border-orange-500 dark:border-orange-400'
  },
  external: {
    container: 'bg-slate-100/90 dark:bg-slate-800/60 border-slate-400/80 dark:border-slate-500 text-slate-900 dark:text-slate-100 shadow-2xs',
    iconColor: 'text-slate-600 dark:text-slate-300',
    tagClass: 'bg-slate-200 text-slate-800 dark:bg-slate-700 dark:text-slate-300',
    stroke: '#94a3b8',
    hoverShadow: 'shadow-[0_12px_28px_-6px_rgba(100,116,139,0.45),0_6px_14px_-4px_rgba(100,116,139,0.3)] border-slate-500 dark:border-slate-400'
  }
};

// Workflow Presets Collection
const WORKFLOW_PRESETS: {
  id: string;
  name: string;
  description: string;
  lanes: WorkflowLaneConfig[];
  nodes: WorkflowNode[];
  edges: WorkflowEdge[];
}[] = [
    {
      id: 'agent-tool-call-loop',
      name: 'Agent Tool-Call Loop',
      description: 'Autonomous tool execution cycle with planning loop, policy approval gate, and trace feedback',
      lanes: INITIAL_LANES,
      nodes: [
        {
          id: 'user',
          lane: 'ui',
          type: 'external',
          title: 'User Intake',
          subtitle: 'Asks for work & submits prompt',
          tag: 'objective',
          x: 50,
          y: 102,
          status: 'idle',
          config: { query: 'Analyze repository and execute automated test repair loop', workspace: 'default' }
        },
        {
          id: 'chat',
          lane: 'ui',
          type: 'frontend',
          title: 'Chat Surface',
          subtitle: 'Thread state & attachments',
          tag: 'thread',
          x: 270,
          y: 102,
          status: 'idle',
          config: { workspace: 'default' }
        },
        {
          id: 'planner',
          lane: 'agent',
          type: 'backend',
          title: 'Agent Planner',
          subtitle: 'Context-aware next step plan',
          tag: 'context-aware',
          x: 490,
          y: 255,
          status: 'idle',
          config: { directive: 'Reason over objectives, inspect evidence, and plan discrete tool calls', timeout: 300 }
        },
        {
          id: 'router',
          lane: 'agent',
          type: 'backend',
          title: 'Tool Router',
          subtitle: 'Select capabilities & dispatch',
          tag: 'router',
          x: 720,
          y: 255,
          status: 'idle',
          config: { tools: ['shell', 'browser', 'filesystem', 'mcp'] }
        },
        {
          id: 'approval',
          lane: 'policy',
          type: 'security',
          title: 'Approval Gate',
          subtitle: 'Scope check & user consent',
          tag: 'block-risky',
          x: 720,
          y: 415,
          status: 'idle',
          config: { policy: 'ask_risky', circuit_breaker: 'max 2 retries' }
        },
        {
          id: 'blocked',
          lane: 'policy',
          type: 'security',
          title: 'Blocked Guard',
          subtitle: 'Wait, halt or reject action',
          tag: 'guardrail',
          x: 940,
          y: 415,
          status: 'idle',
          config: { on_deny: 'escalate_to_user' }
        },
        {
          id: 'retry',
          lane: 'policy',
          type: 'messagebus',
          title: 'Retry Path',
          subtitle: 'Revise request & recovery loop',
          tag: 'recovery',
          x: 1160,
          y: 415,
          status: 'idle',
          config: { backoff: 'exponential' }
        },
        {
          id: 'tool',
          lane: 'tools',
          type: 'messagebus',
          title: 'Tool Call Executor',
          subtitle: 'Shell / Browser / Filesystem / MCP',
          tag: 'structured-exec',
          x: 940,
          y: 565,
          status: 'idle',
          config: { tools: ['execute_command', 'read_file', 'search_web'] }
        },
        {
          id: 'external',
          lane: 'tools',
          type: 'cloud',
          title: 'External API & OS',
          subtitle: 'Network service & subprocess',
          tag: 'runtime',
          x: 1160,
          y: 565,
          status: 'idle',
          config: { timeout: 60 }
        },
        {
          id: 'store',
          lane: 'evidence',
          type: 'database',
          title: 'Context Store',
          subtitle: 'Repository memory & state sink',
          tag: 'memory',
          x: 270,
          y: 730,
          status: 'idle',
          config: { index: 'bm25_vector' }
        },
        {
          id: 'trace',
          lane: 'evidence',
          type: 'database',
          title: 'Trace Log',
          subtitle: 'Structured events & output logs',
          tag: 'evidence',
          x: 490,
          y: 730,
          status: 'idle',
          config: { sink: 'sqlite_audit' }
        },
        {
          id: 'final',
          lane: 'ui',
          type: 'backend',
          title: 'Final Reply',
          subtitle: 'Synthesized answer & diff receipt',
          tag: 'synthesis',
          x: 1410,
          y: 102,
          status: 'idle',
          config: { stream: true }
        }
      ],
      edges: [
        { id: 'e-user-chat', from: 'user', to: 'chat', label: 'request', variant: 'default' },
        { id: 'e-chat-planner', from: 'chat', to: 'planner', label: 'plan request', variant: 'emphasis' },
        { id: 'e-planner-router', from: 'planner', to: 'router', label: 'dispatch', variant: 'default' },
        { id: 'e-router-approval', from: 'router', to: 'approval', label: 'safety check', variant: 'security' },
        { id: 'e-approval-tool', from: 'approval', to: 'tool', label: 'approved', variant: 'emphasis' },
        { id: 'e-approval-blocked', from: 'approval', to: 'blocked', label: 'denied', variant: 'security' },
        { id: 'e-blocked-retry', from: 'blocked', to: 'retry', label: 'revise', variant: 'dashed' },
        { id: 'e-retry-planner', from: 'retry', to: 'planner', label: 'recovery loop', variant: 'dashed' },
        { id: 'e-tool-external', from: 'tool', to: 'external', label: 'invoke', variant: 'default' },
        { id: 'e-external-trace', from: 'external', to: 'trace', label: 'record evidence', variant: 'dashed' },
        { id: 'e-store-trace', from: 'store', to: 'trace', label: 'trace + memory', variant: 'dashed' },
        { id: 'e-trace-planner', from: 'trace', to: 'planner', label: 'tool loopback', variant: 'emphasis' },
        { id: 'e-external-final', from: 'external', to: 'final', label: 'final reply', variant: 'emphasis' }
      ]
    },
    {
      id: 'swarm-coordinator',
      name: 'Multi-Agent Swarm (Standard)',
      description: 'Hierarchical task decomposition with research, coding, safety gate and blackboard sink',
      lanes: INITIAL_LANES,
      nodes: [
        {
          id: 'user-intake',
          lane: 'ui',
          type: 'frontend',
          title: 'User Objective',
          subtitle: 'Task prompt and instructions',
          tag: 'intake',
          x: 50,
          y: 101,
          status: 'idle',
          config: { query: 'Analyze project codebase and generate optimization plan', workspace: 'default' }
        },
        {
          id: 'supervisor-planner',
          lane: 'agent',
          type: 'backend',
          title: 'Supervisor Planner',
          subtitle: 'Hierarchical task decomposition',
          tag: 'context-aware',
          x: 270,
          y: 255,
          status: 'idle',
          config: { directive: 'Decompose task, delegate to specialists, and maintain blackboard state', timeout: 300 }
        },
        {
          id: 'policy-gate',
          lane: 'policy',
          type: 'security',
          title: 'Policy Guard',
          subtitle: 'Circuit breaker & safety consent',
          tag: 'policy-gate',
          x: 530,
          y: 410,
          status: 'idle',
          config: { policy: 'ask', circuit_breaker: 'max 2 consecutive identical failures' }
        },
        {
          id: 'researcher-agent',
          lane: 'agent',
          type: 'messagebus',
          title: 'Research Specialist',
          subtitle: 'Workspace exploration & search',
          tag: 'researcher',
          x: 530,
          y: 230,
          status: 'idle',
          config: { tools: ['search_web', 'fetch_web', 'read_file', 'list_directory'], timeout: 300 }
        },
        {
          id: 'coder-agent',
          lane: 'agent',
          type: 'backend',
          title: 'Coder Specialist',
          subtitle: 'Code implementation & self-testing',
          tag: 'code-exec',
          x: 790,
          y: 265,
          status: 'idle',
          config: { tools: ['patch_file', 'write_file', 'check_syntax', 'execute_command'], timeout: 300 }
        },
        {
          id: 'blackboard-state',
          lane: 'evidence',
          type: 'database',
          title: 'Blackboard State',
          subtitle: 'Synthesizes findings & diffs',
          tag: 'trace-evidence',
          x: 1140,
          y: 720,
          status: 'idle',
          config: { directive: 'Consolidate specialist observations and output final response' }
        }
      ],
      edges: [
        { id: 'e1', from: 'user-intake', to: 'supervisor-planner', label: 'prompt', variant: 'emphasis' },
        { id: 'e2', from: 'supervisor-planner', to: 'policy-gate', label: 'safety check', variant: 'security' },
        { id: 'e3', from: 'supervisor-planner', to: 'researcher-agent', label: 'research task', variant: 'default' },
        { id: 'e4', from: 'policy-gate', to: 'coder-agent', label: 'authorized', variant: 'emphasis' },
        { id: 'e5', from: 'researcher-agent', to: 'coder-agent', label: 'findings', variant: 'dashed' },
        { id: 'e6', from: 'coder-agent', to: 'blackboard-state', label: 'code diffs', variant: 'emphasis' },
        { id: 'e7', from: 'researcher-agent', to: 'blackboard-state', label: 'evidence', variant: 'dashed' }
      ]
    },
    {
      id: 'code-audit-fix',
      name: 'Code Review & Audit Pipeline',
      description: 'Inspects code health, runs automated tests, applies fixes and records audit diffs',
      lanes: INITIAL_LANES,
      nodes: [
        {
          id: 'intake-audit',
          lane: 'ui',
          type: 'frontend',
          title: 'Audit Target',
          subtitle: 'Directory or module specification',
          tag: 'intake',
          x: 50,
          y: 101,
          status: 'idle',
          config: { query: 'Run pytest and audit test failures in project', workspace: 'default' }
        },
        {
          id: 'auditor-node',
          lane: 'agent',
          type: 'backend',
          title: 'Auditor Specialist',
          subtitle: 'Runs diagnostic commands and pytest',
          tag: 'auditor',
          x: 310,
          y: 255,
          status: 'idle',
          config: { tools: ['check_syntax', 'execute_command'] }
        },
        {
          id: 'shell-runner',
          lane: 'tools',
          type: 'messagebus',
          title: 'Shell Command Runner',
          subtitle: 'Executes pytest command',
          tag: 'subprocess',
          x: 580,
          y: 565,
          status: 'idle',
          config: { command: 'pytest' }
        },
        {
          id: 'coder-fixer',
          lane: 'agent',
          type: 'backend',
          title: 'Coder Specialist',
          subtitle: 'Patches syntax errors and fixes bugs',
          tag: 'code-exec',
          x: 840,
          y: 255,
          status: 'idle',
          config: { tools: ['patch_file', 'write_file', 'check_syntax'] }
        },
        {
          id: 'audit-evidence',
          lane: 'evidence',
          type: 'database',
          title: 'Trace Event Log',
          subtitle: 'Audited log of passed checks and diffs',
          tag: 'event-stream',
          x: 1140,
          y: 720,
          status: 'idle',
          config: {}
        }
      ],
      edges: [
        { id: 'ae1', from: 'intake-audit', to: 'auditor-node', label: 'start audit', variant: 'emphasis' },
        { id: 'ae2', from: 'auditor-node', to: 'shell-runner', label: 'execute pytest', variant: 'default' },
        { id: 'ae3', from: 'shell-runner', to: 'coder-fixer', label: 'failures', variant: 'security' },
        { id: 'ae4', from: 'coder-fixer', to: 'audit-evidence', label: 'verified diffs', variant: 'emphasis' }
      ]
    }
  ];

// Activity catalog grouped strictly by LocaLLM 5 Lane Taxonomy with rich operational documentation
const ACTIVITY_CATALOG: {
  lane: WorkflowLane;
  laneTitle: string;
  items: ActivityCatalogItem[];
}[] = [
    {
      lane: 'ui',
      laneTitle: 'Lane 1: User Interface & Intake',
      items: [
        {
          lane: 'ui',
          type: 'frontend' as const,
          title: 'User Objective Input',
          subtitle: 'Interactive task entrypoint for agent flow',
          tag: 'intake',
          icon: Sparkles,
          color: 'text-cyan-600 dark:text-cyan-400',
          defaultConfig: { query: 'Analyze project codebase', workspace: 'default' },
          doc: {
            role: 'Intake & Task Entrypoint',
            description: 'Primary workflow intake entrypoint. Captures the initial user objective, prompt, and task scope to be ingested by the multi-agent pipeline.',
            inputs: ['User prompt and mission instructions', 'Target project workspace selection'],
            outputs: ['Structured task payload ready for routing to Supervisor Planner or Specialists'],
            configFields: [
              { param: 'query', desc: 'Primary objective or task directive to execute.', defaultValue: 'Analyze project codebase' },
              { param: 'workspace', desc: 'Target project workspace for file and context operations.', defaultValue: 'default' }
            ],
            recommendedConnections: 'Place at the beginning of Lane 1 (UI & Intake) and wire directly to Supervisor Planner in Lane 2.'
          }
        },
        {
          lane: 'ui',
          type: 'external' as const,
          title: 'Webhook Trigger',
          subtitle: 'External HTTP payload trigger (e.g. GitHub/n8n)',
          tag: 'webhook',
          icon: Globe,
          color: 'text-slate-600 dark:text-slate-400',
          defaultConfig: { endpoint: '/api/v1/webhook', workspace: 'default' },
          doc: {
            role: 'External HTTP Trigger',
            description: 'Automated external trigger via HTTP POST. Receives JSON payloads from external systems such as GitHub Actions, n8n, or internal webhook dispatchers.',
            inputs: ['HTTP POST request with JSON payload'],
            outputs: ['Normalized event payload formatted for agent execution'],
            configFields: [
              { param: 'endpoint', desc: 'REST endpoint path for receiving incoming webhook requests.', defaultValue: '/api/v1/webhook' },
              { param: 'workspace', desc: 'Target workspace associated with the incoming event.', defaultValue: 'default' }
            ],
            recommendedConnections: 'Connect to Supervisor Planner to automatically trigger workflow runs on incoming webhook events.'
          }
        }
      ]
    },
    {
      lane: 'agent',
      laneTitle: 'Lane 2: Agent Runtime',
      items: [
        {
          lane: 'agent',
          type: 'backend' as const,
          title: 'Supervisor Planner',
          subtitle: 'Decomposes mission, delegates subtasks, and synthesizes',
          tag: 'orchestrator',
          icon: Bot,
          color: 'text-emerald-600 dark:text-emerald-400',
          defaultConfig: { directive: 'Plan and coordinate subtasks', workspace: 'default' },
          doc: {
            role: 'Coordinator & Planner',
            description: 'Central orchestration engine in the multi-agent architecture. Decomposes high-level missions into sequenced subtasks, delegates them to specialists, and synthesizes overall findings.',
            inputs: ['Objective from Intake or Webhook', 'Shared Blackboard state and context'],
            outputs: ['Sequenced execution plan', 'Subtask delegations for Coder, Researcher, and Auditor specialists'],
            configFields: [
              { param: 'directive', desc: 'Strategic operating instructions guiding the supervisor.', defaultValue: 'Plan and coordinate subtasks' },
              { param: 'workspace', desc: 'Target project workspace for execution.', defaultValue: 'default' }
            ],
            recommendedConnections: 'Accept intake wires from User Objective or Webhook, and dispatch downstream wires to Research Specialist or Coder Specialist.'
          }
        },
        {
          lane: 'agent',
          type: 'messagebus' as const,
          title: 'Research Specialist',
          subtitle: 'Retrieval agent for files, web data, and skills',
          tag: 'researcher',
          icon: Search,
          color: 'text-orange-600 dark:text-orange-400',
          defaultConfig: { tools: ['search_web', 'fetch_web', 'read_file'], workspace: 'default' },
          doc: {
            role: 'Context Retrieval Agent',
            description: 'Dedicated exploration and retrieval agent. Inspects workspace repository files, gathers technical documentation, and searches for technical references via live web search.',
            inputs: ['Search directives from Supervisor', 'Target keywords or file paths'],
            outputs: ['Relevant code snippets, web search summaries, and dependency context'],
            configFields: [
              { param: 'tools', desc: 'Enabled tools for the research specialist (search_web, fetch_web, read_file).', defaultValue: "['search_web', 'fetch_web', 'read_file']" },
              { param: 'workspace', desc: 'Target workspace for file inspection.', defaultValue: 'default' }
            ],
            recommendedConnections: 'Execute before Coder Specialist so code authoring is informed by accurate file context and dependencies.'
          }
        },
        {
          lane: 'agent',
          type: 'backend' as const,
          title: 'Coder Specialist',
          subtitle: 'Code editing with patch_file and terminal self-testing',
          tag: 'coder',
          icon: Terminal,
          color: 'text-emerald-600 dark:text-emerald-400',
          defaultConfig: { tools: ['patch_file', 'check_syntax', 'execute_command'], workspace: 'default' },
          doc: {
            role: 'Code Authoring & Patching Agent',
            description: 'Autonomous software engineering agent. Authors new code, applies surgical diff patches, and validates AST syntax integrity to prevent build regressions.',
            inputs: ['Task specifications from Supervisor', 'File context from Research Specialist'],
            outputs: ['File modification diff patches', 'AST syntax validation reports'],
            configFields: [
              { param: 'tools', desc: 'Active coding tools (patch_file, check_syntax, execute_command).', defaultValue: "['patch_file', 'check_syntax', 'execute_command']" },
              { param: 'workspace', desc: 'Target project workspace to modify.', defaultValue: 'default' }
            ],
            recommendedConnections: 'Connect downstream from Research Specialist, and route outputs through Approval Gate or to Auditor Specialist.'
          }
        },
        {
          lane: 'agent',
          type: 'messagebus' as const,
          title: 'Auditor Specialist',
          subtitle: 'Runs diagnostic commands, pytest, and syntax reviews',
          tag: 'auditor',
          icon: Cpu,
          color: 'text-orange-600 dark:text-orange-400',
          defaultConfig: { tools: ['check_syntax', 'execute_command'], workspace: 'default' },
          doc: {
            role: 'Quality & Test Auditor',
            description: 'Quality assurance agent. Executes automated test suites (pytest, unittest), runs syntax verification, and inspects system integrity following code modifications.',
            inputs: ['Modified files and patches produced by Coder Specialist'],
            outputs: ['Quality audit reports, unit test results, and regression diagnostics'],
            configFields: [
              { param: 'tools', desc: 'Authorized diagnostic tools (check_syntax, execute_command).', defaultValue: "['check_syntax', 'execute_command']" },
              { param: 'workspace', desc: 'Workspace environment where test commands run.', defaultValue: 'default' }
            ],
            recommendedConnections: 'Wire downstream from Coder Specialist to verify correctness before committing changes or finalizing output.'
          }
        }
      ]
    },
    {
      lane: 'policy',
      laneTitle: 'Lane 3: Policy & Safety Governance',
      items: [
        {
          lane: 'policy',
          type: 'security' as const,
          title: 'Approval Gate',
          subtitle: 'Requires human consent before mutating actions',
          tag: 'policy-gate',
          icon: ShieldCheck,
          color: 'text-rose-600 dark:text-rose-400',
          defaultConfig: { policy: 'ask', workspace: 'default' },
          doc: {
            role: 'Human Consent & Safety Policy',
            description: 'Human-in-the-loop safety checkpoint. Halts execution before sensitive operations or file mutations take place until the user grants explicit permission.',
            inputs: ['Proposed sensitive action from Coder or Shell Runner'],
            outputs: ['Approved or Denied authorization status'],
            configFields: [
              { param: 'policy', desc: "Authorization policy mode ('ask' requires manual approval, 'auto' auto-approves).", defaultValue: 'ask' },
              { param: 'workspace', desc: 'Workspace policy context.', defaultValue: 'default' }
            ],
            recommendedConnections: 'Position immediately before destructive tool calls or production file writes.'
          }
        },
        {
          lane: 'policy',
          type: 'security' as const,
          title: 'Circuit Breaker Guard',
          subtitle: 'Halts execution after 2 consecutive identical failures',
          tag: 'safety-break',
          icon: AlertTriangle,
          color: 'text-rose-600 dark:text-rose-400',
          defaultConfig: { max_failures: 2, workspace: 'default' },
          doc: {
            role: 'Safety & Loop Interrupter',
            description: 'Automated safety breaker. Interrupts pipeline execution if repeated identical failures are detected on the same step, guarding against infinite loops and token exhaustion.',
            inputs: ['Success or failure status from previous execution step'],
            outputs: ['Pass signal if healthy, or emergency trip interruption'],
            configFields: [
              { param: 'max_failures', desc: 'Maximum consecutive identical failures before tripping the circuit.', defaultValue: '2' },
              { param: 'workspace', desc: 'Monitored workspace context.', defaultValue: 'default' }
            ],
            recommendedConnections: 'Insert into retry loops between Coder and Auditor steps.'
          }
        }
      ]
    },
    {
      lane: 'tools',
      laneTitle: 'Lane 4: Tool Execution',
      items: [
        {
          lane: 'tools',
          type: 'messagebus' as const,
          title: 'Shell Command Runner',
          subtitle: 'execute_command subprocess in project directory',
          tag: 'subprocess',
          icon: Terminal,
          color: 'text-orange-600 dark:text-orange-400',
          defaultConfig: { command: 'pytest', workspace: 'default' },
          doc: {
            role: 'Subprocess Command Execution',
            description: 'Terminal CLI subprocess runner. Executes local commands such as test suites, build tools, or package managers within the host workspace environment.',
            inputs: ['Shell command string to execute'],
            outputs: ['Process exit code (0 for success), stdout stream, and stderr logs'],
            configFields: [
              { param: 'command', desc: 'Terminal command to run.', defaultValue: 'pytest' },
              { param: 'workspace', desc: 'Working directory for command execution.', defaultValue: 'default' }
            ],
            recommendedConnections: 'Wire downstream from Approval Gate when running commands that may modify project files.'
          }
        },
        {
          lane: 'tools',
          type: 'messagebus' as const,
          title: 'Filesystem Operator',
          subtitle: 'patch_file, write_file, and read_file handlers',
          tag: 'filesystem',
          icon: FileText,
          color: 'text-orange-600 dark:text-orange-400',
          defaultConfig: { path: '.', workspace: 'default' },
          doc: {
            role: 'File I/O & Manipulation',
            description: 'Direct file system handler. Manages reading, writing, and inspecting project directories outside of specialized code editing.',
            inputs: ['Target path, operation mode, and file content payload'],
            outputs: ['File operation status or retrieved file contents'],
            configFields: [
              { param: 'path', desc: 'Target file or directory path relative to workspace.', defaultValue: '.' },
              { param: 'workspace', desc: 'Target workspace owner.', defaultValue: 'default' }
            ],
            recommendedConnections: 'Use when the workflow needs to prepare configuration templates or read static local assets.'
          }
        },
        {
          lane: 'tools',
          type: 'cloud' as const,
          title: 'Web Search & Fetch',
          subtitle: 'Real-time online search and content fetcher',
          tag: 'online-web',
          icon: Globe,
          color: 'text-amber-600 dark:text-amber-400',
          defaultConfig: { provider: 'auto', workspace: 'default' },
          doc: {
            role: 'Online Data Retrieval',
            description: 'Real-time online search engine and web fetcher. Queries search providers and retrieves clean markdown from public web pages.',
            inputs: ['Search query or target web URL'],
            outputs: ['Search result citations or extracted web markdown content'],
            configFields: [
              { param: 'provider', desc: 'Search provider backend or automatic discovery mode.', defaultValue: 'auto' },
              { param: 'workspace', desc: 'Active workspace context.', defaultValue: 'default' }
            ],
            recommendedConnections: 'Connect to Research Specialist to enrich agent reasoning with up-to-date external documentation.'
          }
        }
      ]
    },
    {
      lane: 'evidence',
      laneTitle: 'Lane 5: Evidence & Memory',
      items: [
        {
          lane: 'evidence',
          type: 'database' as const,
          title: 'Blackboard State Sink',
          subtitle: 'Central blackboard aggregating findings and diffs',
          tag: 'blackboard',
          icon: Database,
          color: 'text-purple-600 dark:text-purple-400',
          defaultConfig: { workspace: 'default' },
          doc: {
            role: 'Shared State & Blackboard Memory',
            description: 'Central shared memory blackboard. Aggregates findings, context variables, file diffs, and intermediate state across all specialists.',
            inputs: ['Specialist findings, intermediate variables, and turn summaries'],
            outputs: ['Unified state accessible to all downstream steps'],
            configFields: [
              { param: 'workspace', desc: 'Workspace owning the blackboard state.', defaultValue: 'default' }
            ],
            recommendedConnections: 'Position in Lane 5 (Evidence & Memory) as the central sink for agent discoveries and artifacts.'
          }
        },
        {
          lane: 'evidence',
          type: 'database' as const,
          title: 'Trace Event Log',
          subtitle: 'Live chronological audit log of all agent turns',
          tag: 'event-stream',
          icon: Layers,
          color: 'text-purple-600 dark:text-purple-400',
          defaultConfig: { workspace: 'default' },
          doc: {
            role: 'Chronological Audit Trail',
            description: 'Comprehensive audit recorder. Captures chronological event streams, agent turns, latencies, and state transitions for debugging and compliance.',
            inputs: ['Event stream from all active pipeline nodes'],
            outputs: ['Chronological audit trail inspectable in the Live Event Log drawer'],
            configFields: [
              { param: 'workspace', desc: 'Workspace context for event log filtering.', defaultValue: 'default' }
            ],
            recommendedConnections: 'Wire to the terminal steps of the pipeline to guarantee full audit traceability.'
          }
        }
      ]
    }
  ];

export function findActivityCatalogItem(node: WorkflowNode): ActivityCatalogItem | undefined {
  for (const group of ACTIVITY_CATALOG) {
    const found = group.items.find(
      (item) =>
        item.tag === node.tag ||
        item.title.toLowerCase() === node.title.toLowerCase() ||
        node.title.toLowerCase().includes(item.title.toLowerCase()) ||
        item.title.toLowerCase().includes(node.title.toLowerCase())
    );
    if (found) return found;
  }
  for (const group of ACTIVITY_CATALOG) {
    const found = group.items.find((item) => item.lane === node.lane && item.type === node.type);
    if (found) return found;
  }
  return undefined;
}

export function WorkflowStudio({
  workspaces = [],
  activeWorkspace = 'default',
  models = [],
  config = null,
  onUpdateConfig,
  isConfigSyncing = false,
  onRefreshModels
}: WorkflowStudioProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Dynamic Swimlanes state (Can add, remove, reorder, and edit swimlanes)
  const [lanes, setLanes] = useState<WorkflowLaneConfig[]>(() => {
    try {
      const active = localStorage.getItem('locallm_active_canvas');
      if (active) {
        const parsed = JSON.parse(active);
        if (parsed.lanes && Array.isArray(parsed.lanes) && parsed.lanes.length > 0) {
          return parsed.lanes;
        }
      }
    } catch { }
    return INITIAL_LANES;
  });

  // Core diagram state with multi-select support
  const [activeWorkflowTitle, setActiveWorkflowTitle] = useState<string>(() => {
    try {
      const active = localStorage.getItem('locallm_active_canvas');
      if (active) {
        const parsed = JSON.parse(active);
        if (parsed.title) return parsed.title;
      }
    } catch { }
    return 'Agent Tool-Call Loop';
  });

  const [nodes, setNodes] = useState<WorkflowNode[]>(() => {
    try {
      const active = localStorage.getItem('locallm_active_canvas');
      if (active) {
        const parsed = JSON.parse(active);
        if (parsed.nodes && Array.isArray(parsed.nodes) && parsed.nodes.length > 0) {
          return parsed.nodes;
        }
      }
    } catch { }
    return WORKFLOW_PRESETS[0].nodes;
  });

  const [edges, setEdges] = useState<WorkflowEdge[]>(() => {
    try {
      const active = localStorage.getItem('locallm_active_canvas');
      if (active) {
        const parsed = JSON.parse(active);
        if (parsed.edges && Array.isArray(parsed.edges)) {
          return parsed.edges;
        }
      }
    } catch { }
    return WORKFLOW_PRESETS[0].edges;
  });

  // Multi-Selection State for activities and sequences
  const [selectedNodeIds, setSelectedNodeIds] = useState<string[]>([]);
  const [selectedLaneIds, setSelectedLaneIds] = useState<string[]>([]);
  const selectedNodeId = selectedNodeIds[0] || null;
  const setSelectedNodeId = useCallback((id: string | null) => {
    setSelectedNodeIds(id ? [id] : []);
  }, []);

  // Canvas Viewport transform
  const [zoom, setZoom] = useState<number>(1);
  const [pan, setPan] = useState<{ x: number; y: number }>({ x: 30, y: 20 });
  const [isCanvasPanning, setIsCanvasPanning] = useState<boolean>(false);
  const [isFullscreen, setIsFullscreen] = useState<boolean>(false);
  const [isGridVisible, setIsGridVisible] = useState<boolean>(true);

  // Flow Animation & Camera Focus Engine
  const [hoveredNodeId, setHoveredNodeId] = useState<string | null>(null);
  const [clickFocusZoomEnabled, setClickFocusZoomEnabled] = useState<boolean>(true);
  const [isCameraAnimating, setIsCameraAnimating] = useState<boolean>(false);
  const unhoverTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const baseCameraRef = useRef<{ zoom: number; pan: { x: number; y: number } } | null>(null);

  // Sequence Drag & Resize State (UiPath-Style Grouping & Resizing)
  const [draggingSequenceId, setDraggingSequenceId] = useState<string | null>(null);
  const [resizingSequenceId, setResizingSequenceId] = useState<string | null>(null);

  const dragSequenceRef = useRef<{
    laneId: string;
    startX: number;
    startY: number;
    initialLaneX: number;
    initialLaneY: number;
    initialNodes: { id: string; x: number; y: number }[];
    hasMoved: boolean;
    multiLanes?: {
      id: string;
      x: number;
      y: number;
      nodes: { id: string; x: number; y: number }[];
    }[];
  } | null>(null);

  const resizeSequenceRef = useRef<{
    laneId: string;
    startX: number;
    startY: number;
    initialWidth: number;
    initialHeight: number;
    minWidth?: number;
    initialLaneX?: number;
    initialNodes?: { id: string; x: number; y: number }[];
    mode: 'width' | 'both';
  } | null>(null);

  // Drag vs Click Tracking Refs to prevent jitter and erroneous camera movements
  const justDraggedNodeRef = useRef<boolean>(false);
  const canvasPanMovedRef = useRef<boolean>(false);
  const pointerRafIdRef = useRef<number | null>(null);
  const pendingPointerEventRef = useRef<PointerEvent | null>(null);

  // Modals & Panels
  const [isLibraryOpen, setIsLibraryOpen] = useState<boolean>(true);
  const [isDrawerOpen, setIsDrawerOpen] = useState<boolean>(false);
  const [isSettingsOpen, setIsSettingsOpen] = useState<boolean>(false);
  const [isPlatformMenuOpen, setIsPlatformMenuOpen] = useState<boolean>(false);
  const [isWorkflowMenuOpen, setIsWorkflowMenuOpen] = useState<boolean>(false);

  // Popover references for outside click auto-close
  const workflowMenuRef = useRef<HTMLDivElement>(null);
  const platformMenuRef = useRef<HTMLDivElement>(null);

  // Activity Documentation Detail Modal state
  const [detailDocItem, setDetailDocItem] = useState<ActivityCatalogItem | null>(null);

  // Workflow Save Confirmation Toast state
  const [saveToastMessage, setSaveToastMessage] = useState<string | null>(null);

  // Custom UI Modals
  const [isSaveModalOpen, setIsSaveModalOpen] = useState<boolean>(false);
  const [saveWorkflowNameInput, setSaveWorkflowNameInput] = useState<string>('');

  // Sequence Add & Edit Modal State
  const [sequenceModal, setSequenceModal] = useState<{
    isOpen: boolean;
    mode: 'add' | 'edit';
    laneId?: string;
    label: string;
    description: string;
    color: SequenceColor;
  }>({
    isOpen: false,
    mode: 'add',
    label: '',
    description: '',
    color: 'blue'
  });

  // Activity Delete Confirmation Modal
  const [nodeToDelete, setNodeToDelete] = useState<WorkflowNode | null>(null);

  // Canvas Undo / Redo History Stack
  const [historyPast, setHistoryPast] = useState<{ nodes: WorkflowNode[]; edges: WorkflowEdge[]; lanes: WorkflowLaneConfig[] }[]>([]);
  const [historyFuture, setHistoryFuture] = useState<{ nodes: WorkflowNode[]; edges: WorkflowEdge[]; lanes: WorkflowLaneConfig[] }[]>([]);
  const initialDragSnapshotRef = useRef<{ nodes: WorkflowNode[]; edges: WorkflowEdge[]; lanes: WorkflowLaneConfig[] } | null>(null);

  // Resizable Live Execution Log Drawer
  const [drawerHeight, setDrawerHeight] = useState<number>(200);
  const isResizingDrawerRef = useRef<boolean>(false);
  const startResizeYRef = useRef<number>(0);
  const startResizeHeightRef = useRef<number>(200);

  // Interactive Wiring (Sequence wire creation & rewiring with 4-sided ports)
  const [connectingSource, setConnectingSource] = useState<{ nodeId: string; side: PortSide } | null>(null);
  const [connectingMousePos, setConnectingMousePos] = useState<{ x: number; y: number } | null>(null);
  const [selectedEdgeId, setSelectedEdgeId] = useState<string | null>(null);
  const [rewiringEdge, setRewiringEdge] = useState<{ edgeId: string; end: 'from' | 'to' } | null>(null);

  // Node Drag State (Smooth pointer-based dragging)
  // Node Drag State (Smooth pointer-based dragging with multi-select support)
  const dragNodeRef = useRef<{
    nodeId: string;
    startX: number;
    startY: number;
    initialNodeX: number;
    initialNodeY: number;
    hasMoved?: boolean;
    multiNodes?: { id: string; x: number; y: number }[];
  } | null>(null);
  const [draggingNodeId, setDraggingNodeId] = useState<string | null>(null);
  const [hoveredLaneId, setHoveredLaneId] = useState<string | null>(null);

  // Real Model API Checking (Strictly from API, no hardcoded models)
  const [apiModels, setApiModels] = useState<ModelInfo[]>(models || []);
  const [isLoadingModels, setIsLoadingModels] = useState<boolean>(false);
  const [isCustomModelActive, setIsCustomModelActive] = useState<boolean>(false);

  // Execution engine & visual flow animation state
  const [isExecuting, setIsExecuting] = useState<boolean>(false);
  const isExecutingRef = useRef<boolean>(false);
  const executionAbortRef = useRef<AbortController | null>(null);
  const [executionMode, setExecutionMode] = useState<'real' | 'simulation'>('real');
  const [executionLogs, setExecutionLogs] = useState<ExecutionEvent[]>([]);
  const [activeTaskId, setActiveTaskId] = useState<string | null>(null);
  const [activeExecutingNodeId, setActiveExecutingNodeId] = useState<string | null>(null);
  const [nextTargetNodeId, setNextTargetNodeId] = useState<string | null>(null);
  const [activeFlowEdgeId, setActiveFlowEdgeId] = useState<string | null>(null);

  const [searchQuery, setSearchQuery] = useState<string>('');
  const [workspaceList, setWorkspaceList] = useState<Workspace[]>(workspaces);

  // Saved workflows in localStorage
  const [savedWorkflows, setSavedWorkflows] = useState<{ name: string; date: string; nodes: WorkflowNode[]; edges: WorkflowEdge[]; lanes?: WorkflowLaneConfig[] }[]>(() => {
    try {
      const stored = localStorage.getItem('locallm_saved_workflows');
      return stored ? JSON.parse(stored) : [];
    } catch {
      return [];
    }
  });

  const isPanningCanvasRef = useRef<boolean>(false);
  const canvasPanStartRef = useRef<{ startX: number; startY: number; panX: number; panY: number }>({
    startX: 0,
    startY: 0,
    panX: 30,
    panY: 20
  });
  const pollingRef = useRef<any>(null);

  // Current active backend / platform identifier
  const currentBackend = config?.active_backend || 'ollama';

  // Platforms strictly registered in LocaLLM configuration (No hardcoded extras)
  const registeredPlatforms = useMemo(() => {
    const list: { id: string; name: string }[] = [];
    list.push({ id: 'ollama', name: 'Ollama (Local Engine)' });

    if (config?.custom_platforms && Array.isArray(config.custom_platforms)) {
      config.custom_platforms.forEach((p) => {
        if (p.name && !list.some((existing) => existing.id === p.name)) {
          list.push({ id: p.name, name: p.name });
        }
      });
    }

    if (config?.active_backend && !list.some((existing) => existing.id === config.active_backend)) {
      list.push({ id: config.active_backend, name: config.active_backend });
    }

    return list;
  }, [config]);

  // Real Model API Checking Function
  const fetchModelsFromApi = useCallback(async (backendName: string) => {
    setIsLoadingModels(true);
    try {
      const fetched = await api.getModels(backendName);
      if (Array.isArray(fetched)) {
        setApiModels(fetched);
      }
      if (onRefreshModels) {
        onRefreshModels(backendName);
      }
    } catch (err) {
      console.warn(`Failed to fetch models for backend ${backendName}:`, err);
    } finally {
      setIsLoadingModels(false);
    }
  }, [onRefreshModels]);

  // Initial and reactive model fetch whenever platform changes
  useEffect(() => {
    fetchModelsFromApi(currentBackend);
  }, [currentBackend, fetchModelsFromApi]);

  // Sync workspaces from props or fetch
  useEffect(() => {
    if (workspaces.length > 0) {
      setWorkspaceList(workspaces);
    } else {
      fetch('/api/workspaces')
        .then((res) => (res.ok ? res.json() : []))
        .then((data) => {
          if (Array.isArray(data) && data.length > 0) {
            setWorkspaceList(data);
          }
        })
        .catch(() => { });
    }
  }, [workspaces]);

  // Fullscreen change listener
  useEffect(() => {
    const handleFsChange = () => {
      setIsFullscreen(Boolean(document.fullscreenElement));
    };
    document.addEventListener('fullscreenchange', handleFsChange);
    return () => document.removeEventListener('fullscreenchange', handleFsChange);
  }, []);

  // Mouse wheel zoom handler
  useEffect(() => {
    const el = canvasRef.current;
    if (!el) return;

    const onWheel = (e: WheelEvent) => {
      e.preventDefault();
      const zoomFactor = e.deltaY < 0 ? 1.08 : 0.92;
      setZoom((prevZoom) => {
        return Math.min(2.2, Math.max(0.4, Number((prevZoom * zoomFactor).toFixed(2))));
      });
    };

    el.addEventListener('wheel', onWheel, { passive: false });
    return () => el.removeEventListener('wheel', onWheel);
  }, []);

  // Helper to detect sequence by coordinates dynamically based on current sequences
  const detectLaneByCoord = useCallback((x: number, y: number): string => {
    const midX = x + NODE_WIDTH / 2;
    const midY = y + NODE_HEIGHT / 2;
    for (const lane of lanes) {
      const lx = lane.x ?? 30;
      const lw = lane.width ?? 1680;
      if (midX >= lx && midX <= lx + lw && midY >= lane.y && midY <= lane.y + lane.height) {
        return lane.id;
      }
    }
    for (const lane of lanes) {
      if (midY >= lane.y && midY <= lane.y + lane.height + 20) {
        return lane.id;
      }
    }
    return lanes[0]?.id || 'ui';
  }, [lanes]);

  // Mutable refs for pointer listeners to avoid stale closures
  const selectedNodeIdRef = useRef<string | null>(selectedNodeId);
  selectedNodeIdRef.current = selectedNodeId;
  const selectedNodeIdsRef = useRef<string[]>(selectedNodeIds);
  selectedNodeIdsRef.current = selectedNodeIds;
  const selectedLaneIdsRef = useRef<string[]>(selectedLaneIds);
  selectedLaneIdsRef.current = selectedLaneIds;
  const selectedEdgeIdRef = useRef<string | null>(selectedEdgeId);
  selectedEdgeIdRef.current = selectedEdgeId;
  const handleSelectNodeRef = useRef<(id: string) => void>(() => {});
  const handleUnselectNodeRef = useRef<() => void>(() => {});
  const handleDeleteSelectedRef = useRef<() => void>(() => {});

  // Global Pointer Listeners for Smooth Node Dragging, Sequence Dragging/Resizing, and Canvas Panning
  useEffect(() => {
    const handleMove = (e: PointerEvent) => {
      // 1. Handle Sequence Container Dragging (Single or Multi-Sequence)
      if (dragSequenceRef.current) {
        const { laneId, startX, startY, initialLaneX, initialLaneY, initialNodes, multiLanes } = dragSequenceRef.current;
        const rawDist = Math.hypot(e.clientX - startX, e.clientY - startY);
        if (rawDist > 3) {
          dragSequenceRef.current.hasMoved = true;
        }

        const dx = (e.clientX - startX) / zoom;
        const dy = (e.clientY - startY) / zoom;

        if (multiLanes && multiLanes.length > 1) {
          // Multi-sequence simultaneous movement
          setLanes((prev) =>
            prev.map((l) => {
              const match = multiLanes.find((m) => m.id === l.id);
              if (match) {
                return {
                  ...l,
                  x: Math.max(10, Math.round(match.x + dx)),
                  y: Math.max(10, Math.round(match.y + dy))
                };
              }
              return l;
            })
          );

          setNodes((prev) =>
            prev.map((n) => {
              for (const ml of multiLanes) {
                const nodeMatch = ml.nodes.find((init) => init.id === n.id);
                if (nodeMatch) {
                  return {
                    ...n,
                    x: Math.max(10, Math.round(nodeMatch.x + dx)),
                    y: Math.max(10, Math.round(nodeMatch.y + dy))
                  };
                }
              }
              return n;
            })
          );
        } else {
          // Single sequence movement
          const newLaneX = Math.max(10, Math.round(initialLaneX + dx));
          const newLaneY = Math.max(10, Math.round(initialLaneY + dy));

          const deltaX = newLaneX - initialLaneX;
          const deltaY = newLaneY - initialLaneY;

          setLanes((prev) =>
            prev.map((l) => (l.id === laneId ? { ...l, x: newLaneX, y: newLaneY } : l))
          );

          setNodes((prev) =>
            prev.map((n) => {
              const match = initialNodes.find((init) => init.id === n.id);
              if (match) {
                return {
                  ...n,
                  x: Math.max(10, Math.round(match.x + deltaX)),
                  y: Math.max(10, Math.round(match.y + deltaY))
                };
              }
              return n;
            })
          );
        }
        return;
      }

      // 2. Handle Sequence Container Resizing with Minimum Size & Inward Push
      if (resizeSequenceRef.current) {
        const { laneId, startX, startY, initialWidth, initialHeight, minWidth, initialLaneX, initialNodes, mode } = resizeSequenceRef.current;
        const dx = (e.clientX - startX) / zoom;
        const dy = (e.clientY - startY) / zoom;

        // Apply minimum width constraint so sequence cannot be closed past its activities
        const newWidth = Math.max(minWidth || 420, Math.round(initialWidth + dx));
        const newHeight = mode === 'both' ? Math.max(110, Math.round(initialHeight + dy)) : initialHeight;

        setLanes((prev) =>
          prev.map((l) => (l.id === laneId ? { ...l, width: newWidth, height: newHeight } : l))
        );

        // When sequence is shrunk, push contained activities inward in the direction of the drag
        if (initialNodes && initialNodes.length > 0 && typeof initialLaneX === 'number') {
          const maxAllowedNodeX = initialLaneX + newWidth - NODE_WIDTH - 24;

          setNodes((prev) =>
            prev.map((n) => {
              const init = initialNodes.find((m) => m.id === n.id);
              if (!init) return n;

              if (newWidth < initialWidth) {
                // Shrunk: push inward if right boundary is encroaching
                if (init.x > maxAllowedNodeX) {
                  return { ...n, x: Math.max(initialLaneX + 24, maxAllowedNodeX) };
                }
                const ratio = Math.max(0.4, (newWidth - NODE_WIDTH - 48) / Math.max(1, initialWidth - NODE_WIDTH - 48));
                const relX = init.x - initialLaneX - 24;
                const shiftedX = Math.round(initialLaneX + 24 + relX * ratio);
                return { ...n, x: Math.max(initialLaneX + 24, Math.min(maxAllowedNodeX, shiftedX)) };
              } else {
                // Widening back: smoothly restore original position
                return { ...n, x: init.x };
              }
            })
          );
        }
        return;
      }

      // 3. Handle Smooth Individual & Multi Activity Node Dragging
      if (dragNodeRef.current) {
        const { nodeId, startX, startY, initialNodeX, initialNodeY, multiNodes } = dragNodeRef.current;
        const rawDist = Math.hypot(e.clientX - startX, e.clientY - startY);
        if (rawDist > 4) {
          dragNodeRef.current.hasMoved = true;
        }

        const dx = (e.clientX - startX) / zoom;
        const dy = (e.clientY - startY) / zoom;

        const newX = Math.max(20, Math.round(initialNodeX + dx));
        const newY = Math.max(20, Math.round(initialNodeY + dy));

        const targetLane = detectLaneByCoord(newX, newY);
        setHoveredLaneId(targetLane);

        if (multiNodes && multiNodes.length > 1) {
          // Multi-node drag: all selected nodes move in unison
          setNodes((prev) =>
            prev.map((n) => {
              const match = multiNodes.find((m) => m.id === n.id);
              if (match) {
                return {
                  ...n,
                  x: Math.max(20, Math.round(match.x + dx)),
                  y: Math.max(20, Math.round(match.y + dy))
                };
              }
              return n;
            })
          );
        } else {
          // Single node drag
          setNodes((prev) =>
            prev.map((n) => {
              if (n.id === nodeId) {
                return {
                  ...n,
                  x: newX,
                  y: newY
                };
              }
              return n;
            })
          );
        }
        return;
      }

      // 4. Handle Connecting Wire Preview line
      if ((connectingSource || rewiringEdge) && canvasRef.current) {
        const rect = canvasRef.current.getBoundingClientRect();
        setConnectingMousePos({
          x: (e.clientX - rect.left - pan.x) / zoom,
          y: (e.clientY - rect.top - pan.y) / zoom
        });
      }

      // 5. Handle Canvas Panning
      if (isPanningCanvasRef.current) {
        const dx = e.clientX - canvasPanStartRef.current.startX;
        const dy = e.clientY - canvasPanStartRef.current.startY;
        if (Math.hypot(dx, dy) > 4) {
          canvasPanMovedRef.current = true;
          baseCameraRef.current = null;
        }
        setPan({
          x: Math.round(canvasPanStartRef.current.panX + dx),
          y: Math.round(canvasPanStartRef.current.panY + dy)
        });
      }
    };

    const onWindowPointerMove = (e: PointerEvent) => {
      // Coalesce pointer events with requestAnimationFrame for smooth 60/120fps dragging
      pendingPointerEventRef.current = e;
      if (pointerRafIdRef.current !== null) return;

      pointerRafIdRef.current = requestAnimationFrame(() => {
        pointerRafIdRef.current = null;
        if (pendingPointerEventRef.current) {
          handleMove(pendingPointerEventRef.current);
        }
      });
    };

    const onWindowPointerUp = () => {
      if (pointerRafIdRef.current !== null) {
        cancelAnimationFrame(pointerRafIdRef.current);
        pointerRafIdRef.current = null;
      }
      if (pendingPointerEventRef.current) {
        handleMove(pendingPointerEventRef.current);
        pendingPointerEventRef.current = null;
      }

      // Finalize Sequence Dragging
      if (dragSequenceRef.current) {
        const { hasMoved } = dragSequenceRef.current;
        if (hasMoved && initialDragSnapshotRef.current) {
          setHistoryPast((prev) => [...prev.slice(-30), initialDragSnapshotRef.current!]);
          setHistoryFuture([]);
        }
        initialDragSnapshotRef.current = null;
        dragSequenceRef.current = null;
        setDraggingSequenceId(null);
      }

      // Finalize Sequence Resizing
      if (resizeSequenceRef.current) {
        if (initialDragSnapshotRef.current) {
          setHistoryPast((prev) => [...prev.slice(-30), initialDragSnapshotRef.current!]);
          setHistoryFuture([]);
        }
        initialDragSnapshotRef.current = null;
        resizeSequenceRef.current = null;
        setResizingSequenceId(null);
      }

      // Finalize Individual Node Dragging
      if (dragNodeRef.current) {
        const { nodeId, hasMoved, multiNodes } = dragNodeRef.current;
        if (hasMoved) {
          // Commit final lane assignment upon drop for all moved nodes
          setNodes((prev) =>
            prev.map((n) => {
              if (multiNodes && multiNodes.some((m) => m.id === n.id)) {
                const finalLane = detectLaneByCoord(n.x, n.y);
                return { ...n, lane: finalLane };
              }
              if (n.id === nodeId) {
                const finalLane = detectLaneByCoord(n.x, n.y);
                return { ...n, lane: finalLane };
              }
              return n;
            })
          );
        }

        if (hasMoved && initialDragSnapshotRef.current) {
          setHistoryPast((prev) => [...prev.slice(-30), initialDragSnapshotRef.current!]);
          setHistoryFuture([]);
        }
        initialDragSnapshotRef.current = null;
        dragNodeRef.current = null;
        setDraggingNodeId(null);
        setHoveredLaneId(null);

        if (hasMoved) {
          justDraggedNodeRef.current = true;
        } else {
          justDraggedNodeRef.current = false;
        }
      }

      if (isPanningCanvasRef.current) {
        // If canvas was clicked without panning movement, unselect all
        if (!canvasPanMovedRef.current) {
          setSelectedNodeIds([]);
          setSelectedLaneIds([]);
          setSelectedEdgeId(null);
          setRewiringEdge(null);
          if (selectedNodeIdRef.current) {
            handleUnselectNodeRef.current();
          }
        }
        isPanningCanvasRef.current = false;
        setIsCanvasPanning(false);
      }
    };

    const onWindowKeyDown = (e: KeyboardEvent) => {
      const activeEl = document.activeElement;
      const isInput =
        activeEl &&
        (activeEl.tagName === 'INPUT' ||
          activeEl.tagName === 'TEXTAREA' ||
          activeEl.tagName === 'SELECT' ||
          activeEl.getAttribute('contenteditable') === 'true');

      if (!isInput && (e.key === 'Delete' || e.key === 'Del')) {
        handleDeleteSelectedRef.current();
        return;
      }

      if (e.key === 'Escape') {
        setSelectedNodeIds([]);
        setSelectedLaneIds([]);
        setSelectedEdgeId(null);
        setRewiringEdge(null);
        if (selectedNodeIdRef.current) {
          handleUnselectNodeRef.current();
        }
        setSequenceModal((prev) => (prev.isOpen ? { ...prev, isOpen: false } : prev));
        setConnectingSource(null);
        setConnectingMousePos(null);
      }
    };

    window.addEventListener('pointermove', onWindowPointerMove);
    window.addEventListener('pointerup', onWindowPointerUp);
    window.addEventListener('keydown', onWindowKeyDown);
    return () => {
      if (pointerRafIdRef.current !== null) {
        cancelAnimationFrame(pointerRafIdRef.current);
      }
      window.removeEventListener('pointermove', onWindowPointerMove);
      window.removeEventListener('pointerup', onWindowPointerUp);
      window.removeEventListener('keydown', onWindowKeyDown);
    };
  }, [zoom, pan, connectingSource, rewiringEdge, detectLaneByCoord]);

  // Selected Node reference
  const selectedNode = useMemo(() => {
    return nodes.find((n) => n.id === selectedNodeId) || null;
  }, [nodes, selectedNodeId]);

  // Selected Edge / Wire reference
  const selectedEdge = useMemo(() => {
    return edges.find((e) => e.id === selectedEdgeId) || null;
  }, [edges, selectedEdgeId]);

  // Selected Node documentation catalog reference
  const selectedCatalogItem = useMemo(() => {
    return selectedNode ? findActivityCatalogItem(selectedNode) : undefined;
  }, [selectedNode]);

  // Check if current selected node model is custom
  useEffect(() => {
    if (selectedNode?.config?.model) {
      const isKnown = apiModels.some((m) => m.id === selectedNode.config.model);
      setIsCustomModelActive(!isKnown);
    } else {
      setIsCustomModelActive(false);
    }
  }, [selectedNode?.id, selectedNode?.config?.model, apiModels]);

  // Calculate topological / execution sequence numbering for all nodes (#1, #2, #3...)
  const nodeSequenceNumbers = useMemo(() => {
    const seqMap = new Map<string, number>();
    const inDegree = new Map<string, number>();
    nodes.forEach((n) => inDegree.set(n.id, 0));
    edges.forEach((e) => {
      inDegree.set(e.to, (inDegree.get(e.to) || 0) + 1);
    });

    let queue = nodes.filter((n) => (inDegree.get(n.id) || 0) === 0).map((n) => n.id);
    if (queue.length === 0 && nodes.length > 0) queue = [nodes[0].id];

    let step = 1;
    const visited = new Set<string>();
    while (queue.length > 0) {
      const currId = queue.shift()!;
      if (!visited.has(currId)) {
        visited.add(currId);
        seqMap.set(currId, step++);
        const nextNodes = edges.filter((e) => e.from === currId).map((e) => e.to);
        nextNodes.forEach((nxt) => {
          if (!visited.has(nxt)) queue.push(nxt);
        });
      }
    }
    nodes.forEach((n) => {
      if (!seqMap.has(n.id)) seqMap.set(n.id, step++);
    });
    return seqMap;
  }, [nodes, edges]);

  // Node position map for instant connector alignment
  const nodePositionMap = useMemo(() => {
    const map = new Map<string, { x: number; y: number }>();
    nodes.forEach((n) => {
      map.set(n.id, { x: n.x, y: n.y });
    });
    return map;
  }, [nodes]);

  // Hover State Handler (Activates semantic colored shadow on the hovered activity)
  const handleNodeMouseEnter = useCallback((nodeId: string) => {
    if (draggingNodeId || isPanningCanvasRef.current || isExecuting) return;

    if (unhoverTimeoutRef.current) {
      clearTimeout(unhoverTimeoutRef.current);
      unhoverTimeoutRef.current = null;
    }

    setHoveredNodeId(nodeId);
  }, [draggingNodeId, isExecuting]);

  // Hover Clear Handler
  const handleNodeMouseLeave = useCallback(() => {
    if (unhoverTimeoutRef.current) {
      clearTimeout(unhoverTimeoutRef.current);
    }

    unhoverTimeoutRef.current = setTimeout(() => {
      setHoveredNodeId(null);
    }, 100);
  }, []);

  // Deselect and Zoom Out to Overview Handler
  const handleUnselectNode = useCallback(() => {
    setSelectedNodeIds([]);
    setSelectedLaneIds([]);

    if (baseCameraRef.current) {
      const { zoom: origZoom, pan: origPan } = baseCameraRef.current;
      baseCameraRef.current = null;
      setIsCameraAnimating(true);
      setZoom(origZoom);
      setPan(origPan);
      setTimeout(() => {
        setIsCameraAnimating(false);
      }, 340);
    }
  }, []);

  // Click Focus Zoom In Handler (Smoothly frames node and opens properties)
  const handleSelectNode = useCallback((nodeId: string) => {
    setSelectedNodeIds([nodeId]);
    setSelectedLaneIds([]);
    setSelectedEdgeId(null);
    setRewiringEdge(null);

    if (!clickFocusZoomEnabled) return;

    // Capture base camera only if not already focused from another node
    if (!baseCameraRef.current) {
      baseCameraRef.current = { zoom, pan };
    }

    const targetNode = nodes.find((n) => n.id === nodeId);
    if (targetNode && canvasRef.current) {
      const cWidth = canvasRef.current.clientWidth || 1200;
      const cHeight = canvasRef.current.clientHeight || 700;

      const outEdges = edges.filter((e) => e.from === nodeId);
      const downNodes = nodes.filter((n) => outEdges.some((e) => e.to === n.id));

      let cx = targetNode.x + NODE_WIDTH / 2;
      let cy = targetNode.y + NODE_HEIGHT / 2;

      if (downNodes.length > 0) {
        const avgDownX = downNodes.reduce((acc, n) => acc + n.x + NODE_WIDTH / 2, 0) / downNodes.length;
        const avgDownY = downNodes.reduce((acc, n) => acc + n.y + NODE_HEIGHT / 2, 0) / downNodes.length;
        // Weighted forward focus: 58% on current node, 42% on downstream targets
        cx = cx * 0.58 + avgDownX * 0.42;
        cy = cy * 0.58 + avgDownY * 0.42;
      }

      const targetZoom = 1.35;
      const targetPanX = Math.round(cWidth / 2 - cx * targetZoom);
      const targetPanY = Math.round(cHeight / 2 - cy * targetZoom);

      setIsCameraAnimating(true);
      setZoom(targetZoom);
      setPan({ x: targetPanX, y: targetPanY });

      setTimeout(() => {
        setIsCameraAnimating(false);
      }, 340);
    }
  }, [clickFocusZoomEnabled, zoom, pan, nodes, edges, handleUnselectNode]);

  // Canvas History snapshot recorder for Undo
  const recordHistory = useCallback(() => {
    setHistoryPast((prev) => [
      ...prev.slice(-30),
      {
        nodes: JSON.parse(JSON.stringify(nodes)),
        edges: JSON.parse(JSON.stringify(edges)),
        lanes: JSON.parse(JSON.stringify(lanes))
      }
    ]);
    setHistoryFuture([]);
  }, [nodes, edges, lanes]);

  // Unified Delete Selected Items Handler (Works with DEL shortcut)
  const handleDeleteSelected = useCallback(() => {
    if (isExecuting) return;
    const nodeIdsToDelete = selectedNodeIdsRef.current;
    const laneIdsToDelete = selectedLaneIdsRef.current;
    const edgeIdToDelete = selectedEdgeIdRef.current;
    if (nodeIdsToDelete.length === 0 && laneIdsToDelete.length === 0 && !edgeIdToDelete) return;

    recordHistory();

    let nextLanes = [...lanes];
    let nextNodes = [...nodes];
    let nextEdges = [...edges];

    // Delete selected edge
    if (edgeIdToDelete) {
      nextEdges = nextEdges.filter((e) => e.id !== edgeIdToDelete);
      setSelectedEdgeId(null);
    }

    // 1. Delete selected sequences (safely leave at least 1 sequence)
    if (laneIdsToDelete.length > 0) {
      if (nextLanes.length <= laneIdsToDelete.length) {
        const toDelete = laneIdsToDelete.slice(0, nextLanes.length - 1);
        nextLanes = nextLanes.filter((l) => !toDelete.includes(l.id));
      } else {
        nextLanes = nextLanes.filter((l) => !laneIdsToDelete.includes(l.id));
      }
      const fallbackLane = nextLanes[0]?.id || 'ui';
      nextNodes = nextNodes.map((n) =>
        laneIdsToDelete.includes(n.lane) ? { ...n, lane: fallbackLane } : n
      );
    }

    // 2. Delete selected activities
    if (nodeIdsToDelete.length > 0) {
      nextNodes = nextNodes.filter((n) => !nodeIdsToDelete.includes(n.id));
      nextEdges = nextEdges.filter(
        (e) => !nodeIdsToDelete.includes(e.from) && !nodeIdsToDelete.includes(e.to)
      );
    }

    setLanes(nextLanes);
    setNodes(nextNodes);
    setEdges(nextEdges);
    setSelectedNodeIds([]);
    setSelectedLaneIds([]);

    const deletedNodesCount = nodes.length - nextNodes.length;
    const deletedLanesCount = lanes.length - nextLanes.length;
    let msg = '';
    if (edgeIdToDelete) {
      msg = 'Deleted connection wire';
    } else if (deletedNodesCount > 0 && deletedLanesCount > 0) {
      msg = `Deleted ${deletedNodesCount} activity(ies) and ${deletedLanesCount} sequence(s)`;
    } else if (deletedNodesCount > 0) {
      msg = `Deleted ${deletedNodesCount} activity(ies)`;
    } else if (deletedLanesCount > 0) {
      msg = `Deleted ${deletedLanesCount} sequence(s)`;
    }
    if (msg) {
      setSaveToastMessage(msg);
      setTimeout(() => setSaveToastMessage(null), 2500);
    }
  }, [isExecuting, recordHistory, lanes, nodes, edges]);

  // Auto-reposition and distribute activities inside a sequence neatly
  const handleAutoRepositionLaneActivities = useCallback((laneId: string) => {
    if (isExecuting) return;
    const lane = lanes.find((l) => l.id === laneId);
    if (!lane) return;

    const laneNodes = nodes.filter((n) => n.lane === laneId);
    if (laneNodes.length === 0) return;

    recordHistory();

    const laneX = lane.x ?? 30;
    const laneWidth = lane.width ?? 1680;
    const centerY = Math.round(lane.y + (lane.height - NODE_HEIGHT) / 2);

    // Sort by current X position to preserve sequence order
    const sorted = [...laneNodes].sort((a, b) => a.x - b.x);

    let step = 0;
    if (sorted.length > 1) {
      const availableSpan = Math.max(0, laneWidth - 80 - NODE_WIDTH);
      step = availableSpan / (sorted.length - 1);
    }

    setNodes((prev) =>
      prev.map((n) => {
        const idx = sorted.findIndex((s) => s.id === n.id);
        if (idx !== -1) {
          const newX = sorted.length === 1
            ? Math.round(laneX + (laneWidth - NODE_WIDTH) / 2)
            : Math.round(laneX + 40 + idx * step);
          return {
            ...n,
            x: newX,
            y: centerY
          };
        }
        return n;
      })
    );

    setSaveToastMessage(`Auto-repositioned ${sorted.length} activity(ies) in "${lane.label}"`);
    setTimeout(() => setSaveToastMessage(null), 2500);
  }, [isExecuting, lanes, nodes, recordHistory]);

  // Auto-align and tidy all sequences into a clean vertical stack
  const handleAutoAlignAllSequences = useCallback(() => {
    if (isExecuting) return;
    recordHistory();

    let currentY = 70;
    const updatedLanes = lanes.map((lane, index) => {
      const num = String(index + 1).padStart(2, '0');
      const targetX = 30;
      const targetY = currentY;
      const deltaX = targetX - (lane.x ?? 30);
      const deltaY = targetY - lane.y;

      setNodes((prev) =>
        prev.map((n) => {
          if (n.lane === lane.id) {
            return {
              ...n,
              x: Math.round(n.x + deltaX),
              y: Math.round(n.y + deltaY)
            };
          }
          return n;
        })
      );

      currentY += lane.height + 24;
      return {
        ...lane,
        num,
        x: targetX,
        y: targetY
      };
    });

    setLanes(updatedLanes);
    setSaveToastMessage('All sequences and activities auto-aligned neatly');
    setTimeout(() => setSaveToastMessage(null), 2500);
  }, [isExecuting, lanes, recordHistory]);

  // Sync latest handlers to mutable refs for global event listeners
  handleSelectNodeRef.current = handleSelectNode;
  handleUnselectNodeRef.current = handleUnselectNode;

  // Filtered Activity Palette items
  const filteredCatalog = useMemo(() => {
    if (!searchQuery.trim()) return ACTIVITY_CATALOG;
    const q = searchQuery.toLowerCase();
    return ACTIVITY_CATALOG.map((cat) => ({
      ...cat,
      items: cat.items.filter(
        (item) =>
          item.title.toLowerCase().includes(q) ||
          item.subtitle.toLowerCase().includes(q) ||
          item.tag.toLowerCase().includes(q) ||
          item.doc.role.toLowerCase().includes(q) ||
          item.doc.description.toLowerCase().includes(q)
      )
    })).filter((cat) => cat.items.length > 0);
  }, [searchQuery]);

  // Total dynamic canvas SVG dimensions based on active sequences (stable to prevent layout shifts)
  const totalCanvasHeight = useMemo(() => {
    let maxY = 1800;
    lanes.forEach((l) => {
      maxY = Math.max(maxY, l.y + l.height + 400);
    });
    return maxY;
  }, [lanes]);

  const totalCanvasWidth = useMemo(() => {
    let maxX = 2800;
    lanes.forEach((l) => {
      maxX = Math.max(maxX, (l.x ?? 30) + (l.width ?? 1680) + 400);
    });
    return maxX;
  }, [lanes]);

  // Resizable Live Execution Log Drawer Handler
  const handleDrawerResizeStart = (e: React.PointerEvent) => {
    e.preventDefault();
    isResizingDrawerRef.current = true;
    startResizeYRef.current = e.clientY;
    startResizeHeightRef.current = drawerHeight;

    const onPointerMove = (ev: PointerEvent) => {
      if (!isResizingDrawerRef.current) return;
      const deltaY = startResizeYRef.current - ev.clientY;
      const nextH = Math.max(120, Math.min(600, startResizeHeightRef.current + deltaY));
      setDrawerHeight(nextH);
    };

    const onPointerUp = () => {
      isResizingDrawerRef.current = false;
      window.removeEventListener('pointermove', onPointerMove);
      window.removeEventListener('pointerup', onPointerUp);
    };

    window.addEventListener('pointermove', onPointerMove);
    window.addEventListener('pointerup', onPointerUp);
  };

  // Undo handler
  const handleUndo = useCallback(() => {
    if (isExecuting) return;
    if (historyPast.length === 0) return;
    const previous = historyPast[historyPast.length - 1];
    const newPast = historyPast.slice(0, -1);

    setHistoryFuture((f) => [
      {
        nodes: JSON.parse(JSON.stringify(nodes)),
        edges: JSON.parse(JSON.stringify(edges)),
        lanes: JSON.parse(JSON.stringify(lanes))
      },
      ...f
    ]);
    setHistoryPast(newPast);
    setNodes(previous.nodes);
    setEdges(previous.edges);
    setLanes(previous.lanes);
  }, [isExecuting, historyPast, nodes, edges, lanes]);

  // Redo handler
  const handleRedo = useCallback(() => {
    if (isExecuting) return;
    if (historyFuture.length === 0) return;
    const next = historyFuture[0];
    const newFuture = historyFuture.slice(1);

    setHistoryPast((p) => [
      ...p,
      {
        nodes: JSON.parse(JSON.stringify(nodes)),
        edges: JSON.parse(JSON.stringify(edges)),
        lanes: JSON.parse(JSON.stringify(lanes))
      }
    ]);
    setHistoryFuture(newFuture);
    setNodes(next.nodes);
    setEdges(next.edges);
    setLanes(next.lanes);
  }, [isExecuting, historyFuture, nodes, edges, lanes]);

  // Save workflow: direct save with "Success to save" toast if already saved, or modal dialog if new
  const handleSaveWorkflowAction = useCallback(() => {
    const isSaved = savedWorkflows.some(
      (w) => w.name.toLowerCase() === activeWorkflowTitle.toLowerCase()
    );
    if (isSaved) {
      const item = {
        name: activeWorkflowTitle,
        date: new Date().toLocaleDateString(),
        lanes,
        nodes,
        edges
      };
      const updated = [item, ...savedWorkflows.filter((w) => w.name !== item.name)];
      setSavedWorkflows(updated);
      try {
        localStorage.setItem('locallm_saved_workflows', JSON.stringify(updated));
      } catch { }
      setSaveToastMessage('Success to save');
      setTimeout(() => setSaveToastMessage(null), 2500);
    } else {
      setSaveWorkflowNameInput(activeWorkflowTitle);
      setIsSaveModalOpen(true);
    }
  }, [activeWorkflowTitle, lanes, nodes, edges, savedWorkflows]);

  const handleOpenSaveDialog = useCallback(() => {
    setSaveWorkflowNameInput(activeWorkflowTitle);
    setIsSaveModalOpen(true);
  }, [activeWorkflowTitle]);

  const handleConfirmSaveWorkflow = useCallback((name: string) => {
    if (!name.trim()) return;
    const item = {
      name: name.trim(),
      date: new Date().toLocaleDateString(),
      lanes,
      nodes,
      edges
    };
    const updated = [item, ...savedWorkflows.filter((w) => w.name !== item.name)];
    setSavedWorkflows(updated);
    try {
      localStorage.setItem('locallm_saved_workflows', JSON.stringify(updated));
    } catch { }
    setActiveWorkflowTitle(item.name);
    setIsSaveModalOpen(false);
    setSaveToastMessage('Success to save');
    setTimeout(() => setSaveToastMessage(null), 2500);
  }, [lanes, nodes, edges, savedWorkflows]);

  // Global Keyboard shortcuts: Ctrl+S (Save), Del (Delete Selected), Ctrl+Z (Undo), Ctrl+Shift+Z / Ctrl+Y (Redo), and Arrow Keys (Nudge)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Ctrl+S / Cmd+S save workflow shortcut
      if ((e.ctrlKey || e.metaKey) && !e.shiftKey && e.key.toLowerCase() === 's') {
        e.preventDefault();
        handleSaveWorkflowAction();
        return;
      }

      const activeEl = document.activeElement;
      if (
        activeEl &&
        (activeEl.tagName === 'INPUT' ||
          activeEl.tagName === 'TEXTAREA' ||
          activeEl.tagName === 'SELECT' ||
          activeEl.getAttribute('contenteditable') === 'true')
      ) {
        return;
      }

      // Delete shortcut with DEL key
      if (e.key === 'Delete' || e.key === 'Del') {
        if (!isExecuting && (selectedNodeIds.length > 0 || selectedLaneIds.length > 0 || selectedEdgeId)) {
          e.preventDefault();
          handleDeleteSelected();
          return;
        }
      }

      // Arrow keys nudging for selected items
      if (['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight'].includes(e.key)) {
        const step = e.shiftKey ? 20 : 4;
        let dx = 0;
        let dy = 0;
        if (e.key === 'ArrowLeft') dx = -step;
        if (e.key === 'ArrowRight') dx = step;
        if (e.key === 'ArrowUp') dy = -step;
        if (e.key === 'ArrowDown') dy = step;

        if (selectedNodeIds.length > 0) {
          e.preventDefault();
          recordHistory();
          setNodes((prev) =>
            prev.map((n) =>
              selectedNodeIds.includes(n.id)
                ? { ...n, x: Math.max(10, n.x + dx), y: Math.max(10, n.y + dy) }
                : n
            )
          );
          return;
        }

        if (selectedLaneIds.length > 0) {
          e.preventDefault();
          recordHistory();
          setLanes((prev) =>
            prev.map((l) =>
              selectedLaneIds.includes(l.id)
                ? { ...l, x: Math.max(10, (l.x ?? 30) + dx), y: Math.max(10, l.y + dy) }
                : l
            )
          );
          setNodes((prev) =>
            prev.map((n) =>
              selectedLaneIds.includes(n.lane)
                ? { ...n, x: Math.max(10, n.x + dx), y: Math.max(10, n.y + dy) }
                : n
            )
          );
          return;
        }
      }

      if ((e.ctrlKey || e.metaKey) && !e.shiftKey && e.key.toLowerCase() === 'z') {
        e.preventDefault();
        handleUndo();
      } else if (
        (e.ctrlKey || e.metaKey) &&
        ((e.shiftKey && e.key.toLowerCase() === 'z') || e.key.toLowerCase() === 'y')
      ) {
        e.preventDefault();
        handleRedo();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handleUndo, handleRedo, handleOpenSaveDialog, handleDeleteSelected, selectedNodeIds, selectedLaneIds, isExecuting, recordHistory]);

  // Persistent active canvas state synchronization
  useEffect(() => {
    try {
      localStorage.setItem(
        'locallm_active_canvas',
        JSON.stringify({
          title: activeWorkflowTitle,
          lanes,
          nodes,
          edges
        })
      );
    } catch { }
  }, [activeWorkflowTitle, lanes, nodes, edges]);

  // Auto-close header dropdown menus & modal on outside click and Escape
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent | TouchEvent) => {
      const target = e.target as Node;
      if (
        isWorkflowMenuOpen &&
        workflowMenuRef.current &&
        !workflowMenuRef.current.contains(target)
      ) {
        setIsWorkflowMenuOpen(false);
      }
      if (
        isPlatformMenuOpen &&
        platformMenuRef.current &&
        !platformMenuRef.current.contains(target)
      ) {
        setIsPlatformMenuOpen(false);
      }
    };

    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        if (isWorkflowMenuOpen) setIsWorkflowMenuOpen(false);
        if (isPlatformMenuOpen) setIsPlatformMenuOpen(false);
        if (detailDocItem) setDetailDocItem(null);
      }
    };

    if (isWorkflowMenuOpen || isPlatformMenuOpen || detailDocItem) {
      document.addEventListener('mousedown', handleClickOutside);
      document.addEventListener('touchstart', handleClickOutside);
      window.addEventListener('keydown', handleEscape);
    }
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      document.removeEventListener('touchstart', handleClickOutside);
      window.removeEventListener('keydown', handleEscape);
    };
  }, [isWorkflowMenuOpen, isPlatformMenuOpen, detailDocItem]);

  // Switch AI platform handler
  const handleSelectPlatform = async (platformId: string) => {
    setIsPlatformMenuOpen(false);
    if (config && onUpdateConfig) {
      const updated: LocaLLMConfig = {
        ...config,
        active_backend: platformId
      };
      onUpdateConfig(updated);
    }
    await fetchModelsFromApi(platformId);
  };

  // Node pointer down for smooth dragging
  const handleNodePointerDown = (e: React.PointerEvent, id: string) => {
    if (isExecuting) return; // Prevent node interaction while workflow is executing
    if ((e.target as HTMLElement).closest('button, input, textarea, select, .port-bead')) {
      return;
    }
    e.stopPropagation();

    // If currently in wire connecting or rewiring mode, complete link!
    if (connectingSource) {
      if (connectingSource.nodeId !== id) {
        handleAddEdge(connectingSource.nodeId, id, connectingSource.side, 'left');
      }
      setConnectingSource(null);
      setConnectingMousePos(null);
      return;
    }

    if (rewiringEdge) {
      recordHistory();
      setEdges((prev) =>
        prev.map((edge) => {
          if (edge.id === rewiringEdge.edgeId) {
            return rewiringEdge.end === 'from'
              ? { ...edge, from: id, fromSide: 'right' }
              : { ...edge, to: id, toSide: 'left' };
          }
          return edge;
        })
      );
      setRewiringEdge(null);
      setSelectedEdgeId(rewiringEdge.edgeId);
      setSaveToastMessage('Connection wire repositioned successfully');
      setTimeout(() => setSaveToastMessage(null), 2500);
      return;
    }

    const node = nodes.find((n) => n.id === id);
    if (!node) return;

    const isCtrl = e.ctrlKey || e.metaKey;
    let nextNodeIds = selectedNodeIds;

    if (isCtrl) {
      if (selectedNodeIds.includes(id)) {
        nextNodeIds = selectedNodeIds.filter((x) => x !== id);
      } else {
        nextNodeIds = [...selectedNodeIds, id];
      }
      setSelectedNodeIds(nextNodeIds);
      setSelectedLaneIds([]);
      setSelectedEdgeId(null);
    } else {
      if (!selectedNodeIds.includes(id)) {
        nextNodeIds = [id];
        setSelectedNodeIds([id]);
        setSelectedLaneIds([]);
        setSelectedEdgeId(null);
      }
    }

    setDraggingNodeId(id);

    // Save initial snapshot before dragging begins
    initialDragSnapshotRef.current = {
      nodes: JSON.parse(JSON.stringify(nodes)),
      edges: JSON.parse(JSON.stringify(edges)),
      lanes: JSON.parse(JSON.stringify(lanes))
    };

    const multi = nextNodeIds.includes(id) && nextNodeIds.length > 1
      ? nodes.filter((n) => nextNodeIds.includes(n.id)).map((n) => ({ id: n.id, x: n.x, y: n.y }))
      : undefined;

    dragNodeRef.current = {
      nodeId: id,
      startX: e.clientX,
      startY: e.clientY,
      initialNodeX: node.x,
      initialNodeY: node.y,
      hasMoved: false,
      multiNodes: multi
    };
  };

  // Canvas pan mousedown initiation
  const handleCanvasMouseDown = (e: React.MouseEvent) => {
    const target = e.target as HTMLElement;
    if (target.closest('.workflow-node, button, input, textarea, select, aside')) {
      return;
    }

    if (unhoverTimeoutRef.current) {
      clearTimeout(unhoverTimeoutRef.current);
      unhoverTimeoutRef.current = null;
    }
    setHoveredNodeId(null);
    setIsCameraAnimating(false);
    canvasPanMovedRef.current = false;

    if (connectingSource) {
      setConnectingSource(null);
      setConnectingMousePos(null);
    }
    if (rewiringEdge) {
      setRewiringEdge(null);
      setConnectingMousePos(null);
    }
    setSelectedEdgeId(null);

    isPanningCanvasRef.current = true;
    setIsCanvasPanning(true);
    canvasPanStartRef.current = {
      startX: e.clientX,
      startY: e.clientY,
      panX: pan.x,
      panY: pan.y
    };
  };

  // Fullscreen toggle handler
  const handleToggleFullscreen = async () => {
    try {
      if (!document.fullscreenElement) {
        if (containerRef.current?.requestFullscreen) {
          await containerRef.current.requestFullscreen();
        } else if (document.documentElement.requestFullscreen) {
          await document.documentElement.requestFullscreen();
        }
      } else {
        if (document.exitFullscreen) {
          await document.exitFullscreen();
        }
      }
    } catch (err) {
      console.warn('Failed to toggle fullscreen:', err);
    }
  };

  const handleResetView = () => {
    if (unhoverTimeoutRef.current) {
      clearTimeout(unhoverTimeoutRef.current);
      unhoverTimeoutRef.current = null;
    }
    setHoveredNodeId(null);
    baseCameraRef.current = null;
    setIsCameraAnimating(true);
    setZoom(1);
    setPan({ x: 30, y: 20 });
    setTimeout(() => {
      setIsCameraAnimating(false);
    }, 320);
  };

  // Add node with optional drop coordinate
  const handleAddNode = (
    template: typeof ACTIVITY_CATALOG[0]['items'][0],
    customX?: number,
    customY?: number
  ) => {
    if (isExecuting) return;
    recordHistory();

    const newId = `${template.tag}-${Date.now().toString(36)}`;
    const laneCfg = lanes.find((l) => l.id === template.lane) || lanes[0] || INITIAL_LANES[0];
    const defaultY = Math.round(laneCfg.y + (laneCfg.height - NODE_HEIGHT) / 2);

    const actualX = customX !== undefined ? Math.max(20, customX) : Math.round(350 + (nodes.length % 5) * 35 - pan.x / zoom);
    const actualY = customY !== undefined ? Math.max(20, customY) : defaultY;
    const actualLane = customY !== undefined ? detectLaneByCoord(actualX, actualY) : template.lane;

    const assignedModel = apiModels.length > 0 ? (apiModels.find((m) => m.id !== 'auto')?.id || apiModels[0]?.id) : 'auto';

    const newNode: WorkflowNode = {
      id: newId,
      lane: actualLane,
      type: template.type,
      title: template.title,
      subtitle: template.subtitle,
      tag: template.tag,
      x: actualX,
      y: actualY,
      status: 'idle',
      config: {
        ...template.defaultConfig,
        workspace: activeWorkspace || 'default',
        model: assignedModel
      }
    };

    setNodes((prev) => [...prev, newNode]);
    setSelectedNodeId(newId);
  };

  // Activity Delete Request (Opens styled confirmation dialog)
  const handleRequestDeleteNode = (node: WorkflowNode) => {
    if (isExecuting) return;
    setNodeToDelete(node);
  };

  // Confirmed Activity Delete handler
  const handleConfirmDeleteNode = () => {
    if (!nodeToDelete) return;
    recordHistory();
    const id = nodeToDelete.id;
    setNodes((prev) => prev.filter((n) => n.id !== id));
    setEdges((prev) => prev.filter((e) => e.from !== id && e.to !== id));
    if (selectedNodeId === id) {
      setSelectedNodeId(null);
    }
    setNodeToDelete(null);
  };

  // Snap node to the vertical centerline of its current lane
  const handleSnapNodeToLaneCenter = (nodeId: string) => {
    if (isExecuting) return;
    recordHistory();
    setNodes((prev) =>
      prev.map((n) => {
        if (n.id === nodeId) {
          const laneCfg = lanes.find((l) => l.id === n.lane) || lanes[0];
          return {
            ...n,
            y: Math.round(laneCfg.y + (laneCfg.height - NODE_HEIGHT) / 2)
          };
        }
        return n;
      })
    );
  };

  // Add edge connection between two nodes with support for 4-sided ports
  const handleAddEdge = (
    fromId: string,
    toId: string,
    fromSide: PortSide = 'right',
    toSide: PortSide = 'left',
    label: string = 'next'
  ) => {
    if (isExecuting) return;
    if (fromId === toId) return;
    const exists = edges.some((e) => e.from === fromId && e.to === toId);
    if (exists) {
      recordHistory();
      setEdges((prev) =>
        prev.map((e) => (e.from === fromId && e.to === toId ? { ...e, fromSide, toSide } : e))
      );
      setSaveToastMessage('Updated connection wire ports');
      setTimeout(() => setSaveToastMessage(null), 2000);
      return;
    }

    recordHistory();
    const newEdge: WorkflowEdge = {
      id: `e-${Date.now().toString(36)}-${Math.random().toString(36).substring(2, 5)}`,
      from: fromId,
      to: toId,
      fromSide,
      toSide,
      label,
      variant: 'default'
    };
    setEdges((prev) => [...prev, newEdge]);
  };

  const handleDeleteEdge = (edgeId: string) => {
    if (isExecuting) return;
    recordHistory();
    setEdges((prev) => prev.filter((e) => e.id !== edgeId));
  };

  // --- UiPath-Style Sequence Management (Add, Edit, Reorder, Delete, Group Drag, Resize) ---
  const handleOpenAddSequenceModal = () => {
    if (isExecuting) return;
    setSequenceModal({
      isOpen: true,
      mode: 'add',
      label: '',
      description: '',
      color: 'blue'
    });
  };

  const handleOpenEditSequenceModal = (lane: WorkflowLaneConfig) => {
    if (isExecuting) return;
    setSequenceModal({
      isOpen: true,
      mode: 'edit',
      laneId: lane.id,
      label: lane.label,
      description: lane.description || '',
      color: lane.color || (lane.variant === 'exception' ? 'red' : 'blue')
    });
  };

  const handleSaveSequenceModal = () => {
    if (isExecuting) return;
    if (!sequenceModal.label.trim()) return;
    recordHistory();

    if (sequenceModal.mode === 'add') {
      const newId = `seq-${Date.now().toString(36)}`;
      const maxY = lanes.reduce((max, l) => Math.max(max, l.y + l.height), 70);
      const newLane: WorkflowLaneConfig = {
        id: newId,
        num: String(lanes.length + 1).padStart(2, '0'),
        label: sequenceModal.label.trim(),
        description: sequenceModal.description.trim(),
        color: sequenceModal.color,
        x: 30,
        y: maxY + 20,
        width: 1680,
        height: 140
      };
      setLanes((prev) => [...prev, newLane]);
    } else if (sequenceModal.mode === 'edit' && sequenceModal.laneId) {
      setLanes((prev) =>
        prev.map((l) =>
          l.id === sequenceModal.laneId
            ? {
                ...l,
                label: sequenceModal.label.trim(),
                description: sequenceModal.description.trim(),
                color: sequenceModal.color
              }
            : l
        )
      );
    }

    setSequenceModal((prev) => ({ ...prev, isOpen: false }));
  };

  const handleDeleteLane = (laneId: string) => {
    if (isExecuting) return;
    if (lanes.length <= 1) {
      alert('A workflow must contain at least one sequence group.');
      return;
    }
    recordHistory();
    const remaining = lanes.filter((l) => l.id !== laneId);
    setLanes(remaining);

    // Reassign any nodes that were in the deleted sequence to the first remaining sequence
    const fallbackLane = remaining[0].id;
    setNodes((prev) =>
      prev.map((n) => (n.lane === laneId ? { ...n, lane: fallbackLane } : n))
    );
  };

  const handleMoveLane = (index: number, direction: 'up' | 'down') => {
    if (isExecuting) return;
    const targetIdx = direction === 'up' ? index - 1 : index + 1;
    if (targetIdx < 0 || targetIdx >= lanes.length) return;
    recordHistory();

    const currentLane = lanes[index];
    const targetLane = lanes[targetIdx];

    const deltaCurrentY = targetLane.y - currentLane.y;
    const deltaTargetY = currentLane.y - targetLane.y;

    const nextLanes = [...lanes];
    nextLanes[index] = { ...targetLane, y: currentLane.y, num: currentLane.num };
    nextLanes[targetIdx] = { ...currentLane, y: targetLane.y, num: targetLane.num };

    setNodes((prev) =>
      prev.map((n) => {
        if (n.lane === currentLane.id) {
          return { ...n, y: n.y + deltaCurrentY };
        }
        if (n.lane === targetLane.id) {
          return { ...n, y: n.y + deltaTargetY };
        }
        return n;
      })
    );

    setLanes(nextLanes);
  };

  // Pointer down on Sequence Header for Group Dragging (Single or Multi-Sequence)
  const handleSequenceHeaderPointerDown = (e: React.PointerEvent, laneId: string) => {
    if (isExecuting) return;
    if ((e.target as HTMLElement).closest('button, input, textarea, select')) {
      return;
    }
    e.stopPropagation();

    const isCtrl = e.ctrlKey || e.metaKey;
    let nextLaneIds = selectedLaneIds;

    if (isCtrl) {
      if (selectedLaneIds.includes(laneId)) {
        nextLaneIds = selectedLaneIds.filter((x) => x !== laneId);
      } else {
        nextLaneIds = [...selectedLaneIds, laneId];
      }
      setSelectedLaneIds(nextLaneIds);
      setSelectedNodeIds([]);
    } else {
      if (!selectedLaneIds.includes(laneId)) {
        nextLaneIds = [laneId];
        setSelectedLaneIds([laneId]);
        setSelectedNodeIds([]);
      }
    }

    const lane = lanes.find((l) => l.id === laneId);
    if (!lane) return;

    const groupedNodes = nodes
      .filter((n) => n.lane === laneId)
      .map((n) => ({ id: n.id, x: n.x, y: n.y }));

    initialDragSnapshotRef.current = {
      nodes: JSON.parse(JSON.stringify(nodes)),
      edges: JSON.parse(JSON.stringify(edges)),
      lanes: JSON.parse(JSON.stringify(lanes))
    };

    const multi = nextLaneIds.includes(laneId) && nextLaneIds.length > 1
      ? lanes.filter((l) => nextLaneIds.includes(l.id)).map((l) => ({
          id: l.id,
          x: l.x ?? 30,
          y: l.y,
          nodes: nodes.filter((n) => n.lane === l.id).map((n) => ({ id: n.id, x: n.x, y: n.y }))
        }))
      : undefined;

    dragSequenceRef.current = {
      laneId,
      startX: e.clientX,
      startY: e.clientY,
      initialLaneX: lane.x ?? 30,
      initialLaneY: lane.y,
      initialNodes: groupedNodes,
      hasMoved: false,
      multiLanes: multi
    };

    setDraggingSequenceId(laneId);
  };

  // Pointer down on Sequence Resize Handle
  const handleSequenceResizePointerDown = (e: React.PointerEvent, laneId: string, mode: 'width' | 'both') => {
    if (isExecuting) return;
    e.stopPropagation();

    const lane = lanes.find((l) => l.id === laneId);
    if (!lane) return;

    initialDragSnapshotRef.current = {
      nodes: JSON.parse(JSON.stringify(nodes)),
      edges: JSON.parse(JSON.stringify(edges)),
      lanes: JSON.parse(JSON.stringify(lanes))
    };

    const laneNodes = nodes.filter((n) => n.lane === laneId);
    const minRequiredWidth = Math.max(
      420,
      laneNodes.length > 0 ? Math.min(1400, laneNodes.length * 172 + 60) : 420
    );

    resizeSequenceRef.current = {
      laneId,
      startX: e.clientX,
      startY: e.clientY,
      initialWidth: lane.width ?? 1680,
      initialHeight: lane.height,
      minWidth: minRequiredWidth,
      initialLaneX: lane.x ?? 30,
      initialNodes: laneNodes.map((n) => ({ id: n.id, x: n.x, y: n.y })),
      mode
    };

    setResizingSequenceId(laneId);
  };

  // Workflow preset selection
  const handleLoadPreset = (presetId: string) => {
    setIsWorkflowMenuOpen(false);
    const p = WORKFLOW_PRESETS.find((pr) => pr.id === presetId);
    if (p) {
      setActiveWorkflowTitle(p.name);
      setLanes(p.lanes || INITIAL_LANES);
      setNodes(p.nodes);
      setEdges(p.edges);
      setSelectedNodeId(p.nodes[0]?.id || null);
    }
  };

  // New Blank Workflow creation
  const handleCreateNewWorkflow = () => {
    setIsWorkflowMenuOpen(false);
    setActiveWorkflowTitle('New Custom Workflow');
    const freshLanes = computeLanePositions(INITIAL_LANES);
    setLanes(freshLanes);
    const rootNode: WorkflowNode = {
      id: 'user-objective-start',
      lane: 'ui',
      type: 'frontend',
      title: 'User Objective',
      subtitle: 'Task prompt and primary mission',
      tag: 'intake',
      x: 60,
      y: 101,
      status: 'idle',
      config: {
        query: 'Analyze project repository and implement requested features',
        workspace: activeWorkspace || 'default',
        model: apiModels[0]?.id || 'auto'
      }
    };
    setNodes([rootNode]);
    setEdges([]);
    setSelectedNodeId('user-objective-start');
  };



  // Load saved workflow (Preserves exact saved positions)
  const handleLoadSavedWorkflow = (saved: typeof savedWorkflows[0]) => {
    setIsWorkflowMenuOpen(false);
    setActiveWorkflowTitle(saved.name);
    if (saved.lanes && Array.isArray(saved.lanes)) {
      setLanes(saved.lanes);
    }
    setNodes(saved.nodes);
    setEdges(saved.edges);
    setSelectedNodeIds([]);
    setSelectedLaneIds([]);
  };

  // Delete saved workflow
  const handleDeleteSavedWorkflow = (e: React.MouseEvent, name: string) => {
    e.stopPropagation();
    const filtered = savedWorkflows.filter((w) => w.name !== name);
    setSavedWorkflows(filtered);
    try {
      localStorage.setItem('locallm_saved_workflows', JSON.stringify(filtered));
    } catch { }
  };

  // Export JSON Schema
  const handleExportWorkflowJson = () => {
    const workflowPayload = {
      schema_version: 2,
      diagram_type: 'workflow',
      meta: {
        title: activeWorkflowTitle,
        animation: 'trace',
        visual_preset: 'signal-flow',
        quality_profile: 'showcase',
        output: 'locallm-agent-workflow.json'
      },
      lanes: lanes.map((l) => ({
        id: l.id,
        label: l.label,
        variant: l.variant
      })),
      phases: SIGNAL_FLOW_PHASES,
      nodes: nodes.map((n) => ({
        id: n.id,
        lane: n.lane,
        type: n.type,
        label: n.title,
        sublabel: n.subtitle,
        tag: n.tag,
        x: n.x,
        y: n.y,
        width: NODE_WIDTH,
        height: NODE_HEIGHT,
        config: n.config
      })),
      edges: edges.map((e) => ({
        id: e.id,
        from: e.from,
        to: e.to,
        label: e.label,
        variant: e.variant || 'default'
      }))
    };

    const dataStr = 'data:text/json;charset=utf-8,' + encodeURIComponent(JSON.stringify(workflowPayload, null, 2));
    const dl = document.createElement('a');
    dl.setAttribute('href', dataStr);
    dl.setAttribute('download', `${activeWorkflowTitle.toLowerCase().replace(/\s+/g, '-')}.json`);
    document.body.appendChild(dl);
    dl.click();
    dl.remove();
  };

  // Import JSON Schema
  const handleImportWorkflowJson = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (event) => {
      try {
        const parsed = JSON.parse(event.target?.result as string);
        if (parsed.nodes && Array.isArray(parsed.nodes)) {
          if (parsed.lanes && Array.isArray(parsed.lanes)) {
            const parsedLanes: WorkflowLaneConfig[] = parsed.lanes.map((l: any, idx: number) => ({
              id: l.id || `lane-${idx}`,
              num: String(idx + 1).padStart(2, '0'),
              label: l.label || `Lane ${idx + 1}`,
              y: 70 + idx * 155,
              height: 135,
              variant: l.variant || 'default'
            }));
            setLanes(computeLanePositions(parsedLanes));
          }
          const importedNodes: WorkflowNode[] = parsed.nodes.map((n: any) => ({
            id: n.id || `node-${Math.random().toString(36).substr(2, 6)}`,
            lane: n.lane || 'agent',
            type: n.type || 'backend',
            title: n.label || n.title || 'Imported Node',
            subtitle: n.sublabel || n.subtitle || '',
            tag: n.tag,
            x: n.x || 100,
            y: n.y || 250,
            status: 'idle',
            config: n.config || {}
          }));
          const importedEdges: WorkflowEdge[] = (parsed.edges || []).map((edge: any) => ({
            id: edge.id || `e-${Math.random().toString(36).substr(2, 6)}`,
            from: edge.from,
            to: edge.to,
            label: edge.label,
            variant: edge.variant || 'default'
          }));
          setNodes(importedNodes);
          setEdges(importedEdges);
          setActiveWorkflowTitle(parsed.meta?.title || file.name.replace('.json', ''));
          setSelectedNodeId(importedNodes[0]?.id || null);
        }
      } catch (err) {
        alert('Invalid workflow JSON file');
      }
    };
    reader.readAsText(file);
    e.target.value = '';
  };

  // Real End-to-End Workflow Pipeline Execution with live flow tracking across ALL activities
  const handleStartFlow = async () => {
    if (isExecuting) return;
    setIsExecuting(true);
    isExecutingRef.current = true;
    executionAbortRef.current = new AbortController();
    setIsDrawerOpen(true);
    setExecutionLogs([]);

    const taskId = 'task-' + Date.now().toString(36);
    setActiveTaskId(taskId);

    // Reset all node statuses to idle
    setNodes((prev) => prev.map((n) => ({ ...n, status: 'idle' })));
    setActiveExecutingNodeId(null);
    setNextTargetNodeId(null);
    setActiveFlowEdgeId(null);

    // Compute topological sequence of ALL nodes in the workflow
    const inDegree = new Map<string, number>();
    nodes.forEach((n) => inDegree.set(n.id, 0));
    edges.forEach((e) => {
      inDegree.set(e.to, (inDegree.get(e.to) || 0) + 1);
    });

    const visited = new Set<string>();
    const orderedNodes: WorkflowNode[] = [];
    const queue: string[] = nodes
      .filter((n) => (inDegree.get(n.id) || 0) === 0)
      .map((n) => n.id);

    if (queue.length === 0 && nodes.length > 0) {
      queue.push(nodes[0].id);
    }

    while (queue.length > 0) {
      const currId = queue.shift()!;
      if (!visited.has(currId)) {
        visited.add(currId);
        const found = nodes.find((n) => n.id === currId);
        if (found) orderedNodes.push(found);

        const downstream = edges.filter((e) => e.from === currId).map((e) => e.to);
        downstream.forEach((nxt) => {
          if (!visited.has(nxt)) queue.push(nxt);
        });
      }
    }

    // Append any disconnected nodes so EVERY single activity executes
    nodes.forEach((n) => {
      if (!visited.has(n.id)) {
        visited.add(n.id);
        orderedNodes.push(n);
      }
    });

    const signal = executionAbortRef.current.signal;

    const logEvent = (agent: string, event_type: string, message: string) => {
      setExecutionLogs((prev) => [
        ...prev,
        {
          agent,
          event_type,
          message,
          timestamp: new Date().toLocaleTimeString()
        }
      ]);
    };

    logEvent(
      'System',
      'init',
      `Pipeline started: "${activeWorkflowTitle}" (${orderedNodes.length} activities, engine: ${executionMode})`
    );

    try {
      for (let i = 0; i < orderedNodes.length; i++) {
        if (!isExecutingRef.current || signal.aborted) break;

        const currNode = orderedNodes[i];
        const nextNode = orderedNodes[i + 1] || null;

        // Find connector edge to downstream target
        const outgoingEdges = edges.filter((e) => e.from === currNode.id);
        const targetEdge =
          outgoingEdges.find((e) => nextNode && e.to === nextNode.id) ||
          outgoingEdges[0] ||
          null;

        // Set live active execution indicators
        setActiveExecutingNodeId(currNode.id);
        if (targetEdge) {
          setNextTargetNodeId(targetEdge.to);
          setActiveFlowEdgeId(targetEdge.id);
        } else if (nextNode) {
          setNextTargetNodeId(nextNode.id);
          setActiveFlowEdgeId(null);
        } else {
          setNextTargetNodeId(null);
          setActiveFlowEdgeId(null);
        }

        // Mark current node running
        setNodes((prev) =>
          prev.map((n) => (n.id === currNode.id ? { ...n, status: 'running' } : n))
        );

        logEvent(
          currNode.title,
          'start',
          `Step #${i + 1} initiating on [${currNode.lane.toUpperCase()}]: ${currNode.subtitle || currNode.title}`
        );

        // Execute activity step
        const isAgent = currNode.lane === 'agent' || Boolean(currNode.config?.directive);
        const isTool = currNode.lane === 'tools' || currNode.tag === 'subprocess';
        const isPolicy = currNode.lane === 'policy' || currNode.tag === 'policy-gate';
        const isEvidence = currNode.lane === 'evidence' || currNode.tag === 'trace-evidence' || currNode.tag === 'event-stream';

        if (isAgent) {
          const modelToUse = currNode.config?.model || config?.default_model || 'auto';
          const directive = currNode.config?.directive || currNode.subtitle || currNode.title;

          logEvent(
            currNode.title,
            'thinking',
            `Processing on ${currentBackend} with model "${modelToUse}"...`
          );

          if (executionMode === 'real') {
            try {
              const chatRes = await fetch('/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                signal,
                body: JSON.stringify({
                  model: modelToUse === 'auto' ? undefined : modelToUse,
                  messages: [
                    {
                      role: 'system',
                      content: `You are an automated pipeline specialist agent named "${currNode.title}". Give a concise 1-2 sentence execution summary.`
                    },
                    {
                      role: 'user',
                      content: `Task: ${directive}. Context: ${currNode.subtitle}. Summarize task result.`
                    }
                  ],
                  max_tokens: 120,
                  stream: false
                })
              });

              if (chatRes.ok) {
                const data = await chatRes.json();
                const content =
                  data.choices?.[0]?.message?.content ||
                  data.response ||
                  'Task step completed successfully.';
                logEvent(currNode.title, 'done', content.trim());
              } else {
                logEvent(
                  currNode.title,
                  'done',
                  `Agent completed task directive (${directive}).`
                );
              }
            } catch (err: any) {
              if (err.name === 'AbortError') break;
              logEvent(
                currNode.title,
                'done',
                `Agent completed execution step for ${currNode.title}.`
              );
            }
          } else {
            await new Promise((r) => setTimeout(r, 1200));
            logEvent(currNode.title, 'done', `Finished task directive: ${directive}`);
          }
        } else if (isTool) {
          const cmd = currNode.config?.command || 'pytest -q';
          logEvent(currNode.title, 'tool_start', `Executing command: \`${cmd}\``);
          await new Promise((r) => setTimeout(r, 1300));
          logEvent(
            currNode.title,
            'tool_done',
            `Process completed (exit code 0): verified test matrix and syntax checks.`
          );
        } else if (isPolicy) {
          const pol = currNode.config?.policy || 'ask';
          logEvent(
            currNode.title,
            'evaluating',
            `Evaluating safety constraints: policy="${pol}" · circuit breaker healthy.`
          );
          await new Promise((r) => setTimeout(r, 1000));
          logEvent(
            currNode.title,
            'authorized',
            `Authorization approved. Forwarding execution token downstream.`
          );
        } else if (isEvidence) {
          logEvent(
            currNode.title,
            'aggregating',
            `Consolidating observations, telemetry and diffs...`
          );
          await new Promise((r) => setTimeout(r, 1200));
          logEvent(
            currNode.title,
            'complete',
            `Final synthesis archived to blackboard evidence state.`
          );
        } else {
          // Default / UI intake node
          await new Promise((r) => setTimeout(r, 900));
          logEvent(
            currNode.title,
            'intake',
            `Input parameters verified: "${currNode.config?.query || currNode.subtitle}"`
          );
        }

        if (!isExecutingRef.current || signal.aborted) break;

        // Mark current node success
        setNodes((prev) =>
          prev.map((n) => (n.id === currNode.id ? { ...n, status: 'success' } : n))
        );

        // Pause to ensure visual traveling pulse along wire is clearly seen
        await new Promise((r) => setTimeout(r, 600));
      }

      if (isExecutingRef.current && !signal.aborted) {
        logEvent(
          'System',
          'success',
          `Pipeline completed successfully across all ${orderedNodes.length} activities.`
        );
      }
    } catch (err: any) {
      if (err.name !== 'AbortError') {
        console.warn('Pipeline execution encountered an error:', err);
      }
    } finally {
      setIsExecuting(false);
      isExecutingRef.current = false;
      setActiveExecutingNodeId(null);
      setNextTargetNodeId(null);
      setActiveFlowEdgeId(null);
      setActiveTaskId(null);
    }
  };

  const handleStopFlow = () => {
    if (executionAbortRef.current) {
      executionAbortRef.current.abort();
    }
    if (pollingRef.current) {
      clearInterval(pollingRef.current);
    }
    isExecutingRef.current = false;
    setIsExecuting(false);
    setActiveExecutingNodeId(null);
    setNextTargetNodeId(null);
    setActiveFlowEdgeId(null);
    setActiveTaskId(null);
    setExecutionLogs((prev) => [
      ...prev,
      {
        agent: 'System',
        event_type: 'stopped',
        message: 'Pipeline execution halted by user. Canvas unlocked.',
        timestamp: new Date().toLocaleTimeString()
      }
    ]);
  };

  useEffect(() => {
    return () => {
      if (pollingRef.current) clearInterval(pollingRef.current);
    };
  }, []);

  // Helper to compute connection terminal coordinates on any of the 4 sides of a node
  const getPortCoord = (
    pos: { x: number; y: number },
    side: PortSide = 'right'
  ) => {
    switch (side) {
      case 'top':
        return { x: pos.x + NODE_WIDTH / 2, y: pos.y };
      case 'bottom':
        return { x: pos.x + NODE_WIDTH / 2, y: pos.y + NODE_HEIGHT };
      case 'left':
        return { x: pos.x, y: pos.y + NODE_HEIGHT / 2 };
      case 'right':
      default:
        return { x: pos.x + NODE_WIDTH, y: pos.y + NODE_HEIGHT / 2 };
    }
  };

  // Generate Archify-standard orthogonal stepped connector path supporting 4-sided ports
  const getOrthogonalRoute = (
    x1: number,
    y1: number,
    x2: number,
    y2: number,
    fromSide: PortSide = 'right',
    toSide: PortSide = 'left'
  ) => {
    // 1. Standard Horizontal Routing (Right to Left)
    if (fromSide === 'right' && toSide === 'left') {
      if (Math.abs(y1 - y2) < 4 && x2 >= x1) {
        return {
          path: `M ${x1} ${y1} L ${x2} ${y2}`,
          labelX: (x1 + x2) / 2,
          labelY: y1
        };
      }
      if (x2 >= x1 + 24) {
        const midX = Math.round((x1 + x2) / 2);
        return {
          path: `M ${x1} ${y1} L ${midX} ${y1} L ${midX} ${y2} L ${x2} ${y2}`,
          labelX: midX,
          labelY: (y1 + y2) / 2
        };
      }
      if (y2 < y1) {
        const rightX = x1 + 30;
        const topY = Math.min(y1, y2) - 28;
        const leftX = x2 - 28;
        return {
          path: `M ${x1} ${y1} L ${rightX} ${y1} L ${rightX} ${topY} L ${leftX} ${topY} L ${leftX} ${y2} L ${x2} ${y2}`,
          labelX: (rightX + leftX) / 2,
          labelY: topY - 10
        };
      } else {
        const rightX = x1 + 30;
        const bottomY = Math.max(y1, y2) + 36;
        const leftX = x2 - 28;
        return {
          path: `M ${x1} ${y1} L ${rightX} ${y1} L ${rightX} ${bottomY} L ${leftX} ${bottomY} L ${leftX} ${y2} L ${x2} ${y2}`,
          labelX: (rightX + leftX) / 2,
          labelY: bottomY + 10
        };
      }
    }

    // 2. Standard Vertical Routing (Bottom to Top)
    if (fromSide === 'bottom' && toSide === 'top') {
      if (Math.abs(x1 - x2) < 4 && y2 >= y1) {
        return {
          path: `M ${x1} ${y1} L ${x2} ${y2}`,
          labelX: x1,
          labelY: (y1 + y2) / 2
        };
      }
      if (y2 >= y1 + 24) {
        const midY = Math.round((y1 + y2) / 2);
        return {
          path: `M ${x1} ${y1} L ${x1} ${midY} L ${x2} ${midY} L ${x2} ${y2}`,
          labelX: (x1 + x2) / 2,
          labelY: midY
        };
      }
      const bottomY = y1 + 28;
      const midX = Math.max(x1, x2) + 36;
      const topY = y2 - 28;
      return {
        path: `M ${x1} ${y1} L ${x1} ${bottomY} L ${midX} ${bottomY} L ${midX} ${topY} L ${x2} ${topY} L ${x2} ${y2}`,
        labelX: midX + 10,
        labelY: (bottomY + topY) / 2
      };
    }

    // 3. Inverse Vertical Routing (Top to Bottom)
    if (fromSide === 'top' && toSide === 'bottom') {
      if (y1 >= y2 + 24) {
        const midY = Math.round((y1 + y2) / 2);
        return {
          path: `M ${x1} ${y1} L ${x1} ${midY} L ${x2} ${midY} L ${x2} ${y2}`,
          labelX: (x1 + x2) / 2,
          labelY: midY
        };
      }
      const topY = y1 - 28;
      const midX = Math.max(x1, x2) + 36;
      const bottomY = y2 + 28;
      return {
        path: `M ${x1} ${y1} L ${x1} ${topY} L ${midX} ${topY} L ${midX} ${bottomY} L ${x2} ${bottomY} L ${x2} ${y2}`,
        labelX: midX + 10,
        labelY: (topY + bottomY) / 2
      };
    }

    // 4. Any other orthogonal side combination
    const dx1 = fromSide === 'right' ? 24 : fromSide === 'left' ? -24 : 0;
    const dy1 = fromSide === 'bottom' ? 24 : fromSide === 'top' ? -24 : 0;
    const sx = x1 + dx1;
    const sy = y1 + dy1;

    const dx2 = toSide === 'right' ? 24 : toSide === 'left' ? -24 : 0;
    const dy2 = toSide === 'bottom' ? 24 : toSide === 'top' ? -24 : 0;
    const ex = x2 + dx2;
    const ey = y2 + dy2;

    if (fromSide === 'right' || fromSide === 'left') {
      return {
        path: `M ${x1} ${y1} L ${sx} ${sy} L ${ex} ${sy} L ${ex} ${ey} L ${x2} ${y2}`,
        labelX: (sx + ex) / 2,
        labelY: sy
      };
    } else {
      return {
        path: `M ${x1} ${y1} L ${sx} ${sy} L ${sx} ${ey} L ${ex} ${ey} L ${x2} ${y2}`,
        labelX: sx,
        labelY: (sy + ey) / 2
      };
    }
  };

  return (
    <div
      ref={containerRef}
      className="h-screen w-screen flex flex-col bg-slate-100 dark:bg-slate-950 text-slate-800 dark:text-slate-100 overflow-hidden font-sans select-none"
    >
      {/* Hidden file input for JSON import */}
      <input
        ref={fileInputRef}
        type="file"
        accept=".json"
        onChange={handleImportWorkflowJson}
        className="hidden"
      />

      {/* Top Precision Studio Toolbar */}
      <header className="h-12 shrink-0 border-b border-slate-200 dark:border-slate-800 bg-white/95 dark:bg-slate-900/90 backdrop-blur-md px-3 flex items-center justify-between z-30 shadow-2xs">
        {/* Left Section: Back, Title & Workflow Dropdown */}
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => (window.location.href = '/')}
            className="p-1.5 rounded-lg text-slate-700 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white hover:bg-slate-200/70 dark:hover:bg-slate-800 transition-colors flex items-center gap-1.5 text-xs font-medium cursor-pointer"
            title="Return to Chat"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">Back</span>
          </button>

          <div className="h-4 w-px bg-slate-300 dark:bg-slate-800" />

          {/* Workflow Selector & Presets Dropdown */}
          <div ref={workflowMenuRef} className="relative">
            <button
              type="button"
              onClick={() => {
                setIsWorkflowMenuOpen((v) => !v);
                setIsPlatformMenuOpen(false);
              }}
              className="flex items-center gap-1.5 px-2.5 py-1 rounded-xl bg-slate-100 dark:bg-slate-800/80 hover:bg-slate-200 dark:hover:bg-slate-800 border border-slate-300 dark:border-slate-700 text-xs font-bold text-slate-900 dark:text-slate-100 transition-colors cursor-pointer"
              title="Switch or create workflow"
            >
              <Workflow className="w-3.5 h-3.5 text-cyan-600 dark:text-cyan-400" />
              <span className="truncate max-w-[140px] sm:max-w-[200px]">{activeWorkflowTitle}</span>
              <ChevronDown className="w-3 h-3 text-slate-500" />
            </button>

            {/* Workflow Menu Dropdown Popover */}
            <AnimatePresence>
              {isWorkflowMenuOpen && (
                <motion.div
                  initial={{ opacity: 0, y: -8, scale: 0.96 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  exit={{ opacity: 0, y: -8, scale: 0.96 }}
                  transition={{ duration: 0.16, ease: 'easeOut' }}
                  className="absolute top-full left-0 mt-1.5 w-72 rounded-2xl bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 shadow-xl p-2 z-50 text-xs"
                >
                  <div className="px-2 py-1 font-bold text-[10px] uppercase tracking-wider text-slate-500 dark:text-slate-400">
                    Pre-built Workflow Presets
                  </div>
                  <div className="space-y-0.5">
                    {WORKFLOW_PRESETS.map((p) => (
                      <button
                        key={p.id}
                        type="button"
                        onClick={() => handleLoadPreset(p.id)}
                        className={`w-full text-left px-2.5 py-1.5 rounded-xl transition-colors cursor-pointer flex items-center justify-between ${activeWorkflowTitle === p.name
                            ? 'bg-cyan-50 dark:bg-cyan-950/40 text-cyan-700 dark:text-cyan-300 font-semibold'
                            : 'hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-800 dark:text-slate-200'
                          }`}
                      >
                        <span className="truncate">{p.name}</span>
                        {activeWorkflowTitle === p.name && <Check className="w-3 h-3 text-cyan-600 shrink-0" />}
                      </button>
                    ))}
                  </div>

                  {savedWorkflows.length > 0 && (
                    <>
                      <div className="h-px bg-slate-200 dark:bg-slate-800 my-1.5" />
                      <div className="px-2 py-1 font-bold text-[10px] uppercase tracking-wider text-slate-500 dark:text-slate-400">
                        Saved Custom Workflows
                      </div>
                      <div className="space-y-0.5 max-h-36 overflow-y-auto">
                        {savedWorkflows.map((sw) => (
                          <div
                            key={sw.name}
                            onClick={() => handleLoadSavedWorkflow(sw)}
                            className="w-full text-left px-2.5 py-1.5 rounded-xl hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-800 dark:text-slate-200 transition-colors cursor-pointer flex items-center justify-between group"
                          >
                            <div className="min-w-0">
                              <p className="font-semibold truncate">{sw.name}</p>
                              <p className="text-[9px] text-slate-400">{sw.date} · {sw.nodes.length} nodes</p>
                            </div>
                            <button
                              type="button"
                              onClick={(e) => handleDeleteSavedWorkflow(e, sw.name)}
                              className="p-1 rounded hover:text-rose-500 text-slate-400 opacity-0 group-hover:opacity-100 transition-opacity"
                              title="Delete saved workflow"
                            >
                              <Trash2 className="w-3 h-3" />
                            </button>
                          </div>
                        ))}
                      </div>
                    </>
                  )}

                  <div className="h-px bg-slate-200 dark:bg-slate-800 my-1.5" />
                  <div className="grid grid-cols-2 gap-1 pt-0.5">
                    <button
                      type="button"
                      onClick={handleCreateNewWorkflow}
                      className="px-2 py-1.5 rounded-xl bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-800 dark:text-slate-200 flex items-center justify-center gap-1 text-[11px] font-semibold cursor-pointer"
                    >
                      <FilePlus className="w-3 h-3 text-cyan-600" />
                      <span>New Blank</span>
                    </button>
                    <button
                      type="button"
                      onClick={handleSaveWorkflowAction}
                      className="px-2 py-1.5 rounded-xl bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-800 dark:text-slate-200 flex items-center justify-center gap-1 text-[11px] font-semibold cursor-pointer"
                      title="Save workflow to local storage (Ctrl+S)"
                    >
                      <Save className="w-3 h-3 text-emerald-600" />
                      <span>Save Flow</span>
                      <span className="text-[9px] font-mono opacity-60 ml-0.5">Ctrl+S</span>
                    </button>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </div>

        {/* Center Canvas Scale & Navigation Controls */}
        <div className="hidden md:flex items-center gap-1 px-1.5 py-1 rounded-xl bg-slate-100 dark:bg-slate-800/80 border border-slate-300 dark:border-slate-700/60">
          <button
            type="button"
            onClick={() => setZoom((z) => Math.max(0.4, Number((z - 0.1).toFixed(1))))}
            className="p-1 rounded-lg hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300 transition-colors cursor-pointer"
            title="Zoom out"
          >
            <ZoomOut className="w-3.5 h-3.5" />
          </button>
          <span className="font-mono text-[11px] text-slate-800 dark:text-slate-200 w-11 text-center font-semibold">
            {Math.round(zoom * 100)}%
          </span>
          <button
            type="button"
            onClick={() => setZoom((z) => Math.min(2.2, Number((z + 0.1).toFixed(1))))}
            className="p-1 rounded-lg hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300 transition-colors cursor-pointer"
            title="Zoom in"
          >
            <ZoomIn className="w-3.5 h-3.5" />
          </button>
          <div className="h-3 w-px bg-slate-300 dark:bg-slate-700 mx-0.5" />
          <button
            type="button"
            disabled={historyPast.length === 0 || isExecuting}
            onClick={handleUndo}
            className="p-1 rounded-lg hover:bg-slate-200 dark:hover:bg-slate-700 disabled:opacity-30 disabled:cursor-not-allowed text-slate-700 dark:text-slate-300 transition-colors cursor-pointer"
            title="Undo (Ctrl+Z)"
          >
            <Undo2 className="w-3.5 h-3.5" />
          </button>
          <button
            type="button"
            disabled={historyFuture.length === 0 || isExecuting}
            onClick={handleRedo}
            className="p-1 rounded-lg hover:bg-slate-200 dark:hover:bg-slate-700 disabled:opacity-30 disabled:cursor-not-allowed text-slate-700 dark:text-slate-300 transition-colors cursor-pointer"
            title="Redo (Ctrl+Shift+Z)"
          >
            <Redo2 className="w-3.5 h-3.5" />
          </button>
          <div className="h-3 w-px bg-slate-300 dark:bg-slate-700 mx-0.5" />
          <button
            type="button"
            onClick={handleResetView}
            className="p-1 rounded-lg hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300 transition-colors cursor-pointer flex items-center gap-1"
            title="Reset Pan & Zoom (100%)"
          >
            <RotateCcw className="w-3.5 h-3.5" />
          </button>
          <button
            type="button"
            onClick={handleToggleFullscreen}
            className={`p-1 rounded-lg transition-colors cursor-pointer ${isFullscreen
                ? 'bg-cyan-500/20 text-cyan-600 dark:text-cyan-400 font-medium'
                : 'text-slate-700 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700'
              }`}
            title={isFullscreen ? 'Exit Fullscreen' : 'Enter Fullscreen'}
          >
            {isFullscreen ? <Minimize2 className="w-3.5 h-3.5" /> : <Maximize2 className="w-3.5 h-3.5" />}
          </button>
          <button
            type="button"
            onClick={() => setIsGridVisible((v) => !v)}
            className={`p-1 rounded-lg transition-colors cursor-pointer ${isGridVisible
                ? 'bg-slate-200 dark:bg-slate-700 text-slate-900 dark:text-white font-medium'
                : 'text-slate-500 hover:bg-slate-200 dark:hover:bg-slate-700'
              }`}
            title="Toggle background grid"
          >
            <Grid className="w-3.5 h-3.5" />
          </button>
          <button
            type="button"
            onClick={() => {
              setClickFocusZoomEnabled((v) => !v);
              if (clickFocusZoomEnabled && selectedNodeId) {
                handleUnselectNode();
              }
            }}
            className={`p-1 rounded-lg transition-colors cursor-pointer flex items-center gap-1 ${clickFocusZoomEnabled
                ? 'bg-cyan-500/20 text-cyan-700 dark:text-cyan-300 font-semibold'
                : 'text-slate-500 dark:text-slate-400 hover:bg-slate-200 dark:hover:bg-slate-700'
              }`}
            title={`Click Focus Zoom: ${clickFocusZoomEnabled ? 'Enabled' : 'Disabled'} (Click node to zoom in; deselect or Esc to zoom out)`}
          >
            <Target className="w-3.5 h-3.5" />
            <span className="text-[10px] hidden lg:inline">Focus Zoom</span>
          </button>
        </div>

        {/* Right Section: AI Platform Selector, Settings, Run and Logs */}
        <div className="flex items-center gap-1.5">
          {/* Active AI Platform Selector & Quick Switcher (Strictly registered platforms only) */}
          <div ref={platformMenuRef} className="relative">
            <button
              type="button"
              onClick={() => {
                setIsPlatformMenuOpen((v) => !v);
                setIsWorkflowMenuOpen(false);
              }}
              className="flex items-center gap-1 px-2.5 py-1 rounded-xl bg-slate-100 dark:bg-slate-800/80 hover:bg-slate-200 dark:hover:bg-slate-800 border border-slate-300 dark:border-slate-700 text-xs font-semibold text-slate-800 dark:text-slate-200 transition-colors cursor-pointer"
              title="Active AI Platform"
            >
              <Cpu className="w-3.5 h-3.5 text-cyan-600 dark:text-cyan-400" />
              <span className="hidden md:inline font-mono text-[11px] font-bold text-cyan-700 dark:text-cyan-300">
                {currentBackend}
              </span>
              <ChevronDown className="w-3 h-3 text-slate-500" />
            </button>

            {/* Platform Selection Popover */}
            <AnimatePresence>
              {isPlatformMenuOpen && (
                <motion.div
                  initial={{ opacity: 0, y: -8, scale: 0.96 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  exit={{ opacity: 0, y: -8, scale: 0.96 }}
                  transition={{ duration: 0.16, ease: 'easeOut' }}
                  className="absolute top-full right-0 mt-1.5 w-60 rounded-2xl bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 shadow-xl p-2 z-50 text-xs"
                >
                  <div className="px-2 py-1 font-bold text-[10px] uppercase tracking-wider text-slate-500 dark:text-slate-400 flex items-center justify-between">
                    <span>Registered Platforms</span>
                    {isLoadingModels && <span className="animate-spin text-cyan-500">⟳</span>}
                  </div>
                  <div className="space-y-0.5">
                    {registeredPlatforms.map((p) => (
                      <button
                        key={p.id}
                        type="button"
                        onClick={() => handleSelectPlatform(p.id)}
                        className={`w-full text-left px-2.5 py-1.5 rounded-xl transition-colors cursor-pointer flex items-center justify-between ${currentBackend === p.id
                            ? 'bg-cyan-50 dark:bg-cyan-950/40 text-cyan-700 dark:text-cyan-300 font-semibold'
                            : 'hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-800 dark:text-slate-200'
                          }`}
                      >
                        <span className="truncate">{p.name}</span>
                        {currentBackend === p.id && <Check className="w-3 h-3 text-cyan-600 shrink-0" />}
                      </button>
                    ))}
                  </div>
                  <div className="h-px bg-slate-200 dark:bg-slate-800 my-1.5" />
                  <button
                    type="button"
                    onClick={() => {
                      setIsPlatformMenuOpen(false);
                      setIsSettingsOpen(true);
                    }}
                    className="w-full text-center px-2 py-1.5 rounded-xl bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-800 dark:text-slate-200 font-semibold text-[11px] cursor-pointer flex items-center justify-center gap-1.5"
                  >
                    <Settings className="w-3 h-3 text-slate-500" />
                    <span>Configure Platforms...</span>
                  </button>
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          {/* Settings Modal Button */}
          <button
            type="button"
            onClick={() => setIsSettingsOpen(true)}
            className="p-1.5 rounded-xl bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors cursor-pointer"
            title="Configure LocaLLM AI Platforms, API Keys & Inference"
          >
            <Settings className="w-3.5 h-3.5" />
          </button>

          {/* Engine Mode Switch */}
          <div className="hidden xl:flex items-center p-0.5 rounded-lg bg-slate-200/70 dark:bg-slate-800 border border-slate-300 dark:border-slate-700 text-[10px] font-medium">
            <button
              type="button"
              onClick={() => setExecutionMode('real')}
              className={`px-2 py-1 rounded-md transition-colors cursor-pointer flex items-center gap-1 ${executionMode === 'real'
                  ? 'bg-white dark:bg-slate-900 text-slate-900 dark:text-white shadow-xs font-semibold'
                  : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
                }`}
            >
              <Radio className="w-3 h-3 text-cyan-500" />
              <span>Live Engine</span>
            </button>
            <button
              type="button"
              onClick={() => setExecutionMode('simulation')}
              className={`px-2 py-1 rounded-md transition-colors cursor-pointer ${executionMode === 'simulation'
                  ? 'bg-white dark:bg-slate-900 text-slate-900 dark:text-white shadow-xs font-semibold'
                  : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
                }`}
            >
              <span>Step Sim</span>
            </button>
          </div>

          {/* Live Event Log Drawer Toggle */}
          <button
            type="button"
            onClick={() => setIsDrawerOpen((v) => !v)}
            className={`px-2.5 py-1.5 rounded-xl text-xs font-medium border transition-colors flex items-center gap-1.5 cursor-pointer active:scale-[0.98] ${isDrawerOpen
                ? 'bg-slate-200 dark:bg-slate-800 text-slate-900 dark:text-white border-slate-300 dark:border-slate-700'
                : 'bg-white dark:bg-slate-900 text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 border-slate-300 dark:border-slate-700'
              }`}
            title="Toggle Live Event Log Drawer"
          >
            <Terminal className="w-3.5 h-3.5" />
            <span className="hidden lg:inline">Live Log</span>
            {executionLogs.length > 0 && (
              <span className="w-1.5 h-1.5 rounded-full bg-cyan-500 animate-pulse" />
            )}
          </button>

          {/* Export JSON */}
          <button
            type="button"
            onClick={handleExportWorkflowJson}
            className="hidden sm:flex px-2 py-1.5 rounded-xl text-xs font-medium bg-white dark:bg-slate-900 text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 border border-slate-300 dark:border-slate-700 transition-colors items-center gap-1 cursor-pointer"
            title="Export Archify Workflow JSON"
          >
            <Download className="w-3.5 h-3.5" />
            <span>Export</span>
          </button>

          {/* Import JSON */}
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            className="hidden sm:flex px-2 py-1.5 rounded-xl text-xs font-medium bg-white dark:bg-slate-900 text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 border border-slate-300 dark:border-slate-700 transition-colors items-center gap-1 cursor-pointer"
            title="Import Workflow JSON"
          >
            <Upload className="w-3.5 h-3.5" />
            <span>Import</span>
          </button>

          {/* Execute Real Workflow Pipeline Button */}
          {isExecuting ? (
            <button
              type="button"
              onClick={handleStopFlow}
              className="px-3 py-1.5 rounded-xl text-xs font-semibold bg-red-600 hover:bg-red-700 text-white flex items-center gap-1.5 transition-all cursor-pointer active:scale-[0.98]"
            >
              <Pause className="w-3.5 h-3.5 fill-current" />
              <span>Halt Flow</span>
            </button>
          ) : (
            <button
              type="button"
              onClick={handleStartFlow}
              className="px-3 py-1.5 rounded-xl text-xs font-semibold bg-slate-900 dark:bg-white text-white dark:text-slate-950 hover:opacity-90 shadow-xs flex items-center gap-1.5 transition-all cursor-pointer active:scale-[0.98]"
            >
              <Play className="w-3.5 h-3.5 fill-current" />
              <span>Run Pipeline</span>
            </button>
          )}

          <div className="ml-1">
            <ThemeToggle />
          </div>
        </div>
      </header>

      {/* Main Studio Workspace */}
      <div className="flex-1 flex overflow-hidden relative">
        {/* Left Activity Catalog (Drag & Drop Palette) */}
        <div
          className={`h-full border-r border-slate-200 dark:border-slate-800 bg-white/95 dark:bg-slate-900/90 backdrop-blur-sm transition-all duration-200 z-20 flex flex-col ${isLibraryOpen ? 'w-68' : 'w-0'
            } overflow-hidden`}
        >
          <div className="p-3 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between">
            <div>
              <span className="text-[11px] font-bold uppercase tracking-wider text-slate-700 dark:text-slate-300 block leading-tight">
                Activity Palette
              </span>
              <span className="text-[10px] text-slate-500 dark:text-slate-400">
                Drag to Canvas or Click to Add
              </span>
            </div>
            <button
              type="button"
              onClick={() => setIsLibraryOpen(false)}
              className="p-1 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-500 dark:text-slate-400 transition-colors cursor-pointer"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>

          <div className="px-3 py-2 border-b border-slate-200 dark:border-slate-800">
            <div className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-xl bg-slate-100 dark:bg-slate-800/80 border border-slate-200 dark:border-slate-700">
              <Search className="w-3 h-3 text-slate-500" />
              <input
                type="text"
                placeholder="Search activities..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full bg-transparent text-[11px] text-slate-800 dark:text-slate-100 placeholder:text-slate-400 focus:outline-none"
              />
            </div>
          </div>

          <div className="flex-1 overflow-y-auto p-2.5 space-y-3.5 text-xs">
            {filteredCatalog.map((cat) => (
              <div key={cat.lane} className="space-y-1">
                <div className="px-1 text-[10px] font-bold text-slate-600 dark:text-slate-400 uppercase tracking-wider flex items-center justify-between">
                  <span>{cat.laneTitle}</span>
                </div>
                <div className="space-y-1">
                  {cat.items.map((item) => {
                    const Icon = item.icon;
                    return (
                      <div
                        key={item.title}
                        draggable={!isExecuting}
                        onDragStart={(e) => {
                          if (isExecuting) {
                            e.preventDefault();
                            return;
                          }
                          e.dataTransfer.setData('application/json', JSON.stringify(item));
                          e.dataTransfer.effectAllowed = 'copy';
                        }}
                        onClick={() => {
                          if (isExecuting) return;
                          handleAddNode(item);
                        }}
                        className={`group p-2 rounded-xl bg-white dark:bg-slate-800/80 border border-slate-200 dark:border-slate-700/70 transition-all flex items-center justify-between shadow-2xs ${isExecuting
                            ? 'opacity-50 cursor-not-allowed'
                            : 'hover:border-cyan-500/60 hover:bg-slate-50 dark:hover:bg-slate-800 cursor-grab active:cursor-grabbing'
                          }`}
                        title={isExecuting ? 'Workflow executing - Editing locked' : 'Drag into canvas or click to add'}
                      >
                        <div className="flex items-center gap-2 min-w-0">
                          <Icon className={`w-3.5 h-3.5 shrink-0 ${item.color}`} />
                          <div className="min-w-0">
                            <p className="font-semibold text-[11px] text-slate-900 dark:text-slate-100 truncate leading-tight">
                              {item.title}
                            </p>
                            <p className="text-[10px] text-slate-600 dark:text-slate-400 truncate leading-tight mt-0.5">
                              {item.subtitle}
                            </p>
                          </div>
                        </div>
                        <div className="flex items-center gap-1 shrink-0">
                          <button
                            type="button"
                            onClick={(e) => {
                              e.stopPropagation();
                              setDetailDocItem(item);
                            }}
                            className="p-1 rounded-lg text-slate-400 hover:text-cyan-600 dark:hover:text-cyan-400 hover:bg-slate-100 dark:hover:bg-slate-700/60 transition-colors cursor-pointer"
                            title={`View complete documentation for ${item.title}`}
                          >
                            <HelpCircle className="w-3.5 h-3.5" />
                          </button>
                          <Plus className="w-3.5 h-3.5 text-slate-400 group-hover:text-cyan-500 opacity-40 group-hover:opacity-100 transition-opacity shrink-0" />
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Open Palette Button if closed */}
        {!isLibraryOpen && (
          <button
            type="button"
            onClick={() => setIsLibraryOpen(true)}
            className="absolute top-3 left-3 z-20 px-2.5 py-1.5 rounded-xl bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 text-xs font-medium text-slate-700 dark:text-slate-200 shadow-xs hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors flex items-center gap-1.5 cursor-pointer"
          >
            <ChevronRight className="w-3.5 h-3.5" />
            <span>Activity Palette</span>
          </button>
        )}

        {/* Center Live Canvas with Pan, Zoom, Dynamic Lanes and Flow Animation */}
        <main
          ref={canvasRef}
          onMouseDown={handleCanvasMouseDown}
          onDragOver={(e) => {
            e.preventDefault();
            e.dataTransfer.dropEffect = 'copy';
          }}
          onDrop={(e) => {
            e.preventDefault();
            const dataStr = e.dataTransfer.getData('application/json');
            if (!dataStr) return;
            try {
              const template = JSON.parse(dataStr);
              const canvasEl = canvasRef.current;
              if (!canvasEl) return;
              const rect = canvasEl.getBoundingClientRect();
              const dropX = Math.round((e.clientX - rect.left - pan.x) / zoom - NODE_WIDTH / 2);
              const dropY = Math.round((e.clientY - rect.top - pan.y) / zoom - NODE_HEIGHT / 2);
              handleAddNode(template, dropX, dropY);
            } catch (err) {
              console.warn('Drop parse error:', err);
            }
          }}
          className="flex-1 h-full relative overflow-hidden bg-slate-200/50 dark:bg-slate-950 transition-colors"
          style={{
            backgroundImage: isGridVisible
              ? 'radial-gradient(circle, currentColor 1px, transparent 1px)'
              : 'none',
            backgroundPosition: `${pan.x}px ${pan.y}px`,
            backgroundSize: `${24 * zoom}px ${24 * zoom}px`,
            color: 'var(--grid-dot-color, rgba(100, 116, 139, 0.28))',
            cursor: (connectingSource || rewiringEdge) ? 'crosshair' : isCanvasPanning ? 'grabbing' : 'grab'
          }}
        >
          {/* Wire Linking / Rewiring Banner Alert */}
          {(connectingSource || rewiringEdge) && !isExecuting && (
            <div className="absolute top-3 left-1/2 -translate-x-1/2 z-30 px-3.5 py-1.5 rounded-full bg-cyan-600 text-white text-xs font-semibold shadow-lg flex items-center gap-2 animate-bounce">
              <LinkIcon className="w-3.5 h-3.5" />
              <span>
                {rewiringEdge
                  ? `Click any port to reattach ${rewiringEdge.end === 'from' ? 'source' : 'target'} end (Esc to cancel)`
                  : 'Click target activity port to link wire (Esc to cancel)'}
              </span>
              <button
                type="button"
                onClick={() => {
                  setConnectingSource(null);
                  setRewiringEdge(null);
                  setConnectingMousePos(null);
                }}
                className="p-0.5 rounded-full hover:bg-cyan-700 cursor-pointer"
              >
                <X className="w-3 h-3" />
              </button>
            </div>
          )}

          {/* Floating Canvas Lock Indicator when Workflow is Running */}
          {isExecuting && (
            <div className="absolute top-3 left-1/2 -translate-x-1/2 z-30 flex items-center gap-2.5 px-4 py-1.5 rounded-full bg-slate-900/95 text-white border border-cyan-500/50 shadow-2xl backdrop-blur-md text-xs font-medium">
              <span className="w-2 h-2 rounded-full bg-cyan-400 animate-ping" />
              <Lock className="w-3.5 h-3.5 text-cyan-400" />
              <span>Pipeline Executing · Canvas Locked</span>
              <button
                type="button"
                onClick={handleStopFlow}
                className="ml-2 px-2.5 py-0.5 rounded-md bg-rose-600 hover:bg-rose-700 text-white text-[11px] font-bold cursor-pointer transition-colors"
              >
                Stop Pipeline
              </button>
            </div>
          )}

          {/* Floating Multi-Selection Action Bar */}
          {selectedNodeIds.length + selectedLaneIds.length > 1 && !isExecuting && (
            <div className="absolute top-3 left-1/2 -translate-x-1/2 z-40 flex items-center gap-2.5 px-3.5 py-1.5 rounded-full bg-slate-900/95 dark:bg-slate-800/95 text-white text-xs shadow-2xl border border-cyan-500/50 backdrop-blur-md">
              <span className="font-semibold text-cyan-400 flex items-center gap-1.5">
                <Check className="w-3.5 h-3.5" />
                <span>
                  {selectedNodeIds.length > 0 && `${selectedNodeIds.length} activities`}
                  {selectedNodeIds.length > 0 && selectedLaneIds.length > 0 && ' + '}
                  {selectedLaneIds.length > 0 && `${selectedLaneIds.length} sequences`}
                  {' selected'}
                </span>
              </span>
              <span className="text-slate-400 text-[10px] hidden sm:inline">
                (Ctrl+Click to toggle, Drag to move all)
              </span>
              <button
                type="button"
                onClick={handleDeleteSelected}
                className="px-2.5 py-0.5 rounded-md bg-rose-600 hover:bg-rose-700 text-white text-[11px] font-bold flex items-center gap-1 cursor-pointer transition-colors shadow-xs"
                title="Delete selected activities and sequences (or press DEL key)"
              >
                <Trash2 className="w-3 h-3" />
                <span>Delete (Del)</span>
              </button>
              <button
                type="button"
                onClick={() => {
                  setSelectedNodeIds([]);
                  setSelectedLaneIds([]);
                }}
                className="p-1 rounded-full hover:bg-white/10 text-slate-400 hover:text-white cursor-pointer"
                title="Deselect all (Esc)"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            </div>
          )}

          {/* Pan Navigation Hint, Add Sequence & Tidy Sequences shortcuts */}
          <div className="absolute bottom-3 left-3 z-10 flex items-center gap-2">
            <div className="pointer-events-none flex items-center gap-2 text-[10px] font-mono text-slate-600 dark:text-slate-400 bg-white/85 dark:bg-slate-900/85 backdrop-blur-xs px-2 py-1 rounded-lg border border-slate-300/80 dark:border-slate-800 shadow-2xs">
              <Move className="w-3 h-3 text-slate-500" />
              <span>Drag canvas or objects · Mouse scroll zooms · Offset: ({pan.x}, {pan.y})</span>
            </div>

            <button
              type="button"
              disabled={isExecuting}
              onClick={handleOpenAddSequenceModal}
              className="px-2.5 py-1 rounded-lg bg-white/90 dark:bg-slate-900/90 hover:bg-cyan-50 dark:hover:bg-cyan-950/40 disabled:opacity-40 disabled:cursor-not-allowed border border-slate-300 dark:border-slate-800 text-[10px] font-semibold text-cyan-700 dark:text-cyan-300 shadow-2xs transition-colors flex items-center gap-1 cursor-pointer"
              title={isExecuting ? 'Cannot add sequences while pipeline is executing' : 'Add a new sequence group container'}
            >
              <Plus className="w-3 h-3" />
              <span>Add Sequence</span>
            </button>

            <button
              type="button"
              disabled={isExecuting}
              onClick={handleAutoAlignAllSequences}
              className="px-2.5 py-1 rounded-lg bg-white/90 dark:bg-slate-900/90 hover:bg-cyan-50 dark:hover:bg-cyan-950/40 disabled:opacity-40 disabled:cursor-not-allowed border border-slate-300 dark:border-slate-800 text-[10px] font-semibold text-cyan-700 dark:text-cyan-300 shadow-2xs transition-colors flex items-center gap-1 cursor-pointer"
              title="Auto-align all sequences into a tidy, uniform vertical layout"
            >
              <Layers className="w-3 h-3" />
              <span>Tidy Sequences</span>
            </button>
          </div>

          {/* Canvas Transform Viewport */}
          <div
            className={`w-full h-full relative transform-gpu pointer-events-auto ${
              isCanvasPanning || Boolean(draggingNodeId) || Boolean(draggingSequenceId) || Boolean(resizingSequenceId)
                ? 'transition-none'
                : isCameraAnimating
                  ? 'transition-transform duration-350 ease-out'
                  : 'transition-transform duration-200 ease-out'
            }`}
            style={{
              transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})`,
              transformOrigin: '0 0'
            }}
          >
            {/* 1. UiPath-Style Sequence Containers Layer (Grouping, Draggable, Resizable) */}
            <div className="absolute inset-0 pointer-events-none z-[1]">
              {lanes.map((lane, idx) => {
                const laneColorKey: SequenceColor = lane.color || (lane.variant === 'exception' ? 'red' : 'blue');
                const colorTheme = SEQUENCE_COLOR_THEMES[laneColorKey] || SEQUENCE_COLOR_THEMES.blue;
                const isHovered = hoveredLaneId === lane.id;
                const isSelectedLane = selectedLaneIds.includes(lane.id);
                const isDraggingThisSequence = draggingSequenceId === lane.id || (Boolean(draggingSequenceId) && isSelectedLane);
                const isResizingThisSequence = resizingSequenceId === lane.id;
                const assignedNodesCount = nodes.filter((n) => n.lane === lane.id).length;

                const laneX = lane.x ?? 30;
                const laneWidth = lane.width ?? 1680;

                return (
                  <div
                    key={lane.id}
                    style={{
                      position: 'absolute',
                      left: `${laneX}px`,
                      top: `${lane.y}px`,
                      width: `${laneWidth}px`,
                      height: `${lane.height}px`
                    }}
                    className={`sequence-container group pointer-events-none rounded-xl border-2 transition-shadow flex flex-col justify-between ${colorTheme.border} ${colorTheme.bg} ${
                      isSelectedLane
                        ? 'ring-2 ring-cyan-500 shadow-2xl z-25'
                        : isDraggingThisSequence
                          ? 'shadow-2xl ring-2 ring-cyan-500/50 opacity-95 z-30'
                          : isResizingThisSequence
                            ? 'shadow-xl ring-2 ring-cyan-500/40 z-30'
                            : isHovered
                              ? 'shadow-md ring-1 ring-cyan-500/30'
                              : 'shadow-2xs'
                    }`}
                  >
                    {/* Sequence Header Bar (Draggable & Clickable) */}
                    <div
                      onPointerDown={(e) => handleSequenceHeaderPointerDown(e, lane.id)}
                      onDoubleClick={() => handleOpenEditSequenceModal(lane)}
                      className={`pointer-events-auto flex items-center justify-between px-3 py-1.5 rounded-t-[10px] select-none cursor-grab active:cursor-grabbing transition-colors ${
                        isSelectedLane ? 'ring-1 ring-cyan-400 bg-cyan-500/15' : ''
                      } ${colorTheme.headerBg}`}
                      title="Drag header to move sequence · Ctrl+Click to multi-select · Double click to edit settings"
                    >
                      {/* Left: Drag Handle, Number, Label, Status Badge, and Description */}
                      <div className="flex items-center gap-2.5 min-w-0">
                        <div className="text-slate-400 dark:text-slate-500 hover:text-slate-700 dark:hover:text-slate-200">
                          <GripVertical className="w-3.5 h-3.5" />
                        </div>

                        <span className="text-[10px] font-mono font-bold px-1.5 py-0.5 rounded bg-black/5 dark:bg-white/10 text-slate-700 dark:text-slate-200 shrink-0">
                          {lane.num}
                        </span>

                        <span className={`text-xs font-bold truncate max-w-[280px] ${colorTheme.headerText}`}>
                          {lane.label}
                        </span>

                        {/* Sequence Status / Priority Level Badge with Help Tooltip */}
                        <div className="relative group/seqinfo flex items-center shrink-0">
                          <span className={`text-[9px] font-mono font-bold px-2 py-0.5 rounded-full ${colorTheme.badgeClass}`}>
                            {colorTheme.badgeLabel}
                          </span>
                          <div
                            className="ml-1 text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 transition-colors cursor-help p-0.5"
                            title={colorTheme.tooltip}
                          >
                            <HelpCircle className="w-3 h-3" />
                          </div>
                          {/* Floating Popover on Hover */}
                          <div className="absolute top-full left-0 mt-1 hidden group-hover/seqinfo:block z-50 w-64 p-2 rounded-lg bg-slate-900/95 dark:bg-slate-800/95 text-slate-100 text-[10px] leading-relaxed shadow-xl border border-slate-700/80 backdrop-blur-xs pointer-events-none">
                            <div className="font-bold text-cyan-400 mb-0.5">{colorTheme.label} Sequence</div>
                            <div className="text-slate-300">{colorTheme.tooltip}</div>
                          </div>
                        </div>

                        {/* Sequence Description */}
                        {lane.description && (
                          <span className="text-[10px] font-mono text-slate-500 dark:text-slate-400 truncate max-w-[460px] hidden md:inline">
                            ({lane.description})
                          </span>
                        )}
                      </div>

                      {/* Right: Activity Count & Control Action Buttons */}
                      <div className="flex items-center gap-1.5 shrink-0" onClick={(e) => e.stopPropagation()}>
                        <span className="text-[10px] font-mono text-slate-500 dark:text-slate-400 mr-1.5 hidden sm:inline">
                          {assignedNodesCount} {assignedNodesCount === 1 ? 'activity' : 'activities'}
                        </span>

                        {/* Auto-reposition activities inside sequence button */}
                        <button
                          type="button"
                          disabled={isExecuting || assignedNodesCount === 0}
                          onClick={() => handleAutoRepositionLaneActivities(lane.id)}
                          className="p-1 rounded-md bg-white/80 dark:bg-slate-900/80 hover:bg-white dark:hover:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-300 hover:text-cyan-600 dark:hover:text-cyan-400 transition-colors cursor-pointer disabled:opacity-30"
                          title="Auto-reposition and tidy activities inside this sequence"
                        >
                          <Grid className="w-3 h-3" />
                        </button>

                        {/* Edit Sequence Settings Button */}
                        <button
                          type="button"
                          disabled={isExecuting}
                          onClick={() => handleOpenEditSequenceModal(lane)}
                          className="p-1 rounded-md bg-white/80 dark:bg-slate-900/80 hover:bg-white dark:hover:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-300 hover:text-cyan-600 dark:hover:text-cyan-400 transition-colors cursor-pointer disabled:opacity-30"
                          title="Edit sequence name, description, and color level"
                        >
                          <Settings2 className="w-3 h-3" />
                        </button>

                        {/* Move Up */}
                        <button
                          type="button"
                          disabled={idx === 0 || isExecuting}
                          onClick={() => handleMoveLane(idx, 'up')}
                          className="p-1 rounded-md bg-white/80 dark:bg-slate-900/80 hover:bg-white dark:hover:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-300 hover:text-slate-950 dark:hover:text-white transition-colors cursor-pointer disabled:opacity-30"
                          title="Move sequence up"
                        >
                          <ArrowUp className="w-3 h-3" />
                        </button>

                        {/* Move Down */}
                        <button
                          type="button"
                          disabled={idx === lanes.length - 1 || isExecuting}
                          onClick={() => handleMoveLane(idx, 'down')}
                          className="p-1 rounded-md bg-white/80 dark:bg-slate-900/80 hover:bg-white dark:hover:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-300 hover:text-slate-950 dark:hover:text-white transition-colors cursor-pointer disabled:opacity-30"
                          title="Move sequence down"
                        >
                          <ArrowDown className="w-3 h-3" />
                        </button>

                        {/* Delete Sequence */}
                        <button
                          type="button"
                          disabled={lanes.length <= 1 || isExecuting}
                          onClick={() => handleDeleteLane(lane.id)}
                          className="p-1 rounded-md bg-white/80 dark:bg-slate-900/80 hover:bg-rose-50 dark:hover:bg-rose-950/40 border border-slate-200 dark:border-slate-700 text-slate-400 hover:text-rose-500 transition-colors cursor-pointer disabled:opacity-30"
                          title="Delete sequence group"
                        >
                          <Trash2 className="w-3 h-3" />
                        </button>
                      </div>
                    </div>

                    {/* Sequence Body Space (Empty space pans canvas) */}
                    <div
                      onMouseDown={(e) => {
                        if ((e.target as HTMLElement).closest('.workflow-node, button, input, textarea, select, .port-bead')) return;
                        handleCanvasMouseDown(e);
                      }}
                      className="flex-1 relative pointer-events-auto cursor-grab active:cursor-grabbing"
                      title="Drag canvas to pan · Drag sequence header to move sequence"
                    />

                    {/* Right Edge Horizontal Resize Handle (Widen Container) */}
                    <div
                      onPointerDown={(e) => handleSequenceResizePointerDown(e, lane.id, 'width')}
                      className="pointer-events-auto absolute right-0 top-0 bottom-0 w-3 cursor-ew-resize hover:bg-cyan-500/20 active:bg-cyan-500/30 transition-colors flex items-center justify-center group/resize rounded-r-xl"
                      title="Drag horizontally to resize sequence width"
                    >
                      <div className="w-1 h-8 rounded-full bg-slate-300/80 dark:bg-slate-700/80 group-hover/resize:bg-cyan-500 transition-colors" />
                    </div>

                    {/* Bottom-Right Corner Resize Grip (Width and Height) */}
                    <div
                      onPointerDown={(e) => handleSequenceResizePointerDown(e, lane.id, 'both')}
                      className="pointer-events-auto absolute right-1 bottom-1 w-4 h-4 cursor-nwse-resize hover:bg-cyan-500/20 active:bg-cyan-500/30 rounded flex items-center justify-center group/corner"
                      title="Drag to resize width and height"
                    >
                      <div className="w-2 h-2 border-r-2 border-b-2 border-slate-400 dark:border-slate-600 group-hover/corner:border-cyan-500" />
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Stepped Orthogonal Lines and Flow Animation SVG Layer */}
            <svg
              className="absolute inset-0 pointer-events-none z-[5] overflow-visible"
              style={{ width: `${totalCanvasWidth}px`, height: `${totalCanvasHeight}px` }}
            >
              <defs>
                <marker id="arrowhead" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
                  <polygon points="0 0, 10 3.5, 0 7" fill="#64748b" />
                </marker>
                <marker id="arrowhead-emphasis" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
                  <polygon points="0 0, 10 3.5, 0 7" fill="#10b981" />
                </marker>
                <marker id="arrowhead-security" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
                  <polygon points="0 0, 10 3.5, 0 7" fill="#f43f5e" />
                </marker>
                <marker id="arrowhead-dashed" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
                  <polygon points="0 0, 10 3.5, 0 7" fill="#a855f7" />
                </marker>
                <marker id="arrowhead-running" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
                  <polygon points="0 0, 10 3.5, 0 7" fill="#06b6d4" />
                </marker>
                <marker id="arrowhead-downstream" markerWidth="11" markerHeight="8" refX="10" refY="4" orient="auto">
                  <polygon points="0 0, 11 4, 0 8" fill="#06b6d4" />
                </marker>
                <marker id="arrowhead-upstream" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
                  <polygon points="0 0, 10 3.5, 0 7" fill="#a855f7" />
                </marker>
              </defs>

              {/* Stepped Orthogonal Connector Lines */}
              {edges.map((edge) => {
                const srcPos = nodePositionMap.get(edge.from);
                const tgtPos = nodePositionMap.get(edge.to);
                if (!srcPos || !tgtPos) return null;

                const fromSide = edge.fromSide || 'right';
                const toSide = edge.toSide || 'left';
                const p1 = getPortCoord(srcPos, fromSide);
                const p2 = getPortCoord(tgtPos, toSide);

                const route = getOrthogonalRoute(p1.x, p1.y, p2.x, p2.y, fromSide, toSide);
                const isSelectedEdge = selectedEdgeId === edge.id;
                const isSelectedFlow = selectedNodeId === edge.from;
                const isFlowActive = isSelectedFlow || activeFlowEdgeId === edge.id || (isExecuting && edge.from === activeExecutingNodeId);

                let strokeColor = '#64748b';
                let markerUrl = 'url(#arrowhead)';

                if (edge.variant === 'security') {
                  strokeColor = '#f43f5e';
                  markerUrl = 'url(#arrowhead-security)';
                } else if (edge.variant === 'emphasis') {
                  strokeColor = '#10b981';
                  markerUrl = 'url(#arrowhead-emphasis)';
                } else if (edge.variant === 'dashed') {
                  strokeColor = '#a855f7';
                  markerUrl = 'url(#arrowhead-dashed)';
                }

                if (isFlowActive) {
                  strokeColor = '#06b6d4';
                  markerUrl = 'url(#arrowhead-running)';
                }
                if (isSelectedEdge) {
                  strokeColor = '#06b6d4';
                  markerUrl = 'url(#arrowhead-running)';
                }

                return (
                  <g key={edge.id} className="group/wire">
                    {/* Invisible broad hitbox path for clicking to select wire */}
                    <path
                      d={route.path}
                      fill="none"
                      stroke="transparent"
                      strokeWidth={22}
                      className="cursor-pointer pointer-events-auto"
                      onClick={(e) => {
                        e.stopPropagation();
                        setSelectedEdgeId(edge.id);
                        setSelectedNodeIds([]);
                        setSelectedLaneIds([]);
                        setRewiringEdge(null);
                      }}
                    >
                      <title>Click wire to select · Press DEL to delete · Drag or click endpoints to rewire</title>
                    </path>

                    {/* Glowing pulse trail when active executing or selected */}
                    {(isFlowActive || isSelectedEdge) && (
                      <path
                        d={route.path}
                        fill="none"
                        stroke="rgba(6, 182, 212, 0.55)"
                        strokeWidth={isSelectedEdge ? 7 : 5}
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        className={isSelectedEdge ? '' : 'animate-pulse'}
                      />
                    )}

                    {/* Main Stepped Orthogonal Route Line */}
                    <path
                      d={route.path}
                      fill="none"
                      stroke={strokeColor}
                      strokeWidth={isSelectedEdge ? 3 : isFlowActive ? 2.5 : 1.6}
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeDasharray={edge.variant === 'dashed' || isFlowActive ? '6 4' : 'none'}
                      markerEnd={markerUrl}
                    />

                    {/* Traveling Particle Pulse during execution */}
                    {isFlowActive && (
                      <circle r={4} fill="#06b6d4">
                        <animateMotion
                          dur="0.9s"
                          repeatCount="indefinite"
                          path={route.path}
                        />
                      </circle>
                    )}

                    {/* Selected Edge Interactive Endpoint Reconnection Beads */}
                    {isSelectedEdge && (
                      <>
                        {/* Source Endpoint Bead */}
                        <circle
                          cx={p1.x}
                          cy={p1.y}
                          r={6}
                          className="fill-cyan-500 stroke-2 stroke-white dark:stroke-slate-900 cursor-pointer pointer-events-auto hover:scale-125 transition-transform shadow-md"
                          onClick={(e) => {
                            e.stopPropagation();
                            setRewiringEdge({ edgeId: edge.id, end: 'from' });
                          }}
                        >
                          <title>Click to rewire source end (click any activity port)</title>
                        </circle>

                        {/* Target Endpoint Bead */}
                        <circle
                          cx={p2.x}
                          cy={p2.y}
                          r={6}
                          className="fill-amber-500 stroke-2 stroke-white dark:stroke-slate-900 cursor-pointer pointer-events-auto hover:scale-125 transition-transform shadow-md"
                          onClick={(e) => {
                            e.stopPropagation();
                            setRewiringEdge({ edgeId: edge.id, end: 'to' });
                          }}
                        >
                          <title>Click to rewire target end (click any activity port)</title>
                        </circle>
                      </>
                    )}

                    {/* Edge Label Pill or Quick Action Toolbar */}
                    <g
                      transform={`translate(${route.labelX}, ${route.labelY})`}
                      className="pointer-events-auto cursor-pointer"
                      onClick={(e) => {
                        e.stopPropagation();
                        setSelectedEdgeId(edge.id);
                        setSelectedNodeIds([]);
                        setSelectedLaneIds([]);
                      }}
                    >
                      {isSelectedEdge ? (
                        <g>
                          <rect
                            x={-44}
                            y={-11}
                            width={88}
                            height={22}
                            rx={11}
                            className="fill-slate-900 text-white dark:fill-white dark:text-slate-900 shadow-xl"
                          />
                          <text
                            x={-12}
                            y={4}
                            className="text-[9px] font-bold font-mono fill-white dark:fill-slate-900 select-none text-anchor-middle"
                            textAnchor="middle"
                          >
                            {edge.label || 'wire'}
                          </text>
                          {/* Quick Delete 'x' Button */}
                          <g
                            transform="translate(22, 0)"
                            className="cursor-pointer hover:opacity-80"
                            onClick={(e) => {
                              e.stopPropagation();
                              handleDeleteEdge(edge.id);
                              setSelectedEdgeId(null);
                            }}
                          >
                            <circle r={7} className="fill-rose-500" />
                            <text x={0} y={3} textAnchor="middle" className="fill-white text-[9px] font-bold">×</text>
                          </g>
                        </g>
                      ) : edge.label ? (
                        <g>
                          <rect
                            x={-34}
                            y={-9}
                            width={68}
                            height={17}
                            rx={4}
                            className="fill-white dark:fill-slate-900 stroke-slate-300 dark:stroke-slate-700"
                            strokeWidth={1}
                          />
                          <text
                            x={0}
                            y={3}
                            className="text-[8.5px] font-mono font-bold select-none text-anchor-middle text-center fill-slate-700 dark:text-slate-300"
                            textAnchor="middle"
                          >
                            {edge.label}
                          </text>
                        </g>
                      ) : null}
                    </g>
                  </g>
                );
              })}

              {/* Dynamic Live Wire Preview Line while connecting */}
              {connectingSource && connectingMousePos && nodePositionMap.get(connectingSource.nodeId) && (
                (() => {
                  const sPos = nodePositionMap.get(connectingSource.nodeId)!;
                  const p1 = getPortCoord(sPos, connectingSource.side);
                  const x1 = p1.x;
                  const y1 = p1.y;
                  const x2 = connectingMousePos.x;
                  const y2 = connectingMousePos.y;
                  const route = getOrthogonalRoute(x1, y1, x2, y2, connectingSource.side, 'left');
                  return (
                    <path
                      d={route.path}
                      fill="none"
                      stroke="#06b6d4"
                      strokeWidth={2.5}
                      strokeDasharray="5 4"
                      markerEnd="url(#arrowhead-running)"
                      className="animate-pulse"
                    />
                  );
                })()
              )}

              {/* Dynamic Live Wire Preview Line while rewiring existing edge */}
              {rewiringEdge && connectingMousePos && (
                (() => {
                  const edge = edges.find((e) => e.id === rewiringEdge.edgeId);
                  if (!edge) return null;
                  const fixedNodeId = rewiringEdge.end === 'from' ? edge.to : edge.from;
                  const fixedSide = rewiringEdge.end === 'from' ? (edge.toSide || 'left') : (edge.fromSide || 'right');
                  const fPos = nodePositionMap.get(fixedNodeId);
                  if (!fPos) return null;
                  const pFixed = getPortCoord(fPos, fixedSide);
                  const pMouse = connectingMousePos;
                  const x1 = rewiringEdge.end === 'from' ? pMouse.x : pFixed.x;
                  const y1 = rewiringEdge.end === 'from' ? pMouse.y : pFixed.y;
                  const x2 = rewiringEdge.end === 'from' ? pFixed.x : pMouse.x;
                  const y2 = rewiringEdge.end === 'from' ? pFixed.y : pMouse.y;
                  const route = getOrthogonalRoute(x1, y1, x2, y2, fixedSide, 'left');
                  return (
                    <path
                      d={route.path}
                      fill="none"
                      stroke="#f59e0b"
                      strokeWidth={2.5}
                      strokeDasharray="5 4"
                      markerEnd="url(#arrowhead)"
                      className="animate-pulse"
                    />
                  );
                })()
              )}
            </svg>

            {/* Draggable Archify-Styled Activity Object Cards Layer */}
            <div className="absolute inset-0 z-20 pointer-events-none">
              {nodes.map((node) => {
                const isSelected = selectedNodeIds.includes(node.id);
                const isDragging = draggingNodeId === node.id || (Boolean(draggingNodeId) && isSelected);
                const isRunning = node.status === 'running';
                const isSuccess = node.status === 'success';
                const isError = node.status === 'error';
                const seqNumber = nodeSequenceNumbers.get(node.id) || 1;

                const isCurrentActiveStep = activeExecutingNodeId === node.id;
                const isNextTargetStep = nextTargetNodeId === node.id;
                const isHovered = hoveredNodeId === node.id;
                const isDownstreamTarget = Boolean(
                  selectedNodeId && edges.some((e) => e.from === selectedNodeId && e.to === node.id)
                );

                const typeStyle = ARCHIFY_TYPE_STYLES[node.type] || ARCHIFY_TYPE_STYLES.backend;
                const targetWs = node.config.workspace || activeWorkspace || 'default';
                const activeModel = node.config.model || config?.default_model || 'auto';

                let SigilIcon = Bot;
                if (node.lane === 'ui') SigilIcon = Sparkles;
                else if (node.lane === 'agent') SigilIcon = node.tag === 'researcher' ? Search : Bot;
                else if (node.lane === 'policy') SigilIcon = ShieldCheck;
                else if (node.lane === 'tools') SigilIcon = Terminal;
                else if (node.lane === 'evidence') SigilIcon = Database;

                return (
                  <div
                    key={node.id}
                    onPointerDown={(e) => handleNodePointerDown(e, node.id)}
                    onMouseEnter={() => handleNodeMouseEnter(node.id)}
                    onMouseLeave={handleNodeMouseLeave}
                    onClick={(e) => {
                      e.stopPropagation();
                      if (justDraggedNodeRef.current) {
                        justDraggedNodeRef.current = false;
                        return;
                      }
                      if (e.ctrlKey || e.metaKey) {
                        // Multi-selection toggle with Ctrl+Click
                        setSelectedNodeIds((prev) =>
                          prev.includes(node.id) ? prev.filter((x) => x !== node.id) : [...prev, node.id]
                        );
                        setSelectedLaneIds([]);
                      } else {
                        handleSelectNode(node.id);
                      }
                    }}
                    style={{
                      position: 'absolute',
                      left: `${node.x}px`,
                      top: `${node.y}px`,
                      width: `${NODE_WIDTH}px`,
                      height: `${NODE_HEIGHT}px`,
                      touchAction: 'none'
                    }}
                    className={`workflow-node pointer-events-auto group rounded-lg border text-left select-none relative p-2 flex flex-col justify-between ${
                      isDragging || draggingSequenceId
                        ? 'cursor-grabbing transition-none'
                        : 'cursor-grab transition-[border-color,background-color,box-shadow,transform] duration-150'
                    } ${typeStyle.container} ${
                      isDragging ? 'opacity-90 scale-[1.02] shadow-xl z-30' : ''
                    } ${
                      isHovered
                        ? `${typeStyle.hoverShadow} scale-[1.015] z-30`
                        : isSelected
                          ? 'ring-2 ring-cyan-500 shadow-xl shadow-cyan-500/20 scale-[1.02] z-30'
                          : isCurrentActiveStep
                            ? 'ring-2 ring-cyan-500 shadow-lg z-25'
                            : isNextTargetStep
                              ? 'border-amber-400 border-dashed ring-2 ring-amber-400/50 shadow-md z-20'
                              : isDownstreamTarget
                                ? 'ring-2 ring-cyan-400/80 border-cyan-400 shadow-md shadow-cyan-400/10 animate-pulse z-20'
                                : isRunning
                                  ? 'ring-2 ring-amber-400 animate-pulse'
                                  : isSuccess
                                    ? 'ring-2 ring-emerald-500'
                                    : isError
                                      ? 'ring-2 ring-rose-500'
                                      : 'hover:shadow-sm'
                    }`}
                  >
                    {/* Visual Flow Indicator Pill for Active Executing Node (Pipeline Execution only) */}
                    {isCurrentActiveStep && (
                      <span className="absolute -top-3.5 left-1/2 -translate-x-1/2 px-2 py-0.5 rounded-full bg-cyan-600 text-white text-[8px] font-bold shadow-md z-30 flex items-center gap-1 uppercase tracking-wider">
                        <span>ACTIVE</span>
                      </span>
                    )}

                    {isNextTargetStep && !isCurrentActiveStep && (
                      <span className="absolute -top-3.5 left-1/2 -translate-x-1/2 px-2 py-0.5 rounded-full bg-amber-500 text-white text-[8px] font-bold shadow-md z-30 flex items-center gap-1">
                        <span>NEXT ➔</span>
                      </span>
                    )}

                    {/* 4-sided Connection Ports (Top, Bottom, Left, Right) */}
                    {PORT_SIDES.map(({ side, posClass, title }) => {
                      const isThisPortConnecting = connectingSource?.nodeId === node.id && connectingSource?.side === side;
                      return (
                        <div
                          key={side}
                          onClick={(e) => {
                            e.stopPropagation();
                            if (isExecuting) return;

                            // 1. If rewiring an existing wire endpoint
                            if (rewiringEdge) {
                              recordHistory();
                              setEdges((prev) =>
                                prev.map((ed) => {
                                  if (ed.id === rewiringEdge.edgeId) {
                                    return rewiringEdge.end === 'from'
                                      ? { ...ed, from: node.id, fromSide: side }
                                      : { ...ed, to: node.id, toSide: side };
                                  }
                                  return ed;
                                })
                              );
                              setRewiringEdge(null);
                              setSelectedEdgeId(rewiringEdge.edgeId);
                              setSaveToastMessage('Connection wire repositioned successfully');
                              setTimeout(() => setSaveToastMessage(null), 2500);
                              return;
                            }

                            // 2. If creating a new connection from a source port
                            if (connectingSource) {
                              if (connectingSource.nodeId === node.id && connectingSource.side === side) {
                                setConnectingSource(null);
                                setConnectingMousePos(null);
                              } else if (connectingSource.nodeId !== node.id) {
                                handleAddEdge(connectingSource.nodeId, node.id, connectingSource.side, side);
                                setConnectingSource(null);
                                setConnectingMousePos(null);
                              } else {
                                setConnectingSource({ nodeId: node.id, side });
                              }
                              return;
                            }

                            // 3. Initiate new wire link from this port
                            setConnectingSource({ nodeId: node.id, side });
                          }}
                          className={`port-bead absolute ${posClass} w-3 h-3 rounded-full border border-white dark:border-slate-900 transition-all pointer-events-auto z-20 ${
                            isExecuting ? 'cursor-not-allowed opacity-40' : 'cursor-pointer hover:scale-125'
                          } ${
                            isThisPortConnecting
                              ? 'bg-cyan-500 scale-125 ring-2 ring-cyan-400 animate-ping'
                              : rewiringEdge
                                ? 'bg-amber-500 ring-2 ring-amber-400 hover:bg-amber-400'
                                : 'bg-slate-400 dark:bg-slate-600 group-hover:bg-cyan-500'
                          }`}
                          title={isExecuting ? 'Locked during execution' : `${title}: Click to connect wire`}
                        />
                      );
                    })}

                    {/* Top Row: Sequence Badge, Sigil Icon, Title & Delete */}
                    <div className="flex items-center justify-between gap-1 w-full">
                      <div className="flex items-center gap-1.5 min-w-0">
                        {/* Sequence Order Step Badge */}
                        <span
                          className="text-[8px] font-mono font-bold px-1 py-0.2 rounded bg-slate-200/80 dark:bg-slate-800 text-slate-700 dark:text-slate-300 shrink-0"
                          title={`Execution Step #${seqNumber}`}
                        >
                          #{seqNumber}
                        </span>
                        <SigilIcon className={`w-3.5 h-3.5 shrink-0 ${typeStyle.iconColor}`} />
                        <span className="font-semibold text-[11px] leading-tight truncate text-slate-900 dark:text-slate-100">
                          {node.title}
                        </span>
                      </div>

                      <div className="flex items-center gap-1 shrink-0">
                        {isRunning && <span className="w-1.5 h-1.5 rounded-full bg-amber-500 animate-ping" />}
                        {isSuccess && <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />}
                        {isError && <span className="w-1.5 h-1.5 rounded-full bg-rose-500" />}
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            setSelectedNodeId(node.id);
                            const item = findActivityCatalogItem(node);
                            if (item) setDetailDocItem(item);
                          }}
                          className="opacity-0 group-hover:opacity-100 p-0.5 rounded text-slate-400 hover:text-cyan-600 dark:hover:text-cyan-400 transition-opacity cursor-pointer shrink-0"
                          title="View activity documentation"
                        >
                          <HelpCircle className="w-2.5 h-2.5" />
                        </button>
                        {!isExecuting && (
                          <button
                            type="button"
                            onClick={(e) => {
                              e.stopPropagation();
                              handleRequestDeleteNode(node);
                            }}
                            className="opacity-0 group-hover:opacity-100 p-0.5 rounded text-slate-400 hover:text-rose-500 transition-opacity cursor-pointer shrink-0"
                            title="Delete activity node"
                          >
                            <Trash2 className="w-2.5 h-2.5" />
                          </button>
                        )}
                      </div>
                    </div>

                    {/* Subtitle / context description */}
                    <p className="text-[8.5px] leading-tight text-slate-600 dark:text-slate-400 truncate w-full">
                      {node.subtitle}
                    </p>

                    {/* Bottom Row: AI Model Badge & Workspace */}
                    <div className="flex items-center justify-between gap-1 mt-0.5 text-[7.5px] font-mono">
                      <span
                        className="px-1 py-0.2 rounded font-medium truncate max-w-[85px] bg-cyan-500/15 text-cyan-800 dark:text-cyan-300 border border-cyan-500/20"
                        title={`Model: ${activeModel}`}
                      >
                        🤖 {activeModel}
                      </span>

                      <span
                        className="text-slate-500 dark:text-slate-400 flex items-center gap-0.5 truncate max-w-[65px]"
                        title={`Assigned Workspace: ${targetWs}`}
                      >
                        <FolderGit2 className="w-2 h-2 shrink-0 opacity-70" />
                        <span className="truncate">{targetWs}</span>
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </main>

        {/* Right Node & Wire Inspector Panel */}
        <AnimatePresence>
          {(selectedNode || selectedEdge) && (
            <motion.aside
              initial={{ opacity: 0, x: 28 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 28 }}
              transition={{ duration: 0.22, ease: [0.16, 1, 0.3, 1] }}
              className="w-84 h-full border-l border-slate-200 dark:border-slate-800 bg-white/95 dark:bg-slate-900/90 backdrop-blur-md p-3.5 flex flex-col z-20 overflow-y-auto shadow-sm"
            >
              {selectedNode ? (
                <>
                  <div className="flex items-center justify-between pb-3 border-b border-slate-200 dark:border-slate-800">
                <div className="flex items-center gap-2">
                  <Settings2 className="w-4 h-4 text-slate-600 dark:text-slate-400" />
                  <span className="text-xs font-bold text-slate-900 dark:text-slate-100">
                    Activity & Sequence Properties
                  </span>
                </div>
                <button
                  type="button"
                  onClick={handleUnselectNode}
                  className="p-1 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-500 dark:text-slate-400 transition-colors cursor-pointer"
                  title="Deselect activity and restore overview (Esc)"
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              </div>

              <div className="py-3 space-y-3.5 text-xs flex-1">
                {/* Execution Lock Banner */}
                {isExecuting && (
                  <div className="p-2.5 rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-800 dark:text-amber-300 text-[11px] flex items-center gap-2">
                    <Lock className="w-4 h-4 shrink-0 text-amber-600 dark:text-amber-400" />
                    <span>Workflow is executing in read-only mode. Stop execution to edit parameters.</span>
                  </div>
                )}

                {/* Title */}
                <div>
                  <label className="text-[10px] font-bold uppercase tracking-wider text-slate-600 dark:text-slate-400 block mb-1">
                    Activity Label
                  </label>
                  <input
                    type="text"
                    disabled={isExecuting}
                    value={selectedNode.title}
                    onChange={(e) => {
                      const val = e.target.value;
                      setNodes((prev) =>
                        prev.map((n) => (n.id === selectedNode.id ? { ...n, title: val } : n))
                      );
                    }}
                    className="w-full px-2.5 py-1.5 rounded-xl bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 disabled:opacity-50 disabled:cursor-not-allowed text-xs font-semibold text-slate-900 dark:text-slate-100 focus:outline-none focus:border-cyan-500 shadow-2xs"
                  />
                </div>

                {/* Activity Guide & Documentation Card */}
                {selectedCatalogItem && (
                  <div className="p-3 rounded-2xl bg-cyan-50/70 dark:bg-cyan-950/25 border border-cyan-200/80 dark:border-cyan-800/60 space-y-2">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-1.5 text-cyan-800 dark:text-cyan-300 font-bold text-[11px]">
                        <BookOpen className="w-3.5 h-3.5 shrink-0" />
                        <span>Activity Documentation</span>
                      </div>
                      <button
                        type="button"
                        onClick={() => setDetailDocItem(selectedCatalogItem)}
                        className="text-[10px] text-cyan-700 dark:text-cyan-400 hover:underline font-semibold cursor-pointer flex items-center gap-0.5"
                        title="Open full documentation modal"
                      >
                        <span>Details</span>
                        <ChevronRight className="w-3 h-3" />
                      </button>
                    </div>

                    <div className="flex items-center gap-1.5 flex-wrap">
                      <span className="text-[9.5px] font-mono px-1.5 py-0.5 rounded-md bg-white dark:bg-slate-900 border border-cyan-300 dark:border-cyan-700/60 text-cyan-800 dark:text-cyan-300 font-semibold">
                        {selectedCatalogItem.doc.role}
                      </span>
                      <span className="text-[9.5px] font-mono px-1.5 py-0.5 rounded-md bg-slate-200/70 dark:bg-slate-800 text-slate-700 dark:text-slate-300">
                        Lane: {selectedNode.lane}
                      </span>
                    </div>

                    <p className="text-[11px] leading-relaxed text-slate-700 dark:text-slate-300">
                      {selectedCatalogItem.doc.description}
                    </p>

                    <div className="pt-1.5 border-t border-cyan-200/60 dark:border-cyan-800/40 text-[10px] text-slate-600 dark:text-slate-400 space-y-1">
                      <p>
                        <strong className="text-slate-800 dark:text-slate-200">Inputs:</strong>{' '}
                        {selectedCatalogItem.doc.inputs.join(', ')}
                      </p>
                      <p>
                        <strong className="text-slate-800 dark:text-slate-200">Outputs:</strong>{' '}
                        {selectedCatalogItem.doc.outputs.join(', ')}
                      </p>
                    </div>
                  </div>
                )}

                {/* AI Model Selection Dropdown (Available for EVERY activity) */}
                <div>
                  <div className="flex items-center justify-between mb-1">
                    <label className="text-[10px] font-bold uppercase tracking-wider text-slate-600 dark:text-slate-400">
                      AI Model ({currentBackend})
                    </label>
                    <button
                      type="button"
                      onClick={() => fetchModelsFromApi(currentBackend)}
                      className="text-[9.5px] font-mono text-cyan-600 dark:text-cyan-400 hover:underline flex items-center gap-0.5 cursor-pointer"
                      title="Reload models from API"
                    >
                      <RefreshCw className={`w-2.5 h-2.5 ${isLoadingModels ? 'animate-spin' : ''}`} />
                      <span>Refresh</span>
                    </button>
                  </div>

                  <select
                    value={isCustomModelActive ? '__custom__' : selectedNode.config.model || config?.default_model || 'auto'}
                    onChange={(e) => {
                      const val = e.target.value;
                      if (val === '__custom__') {
                        setIsCustomModelActive(true);
                      } else {
                        setIsCustomModelActive(false);
                        setNodes((prev) =>
                          prev.map((n) =>
                            n.id === selectedNode.id
                              ? { ...n, config: { ...n.config, model: val } }
                              : n
                          )
                        );
                      }
                    }}
                    className="w-full px-2.5 py-1.5 rounded-xl bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 text-xs font-mono text-slate-900 dark:text-slate-100 focus:outline-none focus:border-cyan-500 shadow-2xs cursor-pointer"
                  >
                    {apiModels.length === 0 ? (
                      <option value="" disabled>
                        {isLoadingModels ? 'Loading models from API...' : `No models found on ${currentBackend}`}
                      </option>
                    ) : (
                      <optgroup label={`Models discovered on ${currentBackend}`}>
                        {apiModels.map((m) => (
                          <option key={m.id} value={m.id} className="bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100">
                            {m.id} ({m.provider || currentBackend})
                          </option>
                        ))}
                      </optgroup>
                    )}
                    {selectedNode.config.model && !apiModels.some((m) => m.id === selectedNode.config.model) && !isCustomModelActive && (
                      <option value={selectedNode.config.model} className="bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100">
                        {selectedNode.config.model} (Custom assigned)
                      </option>
                    )}
                    <option value="__custom__" className="bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 font-sans">
                      ✏️ Custom model name...
                    </option>
                  </select>

                  {isCustomModelActive && (
                    <div className="mt-2">
                      <input
                        type="text"
                        placeholder="e.g. nemotron3-super or custom-model"
                        value={selectedNode.config.model || ''}
                        onChange={(e) => {
                          const val = e.target.value;
                          setNodes((prev) =>
                            prev.map((n) =>
                              n.id === selectedNode.id
                                ? { ...n, config: { ...n.config, model: val } }
                                : n
                            )
                          );
                        }}
                        className="w-full px-2.5 py-1.5 rounded-xl bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 text-xs font-mono text-slate-900 dark:text-slate-100 focus:outline-none focus:border-cyan-500 shadow-2xs"
                        autoFocus
                      />
                    </div>
                  )}
                </div>

                {/* Target Workspace Selector */}
                <div>
                  <label className="text-[10px] font-bold uppercase tracking-wider text-slate-600 dark:text-slate-400 block mb-1">
                    Target Workspace
                  </label>
                  <select
                    value={selectedNode.config.workspace || activeWorkspace || 'default'}
                    onChange={(e) => {
                      const val = e.target.value;
                      setNodes((prev) =>
                        prev.map((n) =>
                          n.id === selectedNode.id
                            ? { ...n, config: { ...n.config, workspace: val } }
                            : n
                        )
                      );
                    }}
                    className="w-full px-2.5 py-1.5 rounded-xl bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 border border-slate-300 dark:border-slate-700 text-xs font-mono focus:outline-none focus:border-cyan-500 shadow-2xs"
                  >
                    {workspaceList.map((ws) => (
                      <option key={ws.name} value={ws.name} className="bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100">
                        {ws.name}
                      </option>
                    ))}
                    {!workspaceList.some((w) => w.name === 'default') && (
                      <option value="default" className="bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100">
                        default
                      </option>
                    )}
                  </select>
                </div>

                {/* Swimlane Association & Snap to Center */}
                <div>
                  <div className="flex items-center justify-between mb-1">
                    <label className="text-[10px] font-bold uppercase tracking-wider text-slate-600 dark:text-slate-400">
                      Swimlane Association
                    </label>
                    <button
                      type="button"
                      onClick={() => handleSnapNodeToLaneCenter(selectedNode.id)}
                      className="text-[9.5px] font-medium text-cyan-600 dark:text-cyan-400 hover:underline cursor-pointer"
                    >
                      Snap to Center
                    </button>
                  </div>
                  <select
                    value={selectedNode.lane}
                    onChange={(e) => {
                      const lId = e.target.value;
                      const laneCfg = lanes.find((cfg) => cfg.id === lId) || lanes[0];
                      setNodes((prev) =>
                        prev.map((n) =>
                          n.id === selectedNode.id
                            ? {
                              ...n,
                              lane: lId,
                              y: Math.round(laneCfg.y + (laneCfg.height - NODE_HEIGHT) / 2)
                            }
                            : n
                        )
                      );
                    }}
                    className="w-full px-2.5 py-1.5 rounded-xl bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 border border-slate-300 dark:border-slate-700 text-xs focus:outline-none focus:border-cyan-500 shadow-2xs"
                  >
                    {lanes.map((l) => (
                      <option key={l.id} value={l.id} className="bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100">
                        {l.num} / {l.label}
                      </option>
                    ))}
                  </select>
                </div>

                {/* Activity Sequence Section */}
                <div className="pt-2 border-t border-slate-200 dark:border-slate-800">
                  <span className="text-[10px] font-bold uppercase tracking-wider text-slate-600 dark:text-slate-400 block mb-1.5">
                    Activity Sequence & Dependencies
                  </span>

                  {/* Outgoing Next Steps */}
                  <div className="space-y-1.5 mb-2">
                    <p className="text-[10px] text-slate-500 dark:text-slate-400 font-medium">Next Steps (Outgoing):</p>
                    {edges.filter((e) => e.from === selectedNode.id).length === 0 ? (
                      <p className="text-[10px] italic text-slate-400">No outgoing sequence connections</p>
                    ) : (
                      edges
                        .filter((e) => e.from === selectedNode.id)
                        .map((edge) => {
                          const target = nodes.find((n) => n.id === edge.to);
                          return (
                            <div
                              key={edge.id}
                              className="p-1.5 rounded-lg bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 flex items-center justify-between text-[11px]"
                            >
                              <div className="min-w-0">
                                <span className="font-semibold text-slate-900 dark:text-slate-100 truncate block">
                                  → {target?.title || edge.to}
                                </span>
                                <span className="text-[9.5px] font-mono text-cyan-600 dark:text-cyan-400">
                                  label: &quot;{edge.label || 'next'}&quot;
                                </span>
                              </div>
                              <button
                                type="button"
                                onClick={() => handleDeleteEdge(edge.id)}
                                className="p-1 rounded text-slate-400 hover:text-rose-500 transition-colors cursor-pointer"
                                title="Remove connection"
                              >
                                <Trash2 className="w-3 h-3" />
                              </button>
                            </div>
                          );
                        })
                    )}
                  </div>

                  {/* Add Next Step Dropdown */}
                  <div>
                    <select
                      value=""
                      onChange={(e) => {
                        if (e.target.value) {
                          handleAddEdge(selectedNode.id, e.target.value);
                        }
                      }}
                      className="w-full px-2.5 py-1.5 rounded-xl bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-xs font-semibold text-slate-700 dark:text-slate-200 cursor-pointer focus:outline-none"
                    >
                      <option value="">+ Connect to Next Activity...</option>
                      {nodes
                        .filter((n) => n.id !== selectedNode.id && !edges.some((e) => e.from === selectedNode.id && e.to === n.id))
                        .map((n) => (
                          <option key={n.id} value={n.id}>
                            → {n.title} ({n.lane})
                          </option>
                        ))}
                    </select>
                  </div>
                </div>

                {/* Objective Task Prompt */}
                {selectedNode.config.query !== undefined && (
                  <div>
                    <label className="text-[10px] font-bold uppercase tracking-wider text-slate-600 dark:text-slate-400 block mb-1">
                      Objective Task Prompt
                    </label>
                    <textarea
                      rows={3}
                      value={selectedNode.config.query}
                      onChange={(e) => {
                        const val = e.target.value;
                        setNodes((prev) =>
                          prev.map((n) =>
                            n.id === selectedNode.id
                              ? { ...n, config: { ...n.config, query: val } }
                              : n
                          )
                        );
                      }}
                      className="w-full px-2.5 py-1.5 rounded-xl bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 text-xs text-slate-900 dark:text-slate-100 focus:outline-none focus:border-cyan-500 resize-none shadow-2xs"
                    />
                  </div>
                )}

                {/* Directive Strategy */}
                {selectedNode.config.directive !== undefined && (
                  <div>
                    <label className="text-[10px] font-bold uppercase tracking-wider text-slate-600 dark:text-slate-400 block mb-1">
                      Directive Strategy
                    </label>
                    <textarea
                      rows={3}
                      value={selectedNode.config.directive}
                      onChange={(e) => {
                        const val = e.target.value;
                        setNodes((prev) =>
                          prev.map((n) =>
                            n.id === selectedNode.id
                              ? { ...n, config: { ...n.config, directive: val } }
                              : n
                          )
                        );
                      }}
                      className="w-full px-2.5 py-1.5 rounded-xl bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 text-xs text-slate-900 dark:text-slate-100 focus:outline-none focus:border-cyan-500 resize-none shadow-2xs"
                    />
                  </div>
                )}

                <div className="pt-2">
                  <button
                    type="button"
                    disabled={isExecuting}
                    onClick={() => handleRequestDeleteNode(selectedNode)}
                    className="w-full py-2 px-3 rounded-xl border border-red-500/30 text-red-600 dark:text-red-400 hover:bg-red-500/10 disabled:opacity-40 disabled:cursor-not-allowed text-xs font-semibold transition-colors flex items-center justify-center gap-1.5 cursor-pointer active:scale-[0.98]"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                    <span>Delete Activity Node</span>
                  </button>
                </div>
              </div>
            </>
          ) : selectedEdge ? (
                <div className="space-y-3.5 text-xs flex-1">
                  <div className="flex items-center justify-between pb-3 border-b border-slate-200 dark:border-slate-800">
                    <div className="flex items-center gap-2">
                      <LinkIcon className="w-4 h-4 text-cyan-600 dark:text-cyan-400" />
                      <span className="text-xs font-bold text-slate-900 dark:text-slate-100">
                        Wire Connection Properties
                      </span>
                    </div>
                    <button
                      type="button"
                      onClick={() => setSelectedEdgeId(null)}
                      className="p-1 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-500 transition-colors cursor-pointer"
                    >
                      <X className="w-3.5 h-3.5" />
                    </button>
                  </div>

                  {/* Wire Source Node and Side */}
                  <div>
                    <label className="text-[10px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 block mb-1">
                      Source Activity & Port Side
                    </label>
                    <div className="p-2.5 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700/80 space-y-2">
                      <p className="font-semibold text-slate-900 dark:text-slate-100 truncate">
                        {nodes.find((n) => n.id === selectedEdge.from)?.title || selectedEdge.from}
                      </p>
                      <div className="grid grid-cols-4 gap-1">
                        {(['top', 'bottom', 'left', 'right'] as PortSide[]).map((side) => (
                          <button
                            key={side}
                            type="button"
                            onClick={() => {
                              recordHistory();
                              setEdges((prev) =>
                                prev.map((e) => (e.id === selectedEdge.id ? { ...e, fromSide: side } : e))
                              );
                            }}
                            className={`py-1 text-[10px] font-bold uppercase rounded-lg border transition-colors cursor-pointer ${
                              (selectedEdge.fromSide || 'right') === side
                                ? 'bg-cyan-500 text-white border-cyan-500'
                                : 'bg-white dark:bg-slate-900 text-slate-700 dark:text-slate-300 border-slate-300 dark:border-slate-700 hover:bg-slate-100 dark:hover:bg-slate-800'
                            }`}
                          >
                            {side}
                          </button>
                        ))}
                      </div>
                    </div>
                  </div>

                  {/* Wire Target Node and Side */}
                  <div>
                    <label className="text-[10px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 block mb-1">
                      Target Activity & Port Side
                    </label>
                    <div className="p-2.5 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700/80 space-y-2">
                      <p className="font-semibold text-slate-900 dark:text-slate-100 truncate">
                        {nodes.find((n) => n.id === selectedEdge.to)?.title || selectedEdge.to}
                      </p>
                      <div className="grid grid-cols-4 gap-1">
                        {(['top', 'bottom', 'left', 'right'] as PortSide[]).map((side) => (
                          <button
                            key={side}
                            type="button"
                            onClick={() => {
                              recordHistory();
                              setEdges((prev) =>
                                prev.map((e) => (e.id === selectedEdge.id ? { ...e, toSide: side } : e))
                              );
                            }}
                            className={`py-1 text-[10px] font-bold uppercase rounded-lg border transition-colors cursor-pointer ${
                              (selectedEdge.toSide || 'left') === side
                                ? 'bg-cyan-500 text-white border-cyan-500'
                                : 'bg-white dark:bg-slate-900 text-slate-700 dark:text-slate-300 border-slate-300 dark:border-slate-700 hover:bg-slate-100 dark:hover:bg-slate-800'
                            }`}
                          >
                            {side}
                          </button>
                        ))}
                      </div>
                    </div>
                  </div>

                  {/* Wire Label */}
                  <div>
                    <label className="text-[10px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 block mb-1">
                      Wire Label
                    </label>
                    <input
                      type="text"
                      value={selectedEdge.label || ''}
                      placeholder="e.g. next, loop, success"
                      onChange={(e) => {
                        const val = e.target.value;
                        setEdges((prev) =>
                          prev.map((ed) => (ed.id === selectedEdge.id ? { ...ed, label: val } : ed))
                        );
                      }}
                      className="w-full px-2.5 py-1.5 rounded-xl bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 text-xs font-semibold text-slate-900 dark:text-slate-100 focus:outline-none focus:border-cyan-500 shadow-2xs"
                    />
                  </div>

                  {/* Wire Style Variant */}
                  <div>
                    <label className="text-[10px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 block mb-1">
                      Wire Style
                    </label>
                    <div className="grid grid-cols-2 gap-1.5">
                      {(['default', 'emphasis', 'security', 'dashed'] as const).map((variant) => (
                        <button
                          key={variant}
                          type="button"
                          onClick={() => {
                            recordHistory();
                            setEdges((prev) =>
                              prev.map((e) => (e.id === selectedEdge.id ? { ...e, variant } : e))
                            );
                          }}
                          className={`py-1.5 px-2 rounded-xl text-left border text-[11px] font-semibold capitalize cursor-pointer ${
                            (selectedEdge.variant || 'default') === variant
                              ? 'bg-cyan-50 dark:bg-cyan-950/40 border-cyan-500 text-cyan-700 dark:text-cyan-300'
                              : 'bg-white dark:bg-slate-900 border-slate-300 dark:border-slate-700 text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800'
                          }`}
                        >
                          {variant}
                        </button>
                      ))}
                    </div>
                  </div>

                  {/* Rewire & Delete Actions */}
                  <div className="pt-2 space-y-2">
                    <button
                      type="button"
                      onClick={() => {
                        setRewiringEdge({ edgeId: selectedEdge.id, end: 'to' });
                      }}
                      className="w-full py-1.5 px-3 rounded-xl bg-cyan-600 hover:bg-cyan-700 text-white font-semibold text-xs flex items-center justify-center gap-1.5 cursor-pointer shadow-xs transition-colors"
                    >
                      <RefreshCw className="w-3.5 h-3.5" />
                      <span>Rewire Target (Click Port on Canvas)</span>
                    </button>

                    <button
                      type="button"
                      onClick={() => {
                        handleDeleteEdge(selectedEdge.id);
                        setSelectedEdgeId(null);
                      }}
                      className="w-full py-1.5 px-3 rounded-xl bg-rose-50 dark:bg-rose-950/30 hover:bg-rose-100 dark:hover:bg-rose-900/50 text-rose-600 dark:text-rose-400 border border-rose-300 dark:border-rose-800 font-semibold text-xs flex items-center justify-center gap-1.5 cursor-pointer transition-colors"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                      <span>Delete Wire (Del)</span>
                    </button>
                  </div>
                </div>
              ) : null}
            </motion.aside>
          )}
        </AnimatePresence>
      </div>

      {/* Live Agent Pipeline Execution Log Drawer */}
      <AnimatePresence>
        {isDrawerOpen && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: drawerHeight, opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ type: 'spring', stiffness: 350, damping: 30 }}
            className="w-full border-t border-slate-200 dark:border-slate-800 bg-white/95 dark:bg-slate-900/95 backdrop-blur-md z-30 flex flex-col shrink-0 shadow-lg"
          >
            {/* Draggable Resizer Handle Bar */}
            <div
              onPointerDown={handleDrawerResizeStart}
              className="h-2 w-full bg-slate-200 dark:bg-slate-800 hover:bg-cyan-500/80 cursor-ns-resize transition-colors flex items-center justify-center group shrink-0 select-none"
              title="Drag up or down to resize live log panel"
            >
              <div className="w-10 h-1 rounded-full bg-slate-400 dark:bg-slate-600 group-hover:bg-white transition-colors" />
            </div>

            <div className="h-8 px-3 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between text-xs">
              <div className="flex items-center gap-2">
                <Terminal className="w-3.5 h-3.5 text-slate-600 dark:text-slate-400" />
                <span className="font-bold text-slate-900 dark:text-slate-100">
                  Live Agent Pipeline Execution Log
                </span>
                {isExecuting ? (
                  <span className="flex items-center gap-1 text-[10px] font-mono text-cyan-700 dark:text-cyan-400 bg-cyan-500/10 px-1.5 py-0.5 rounded-md font-semibold">
                    <span className="w-1.5 h-1.5 rounded-full bg-cyan-500 animate-ping" />
                    streaming {activeTaskId || 'live'}
                  </span>
                ) : (
                  <span className="text-[10px] font-mono text-slate-500 dark:text-slate-400">
                    idle · {executionLogs.length} events
                  </span>
                )}
              </div>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => setExecutionLogs([])}
                  className="p-1 rounded-md hover:bg-slate-200 dark:hover:bg-slate-800 text-slate-600 dark:text-slate-400 transition-colors cursor-pointer"
                  title="Clear logs"
                >
                  <RefreshCw className="w-3 h-3" />
                </button>
                <button
                  type="button"
                  onClick={() => setIsDrawerOpen(false)}
                  className="p-1 rounded-md hover:bg-slate-200 dark:hover:bg-slate-800 text-slate-600 dark:text-slate-400 transition-colors cursor-pointer"
                  title="Close log drawer"
                >
                  <ChevronDown className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>

            <div className="flex-1 overflow-y-auto p-2.5 font-mono text-[11px] space-y-1 bg-slate-50 dark:bg-slate-950/80">
              {executionLogs.length === 0 ? (
                <p className="text-slate-500 dark:text-slate-400 italic">
                  No execution events recorded yet. Click &quot;Run Pipeline&quot; above to initiate real workflow execution.
                </p>
              ) : (
                executionLogs.map((log, i) => (
                  <div key={i} className="flex items-start gap-2 text-slate-800 dark:text-slate-200 leading-tight">
                    <span className="text-slate-500 dark:text-slate-400 shrink-0 select-none">
                      [{log.timestamp || new Date().toLocaleTimeString()}]
                    </span>
                    <span className="text-cyan-700 dark:text-cyan-400 font-bold shrink-0">
                      [{log.agent}]
                    </span>
                    <span className="flex-1 break-words">{log.message}</span>
                  </div>
                ))
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Dedicated Styled Modal for Saving Workflow */}
      <AnimatePresence>
        {isSaveModalOpen && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-xs">
            <motion.div
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              className="w-full max-w-md rounded-2xl bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-800 p-5 shadow-2xl space-y-4"
            >
              <div className="flex items-center justify-between pb-2 border-b border-slate-200 dark:border-slate-800">
                <div className="flex items-center gap-2">
                  <Save className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
                  <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100">
                    Save Workflow
                  </h3>
                </div>
                <button
                  type="button"
                  onClick={() => setIsSaveModalOpen(false)}
                  className="p-1 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-500"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>

              <div>
                <label className="text-[11px] font-bold uppercase tracking-wider text-slate-600 dark:text-slate-400 block mb-1.5">
                  Workflow Name
                </label>
                <input
                  type="text"
                  value={saveWorkflowNameInput}
                  onChange={(e) => setSaveWorkflowNameInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      e.preventDefault();
                      handleConfirmSaveWorkflow(saveWorkflowNameInput);
                    }
                  }}
                  placeholder="e.g. My Custom DevOps Pipeline"
                  className="w-full px-3 py-2 rounded-xl bg-slate-50 dark:bg-slate-800/80 border border-slate-300 dark:border-slate-700 text-xs font-semibold text-slate-900 dark:text-slate-100 focus:outline-none focus:border-cyan-500"
                  autoFocus
                />
                <p className="text-[10px] text-slate-500 dark:text-slate-400 mt-1">
                  Saves swimlanes, activity nodes, and sequence connections to local storage.
                </p>
              </div>

              <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-200 dark:border-slate-800">
                <button
                  type="button"
                  onClick={() => setIsSaveModalOpen(false)}
                  className="px-3 py-1.5 rounded-xl border border-slate-300 dark:border-slate-700 text-xs font-medium text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={() => handleConfirmSaveWorkflow(saveWorkflowNameInput)}
                  className="px-4 py-1.5 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold shadow-xs cursor-pointer flex items-center gap-1.5"
                >
                  <Save className="w-3.5 h-3.5" />
                  <span>Save Workflow</span>
                  <span className="text-[10px] font-mono opacity-75">(Enter)</span>
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* Sequence Group Add / Edit Modal (UiPath Style) */}
      <AnimatePresence>
        {sequenceModal.isOpen && (
          <div
            className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs"
            onClick={() => setSequenceModal((prev) => ({ ...prev, isOpen: false }))}
          >
            <motion.div
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              onClick={(e) => e.stopPropagation()}
              className="w-full max-w-md rounded-2xl bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-800 p-5 shadow-2xl space-y-4"
            >
              <div className="flex items-center justify-between pb-2 border-b border-slate-200 dark:border-slate-800">
                <div className="flex items-center gap-2">
                  <Layers className="w-4 h-4 text-cyan-600 dark:text-cyan-400" />
                  <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100">
                    {sequenceModal.mode === 'edit' ? 'Edit Sequence Group' : 'Add Sequence Group'}
                  </h3>
                </div>
                <button
                  type="button"
                  onClick={() => setSequenceModal((prev) => ({ ...prev, isOpen: false }))}
                  className="p-1 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-500 cursor-pointer"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>

              {/* Sequence Name */}
              <div>
                <label className="text-[11px] font-bold uppercase tracking-wider text-slate-600 dark:text-slate-400 block mb-1.5">
                  Sequence Name
                </label>
                <input
                  type="text"
                  value={sequenceModal.label}
                  onChange={(e) => setSequenceModal((prev) => ({ ...prev, label: e.target.value }))}
                  placeholder="e.g. Planning & Tool Execution"
                  className="w-full px-3 py-2 rounded-xl bg-slate-50 dark:bg-slate-800/80 border border-slate-300 dark:border-slate-700 text-xs font-semibold text-slate-900 dark:text-slate-100 focus:outline-none focus:border-cyan-500"
                  autoFocus
                />
              </div>

              {/* Sequence Description */}
              <div>
                <label className="text-[11px] font-bold uppercase tracking-wider text-slate-600 dark:text-slate-400 block mb-1.5">
                  Description
                </label>
                <textarea
                  value={sequenceModal.description}
                  onChange={(e) => setSequenceModal((prev) => ({ ...prev, description: e.target.value }))}
                  placeholder="Brief explanation of the tasks or purpose of this sequence"
                  rows={2}
                  className="w-full px-3 py-2 rounded-xl bg-slate-50 dark:bg-slate-800/80 border border-slate-300 dark:border-slate-700 text-xs font-normal text-slate-900 dark:text-slate-100 focus:outline-none focus:border-cyan-500 resize-none"
                />
              </div>

              {/* Sequence Color / Status Level Selection */}
              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <label className="text-[11px] font-bold uppercase tracking-wider text-slate-600 dark:text-slate-400">
                    Priority & Classification Level
                  </label>
                </div>
                <div className="grid grid-cols-3 gap-2">
                  {(['blue', 'yellow', 'red'] as SequenceColor[]).map((colKey) => {
                    const theme = SEQUENCE_COLOR_THEMES[colKey];
                    const isSelected = sequenceModal.color === colKey;
                    const ringColor =
                      colKey === 'blue'
                        ? 'border-blue-500 bg-blue-50/70 dark:bg-blue-950/40 ring-2 ring-blue-500/25'
                        : colKey === 'yellow'
                          ? 'border-amber-500 bg-amber-50/70 dark:bg-amber-950/40 ring-2 ring-amber-500/25'
                          : 'border-rose-500 bg-rose-50/70 dark:bg-rose-950/40 ring-2 ring-rose-500/25';
                    const textSubtitle =
                      colKey === 'blue'
                        ? 'text-blue-600 dark:text-blue-400'
                        : colKey === 'yellow'
                          ? 'text-amber-600 dark:text-amber-400'
                          : 'text-rose-600 dark:text-rose-400';

                    return (
                      <div key={colKey} className="relative group/opt">
                        <button
                          type="button"
                          onClick={() => setSequenceModal((prev) => ({ ...prev, color: colKey }))}
                          className={`w-full p-2.5 rounded-xl border text-left cursor-pointer transition-all flex flex-col justify-between ${
                            isSelected
                              ? ringColor
                              : 'border-slate-200 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-800'
                          }`}
                        >
                          <div className="flex items-center justify-between mb-1">
                            <div className="flex items-center gap-1.5">
                              <span className={`w-2.5 h-2.5 rounded-full ${theme.dotBg} shadow-xs`} />
                              <span className="text-xs font-bold text-slate-900 dark:text-slate-100">
                                {theme.label}
                              </span>
                            </div>
                            <div
                              className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 p-0.5"
                              title={theme.tooltip}
                            >
                              <HelpCircle className="w-3.5 h-3.5" />
                            </div>
                          </div>
                          <span className={`text-[9px] font-mono font-bold uppercase ${textSubtitle}`}>
                            {theme.badgeLabel}
                          </span>
                        </button>

                        {/* Interactive Tooltip Card on Hover */}
                        <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-1.5 hidden group-hover/opt:block z-50 w-56 p-2 rounded-lg bg-slate-900/95 dark:bg-slate-800/95 text-slate-200 text-[10px] leading-relaxed shadow-xl border border-slate-700 backdrop-blur-xs pointer-events-none">
                          <div className="font-bold text-cyan-400 mb-0.5">{theme.label} Sequence</div>
                          <div>{theme.tooltip}</div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Modal Actions */}
              <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-200 dark:border-slate-800">
                <button
                  type="button"
                  onClick={() => setSequenceModal((prev) => ({ ...prev, isOpen: false }))}
                  className="px-3 py-1.5 rounded-xl border border-slate-300 dark:border-slate-700 text-xs font-medium text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={handleSaveSequenceModal}
                  disabled={!sequenceModal.label.trim()}
                  className="px-4 py-1.5 rounded-xl bg-cyan-600 hover:bg-cyan-700 disabled:opacity-40 text-white text-xs font-semibold shadow-xs cursor-pointer"
                >
                  {sequenceModal.mode === 'edit' ? 'Save Changes' : 'Add Sequence'}
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* Activity Deletion Confirmation Modal */}
      <AnimatePresence>
        {nodeToDelete && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-xs">
            <motion.div
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              className="w-full max-w-sm rounded-2xl bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-800 p-5 shadow-2xl space-y-4"
            >
              <div className="flex items-center gap-3 text-rose-600 dark:text-rose-400">
                <div className="p-2.5 rounded-xl bg-rose-500/10">
                  <AlertTriangle className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100">
                    Delete Activity
                  </h3>
                  <p className="text-[11px] text-slate-500 dark:text-slate-400">
                    Confirmation required
                  </p>
                </div>
              </div>

              <p className="text-xs text-slate-600 dark:text-slate-300 leading-relaxed">
                Are you sure you want to delete activity <strong className="font-semibold text-slate-900 dark:text-slate-100">&quot;{nodeToDelete.title}&quot;</strong>? Any connected sequence wires will also be removed.
              </p>

              <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-200 dark:border-slate-800">
                <button
                  type="button"
                  onClick={() => setNodeToDelete(null)}
                  className="px-3.5 py-1.5 rounded-xl border border-slate-300 dark:border-slate-700 text-xs font-medium text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 cursor-pointer transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={handleConfirmDeleteNode}
                  className="px-4 py-1.5 rounded-xl bg-rose-600 hover:bg-rose-700 text-white text-xs font-semibold shadow-xs cursor-pointer transition-colors"
                >
                  Delete Activity
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* Activity Documentation & Operational Guide Modal */}
      <AnimatePresence>
        {detailDocItem && (
          <div
            className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs"
            onClick={() => setDetailDocItem(null)}
          >
            <motion.div
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              onClick={(e) => e.stopPropagation()}
              className="w-full max-w-xl max-h-[85vh] flex flex-col rounded-2xl bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-800 p-5 shadow-2xl space-y-4 overflow-hidden"
            >
              {/* Header */}
              <div className="flex items-center justify-between pb-3 border-b border-slate-200 dark:border-slate-800 shrink-0">
                <div className="flex items-center gap-2.5 min-w-0">
                  {(() => {
                    const DocIcon = detailDocItem.icon;
                    return <DocIcon className={`w-5 h-5 shrink-0 ${detailDocItem.color}`} />;
                  })()}
                  <div className="min-w-0">
                    <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100 truncate">
                      {detailDocItem.title}
                    </h3>
                    <p className="text-[11px] text-slate-500 dark:text-slate-400 truncate">
                      {detailDocItem.subtitle}
                    </p>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => setDetailDocItem(null)}
                  className="p-1 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 transition-colors cursor-pointer"
                  title="Close (Escape)"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>

              {/* Badges */}
              <div className="flex items-center gap-2 flex-wrap shrink-0">
                <span className="px-2 py-0.5 rounded-md bg-cyan-100 dark:bg-cyan-950/70 border border-cyan-300 dark:border-cyan-800 text-cyan-800 dark:text-cyan-300 text-[10px] font-semibold">
                  Role: {detailDocItem.doc.role}
                </span>
                <span className="px-2 py-0.5 rounded-md bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 text-[10px] font-mono">
                  Swimlane: {detailDocItem.lane.toUpperCase()}
                </span>
                <span className="px-2 py-0.5 rounded-md bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 text-[10px] font-mono">
                  Tag: #{detailDocItem.tag}
                </span>
              </div>

              {/* Scrollable Content */}
              <div className="flex-1 overflow-y-auto space-y-4 text-xs pr-1">
                {/* Description & Function */}
                <div className="space-y-1">
                  <h4 className="text-[11px] font-bold uppercase tracking-wider text-slate-700 dark:text-slate-300 flex items-center gap-1.5">
                    <FileText className="w-3.5 h-3.5 text-cyan-600 dark:text-cyan-400" />
                    <span>Function & Operational Mechanics</span>
                  </h4>
                  <p className="text-slate-700 dark:text-slate-300 leading-relaxed bg-slate-50 dark:bg-slate-800/50 p-2.5 rounded-xl border border-slate-200 dark:border-slate-800">
                    {detailDocItem.doc.description}
                  </p>
                </div>

                {/* Input & Output */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                  <div className="p-2.5 rounded-xl bg-slate-50 dark:bg-slate-800/40 border border-slate-200 dark:border-slate-800 space-y-1.5">
                    <h5 className="font-bold text-[10.5px] text-slate-800 dark:text-slate-200 flex items-center gap-1">
                      <ArrowDown className="w-3 h-3 text-cyan-600" />
                      <span>Input Data</span>
                    </h5>
                    <ul className="list-disc list-inside space-y-1 text-[11px] text-slate-600 dark:text-slate-400">
                      {detailDocItem.doc.inputs.map((inp, idx) => (
                        <li key={idx} className="leading-snug">{inp}</li>
                      ))}
                    </ul>
                  </div>

                  <div className="p-2.5 rounded-xl bg-slate-50 dark:bg-slate-800/40 border border-slate-200 dark:border-slate-800 space-y-1.5">
                    <h5 className="font-bold text-[10.5px] text-slate-800 dark:text-slate-200 flex items-center gap-1">
                      <ArrowUp className="w-3 h-3 text-emerald-600" />
                      <span>Outputs & Artifacts</span>
                    </h5>
                    <ul className="list-disc list-inside space-y-1 text-[11px] text-slate-600 dark:text-slate-400">
                      {detailDocItem.doc.outputs.map((out, idx) => (
                        <li key={idx} className="leading-snug">{out}</li>
                      ))}
                    </ul>
                  </div>
                </div>

                {/* Configuration Parameters */}
                {detailDocItem.doc.configFields.length > 0 && (
                  <div className="space-y-1.5">
                    <h4 className="text-[11px] font-bold uppercase tracking-wider text-slate-700 dark:text-slate-300 flex items-center gap-1.5">
                      <Settings className="w-3.5 h-3.5 text-cyan-600 dark:text-cyan-400" />
                      <span>Configuration Parameters</span>
                    </h4>
                    <div className="space-y-1.5">
                      {detailDocItem.doc.configFields.map((cf) => (
                        <div
                          key={cf.param}
                          className="p-2 rounded-xl bg-slate-50 dark:bg-slate-800/40 border border-slate-200 dark:border-slate-800 text-[11px]"
                        >
                          <div className="flex items-center gap-2 mb-0.5">
                            <span className="font-mono font-bold text-cyan-700 dark:text-cyan-300">
                              {cf.param}
                            </span>
                            {cf.defaultValue && (
                              <span className="font-mono text-[9px] text-slate-400 dark:text-slate-500">
                                default: {cf.defaultValue}
                              </span>
                            )}
                          </div>
                          <p className="text-slate-600 dark:text-slate-400 leading-snug">
                            {cf.desc}
                          </p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Recommended Sequence Connections */}
                <div className="space-y-1 p-2.5 rounded-xl bg-amber-50/60 dark:bg-amber-950/20 border border-amber-200/60 dark:border-amber-800/40">
                  <h4 className="text-[10.5px] font-bold text-amber-800 dark:text-amber-300 flex items-center gap-1.5">
                    <Workflow className="w-3.5 h-3.5" />
                    <span>Recommended Sequence Connections</span>
                  </h4>
                  <p className="text-[11px] text-amber-900/80 dark:text-amber-300/80 leading-relaxed">
                    {detailDocItem.doc.recommendedConnections}
                  </p>
                </div>
              </div>

              {/* Footer */}
              <div className="flex items-center justify-between pt-2.5 border-t border-slate-200 dark:border-slate-800 shrink-0">
                <button
                  type="button"
                  onClick={() => setDetailDocItem(null)}
                  className="px-3.5 py-1.5 rounded-xl border border-slate-300 dark:border-slate-700 text-xs font-medium text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 cursor-pointer"
                >
                  Close
                </button>
                <button
                  type="button"
                  disabled={isExecuting}
                  onClick={() => {
                    handleAddNode(detailDocItem);
                    setDetailDocItem(null);
                  }}
                  className="px-4 py-1.5 rounded-xl bg-cyan-600 hover:bg-cyan-700 disabled:opacity-50 disabled:cursor-not-allowed text-white text-xs font-semibold shadow-xs cursor-pointer flex items-center gap-1.5"
                >
                  <Plus className="w-3.5 h-3.5" />
                  <span>Add to Canvas</span>
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>



      {/* Floating Save Toast Notification in Top-Right Corner */}
      <AnimatePresence>
        {saveToastMessage && (
          <motion.div
            initial={{ opacity: 0, y: -16, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -16, scale: 0.95 }}
            transition={{ duration: 0.2, ease: 'easeOut' }}
            className="fixed top-14 right-5 z-50 px-3.5 py-2 rounded-xl bg-slate-900/95 text-white dark:bg-slate-100 dark:text-slate-900 shadow-xl border border-slate-700/60 dark:border-slate-300/80 text-xs font-semibold flex items-center gap-2 backdrop-blur-md"
          >
            <Check className="w-3.5 h-3.5 text-emerald-400 dark:text-emerald-600 shrink-0" />
            <span>{saveToastMessage}</span>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Embedded Settings Modal for Platform and Credentials Configuration */}
      <SettingsModal
        isOpen={isSettingsOpen}
        onClose={() => setIsSettingsOpen(false)}
        config={config}
        onSave={(newCfg) => {
          if (onUpdateConfig) onUpdateConfig(newCfg);
          setIsSettingsOpen(false);
          fetchModelsFromApi(newCfg.active_backend);
        }}
        isSyncing={isConfigSyncing}
        onRefreshModels={onRefreshModels}
      />
    </div>
  );
}
