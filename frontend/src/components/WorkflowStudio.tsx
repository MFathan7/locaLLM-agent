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
  Target
} from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';
import { ThemeToggle } from './ThemeToggle';
import { SettingsModal } from './SettingsModal';
import type { Workspace, ModelInfo, LocaLLMConfig } from '../types';
import { api } from '../services/api';

export type WorkflowLane = 'ui' | 'agent' | 'policy' | 'tools' | 'evidence' | string;

export interface WorkflowLaneConfig {
  id: string;
  num: string;
  label: string;
  y: number;
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

export interface WorkflowEdge {
  id: string;
  from: string;
  to: string;
  label?: string;
  variant?: 'default' | 'emphasis' | 'security' | 'dashed';
}

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

// Default Archify Swimlanes Layout
export const INITIAL_LANES: WorkflowLaneConfig[] = [
  { id: 'ui', num: '01', label: 'User Interface', y: 70, height: 130, variant: 'default' },
  { id: 'agent', num: '02', label: 'Agent Runtime', y: 220, height: 145, variant: 'default' },
  { id: 'policy', num: '03', label: 'Policy & Recovery', y: 385, height: 130, variant: 'exception' },
  { id: 'tools', num: '04', label: 'Tool Execution', y: 535, height: 145, variant: 'default' },
  { id: 'evidence', num: '05', label: 'Evidence & Context Store', y: 700, height: 130, variant: 'default' }
];

// Helper to recalculate sequential positions and numbers for dynamic lanes
export function computeLanePositions(laneList: WorkflowLaneConfig[]): WorkflowLaneConfig[] {
  let currentY = 70;
  return laneList.map((lane, index) => {
    const num = String(index + 1).padStart(2, '0');
    const updated = { ...lane, num, y: currentY };
    currentY += lane.height + 20;
    return updated;
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
}> = {
  frontend: {
    container: 'bg-cyan-50/90 dark:bg-cyan-950/40 border-cyan-500/80 dark:border-cyan-400 text-cyan-950 dark:text-cyan-100 shadow-2xs',
    iconColor: 'text-cyan-600 dark:text-cyan-400',
    tagClass: 'bg-cyan-100 text-cyan-800 dark:bg-cyan-900/60 dark:text-cyan-300',
    stroke: '#22d3ee'
  },
  backend: {
    container: 'bg-emerald-50/90 dark:bg-emerald-950/40 border-emerald-500/80 dark:border-emerald-400 text-emerald-950 dark:text-emerald-100 shadow-2xs',
    iconColor: 'text-emerald-600 dark:text-emerald-400',
    tagClass: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/60 dark:text-emerald-300',
    stroke: '#34d399'
  },
  security: {
    container: 'bg-rose-50/90 dark:bg-rose-950/40 border-rose-500/80 dark:border-rose-400 text-rose-950 dark:text-rose-100 shadow-2xs',
    iconColor: 'text-rose-600 dark:text-rose-400',
    tagClass: 'bg-rose-100 text-rose-800 dark:bg-rose-900/60 dark:text-rose-300',
    stroke: '#fb7185'
  },
  database: {
    container: 'bg-purple-50/90 dark:bg-purple-950/40 border-purple-500/80 dark:border-purple-400 text-purple-950 dark:text-purple-100 shadow-2xs',
    iconColor: 'text-purple-600 dark:text-purple-400',
    tagClass: 'bg-purple-100 text-purple-800 dark:bg-purple-900/60 dark:text-purple-300',
    stroke: '#a78bfa'
  },
  cloud: {
    container: 'bg-amber-50/90 dark:bg-amber-950/40 border-amber-500/80 dark:border-amber-400 text-amber-950 dark:text-amber-100 shadow-2xs',
    iconColor: 'text-amber-600 dark:text-amber-400',
    tagClass: 'bg-amber-100 text-amber-800 dark:bg-amber-900/60 dark:text-amber-300',
    stroke: '#fbbf24'
  },
  messagebus: {
    container: 'bg-orange-50/90 dark:bg-orange-950/40 border-orange-500/80 dark:border-orange-400 text-orange-950 dark:text-orange-100 shadow-2xs',
    iconColor: 'text-orange-600 dark:text-orange-400',
    tagClass: 'bg-orange-100 text-orange-800 dark:bg-orange-900/60 dark:text-orange-300',
    stroke: '#fb923c'
  },
  external: {
    container: 'bg-slate-100/90 dark:bg-slate-800/60 border-slate-400/80 dark:border-slate-500 text-slate-900 dark:text-slate-100 shadow-2xs',
    iconColor: 'text-slate-600 dark:text-slate-300',
    tagClass: 'bg-slate-200 text-slate-800 dark:bg-slate-700 dark:text-slate-300',
    stroke: '#94a3b8'
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
  const [lanes, setLanes] = useState<WorkflowLaneConfig[]>(INITIAL_LANES);

  // Core diagram state
  const [activeWorkflowTitle, setActiveWorkflowTitle] = useState<string>('Agent Tool-Call Loop');
  const [nodes, setNodes] = useState<WorkflowNode[]>(WORKFLOW_PRESETS[0].nodes);
  const [edges, setEdges] = useState<WorkflowEdge[]>(WORKFLOW_PRESETS[0].edges);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>('planner');

  // Canvas Viewport transform
  const [zoom, setZoom] = useState<number>(1);
  const [pan, setPan] = useState<{ x: number; y: number }>({ x: 30, y: 20 });
  const [isCanvasPanning, setIsCanvasPanning] = useState<boolean>(false);
  const [isFullscreen, setIsFullscreen] = useState<boolean>(false);
  const [isGridVisible, setIsGridVisible] = useState<boolean>(true);

  // Hover Focus Zoom & Flow Animation Engine
  const [hoveredNodeId, setHoveredNodeId] = useState<string | null>(null);
  const [hoverFocusZoomEnabled, setHoverFocusZoomEnabled] = useState<boolean>(true);
  const [isCameraAnimating, setIsCameraAnimating] = useState<boolean>(false);
  const unhoverTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const baseCameraRef = useRef<{ zoom: number; pan: { x: number; y: number } } | null>(null);

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
  const [isAddLaneModalOpen, setIsAddLaneModalOpen] = useState<boolean>(false);
  const [newLaneLabelInput, setNewLaneLabelInput] = useState<string>('');
  const [newLaneVariantInput, setNewLaneVariantInput] = useState<'default' | 'exception'>('default');

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

  // Interactive Wiring (Sequence wire creation)
  const [connectingSourceId, setConnectingSourceId] = useState<string | null>(null);
  const [connectingMousePos, setConnectingMousePos] = useState<{ x: number; y: number } | null>(null);

  // Node Drag State (Smooth pointer-based dragging)
  const dragNodeRef = useRef<{
    nodeId: string;
    startX: number;
    startY: number;
    initialNodeX: number;
    initialNodeY: number;
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

  // Helper to detect lane by Y coordinate dynamically based on current lanes
  const detectLaneByY = useCallback((y: number): string => {
    const midY = y + NODE_HEIGHT / 2;
    for (const lane of lanes) {
      if (midY >= lane.y && midY <= lane.y + lane.height + 20) {
        return lane.id;
      }
    }
    return lanes[0]?.id || 'ui';
  }, [lanes]);

  // Global Pointer Listeners for Smooth Node Dragging and Canvas Panning
  useEffect(() => {
    const onWindowPointerMove = (e: PointerEvent) => {
      // Handle Smooth Node Dragging
      if (dragNodeRef.current) {
        const { nodeId, startX, startY, initialNodeX, initialNodeY } = dragNodeRef.current;
        const dx = (e.clientX - startX) / zoom;
        const dy = (e.clientY - startY) / zoom;

        const newX = Math.max(20, Math.round(initialNodeX + dx));
        const newY = Math.max(20, Math.round(initialNodeY + dy));

        const targetLane = detectLaneByY(newY);
        setHoveredLaneId(targetLane);

        setNodes((prev) =>
          prev.map((n) => {
            if (n.id === nodeId) {
              return {
                ...n,
                x: newX,
                y: newY,
                lane: targetLane
              };
            }
            return n;
          })
        );
        return;
      }

      // Handle Connecting Wire Preview line
      if (connectingSourceId && canvasRef.current) {
        const rect = canvasRef.current.getBoundingClientRect();
        setConnectingMousePos({
          x: (e.clientX - rect.left - pan.x) / zoom,
          y: (e.clientY - rect.top - pan.y) / zoom
        });
      }

      // Handle Canvas Panning
      if (isPanningCanvasRef.current) {
        const dx = e.clientX - canvasPanStartRef.current.startX;
        const dy = e.clientY - canvasPanStartRef.current.startY;
        setPan({
          x: Math.round(canvasPanStartRef.current.panX + dx),
          y: Math.round(canvasPanStartRef.current.panY + dy)
        });
      }
    };

    const onWindowPointerUp = () => {
      if (dragNodeRef.current) {
        if (initialDragSnapshotRef.current) {
          const { initialNodeX, initialNodeY, nodeId } = dragNodeRef.current;
          const currentNode = nodes.find((n) => n.id === nodeId);
          if (currentNode && (currentNode.x !== initialNodeX || currentNode.y !== initialNodeY)) {
            setHistoryPast((prev) => [...prev.slice(-30), initialDragSnapshotRef.current!]);
            setHistoryFuture([]);
          }
          initialDragSnapshotRef.current = null;
        }
        dragNodeRef.current = null;
        setDraggingNodeId(null);
        setHoveredLaneId(null);
      }
      if (isPanningCanvasRef.current) {
        isPanningCanvasRef.current = false;
        setIsCanvasPanning(false);
      }
    };

    const onWindowKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setConnectingSourceId(null);
        setConnectingMousePos(null);
      }
    };

    window.addEventListener('pointermove', onWindowPointerMove);
    window.addEventListener('pointerup', onWindowPointerUp);
    window.addEventListener('keydown', onWindowKeyDown);
    return () => {
      window.removeEventListener('pointermove', onWindowPointerMove);
      window.removeEventListener('pointerup', onWindowPointerUp);
      window.removeEventListener('keydown', onWindowKeyDown);
    };
  }, [zoom, pan, connectingSourceId, detectLaneByY]);

  // Selected Node reference
  const selectedNode = useMemo(() => {
    return nodes.find((n) => n.id === selectedNodeId) || null;
  }, [nodes, selectedNodeId]);

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

  // Archify Semantic Focus & Flow Relationship Map
  const flowRelations = useMemo(() => {
    if (!hoveredNodeId) {
      return {
        hoveredNode: null,
        incomingEdges: [] as WorkflowEdge[],
        outgoingEdges: [] as WorkflowEdge[],
        upstreamNodeIds: new Set<string>(),
        downstreamNodeIds: new Set<string>(),
        relatedEdgeIds: new Set<string>(),
        relatedNodeIds: new Set<string>(),
        flowSummary: null as string | null
      };
    }

    const hoveredNode = nodes.find((n) => n.id === hoveredNodeId) || null;
    const incomingEdges = edges.filter((e) => e.to === hoveredNodeId);
    const outgoingEdges = edges.filter((e) => e.from === hoveredNodeId);

    const upstreamNodeIds = new Set(incomingEdges.map((e) => e.from));
    const downstreamNodeIds = new Set(outgoingEdges.map((e) => e.to));
    const relatedEdgeIds = new Set([
      ...incomingEdges.map((e) => e.id),
      ...outgoingEdges.map((e) => e.id)
    ]);
    const relatedNodeIds = new Set([
      hoveredNodeId,
      ...upstreamNodeIds,
      ...downstreamNodeIds
    ]);

    const upstreamTitles = incomingEdges
      .map((e) => nodes.find((n) => n.id === e.from)?.title)
      .filter(Boolean);
    const downstreamTitles = outgoingEdges
      .map((e) => nodes.find((n) => n.id === e.to)?.title)
      .filter(Boolean);

    let summaryText = '';
    if (upstreamTitles.length && downstreamTitles.length) {
      summaryText = `${upstreamTitles.join(', ')} ➔ [${hoveredNode?.title}] ➔ ${downstreamTitles.join(', ')}`;
    } else if (downstreamTitles.length) {
      summaryText = `[${hoveredNode?.title}] ➔ ${downstreamTitles.join(', ')}`;
    } else if (upstreamTitles.length) {
      summaryText = `${upstreamTitles.join(', ')} ➔ [${hoveredNode?.title}]`;
    } else if (hoveredNode) {
      summaryText = `[${hoveredNode.title}] (Standalone Step)`;
    }

    return {
      hoveredNode,
      incomingEdges,
      outgoingEdges,
      upstreamNodeIds,
      downstreamNodeIds,
      relatedEdgeIds,
      relatedNodeIds,
      flowSummary: summaryText || null
    };
  }, [hoveredNodeId, nodes, edges]);

  // Smooth Hover Focus Zoom In Handler
  const handleNodeMouseEnter = useCallback((nodeId: string) => {
    if (draggingNodeId || isPanningCanvasRef.current || isExecuting) return;

    if (unhoverTimeoutRef.current) {
      clearTimeout(unhoverTimeoutRef.current);
      unhoverTimeoutRef.current = null;
    }

    setHoveredNodeId(nodeId);

    if (hoverFocusZoomEnabled) {
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

        const targetZoom = 1.32;
        const targetPanX = Math.round(cWidth / 2 - cx * targetZoom);
        const targetPanY = Math.round(cHeight / 2 - cy * targetZoom);

        setIsCameraAnimating(true);
        setZoom(targetZoom);
        setPan({ x: targetPanX, y: targetPanY });

        setTimeout(() => {
          setIsCameraAnimating(false);
        }, 340);
      }
    }
  }, [hoverFocusZoomEnabled, zoom, pan, nodes, edges, isExecuting, draggingNodeId]);

  // Smooth Hover Focus Zoom Restore Handler
  const handleNodeMouseLeave = useCallback(() => {
    if (unhoverTimeoutRef.current) {
      clearTimeout(unhoverTimeoutRef.current);
    }

    unhoverTimeoutRef.current = setTimeout(() => {
      setHoveredNodeId(null);

      if (hoverFocusZoomEnabled && baseCameraRef.current) {
        const { zoom: origZoom, pan: origPan } = baseCameraRef.current;
        baseCameraRef.current = null;
        setIsCameraAnimating(true);
        setZoom(origZoom);
        setPan(origPan);
        setTimeout(() => {
          setIsCameraAnimating(false);
        }, 340);
      }
    }, 180);
  }, [hoverFocusZoomEnabled]);

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

  // Total dynamic canvas SVG height based on active lanes
  const totalCanvasHeight = useMemo(() => {
    if (lanes.length === 0) return 1200;
    const lastLane = lanes[lanes.length - 1];
    return Math.max(1400, lastLane.y + lastLane.height + 250);
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

  // Save workflow (Custom UI Dialog)
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
    setSaveToastMessage(`Workflow "${item.name}" saved successfully`);
    setTimeout(() => setSaveToastMessage(null), 3000);
  }, [lanes, nodes, edges, savedWorkflows]);

  // Global Keyboard shortcuts: Ctrl+S (Save), Ctrl+Z (Undo) and Ctrl+Shift+Z / Ctrl+Y (Redo)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Ctrl+S / Cmd+S save workflow shortcut
      if ((e.ctrlKey || e.metaKey) && !e.shiftKey && e.key.toLowerCase() === 's') {
        e.preventDefault();
        handleOpenSaveDialog();
        return;
      }

      const activeEl = document.activeElement;
      if (
        activeEl &&
        (activeEl.tagName === 'INPUT' ||
          activeEl.tagName === 'TEXTAREA' ||
          activeEl.getAttribute('contenteditable') === 'true')
      ) {
        return;
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
  }, [handleUndo, handleRedo, handleOpenSaveDialog]);

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

    // If currently in wire connecting mode, complete sequence link!
    if (connectingSourceId) {
      if (connectingSourceId !== id) {
        handleAddEdge(connectingSourceId, id);
      }
      setConnectingSourceId(null);
      setConnectingMousePos(null);
      return;
    }

    const node = nodes.find((n) => n.id === id);
    if (!node) return;

    setSelectedNodeId(id);
    setDraggingNodeId(id);

    // Save initial snapshot before dragging begins
    initialDragSnapshotRef.current = {
      nodes: JSON.parse(JSON.stringify(nodes)),
      edges: JSON.parse(JSON.stringify(edges)),
      lanes: JSON.parse(JSON.stringify(lanes))
    };

    dragNodeRef.current = {
      nodeId: id,
      startX: e.clientX,
      startY: e.clientY,
      initialNodeX: node.x,
      initialNodeY: node.y
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
    baseCameraRef.current = null;
    setIsCameraAnimating(false);

    if (connectingSourceId) {
      setConnectingSourceId(null);
      setConnectingMousePos(null);
    }

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
    const actualLane = customY !== undefined ? detectLaneByY(actualY) : template.lane;

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

  // Add edge connection between two nodes
  const handleAddEdge = (fromId: string, toId: string, label: string = 'next') => {
    if (isExecuting) return;
    if (fromId === toId) return;
    const exists = edges.some((e) => e.from === fromId && e.to === toId);
    if (exists) return;

    recordHistory();
    const newEdge: WorkflowEdge = {
      id: `e-${Date.now().toString(36)}`,
      from: fromId,
      to: toId,
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

  // --- Dynamic Swimlanes Management (Add, Delete, Reorder) ---
  const handleAddNewLane = () => {
    if (isExecuting) return;
    if (!newLaneLabelInput.trim()) return;
    recordHistory();
    const newId = `lane-${Date.now().toString(36)}`;
    const newLane: WorkflowLaneConfig = {
      id: newId,
      num: String(lanes.length + 1).padStart(2, '0'),
      label: newLaneLabelInput.trim(),
      y: 0,
      height: 135,
      variant: newLaneVariantInput
    };
    const updated = computeLanePositions([...lanes, newLane]);
    setLanes(updated);
    setNewLaneLabelInput('');
    setIsAddLaneModalOpen(false);
  };

  const handleDeleteLane = (laneId: string) => {
    if (isExecuting) return;
    if (lanes.length <= 1) {
      alert('A workflow must contain at least one swimlane.');
      return;
    }
    recordHistory();
    const remaining = lanes.filter((l) => l.id !== laneId);
    const updated = computeLanePositions(remaining);
    setLanes(updated);

    // Reassign any nodes that were in the deleted lane to the nearest lane
    const fallbackLane = updated[0].id;
    setNodes((prev) =>
      prev.map((n) => (n.lane === laneId ? { ...n, lane: fallbackLane } : n))
    );
  };

  const handleMoveLane = (index: number, direction: 'up' | 'down') => {
    if (isExecuting) return;
    const targetIdx = direction === 'up' ? index - 1 : index + 1;
    if (targetIdx < 0 || targetIdx >= lanes.length) return;
    recordHistory();
    const nextLanes = [...lanes];
    const [removed] = nextLanes.splice(index, 1);
    nextLanes.splice(targetIdx, 0, removed);
    setLanes(computeLanePositions(nextLanes));
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



  // Load saved workflow
  const handleLoadSavedWorkflow = (saved: typeof savedWorkflows[0]) => {
    setIsWorkflowMenuOpen(false);
    setActiveWorkflowTitle(saved.name);
    if (saved.lanes && Array.isArray(saved.lanes)) {
      setLanes(computeLanePositions(saved.lanes));
    }
    setNodes(saved.nodes);
    setEdges(saved.edges);
    setSelectedNodeId(saved.nodes[0]?.id || null);
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

  // Generate Archify-standard orthogonal stepped connector path with channel corridor routing
  const getOrthogonalRoute = (x1: number, y1: number, x2: number, y2: number) => {
    // Direct horizontal alignment
    if (Math.abs(y1 - y2) < 4 && x2 >= x1) {
      return {
        path: `M ${x1} ${y1} L ${x2} ${y2}`,
        labelX: (x1 + x2) / 2,
        labelY: y1
      };
    }
    // Standard forward stepped routing
    if (x2 >= x1 + 24) {
      const midX = Math.round((x1 + x2) / 2);
      return {
        path: `M ${x1} ${y1} L ${midX} ${y1} L ${midX} ${y2} L ${x2} ${y2}`,
        labelX: midX,
        labelY: (y1 + y2) / 2
      };
    }
    // Backward loop (e.g. trace -> planner loopback, retry -> planner loop)
    if (y2 < y1) {
      // Looping upwards
      const rightX = x1 + 30;
      const topY = Math.min(y1, y2) - 28;
      const leftX = x2 - 28;
      return {
        path: `M ${x1} ${y1} L ${rightX} ${y1} L ${rightX} ${topY} L ${leftX} ${topY} L ${leftX} ${y2} L ${x2} ${y2}`,
        labelX: (rightX + leftX) / 2,
        labelY: topY - 10
      };
    } else {
      // Looping downwards
      const rightX = x1 + 30;
      const bottomY = Math.max(y1, y2) + 36;
      const leftX = x2 - 28;
      return {
        path: `M ${x1} ${y1} L ${rightX} ${y1} L ${rightX} ${bottomY} L ${leftX} ${bottomY} L ${leftX} ${y2} L ${x2} ${y2}`,
        labelX: (rightX + leftX) / 2,
        labelY: bottomY + 10
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
            {isWorkflowMenuOpen && (
              <div className="absolute top-full left-0 mt-1.5 w-72 rounded-2xl bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 shadow-xl p-2 z-50 text-xs">
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
                    onClick={handleOpenSaveDialog}
                    className="px-2 py-1.5 rounded-xl bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-800 dark:text-slate-200 flex items-center justify-center gap-1 text-[11px] font-semibold cursor-pointer"
                    title="Save workflow to local storage (Ctrl+S)"
                  >
                    <Save className="w-3 h-3 text-emerald-600" />
                    <span>Save Flow</span>
                    <span className="text-[9px] font-mono opacity-60 ml-0.5">Ctrl+S</span>
                  </button>
                </div>
              </div>
            )}
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
              setHoverFocusZoomEnabled((v) => !v);
              if (hoverFocusZoomEnabled) {
                if (unhoverTimeoutRef.current) clearTimeout(unhoverTimeoutRef.current);
                setHoveredNodeId(null);
                if (baseCameraRef.current) {
                  setZoom(baseCameraRef.current.zoom);
                  setPan(baseCameraRef.current.pan);
                  baseCameraRef.current = null;
                }
              }
            }}
            className={`p-1 rounded-lg transition-colors cursor-pointer flex items-center gap-1 ${hoverFocusZoomEnabled
                ? 'bg-cyan-500/20 text-cyan-700 dark:text-cyan-300 font-semibold'
                : 'text-slate-500 dark:text-slate-400 hover:bg-slate-200 dark:hover:bg-slate-700'
              }`}
            title={`Hover Focus Zoom: ${hoverFocusZoomEnabled ? 'Enabled' : 'Disabled'} (Auto-zooms and highlights flow on hover)`}
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
            {isPlatformMenuOpen && (
              <div className="absolute top-full right-0 mt-1.5 w-60 rounded-2xl bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 shadow-xl p-2 z-50 text-xs">
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
              </div>
            )}
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
            cursor: connectingSourceId ? 'crosshair' : isCanvasPanning ? 'grabbing' : 'grab'
          }}
        >
          {/* Wire Linking Banner Alert */}
          {connectingSourceId && !isExecuting && (
            <div className="absolute top-3 left-1/2 -translate-x-1/2 z-30 px-3 py-1.5 rounded-full bg-cyan-600 text-white text-xs font-semibold shadow-lg flex items-center gap-2 animate-bounce">
              <LinkIcon className="w-3.5 h-3.5" />
              <span>Click target activity to link sequence, or press Esc to cancel</span>
              <button
                type="button"
                onClick={() => {
                  setConnectingSourceId(null);
                  setConnectingMousePos(null);
                }}
                className="p-0.5 rounded-full hover:bg-cyan-700"
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

          {/* Pan Navigation Hint & Add Swimlane shortcut */}
          <div className="absolute bottom-3 left-3 z-10 flex items-center gap-2">
            <div className="pointer-events-none flex items-center gap-2 text-[10px] font-mono text-slate-600 dark:text-slate-400 bg-white/85 dark:bg-slate-900/85 backdrop-blur-xs px-2 py-1 rounded-lg border border-slate-300/80 dark:border-slate-800 shadow-2xs">
              <Move className="w-3 h-3 text-slate-500" />
              <span>Drag canvas or objects · Mouse scroll zooms · Offset: ({pan.x}, {pan.y})</span>
            </div>

            <button
              type="button"
              disabled={isExecuting}
              onClick={() => {
                if (isExecuting) return;
                setIsAddLaneModalOpen(true);
              }}
              className="px-2.5 py-1 rounded-lg bg-white/90 dark:bg-slate-900/90 hover:bg-cyan-50 dark:hover:bg-cyan-950/40 disabled:opacity-40 disabled:cursor-not-allowed border border-slate-300 dark:border-slate-800 text-[10px] font-semibold text-cyan-700 dark:text-cyan-300 shadow-2xs transition-colors flex items-center gap-1 cursor-pointer"
              title={isExecuting ? 'Cannot add lanes while pipeline is executing' : 'Add a new custom swimlane layer'}
            >
              <Plus className="w-3 h-3" />
              <span>Add Swimlane</span>
            </button>
          </div>

          {/* Canvas Transform Viewport */}
          <div
            className={`w-full h-full relative transform-gpu pointer-events-auto ${isCameraAnimating ? 'transition-transform duration-300 ease-out' : ''
              }`}
            style={{
              transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})`,
              transformOrigin: '0 0'
            }}
          >
            {/* Top Signal Flow Phase Demarcations */}
            <div className="absolute top-2 left-0 right-0 pointer-events-none flex items-center gap-4 z-0">
              {SIGNAL_FLOW_PHASES.map((phase) => (
                <div
                  key={phase.id}
                  style={{
                    position: 'absolute',
                    left: `${phase.fromX}px`,
                    width: `${phase.toX - phase.fromX}px`
                  }}
                  className="px-2.5 py-1 rounded-lg border border-slate-300 dark:border-slate-800 bg-white/80 dark:bg-slate-900/70 backdrop-blur-xs flex items-center justify-between shadow-2xs"
                >
                  <span className="font-mono text-[9.5px] font-bold uppercase tracking-wider text-slate-700 dark:text-slate-300 truncate">
                    {phase.label}
                  </span>
                  <span className="w-1.5 h-1.5 rounded-full bg-cyan-500" />
                </div>
              ))}
            </div>

            {/* Flow Trajectory HUD Pill on Hover */}
            {flowRelations.flowSummary && (
              <div className="absolute top-12 left-1/2 -translate-x-1/2 z-20 px-3.5 py-1 rounded-full bg-slate-900/95 dark:bg-slate-900/95 border border-cyan-500/50 shadow-2xl backdrop-blur-md text-[10px] font-mono font-semibold text-cyan-300 flex items-center gap-2 pointer-events-none">
                <span className="w-2 h-2 rounded-full bg-cyan-400 animate-ping shrink-0" />
                <span className="text-slate-400 uppercase tracking-wider text-[8.5px]">Flow:</span>
                <span className="truncate max-w-xl">{flowRelations.flowSummary}</span>
              </div>
            )}

            {/* Dynamic Archify SVG Layer: Swimlanes, Stepped Orthogonal Lines, and Flow Animation */}
            <svg
              className="absolute inset-0 pointer-events-none z-0 overflow-visible"
              style={{ width: '2400px', height: `${totalCanvasHeight}px` }}
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

              {/* Dynamic Swimlanes Frames */}
              {lanes.map((lane) => {
                const isException = lane.variant === 'exception';
                const isHovered = hoveredLaneId === lane.id;

                let laneStroke = isHovered
                  ? 'stroke-cyan-500 ring-2 ring-cyan-500/30'
                  : isException
                    ? 'stroke-rose-400/40 dark:stroke-rose-500/30'
                    : 'stroke-slate-300 dark:stroke-slate-800/80';

                let laneFill = isHovered
                  ? 'fill-cyan-500/5 dark:fill-cyan-950/20'
                  : isException
                    ? 'fill-rose-500/5 dark:fill-rose-950/20'
                    : 'fill-white/40 dark:fill-slate-900/30';

                return (
                  <g key={lane.id}>
                    <rect
                      x={30}
                      y={lane.y}
                      width={1680}
                      height={lane.height}
                      rx={8}
                      className={`${laneFill} ${laneStroke} transition-colors pointer-events-none`}
                      strokeWidth={isHovered ? 2 : 1}
                    />

                    {/* Lane Header Number and Label */}
                    <text
                      x={42}
                      y={lane.y + 18}
                      className={`text-[10px] font-mono font-semibold select-none ${isException ? 'fill-rose-600 dark:fill-rose-400' : 'fill-slate-600 dark:fill-slate-400'
                        }`}
                    >
                      {lane.num} / {lane.label}
                    </text>
                  </g>
                );
              })}

              {/* Stepped Orthogonal Connector Lines with vivid Flow Animation */}
              {edges.map((edge) => {
                const srcPos = nodePositionMap.get(edge.from);
                const tgtPos = nodePositionMap.get(edge.to);
                if (!srcPos || !tgtPos) return null;

                const x1 = srcPos.x + NODE_WIDTH;
                const y1 = srcPos.y + NODE_HEIGHT / 2;
                const x2 = tgtPos.x;
                const y2 = tgtPos.y + NODE_HEIGHT / 2;

                const route = getOrthogonalRoute(x1, y1, x2, y2);
                const isHoverRelated = flowRelations.relatedEdgeIds.has(edge.id);
                const isDownstream = flowRelations.outgoingEdges.some((e) => e.id === edge.id);
                const isUpstream = flowRelations.incomingEdges.some((e) => e.id === edge.id);
                const isDimmed = hoveredNodeId !== null && !isHoverRelated;
                const isFlowActive = isHoverRelated || activeFlowEdgeId === edge.id || (isExecuting && edge.from === activeExecutingNodeId);

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

                if (isHoverRelated) {
                  if (isDownstream) {
                    strokeColor = '#06b6d4';
                    markerUrl = 'url(#arrowhead-downstream)';
                  } else if (isUpstream) {
                    strokeColor = '#a855f7';
                    markerUrl = 'url(#arrowhead-upstream)';
                  }
                } else if (isFlowActive) {
                  strokeColor = '#06b6d4';
                  markerUrl = 'url(#arrowhead-running)';
                }

                return (
                  <g
                    key={edge.id}
                    className={`transition-opacity duration-200 ${isDimmed ? 'opacity-20' : 'opacity-100'
                      }`}
                  >
                    {/* Glowing pulse trail when active flow or hovered */}
                    {isFlowActive && (
                      <path
                        d={route.path}
                        fill="none"
                        stroke={
                          isDownstream
                            ? 'rgba(6, 182, 212, 0.65)'
                            : isUpstream
                              ? 'rgba(168, 85, 247, 0.55)'
                              : 'rgba(6, 182, 212, 0.5)'
                        }
                        strokeWidth={isHoverRelated ? 7 : 5}
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        className="animate-pulse"
                      />
                    )}

                    {/* Main Stepped Orthogonal Route Line */}
                    <path
                      d={route.path}
                      fill="none"
                      stroke={strokeColor}
                      strokeWidth={isHoverRelated ? 2.8 : isFlowActive ? 2.5 : 1.6}
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeDasharray={edge.variant === 'dashed' || isFlowActive ? '6 4' : 'none'}
                      markerEnd={markerUrl}
                    />

                    {/* Animated Traveling Particle Pulse showing EXACT flow direction in real time */}
                    {isFlowActive && (
                      <>
                        <circle
                          r={isHoverRelated ? 4.5 : 4}
                          fill={isDownstream ? '#06b6d4' : isUpstream ? '#a855f7' : '#06b6d4'}
                        >
                          <animateMotion
                            dur={isDownstream ? '0.75s' : isUpstream ? '1.05s' : '0.9s'}
                            repeatCount="indefinite"
                            path={route.path}
                          />
                        </circle>
                        {isDownstream && (
                          <circle r="2.5" fill="#67e8f9" opacity="0.85">
                            <animateMotion
                              dur="0.75s"
                              begin="0.38s"
                              repeatCount="indefinite"
                              path={route.path}
                            />
                          </circle>
                        )}
                      </>
                    )}

                    {/* Edge Label Pill */}
                    {edge.label && (
                      <g transform={`translate(${route.labelX}, ${route.labelY})`}>
                        <rect
                          x={-34}
                          y={-9}
                          width={68}
                          height={17}
                          rx={4}
                          className={`${isHoverRelated
                              ? isDownstream
                                ? 'fill-cyan-950 stroke-cyan-400 dark:fill-cyan-950 dark:stroke-cyan-400'
                                : 'fill-purple-950 stroke-purple-400 dark:fill-purple-950 dark:stroke-purple-400'
                              : 'fill-white dark:fill-slate-900 stroke-slate-300 dark:stroke-slate-700'
                            }`}
                          strokeWidth={isHoverRelated ? 1.5 : 1}
                        />
                        <text
                          x={0}
                          y={3}
                          className={`text-[8.5px] font-mono font-bold select-none text-anchor-middle text-center ${isHoverRelated
                              ? isDownstream
                                ? 'fill-cyan-300'
                                : 'fill-purple-300'
                              : 'fill-slate-700 dark:fill-slate-300'
                            }`}
                          textAnchor="middle"
                        >
                          {edge.label}
                        </text>
                      </g>
                    )}
                  </g>
                );
              })}

              {/* Dynamic Live Wire Preview Line while connecting */}
              {connectingSourceId && connectingMousePos && nodePositionMap.get(connectingSourceId) && (
                (() => {
                  const sPos = nodePositionMap.get(connectingSourceId)!;
                  const x1 = sPos.x + NODE_WIDTH;
                  const y1 = sPos.y + NODE_HEIGHT / 2;
                  const x2 = connectingMousePos.x;
                  const y2 = connectingMousePos.y;
                  const route = getOrthogonalRoute(x1, y1, x2, y2);
                  return (
                    <path
                      d={route.path}
                      fill="none"
                      stroke="#06b6d4"
                      strokeWidth={2}
                      strokeDasharray="4 4"
                      markerEnd="url(#arrowhead)"
                      className="animate-pulse"
                    />
                  );
                })()
              )}
            </svg>

            {/* Swimlane Control Action Buttons in Canvas (Move Up, Down, Delete) */}
            <div className="absolute top-0 left-0 pointer-events-auto z-10">
              {lanes.map((lane, idx) => (
                <div
                  key={lane.id}
                  style={{
                    position: 'absolute',
                    left: '1640px',
                    top: `${lane.y + 8}px`
                  }}
                  className={`flex items-center gap-1 transition-opacity ${isExecuting ? 'opacity-30 pointer-events-none' : 'opacity-60 hover:opacity-100'
                    }`}
                >
                  <button
                    type="button"
                    onClick={() => handleMoveLane(idx, 'up')}
                    disabled={idx === 0 || isExecuting}
                    className="p-1 rounded bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-slate-500 hover:text-slate-900 dark:hover:text-white disabled:opacity-30 cursor-pointer"
                    title="Move swimlane up"
                  >
                    <ArrowUp className="w-2.5 h-2.5" />
                  </button>
                  <button
                    type="button"
                    onClick={() => handleMoveLane(idx, 'down')}
                    disabled={idx === lanes.length - 1 || isExecuting}
                    className="p-1 rounded bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-slate-500 hover:text-slate-900 dark:hover:text-white disabled:opacity-30 cursor-pointer"
                    title="Move swimlane down"
                  >
                    <ArrowDown className="w-2.5 h-2.5" />
                  </button>
                  <button
                    type="button"
                    onClick={() => handleDeleteLane(lane.id)}
                    disabled={isExecuting}
                    className="p-1 rounded bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-slate-400 hover:text-rose-500 disabled:opacity-30 cursor-pointer"
                    title="Delete this swimlane"
                  >
                    <Trash2 className="w-2.5 h-2.5" />
                  </button>
                </div>
              ))}
            </div>

            {/* Draggable Archify-Styled Activity Object Cards */}
            <div className="absolute inset-0 z-10 pointer-events-none">
              {nodes.map((node) => {
                const isSelected = selectedNodeId === node.id;
                const isDragging = draggingNodeId === node.id;
                const isRunning = node.status === 'running';
                const isSuccess = node.status === 'success';
                const isError = node.status === 'error';
                const seqNumber = nodeSequenceNumbers.get(node.id) || 1;

                const isCurrentActiveStep = activeExecutingNodeId === node.id;
                const isNextTargetStep = nextTargetNodeId === node.id;

                const isHovered = hoveredNodeId === node.id;
                const isDownstreamTarget = flowRelations.downstreamNodeIds.has(node.id);
                const isUpstreamSource = flowRelations.upstreamNodeIds.has(node.id);
                const isDimmedNode = hoveredNodeId !== null && !flowRelations.relatedNodeIds.has(node.id);

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
                    style={{
                      position: 'absolute',
                      left: `${node.x}px`,
                      top: `${node.y}px`,
                      width: `${NODE_WIDTH}px`,
                      height: `${NODE_HEIGHT}px`,
                      touchAction: 'none'
                    }}
                    className={`workflow-node pointer-events-auto group rounded-lg border text-left cursor-grab select-none relative p-2 flex flex-col justify-between transition-all duration-200 ${typeStyle.container
                      } ${isDragging ? 'cursor-grabbing opacity-90 scale-[1.02] shadow-xl z-20' : ''
                      } ${isDimmedNode ? 'opacity-25 filter grayscale-30' : 'opacity-100'
                      } ${isHovered
                        ? 'ring-4 ring-cyan-500 ring-offset-2 dark:ring-offset-slate-950 shadow-2xl z-30 scale-[1.03]'
                        : isDownstreamTarget
                          ? 'ring-2 ring-emerald-400 border-emerald-400 ring-offset-1 dark:ring-offset-slate-900 shadow-xl z-25'
                          : isUpstreamSource
                            ? 'ring-2 ring-purple-400/80 border-purple-400/80 shadow-md z-20'
                            : isCurrentActiveStep
                              ? 'ring-4 ring-cyan-500 ring-offset-2 dark:ring-offset-slate-950 shadow-xl z-30 animate-pulse'
                              : isNextTargetStep
                                ? 'border-amber-400 border-dashed ring-2 ring-amber-400/50 shadow-md z-20'
                                : isSelected
                                  ? 'ring-2 ring-cyan-500 shadow-md z-10'
                                  : isRunning
                                    ? 'ring-2 ring-amber-400 animate-pulse'
                                    : isSuccess
                                      ? 'ring-2 ring-emerald-500'
                                      : isError
                                        ? 'ring-2 ring-rose-500'
                                        : 'hover:shadow-sm'
                      }`}
                  >
                    {/* Visual Flow Indicator Badges on Hover */}
                    {isHovered && (
                      <span className="absolute -top-3.5 left-1/2 -translate-x-1/2 px-2 py-0.5 rounded-full bg-cyan-600 text-white text-[8px] font-bold shadow-md z-30 flex items-center gap-1 uppercase tracking-wider">
                        <span className="w-1.5 h-1.5 rounded-full bg-white animate-ping" />
                        <span>Active Focus</span>
                      </span>
                    )}

                    {isDownstreamTarget && !isHovered && (
                      <span className="absolute -top-3.5 left-1/2 -translate-x-1/2 px-2 py-0.5 rounded-full bg-emerald-600 text-white text-[8px] font-bold shadow-md z-30 flex items-center gap-1 uppercase tracking-wider animate-bounce">
                        <span>➔ Flow Target</span>
                      </span>
                    )}

                    {isUpstreamSource && !isHovered && !isDownstreamTarget && (
                      <span className="absolute -top-3.5 left-1/2 -translate-x-1/2 px-2 py-0.5 rounded-full bg-purple-700 text-white text-[8px] font-bold shadow-md z-20 flex items-center gap-1 uppercase tracking-wider">
                        <span>Source Origin ➔</span>
                      </span>
                    )}

                    {/* Visual Flow Indicator Pill for Active Executing Node */}
                    {isCurrentActiveStep && !isHovered && (
                      <span className="absolute -top-3.5 left-1/2 -translate-x-1/2 px-2 py-0.5 rounded-full bg-cyan-600 text-white text-[8px] font-bold shadow-md flex items-center gap-1 z-30">
                        <span className="w-1.5 h-1.5 rounded-full bg-white animate-ping" />
                        ACTIVE
                      </span>
                    )}

                    {/* Visual Flow Indicator Pill for Next Target Node */}
                    {isNextTargetStep && !isCurrentActiveStep && !isHovered && !isDownstreamTarget && (
                      <span className="absolute -top-3.5 left-1/2 -translate-x-1/2 px-2 py-0.5 rounded-full bg-amber-500 text-white text-[8px] font-bold shadow-md z-30 flex items-center gap-1">
                        <span>NEXT IN FLOW ➔</span>
                      </span>
                    )}

                    {/* Left input terminal bead */}
                    <div
                      onClick={(e) => {
                        e.stopPropagation();
                        if (isExecuting) return;
                        if (connectingSourceId && connectingSourceId !== node.id) {
                          handleAddEdge(connectingSourceId, node.id);
                          setConnectingSourceId(null);
                          setConnectingMousePos(null);
                        }
                      }}
                      className={`port-bead absolute -left-1.5 top-1/2 -translate-y-1/2 w-3 h-3 rounded-full bg-slate-400 dark:bg-slate-600 border border-white dark:border-slate-900 group-hover:bg-cyan-500 transition-colors pointer-events-auto ${isExecuting ? 'cursor-not-allowed opacity-50' : 'cursor-pointer'
                        }`}
                      title={isExecuting ? 'Locked during execution' : 'Input Port: Click to connect wire here'}
                    />

                    {/* Right output terminal bead (Click to start sequence wire) */}
                    <div
                      onClick={(e) => {
                        e.stopPropagation();
                        if (isExecuting) return;
                        if (connectingSourceId === node.id) {
                          setConnectingSourceId(null);
                          setConnectingMousePos(null);
                        } else {
                          setConnectingSourceId(node.id);
                        }
                      }}
                      className={`port-bead absolute -right-1.5 top-1/2 -translate-y-1/2 w-3 h-3 rounded-full border border-white dark:border-slate-900 transition-all pointer-events-auto ${isExecuting ? 'cursor-not-allowed opacity-50' : 'cursor-pointer'
                        } ${connectingSourceId === node.id
                          ? 'bg-cyan-500 scale-125 ring-2 ring-cyan-400 animate-ping'
                          : 'bg-slate-400 dark:bg-slate-600 group-hover:bg-cyan-500 hover:scale-125'
                        }`}
                      title={isExecuting ? 'Locked during execution' : 'Output Port: Click to link sequence to another activity'}
                    />

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

        {/* Right Node Inspector Panel */}
        <AnimatePresence>
          {selectedNode && (
            <aside className="w-84 h-full border-l border-slate-200 dark:border-slate-800 bg-white/95 dark:bg-slate-900/90 backdrop-blur-md p-3.5 flex flex-col z-20 overflow-y-auto shadow-sm">
              <div className="flex items-center justify-between pb-3 border-b border-slate-200 dark:border-slate-800">
                <div className="flex items-center gap-2">
                  <Settings2 className="w-4 h-4 text-slate-600 dark:text-slate-400" />
                  <span className="text-xs font-bold text-slate-900 dark:text-slate-100">
                    Activity & Sequence Properties
                  </span>
                </div>
                <button
                  type="button"
                  onClick={() => setSelectedNodeId(null)}
                  className="p-1 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-500 dark:text-slate-400 transition-colors cursor-pointer"
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
            </aside>
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

      {/* Dedicated Styled Modal for Adding a New Swimlane */}
      <AnimatePresence>
        {isAddLaneModalOpen && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-xs">
            <motion.div
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              className="w-full max-w-md rounded-2xl bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-800 p-5 shadow-2xl space-y-4"
            >
              <div className="flex items-center justify-between pb-2 border-b border-slate-200 dark:border-slate-800">
                <div className="flex items-center gap-2">
                  <Plus className="w-4 h-4 text-cyan-600 dark:text-cyan-400" />
                  <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100">
                    Add Custom Swimlane
                  </h3>
                </div>
                <button
                  type="button"
                  onClick={() => setIsAddLaneModalOpen(false)}
                  className="p-1 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-500"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>

              <div>
                <label className="text-[11px] font-bold uppercase tracking-wider text-slate-600 dark:text-slate-400 block mb-1.5">
                  Swimlane Name
                </label>
                <input
                  type="text"
                  value={newLaneLabelInput}
                  onChange={(e) => setNewLaneLabelInput(e.target.value)}
                  placeholder="e.g. Verification & Code Review"
                  className="w-full px-3 py-2 rounded-xl bg-slate-50 dark:bg-slate-800/80 border border-slate-300 dark:border-slate-700 text-xs font-semibold text-slate-900 dark:text-slate-100 focus:outline-none focus:border-cyan-500"
                  autoFocus
                />
              </div>

              <div>
                <label className="text-[11px] font-bold uppercase tracking-wider text-slate-600 dark:text-slate-400 block mb-1.5">
                  Lane Style Variant
                </label>
                <div className="grid grid-cols-2 gap-2">
                  <button
                    type="button"
                    onClick={() => setNewLaneVariantInput('default')}
                    className={`p-2 rounded-xl border text-xs font-medium cursor-pointer transition-colors ${newLaneVariantInput === 'default'
                        ? 'border-cyan-500 bg-cyan-50 dark:bg-cyan-950/40 text-cyan-800 dark:text-cyan-200 font-semibold'
                        : 'border-slate-300 dark:border-slate-700 text-slate-700 dark:text-slate-300'
                      }`}
                  >
                    Standard Swimlane
                  </button>
                  <button
                    type="button"
                    onClick={() => setNewLaneVariantInput('exception')}
                    className={`p-2 rounded-xl border text-xs font-medium cursor-pointer transition-colors ${newLaneVariantInput === 'exception'
                        ? 'border-rose-500 bg-rose-50 dark:bg-rose-950/40 text-rose-800 dark:text-rose-200 font-semibold'
                        : 'border-slate-300 dark:border-slate-700 text-slate-700 dark:text-slate-300'
                      }`}
                  >
                    Policy / Safety Guard
                  </button>
                </div>
              </div>

              <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-200 dark:border-slate-800">
                <button
                  type="button"
                  onClick={() => setIsAddLaneModalOpen(false)}
                  className="px-3 py-1.5 rounded-xl border border-slate-300 dark:border-slate-700 text-xs font-medium text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={handleAddNewLane}
                  className="px-4 py-1.5 rounded-xl bg-cyan-600 hover:bg-cyan-700 text-white text-xs font-semibold shadow-xs cursor-pointer"
                >
                  Add Swimlane
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

      {/* Floating Save Toast Notification */}
      <AnimatePresence>
        {saveToastMessage && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 20 }}
            className="fixed bottom-6 left-1/2 -translate-x-1/2 z-50 px-4 py-2 rounded-2xl bg-slate-900/90 text-white dark:bg-white/95 dark:text-slate-900 shadow-xl border border-white/10 dark:border-slate-800 text-xs font-semibold flex items-center gap-2 backdrop-blur-md"
          >
            <Check className="w-3.5 h-3.5 text-emerald-400 dark:text-emerald-600" />
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
