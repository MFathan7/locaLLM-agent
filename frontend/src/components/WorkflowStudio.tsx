import { useState, useRef, useMemo, useEffect } from 'react';
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
  Grid,
  Check,
  Download,
  Settings2,
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
  Move
} from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';
import { ThemeToggle } from './ThemeToggle';
import type { Workspace } from '../types';

export type WorkflowLane = 'ui' | 'agent' | 'policy' | 'tools' | 'evidence';

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
}

// Signal Flow sequence phases definition
const SIGNAL_FLOW_PHASES: WorkflowPhase[] = [
  { id: 'intake', label: 'Phase 1: Intake & Context', fromX: 20, toX: 280, variant: 'default' },
  { id: 'reasoning', label: 'Phase 2: Planning & Policy Governance', fromX: 290, toX: 830, variant: 'emphasis' },
  { id: 'execution', label: 'Phase 3: Specialist Execution', fromX: 840, toX: 1130, variant: 'security' },
  { id: 'evidence', label: 'Phase 4: Evidence & Blackboard', fromX: 1140, toX: 1460, variant: 'dashed' }
];

// Starter DAG using LocaLLM Multi-Agent Architecture
const DEFAULT_NODES: WorkflowNode[] = [
  {
    id: 'user-intake',
    lane: 'ui',
    type: 'frontend',
    title: 'User Objective',
    subtitle: 'Task prompt and instructions',
    tag: 'intake',
    x: 40,
    y: 190,
    status: 'idle',
    config: {
      query: 'Analyze project codebase and generate optimization plan',
      workspace: 'default'
    }
  },
  {
    id: 'supervisor-planner',
    lane: 'agent',
    type: 'backend',
    title: 'Supervisor Planner',
    subtitle: 'Hierarchical task decomposition',
    tag: 'context-aware',
    x: 330,
    y: 170,
    status: 'idle',
    config: {
      model: 'gemma4:12b',
      workspace: 'default',
      directive: 'Decompose task, delegate to specialists, and maintain blackboard state',
      timeout: 300
    }
  },
  {
    id: 'policy-gate',
    lane: 'policy',
    type: 'security',
    title: 'Policy & Safety Guard',
    subtitle: 'Circuit breaker and permission check',
    tag: 'policy-gate',
    x: 600,
    y: 70,
    status: 'idle',
    config: {
      policy: 'ask',
      circuit_breaker: 'max 2 consecutive identical failures',
      workspace: 'default'
    }
  },
  {
    id: 'researcher-agent',
    lane: 'agent',
    type: 'messagebus',
    title: 'Research Specialist',
    subtitle: 'Workspace exploration & web search',
    tag: 'read-only',
    x: 600,
    y: 280,
    status: 'idle',
    config: {
      model: 'gemma4:12b',
      workspace: 'default',
      tools: ['search_web', 'fetch_web', 'read_file', 'list_directory'],
      timeout: 300
    }
  },
  {
    id: 'coder-agent',
    lane: 'agent',
    type: 'messagebus',
    title: 'Coder Specialist',
    subtitle: 'Code implementation and self-testing',
    tag: 'code-exec',
    x: 880,
    y: 120,
    status: 'idle',
    config: {
      model: 'gemma4:12b',
      workspace: 'default',
      tools: ['patch_file', 'write_file', 'check_syntax', 'execute_command'],
      timeout: 300
    }
  },
  {
    id: 'blackboard-state',
    lane: 'evidence',
    type: 'database',
    title: 'Blackboard State',
    subtitle: 'Synthesizes findings & verified diffs',
    tag: 'trace-evidence',
    x: 1170,
    y: 190,
    status: 'idle',
    config: {
      workspace: 'default',
      directive: 'Consolidate specialist observations and output final response'
    }
  }
];

const DEFAULT_EDGES: WorkflowEdge[] = [
  { id: 'e1', from: 'user-intake', to: 'supervisor-planner', label: 'prompt', variant: 'emphasis' },
  { id: 'e2', from: 'supervisor-planner', to: 'policy-gate', label: 'safety check', variant: 'security' },
  { id: 'e3', from: 'supervisor-planner', to: 'researcher-agent', label: 'research task', variant: 'default' },
  { id: 'e4', from: 'policy-gate', to: 'coder-agent', label: 'authorized', variant: 'emphasis' },
  { id: 'e5', from: 'researcher-agent', to: 'coder-agent', label: 'findings', variant: 'dashed' },
  { id: 'e6', from: 'coder-agent', to: 'blackboard-state', label: 'code diffs', variant: 'emphasis' },
  { id: 'e7', from: 'researcher-agent', to: 'blackboard-state', label: 'evidence', variant: 'dashed' }
];

// Activity catalog grouped strictly by LocaLLM 5 Lane Taxonomy
const ACTIVITY_CATALOG = [
  {
    lane: 'ui' as WorkflowLane,
    laneTitle: 'Lane 1: User Interface & Intake',
    items: [
      {
        lane: 'ui' as WorkflowLane,
        type: 'frontend' as const,
        title: 'User Objective Input',
        subtitle: 'Interactive task entrypoint for agent flow',
        tag: 'intake',
        icon: Sparkles,
        color: 'text-sky-600 dark:text-sky-400',
        defaultConfig: { query: 'Analyze project codebase', workspace: 'default' }
      },
      {
        lane: 'ui' as WorkflowLane,
        type: 'external' as const,
        title: 'Webhook Trigger',
        subtitle: 'External HTTP payload trigger (e.g. GitHub/n8n)',
        tag: 'webhook',
        icon: Globe,
        color: 'text-sky-600 dark:text-sky-400',
        defaultConfig: { endpoint: '/api/v1/webhook', workspace: 'default' }
      }
    ]
  },
  {
    lane: 'agent' as WorkflowLane,
    laneTitle: 'Lane 2: Agent Runtime',
    items: [
      {
        lane: 'agent' as WorkflowLane,
        type: 'backend' as const,
        title: 'Supervisor Planner',
        subtitle: 'Decomposes mission, delegates subtasks, and synthesizes',
        tag: 'orchestrator',
        icon: Bot,
        color: 'text-blue-600 dark:text-blue-400',
        defaultConfig: { model: 'gemma4:12b', workspace: 'default', directive: 'Plan and coordinate subtasks' }
      },
      {
        lane: 'agent' as WorkflowLane,
        type: 'messagebus' as const,
        title: 'Research Specialist',
        subtitle: 'Retrieval agent for files, web data, and skills',
        tag: 'researcher',
        icon: Search,
        color: 'text-cyan-600 dark:text-cyan-400',
        defaultConfig: { model: 'gemma4:12b', workspace: 'default', tools: ['search_web', 'fetch_web', 'read_file'] }
      },
      {
        lane: 'agent' as WorkflowLane,
        type: 'messagebus' as const,
        title: 'Coder Specialist',
        subtitle: 'Code editing with patch_file and terminal self-testing',
        tag: 'coder',
        icon: Terminal,
        color: 'text-emerald-600 dark:text-emerald-400',
        defaultConfig: { model: 'gemma4:12b', workspace: 'default', tools: ['patch_file', 'check_syntax', 'execute_command'] }
      },
      {
        lane: 'agent' as WorkflowLane,
        type: 'messagebus' as const,
        title: 'Auditor Specialist',
        subtitle: 'Runs diagnostic commands, pytest, and syntax reviews',
        tag: 'auditor',
        icon: Cpu,
        color: 'text-amber-600 dark:text-amber-400',
        defaultConfig: { model: 'gemma4:12b', workspace: 'default', tools: ['check_syntax', 'execute_command'] }
      }
    ]
  },
  {
    lane: 'policy' as WorkflowLane,
    laneTitle: 'Lane 3: Policy & Safety Gates',
    items: [
      {
        lane: 'policy' as WorkflowLane,
        type: 'security' as const,
        title: 'Approval Gate',
        subtitle: 'Requires human consent before mutating actions',
        tag: 'policy-gate',
        icon: ShieldCheck,
        color: 'text-rose-600 dark:text-rose-400',
        defaultConfig: { policy: 'ask', workspace: 'default' }
      },
      {
        lane: 'policy' as WorkflowLane,
        type: 'security' as const,
        title: 'Circuit Breaker Guard',
        subtitle: 'Halts execution after 2 consecutive identical failures',
        tag: 'safety-break',
        icon: AlertTriangle,
        color: 'text-rose-600 dark:text-rose-400',
        defaultConfig: { max_failures: 2, workspace: 'default' }
      }
    ]
  },
  {
    lane: 'tools' as WorkflowLane,
    laneTitle: 'Lane 4: Tool Execution',
    items: [
      {
        lane: 'tools' as WorkflowLane,
        type: 'messagebus' as const,
        title: 'Shell Command Runner',
        subtitle: 'execute_command subprocess in project directory',
        tag: 'subprocess',
        icon: Terminal,
        color: 'text-amber-600 dark:text-amber-400',
        defaultConfig: { command: 'pytest', workspace: 'default' }
      },
      {
        lane: 'tools' as WorkflowLane,
        type: 'messagebus' as const,
        title: 'Filesystem Operator',
        subtitle: 'patch_file, write_file, and read_file handlers',
        tag: 'filesystem',
        icon: FileText,
        color: 'text-amber-600 dark:text-amber-400',
        defaultConfig: { path: '.', workspace: 'default' }
      },
      {
        lane: 'tools' as WorkflowLane,
        type: 'cloud' as const,
        title: 'Web Search & Fetch',
        subtitle: 'Real-time online search and content fetcher',
        tag: 'online-web',
        icon: Globe,
        color: 'text-cyan-600 dark:text-cyan-400',
        defaultConfig: { provider: 'auto', workspace: 'default' }
      }
    ]
  },
  {
    lane: 'evidence' as WorkflowLane,
    laneTitle: 'Lane 5: Evidence & Memory',
    items: [
      {
        lane: 'evidence' as WorkflowLane,
        type: 'database' as const,
        title: 'Blackboard State Sink',
        subtitle: 'Central blackboard aggregating findings and diffs',
        tag: 'blackboard',
        icon: Database,
        color: 'text-purple-600 dark:text-purple-400',
        defaultConfig: { workspace: 'default' }
      },
      {
        lane: 'evidence' as WorkflowLane,
        type: 'database' as const,
        title: 'Trace Event Log',
        subtitle: 'Live chronological audit log of all agent turns',
        tag: 'event-stream',
        icon: Layers,
        color: 'text-purple-600 dark:text-purple-400',
        defaultConfig: { workspace: 'default' }
      }
    ]
  }
];

export function WorkflowStudio({ workspaces = [], activeWorkspace = 'default' }: WorkflowStudioProps) {
  const [nodes, setNodes] = useState<WorkflowNode[]>(DEFAULT_NODES);
  const [edges, setEdges] = useState<WorkflowEdge[]>(DEFAULT_EDGES);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>('supervisor-planner');
  const [zoom, setZoom] = useState<number>(1);
  const [pan, setPan] = useState<{ x: number; y: number }>({ x: 0, y: 0 });
  const [isPanning, setIsPanning] = useState<boolean>(false);
  const [isGridVisible, setIsGridVisible] = useState<boolean>(true);
  const [isLibraryOpen, setIsLibraryOpen] = useState<boolean>(true);
  const [isDrawerOpen, setIsDrawerOpen] = useState<boolean>(false);
  const [isExecuting, setIsExecuting] = useState<boolean>(false);
  const [executionMode, setExecutionMode] = useState<'real' | 'simulation'>('real');
  const [executionLogs, setExecutionLogs] = useState<ExecutionEvent[]>([]);
  const [activeTaskId, setActiveTaskId] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [workspaceList, setWorkspaceList] = useState<Workspace[]>(workspaces);

  const canvasRef = useRef<HTMLDivElement>(null);
  const panStartRef = useRef<{ x: number; y: number }>({ x: 0, y: 0 });
  const pollingRef = useRef<any>(null);

  // Fetch workspaces if not passed via props
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
        .catch(() => {});
    }
  }, [workspaces]);

  const selectedNode = useMemo(() => {
    return nodes.find((n) => n.id === selectedNodeId) || null;
  }, [nodes, selectedNodeId]);

  const handleBackToChat = () => {
    window.location.href = '/';
  };

  // Canvas Pan handlers
  const handleCanvasMouseDown = (e: React.MouseEvent) => {
    // Only pan if clicking empty canvas or background layer
    const target = e.target as HTMLElement;
    if (target.dataset?.canvasBg || target === canvasRef.current || target.tagName === 'svg') {
      setIsPanning(true);
      panStartRef.current = {
        x: e.clientX - pan.x,
        y: e.clientY - pan.y
      };
    }
  };

  const handleCanvasMouseMove = (e: React.MouseEvent) => {
    if (isPanning) {
      setPan({
        x: Math.round(e.clientX - panStartRef.current.x),
        y: Math.round(e.clientY - panStartRef.current.y)
      });
    }
  };

  const handleCanvasMouseUp = () => {
    setIsPanning(false);
  };

  const handleResetView = () => {
    setZoom(1);
    setPan({ x: 0, y: 0 });
  };

  const handleNodeDrag = (id: string, deltaX: number, deltaY: number) => {
    setNodes((prev) =>
      prev.map((n) => {
        if (n.id === id) {
          return {
            ...n,
            x: Math.max(20, Math.round(n.x + deltaX)),
            y: Math.max(20, Math.round(n.y + deltaY))
          };
        }
        return n;
      })
    );
  };

  const handleAddNode = (template: typeof ACTIVITY_CATALOG[0]['items'][0]) => {
    const newId = `${template.tag}-${Date.now().toString(36)}`;
    const newNode: WorkflowNode = {
      id: newId,
      lane: template.lane,
      type: template.type,
      title: template.title,
      subtitle: template.subtitle,
      tag: template.tag,
      x: 350 + (nodes.length % 5) * 35 - pan.x / zoom,
      y: 180 + (nodes.length % 5) * 35 - pan.y / zoom,
      status: 'idle',
      config: {
        ...template.defaultConfig,
        workspace: activeWorkspace || 'default'
      }
    };
    setNodes((prev) => [...prev, newNode]);
    setSelectedNodeId(newId);
  };

  const handleDeleteNode = (id: string) => {
    setNodes((prev) => prev.filter((n) => n.id !== id));
    setEdges((prev) => prev.filter((e) => e.from !== id && e.to !== id));
    if (selectedNodeId === id) {
      setSelectedNodeId(null);
    }
  };

  // Map real agent events from backend to canvas node statuses
  const applyEventToNodes = (ev: ExecutionEvent) => {
    const agentName = ev.agent.toLowerCase();
    const evType = ev.event_type.toLowerCase();

    setNodes((prev) =>
      prev.map((n) => {
        const isSupervisor = n.id.includes('supervisor') && agentName.includes('supervisor');
        const isResearcher = (n.id.includes('researcher') || n.tag === 'researcher') && agentName.includes('research');
        const isCoder = (n.id.includes('coder') || n.tag === 'coder') && agentName.includes('coder');
        const isAuditor = (n.id.includes('auditor') || n.tag === 'auditor') && agentName.includes('auditor');
        const isBlackboard = n.id.includes('blackboard') || n.lane === 'evidence';

        if (isSupervisor || isResearcher || isCoder || isAuditor) {
          if (evType === 'done' || evType === 'complete' || evType === 'subtask_done') {
            return { ...n, status: 'success' };
          }
          if (evType === 'error' || evType === 'failed') {
            return { ...n, status: 'error' };
          }
          return { ...n, status: 'running' };
        }

        if (isBlackboard && (evType === 'complete' || evType === 'subtask_done')) {
          return { ...n, status: evType === 'complete' ? 'success' : 'running' };
        }

        return n;
      })
    );
  };

  // Run real execution through API Gateway or fallback to step simulation
  const handleStartFlow = async () => {
    if (isExecuting) return;
    setIsExecuting(true);
    setIsDrawerOpen(true);
    setExecutionLogs([]);

    // Reset node statuses
    setNodes((prev) => prev.map((n) => ({ ...n, status: 'idle' })));

    const intakeNode = nodes.find((n) => n.lane === 'ui' && n.config?.query);
    const taskQuery = intakeNode?.config?.query || 'Analyze project codebase and generate optimization plan';

    // Collect per-agent workspace assignments
    const supervisorNode = nodes.find((n) => n.id.includes('supervisor'));
    const primaryWs = supervisorNode?.config?.workspace || intakeNode?.config?.workspace || activeWorkspace || 'default';

    const agentWorkspaces: Record<string, string> = {};
    nodes.forEach((n) => {
      if (n.lane === 'agent' && n.config?.workspace) {
        if (n.id.includes('research') || n.tag === 'researcher') {
          agentWorkspaces.researcher = n.config.workspace;
        } else if (n.id.includes('coder') || n.tag === 'coder') {
          agentWorkspaces.coder = n.config.workspace;
        } else if (n.id.includes('auditor') || n.tag === 'auditor') {
          agentWorkspaces.auditor = n.config.workspace;
        } else if (n.id.includes('supervisor')) {
          agentWorkspaces.supervisor = n.config.workspace;
        }
      }
    });

    if (executionMode === 'real') {
      try {
        const runRes = await fetch('/api/agent/run', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            task: taskQuery,
            workspace: primaryWs,
            agent_workspaces: agentWorkspaces,
            async: true
          })
        });

        if (runRes.ok) {
          const runData = await runRes.json();
          const taskId = runData.task_id;
          setActiveTaskId(taskId);

          const initialEv: ExecutionEvent = {
            agent: 'Supervisor',
            event_type: 'start',
            message: `Initiated live agent task (${taskId}) [ws: ${primaryWs}]: ${taskQuery}`,
            timestamp: new Date().toLocaleTimeString()
          };
          setExecutionLogs([initialEv]);
          applyEventToNodes(initialEv);

          // Poll live status and events every 600ms
          pollingRef.current = setInterval(async () => {
            try {
              const statusRes = await fetch(`/api/agent/status?task_id=${taskId}`);
              if (statusRes.ok) {
                const sData = await statusRes.json();
                if (sData.events && Array.isArray(sData.events)) {
                  setExecutionLogs(sData.events);
                  if (sData.events.length > 0) {
                    const latest = sData.events[sData.events.length - 1];
                    applyEventToNodes(latest);
                  }
                }

                if (sData.status === 'completed' || sData.status === 'failed') {
                  clearInterval(pollingRef.current);
                  setIsExecuting(false);
                  setNodes((prev) =>
                    prev.map((n) =>
                      n.id.includes('blackboard')
                        ? { ...n, status: sData.status === 'completed' ? 'success' : 'error' }
                        : n
                    )
                  );
                }
              }
            } catch {
              // Ignore polling blips
            }
          }, 600);
          return;
        }
      } catch (err: any) {
        console.warn('Backend agent API offline, transitioning to local simulation:', err);
      }
    }

    // Step-by-step visual simulation fallback
    const simSteps: { id: string; agent: string; msg: string }[] = [
      { id: 'user-intake', agent: 'Intake', msg: `Received user objective: "${taskQuery}"` },
      { id: 'supervisor-planner', agent: 'Supervisor', msg: `Analyzing requirements in workspace '${primaryWs}' and preparing delegation strategy` },
      { id: 'policy-gate', agent: 'PolicyGate', msg: 'Inspecting permissions: Mutation policy set to verified scope' },
      { id: 'researcher-agent', agent: 'ResearchAgent', msg: `Executing read_file in workspace '${agentWorkspaces.researcher || primaryWs}'` },
      { id: 'coder-agent', agent: 'CoderAgent', msg: `Running syntax checks and validating implementation in workspace '${agentWorkspaces.coder || primaryWs}'` },
      { id: 'blackboard-state', agent: 'Blackboard', msg: 'Mission completed cleanly: 0 errors recorded' }
    ];

    simSteps.forEach((step, idx) => {
      setTimeout(() => {
        setNodes((prev) =>
          prev.map((n) => {
            if (n.id === step.id) return { ...n, status: 'running' };
            return n;
          })
        );
        const ev: ExecutionEvent = {
          agent: step.agent,
          event_type: 'step',
          message: step.msg,
          timestamp: new Date().toLocaleTimeString()
        };
        setExecutionLogs((l) => [...l, ev]);
      }, idx * 1000);

      setTimeout(() => {
        setNodes((prev) =>
          prev.map((n) => {
            if (n.id === step.id) return { ...n, status: 'success' };
            return n;
          })
        );
        if (idx === simSteps.length - 1) {
          setIsExecuting(false);
        }
      }, idx * 1000 + 800);
    });
  };

  const handleStopFlow = () => {
    if (pollingRef.current) {
      clearInterval(pollingRef.current);
    }
    setIsExecuting(false);
  };

  useEffect(() => {
    return () => {
      if (pollingRef.current) clearInterval(pollingRef.current);
    };
  }, []);

  const handleExportWorkflowJson = () => {
    const workflowPayload = {
      schema_version: 2,
      diagram_type: 'workflow',
      meta: {
        title: 'LocaLLM Agent Workflow',
        animation: 'trace',
        visual_preset: 'signal-flow',
        quality_profile: 'showcase',
        output: 'locallm-agent-workflow.json'
      },
      lanes: [
        { id: 'ui', label: 'User Interface & Intake' },
        { id: 'agent', label: 'Agent Runtime' },
        { id: 'policy', label: 'Policy & Safety Governance', variant: 'exception' },
        { id: 'tools', label: 'Tool Execution' },
        { id: 'evidence', label: 'Evidence & Blackboard' }
      ],
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
    dl.setAttribute('download', 'locallm-agent-workflow.json');
    document.body.appendChild(dl);
    dl.click();
    dl.remove();
  };

  const nodePositionMap = useMemo(() => {
    const map = new Map<string, { x: number; y: number }>();
    nodes.forEach((n) => {
      map.set(n.id, { x: n.x, y: n.y });
    });
    return map;
  }, [nodes]);

  const filteredCatalog = useMemo(() => {
    if (!searchQuery.trim()) return ACTIVITY_CATALOG;
    const q = searchQuery.toLowerCase();
    return ACTIVITY_CATALOG.map((cat) => ({
      ...cat,
      items: cat.items.filter(
        (item) => item.title.toLowerCase().includes(q) || item.subtitle.toLowerCase().includes(q)
      )
    })).filter((cat) => cat.items.length > 0);
  }, [searchQuery]);

  return (
    <div className="h-screen w-screen flex flex-col bg-slate-100 dark:bg-slate-950 text-slate-800 dark:text-slate-100 overflow-hidden font-sans select-none">
      {/* Precision Top Toolbar */}
      <header className="h-12 shrink-0 border-b border-slate-200 dark:border-slate-800 bg-white/95 dark:bg-slate-900/90 backdrop-blur-md px-3 flex items-center justify-between z-30 shadow-2xs">
        <div className="flex items-center gap-2.5">
          <button
            type="button"
            onClick={handleBackToChat}
            className="p-1.5 rounded-lg text-slate-700 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white hover:bg-slate-200/70 dark:hover:bg-slate-800 transition-colors flex items-center gap-1.5 text-xs font-medium cursor-pointer"
            title="Return to Chat"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">Back to Chat</span>
          </button>

          <div className="h-4 w-px bg-slate-300 dark:bg-slate-800" />

          <div className="flex items-center gap-2">
            <Workflow className="w-4 h-4 text-sky-600 dark:text-sky-400" />
            <span className="text-xs font-bold text-slate-900 dark:text-slate-100 tracking-tight">
              LocaLLM Agent Workflow
            </span>
            <span className="font-mono text-[10px] px-1.5 py-0.5 rounded-md bg-slate-200/80 dark:bg-slate-800 text-slate-700 dark:text-slate-300">
              Signal Flow · {nodes.length} nodes
            </span>
          </div>
        </div>

        {/* Center Canvas Scale & Navigation Controls */}
        <div className="hidden md:flex items-center gap-1 px-1.5 py-1 rounded-xl bg-slate-100 dark:bg-slate-800/80 border border-slate-300 dark:border-slate-700/60">
          <button
            type="button"
            onClick={() => setZoom((z) => Math.max(0.5, Number((z - 0.1).toFixed(1))))}
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
            onClick={() => setZoom((z) => Math.min(1.8, Number((z + 0.1).toFixed(1))))}
            className="p-1 rounded-lg hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300 transition-colors cursor-pointer"
            title="Zoom in"
          >
            <ZoomIn className="w-3.5 h-3.5" />
          </button>
          <div className="h-3 w-px bg-slate-300 dark:bg-slate-700 mx-0.5" />
          <button
            type="button"
            onClick={handleResetView}
            className="p-1 rounded-lg hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300 transition-colors cursor-pointer flex items-center gap-1"
            title="Reset Pan & Scale (100%)"
          >
            <Maximize2 className="w-3.5 h-3.5" />
          </button>
          <button
            type="button"
            onClick={() => setIsGridVisible((v) => !v)}
            className={`p-1 rounded-lg transition-colors cursor-pointer ${
              isGridVisible
                ? 'bg-slate-200 dark:bg-slate-700 text-slate-900 dark:text-white font-medium'
                : 'text-slate-500 hover:bg-slate-200 dark:hover:bg-slate-700'
            }`}
            title="Toggle background grid"
          >
            <Grid className="w-3.5 h-3.5" />
          </button>
        </div>

        {/* Right Action Controls */}
        <div className="flex items-center gap-1.5">
          {/* Mode switch */}
          <div className="hidden lg:flex items-center p-0.5 rounded-lg bg-slate-200/70 dark:bg-slate-800 border border-slate-300 dark:border-slate-700 text-[10px] font-medium">
            <button
              type="button"
              onClick={() => setExecutionMode('real')}
              className={`px-2 py-1 rounded-md transition-colors cursor-pointer flex items-center gap-1 ${
                executionMode === 'real'
                  ? 'bg-white dark:bg-slate-900 text-slate-900 dark:text-white shadow-xs font-semibold'
                  : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
              }`}
            >
              <Radio className="w-3 h-3 text-sky-500" />
              <span>Live Engine</span>
            </button>
            <button
              type="button"
              onClick={() => setExecutionMode('simulation')}
              className={`px-2 py-1 rounded-md transition-colors cursor-pointer ${
                executionMode === 'simulation'
                  ? 'bg-white dark:bg-slate-900 text-slate-900 dark:text-white shadow-xs font-semibold'
                  : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
              }`}
            >
              <span>Step Sim</span>
            </button>
          </div>

          <button
            type="button"
            onClick={() => setIsDrawerOpen((v) => !v)}
            className={`px-2.5 py-1.5 rounded-xl text-xs font-medium border transition-colors flex items-center gap-1.5 cursor-pointer active:scale-[0.98] ${
              isDrawerOpen
                ? 'bg-slate-200 dark:bg-slate-800 text-slate-900 dark:text-white border-slate-300 dark:border-slate-700'
                : 'bg-white dark:bg-slate-900 text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 border-slate-300 dark:border-slate-700'
            }`}
            title="Toggle Live Event Log Drawer"
          >
            <Terminal className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">Event Log</span>
            {executionLogs.length > 0 && (
              <span className="w-1.5 h-1.5 rounded-full bg-sky-500 animate-pulse" />
            )}
          </button>

          <button
            type="button"
            onClick={handleExportWorkflowJson}
            className="px-2.5 py-1.5 rounded-xl text-xs font-medium bg-white dark:bg-slate-900 text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 border border-slate-300 dark:border-slate-700 transition-colors flex items-center gap-1.5 cursor-pointer active:scale-[0.98]"
            title="Export LocaLLM Workflow JSON Schema"
          >
            <Download className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">Export JSON</span>
          </button>

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
        {/* Left Activity Catalog Drawer */}
        <div
          className={`h-full border-r border-slate-200 dark:border-slate-800 bg-white/95 dark:bg-slate-900/90 backdrop-blur-sm transition-all duration-200 z-20 flex flex-col ${
            isLibraryOpen ? 'w-68' : 'w-0'
          } overflow-hidden`}
        >
          <div className="p-3 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between">
            <div>
              <span className="text-[11px] font-bold uppercase tracking-wider text-slate-700 dark:text-slate-300 block leading-tight">
                Activity Palette
              </span>
              <span className="text-[10px] text-slate-500 dark:text-slate-400">
                5 Lanes · Signal Flow Nodes
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
                        onClick={() => handleAddNode(item)}
                        className="group p-2 rounded-xl bg-white dark:bg-slate-800/80 border border-slate-200 dark:border-slate-700/70 hover:border-sky-500/60 hover:bg-slate-50 dark:hover:bg-slate-800 transition-all cursor-pointer flex items-center justify-between shadow-2xs"
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
                        <Plus className="w-3 h-3 text-slate-400 group-hover:text-sky-500 opacity-0 group-hover:opacity-100 transition-opacity shrink-0" />
                      </div>
                    );
                  })}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Toggle Library Button if closed */}
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

        {/* Center Live Canvas with Pan & Zoom */}
        <main
          ref={canvasRef}
          data-canvas-bg="true"
          onMouseDown={handleCanvasMouseDown}
          onMouseMove={handleCanvasMouseMove}
          onMouseUp={handleCanvasMouseUp}
          onMouseLeave={handleCanvasMouseUp}
          className="flex-1 h-full relative overflow-hidden bg-slate-200/60 dark:bg-slate-950 transition-colors"
          style={{
            backgroundImage: isGridVisible
              ? 'radial-gradient(circle, currentColor 1px, transparent 1px)'
              : 'none',
            backgroundPosition: `${pan.x}px ${pan.y}px`,
            backgroundSize: `${24 * zoom}px ${24 * zoom}px`,
            color: 'var(--grid-dot-color, rgba(100, 116, 139, 0.28))',
            cursor: isPanning ? 'grabbing' : 'grab'
          }}
        >
          {/* Pan Navigation Hint */}
          <div className="absolute bottom-3 left-3 z-10 pointer-events-none flex items-center gap-2 text-[10px] font-mono text-slate-600 dark:text-slate-400 bg-white/80 dark:bg-slate-900/80 px-2 py-1 rounded-lg border border-slate-300/80 dark:border-slate-800 shadow-2xs">
            <Move className="w-3 h-3 text-slate-500" />
            <span>Drag canvas to pan · Offset: ({pan.x}, {pan.y})</span>
          </div>

          {/* Canvas Transform Viewport */}
          <div
            className="w-full h-full relative transform-gpu"
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
                  className="px-2.5 py-1 rounded-lg border border-slate-300 dark:border-slate-800 bg-white/70 dark:bg-slate-900/60 backdrop-blur-xs flex items-center justify-between shadow-2xs"
                >
                  <span className="font-mono text-[10px] font-bold uppercase tracking-wider text-slate-700 dark:text-slate-300 truncate">
                    {phase.label}
                  </span>
                  <span className="w-1.5 h-1.5 rounded-full bg-sky-500" />
                </div>
              ))}
            </div>

            {/* Horizontal Swimlane Guide Lines */}
            <div className="absolute top-12 left-0 right-0 pointer-events-none opacity-40 dark:opacity-20 flex flex-col gap-28">
              <div className="h-px border-t border-dashed border-slate-400 dark:border-slate-600 w-[1800px]" />
              <div className="h-px border-t border-dashed border-slate-400 dark:border-slate-600 w-[1800px]" />
              <div className="h-px border-t border-dashed border-slate-400 dark:border-slate-600 w-[1800px]" />
            </div>

            {/* SVG Connection Layer */}
            <svg
              className="absolute inset-0 pointer-events-none z-0 overflow-visible"
              style={{ width: '2400px', height: '1600px' }}
            >
              <defs>
                <linearGradient id="edge-flow-grad" x1="0%" y1="0%" x2="100%" y2="0%">
                  <stop offset="0%" stopColor="#38bdf8" stopOpacity="0.4" />
                  <stop offset="50%" stopColor="#38bdf8" stopOpacity="1" />
                  <stop offset="100%" stopColor="#0ea5e9" stopOpacity="0.4" />
                </linearGradient>
              </defs>

              {edges.map((edge) => {
                const srcPos = nodePositionMap.get(edge.from);
                const tgtPos = nodePositionMap.get(edge.to);
                if (!srcPos || !tgtPos) return null;

                const x1 = srcPos.x + 250;
                const y1 = srcPos.y + 45;
                const x2 = tgtPos.x;
                const y2 = tgtPos.y + 45;

                const dx = Math.max(45, (x2 - x1) * 0.45);
                const pathD = `M ${x1} ${y1} C ${x1 + dx} ${y1}, ${x2 - dx} ${y2}, ${x2} ${y2}`;

                const isEdgeRunning = isExecuting;

                let strokeColor = '#94a3b8';
                if (edge.variant === 'security') strokeColor = '#f43f5e';
                if (edge.variant === 'emphasis') strokeColor = '#0284c7';
                if (edge.variant === 'dashed') strokeColor = '#a855f7';
                if (isEdgeRunning) strokeColor = '#38bdf8';

                return (
                  <g key={edge.id}>
                    {/* Background glow path when executing */}
                    {isEdgeRunning && (
                      <path
                        d={pathD}
                        fill="none"
                        stroke="rgba(56, 189, 248, 0.35)"
                        strokeWidth={6}
                        strokeLinecap="round"
                      />
                    )}

                    {/* Main connection line */}
                    <path
                      d={pathD}
                      fill="none"
                      stroke={strokeColor}
                      strokeWidth={isEdgeRunning ? 2.5 : 1.8}
                      strokeDasharray={edge.variant === 'dashed' || isEdgeRunning ? '6 4' : 'none'}
                      className={isEdgeRunning ? 'animate-pulse' : ''}
                    />

                    {/* Edge Label */}
                    {edge.label && (
                      <g>
                        <rect
                          x={(x1 + x2) / 2 - 28}
                          y={(y1 + y2) / 2 - 16}
                          width={56}
                          height={16}
                          rx={4}
                          className="fill-white dark:fill-slate-900 stroke-slate-300 dark:stroke-slate-700"
                          strokeWidth={1}
                        />
                        <text
                          x={(x1 + x2) / 2}
                          y={(y1 + y2) / 2 - 4}
                          fill="currentColor"
                          className="text-[9px] font-mono font-medium fill-slate-700 dark:fill-slate-300 select-none text-anchor-middle text-center"
                          textAnchor="middle"
                        >
                          {edge.label}
                        </text>
                      </g>
                    )}

                    {/* Target End Terminal Bead */}
                    <circle cx={x2} cy={y2} r={3.5} fill={strokeColor} />
                  </g>
                );
              })}
            </svg>

            {/* Draggable Node Cards */}
            <div className="absolute inset-0 z-10 pointer-events-none">
              {nodes.map((node) => {
                const isSelected = selectedNodeId === node.id;
                const isRunning = node.status === 'running';
                const isSuccess = node.status === 'success';
                const isError = node.status === 'error';

                let laneBorderColor = 'border-slate-300 dark:border-slate-700';
                let laneAccentBar = 'bg-slate-400';
                let laneBadgeClass = 'bg-slate-200 text-slate-800 dark:bg-slate-800 dark:text-slate-300';

                if (node.lane === 'ui') {
                  laneAccentBar = 'bg-sky-500';
                  laneBadgeClass = 'bg-sky-100 text-sky-800 dark:bg-sky-950/80 dark:text-sky-300';
                } else if (node.lane === 'agent') {
                  laneAccentBar = 'bg-blue-500';
                  laneBadgeClass = 'bg-blue-100 text-blue-800 dark:bg-blue-950/80 dark:text-blue-300';
                } else if (node.lane === 'policy') {
                  laneAccentBar = 'bg-rose-500';
                  laneBadgeClass = 'bg-rose-100 text-rose-800 dark:bg-rose-950/80 dark:text-rose-300';
                } else if (node.lane === 'tools') {
                  laneAccentBar = 'bg-amber-500';
                  laneBadgeClass = 'bg-amber-100 text-amber-800 dark:bg-amber-950/80 dark:text-amber-300';
                } else if (node.lane === 'evidence') {
                  laneAccentBar = 'bg-purple-500';
                  laneBadgeClass = 'bg-purple-100 text-purple-800 dark:bg-purple-950/80 dark:text-purple-300';
                }

                if (isSelected) laneBorderColor = 'border-sky-500 ring-2 ring-sky-500/25';
                else if (isRunning) laneBorderColor = 'border-amber-500 ring-2 ring-amber-500/30';
                else if (isSuccess) laneBorderColor = 'border-emerald-500';
                else if (isError) laneBorderColor = 'border-red-500 ring-2 ring-red-500/30';

                const targetWs = node.config.workspace || activeWorkspace || 'default';

                return (
                  <motion.div
                    key={node.id}
                    drag
                    dragMomentum={false}
                    onDrag={(_, info) => handleNodeDrag(node.id, info.delta.x / zoom, info.delta.y / zoom)}
                    onClick={(e) => {
                      e.stopPropagation();
                      setSelectedNodeId(node.id);
                    }}
                    style={{
                      position: 'absolute',
                      left: `${node.x}px`,
                      top: `${node.y}px`,
                      width: '250px'
                    }}
                    className={`pointer-events-auto group rounded-xl bg-white dark:bg-slate-900 border ${laneBorderColor} shadow-sm hover:shadow-md transition-shadow cursor-grab active:cursor-grabbing select-none`}
                  >
                    {/* Top lane accent color stripe */}
                    <div className={`h-1 w-full rounded-t-xl ${laneAccentBar}`} />

                    {/* Input Port Bead */}
                    {node.lane !== 'ui' && (
                      <div
                        className="absolute -left-1.5 top-1/2 -translate-y-1/2 w-3 h-3 rounded-full bg-slate-400 dark:bg-slate-600 border-2 border-white dark:border-slate-900 group-hover:bg-sky-500 transition-colors shadow-2xs"
                        title="Input Port"
                      />
                    )}

                    {/* Output Port Bead */}
                    {node.lane !== 'evidence' && (
                      <div
                        className="absolute -right-1.5 top-1/2 -translate-y-1/2 w-3 h-3 rounded-full bg-slate-400 dark:bg-slate-600 border-2 border-white dark:border-slate-900 group-hover:bg-sky-500 transition-colors shadow-2xs"
                        title="Output Port"
                      />
                    )}

                    <div className="p-3">
                      {/* Node Header */}
                      <div className="flex items-center justify-between gap-1.5">
                        <div className="flex items-center gap-1.5 min-w-0">
                          {node.lane === 'ui' && <Sparkles className="w-3.5 h-3.5 text-sky-600 dark:text-sky-400 shrink-0" />}
                          {node.lane === 'agent' && <Bot className="w-3.5 h-3.5 text-blue-600 dark:text-blue-400 shrink-0" />}
                          {node.lane === 'policy' && <ShieldCheck className="w-3.5 h-3.5 text-rose-600 dark:text-rose-400 shrink-0" />}
                          {node.lane === 'tools' && <Terminal className="w-3.5 h-3.5 text-amber-600 dark:text-amber-400 shrink-0" />}
                          {node.lane === 'evidence' && <Database className="w-3.5 h-3.5 text-purple-600 dark:text-purple-400 shrink-0" />}
                          <span className="font-bold text-xs text-slate-900 dark:text-slate-100 truncate">
                            {node.title}
                          </span>
                        </div>

                        {/* Status Bead & Actions */}
                        <div className="flex items-center gap-1 shrink-0">
                          {isRunning && (
                            <span className="w-2 h-2 rounded-full bg-amber-500 animate-ping" />
                          )}
                          {isSuccess && (
                            <span className="w-2 h-2 rounded-full bg-emerald-500" />
                          )}
                          {isError && (
                            <span className="w-2 h-2 rounded-full bg-red-500" />
                          )}
                          <button
                            type="button"
                            onClick={(e) => {
                              e.stopPropagation();
                              handleDeleteNode(node.id);
                            }}
                            className="opacity-0 group-hover:opacity-100 p-0.5 rounded-md hover:text-red-500 text-slate-400 transition-opacity cursor-pointer"
                            title="Delete node"
                          >
                            <Trash2 className="w-3 h-3" />
                          </button>
                        </div>
                      </div>

                      <p className="text-[11px] text-slate-700 dark:text-slate-300 truncate mt-0.5 leading-tight">
                        {node.subtitle}
                      </p>

                      {/* Workspace Context Tag */}
                      <div className="mt-2 flex items-center justify-between text-[10px] font-mono">
                        <span className={`px-1.5 py-0.5 rounded-md font-semibold ${laneBadgeClass}`}>
                          {node.lane}
                        </span>

                        <span
                          className="flex items-center gap-1 px-1.5 py-0.5 rounded-md bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-slate-700 font-semibold"
                          title={`Assigned Workspace: ${targetWs}`}
                        >
                          <FolderGit2 className="w-2.5 h-2.5 text-slate-500" />
                          <span className="truncate max-w-[85px]">{targetWs}</span>
                        </span>
                      </div>
                    </div>
                  </motion.div>
                );
              })}
            </div>
          </div>
        </main>

        {/* Right Node Inspector Panel */}
        <AnimatePresence>
          {selectedNode && (
            <aside className="w-80 h-full border-l border-slate-200 dark:border-slate-800 bg-white/95 dark:bg-slate-900/90 backdrop-blur-md p-3.5 flex flex-col z-20 overflow-y-auto shadow-sm">
              <div className="flex items-center justify-between pb-3 border-b border-slate-200 dark:border-slate-800">
                <div className="flex items-center gap-2">
                  <Settings2 className="w-4 h-4 text-slate-600 dark:text-slate-400" />
                  <span className="text-xs font-bold text-slate-900 dark:text-slate-100">
                    Activity & Agent Properties
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
                {/* Title */}
                <div>
                  <label className="text-[10px] font-bold uppercase tracking-wider text-slate-600 dark:text-slate-400 block mb-1">
                    Activity Label
                  </label>
                  <input
                    type="text"
                    value={selectedNode.title}
                    onChange={(e) => {
                      const val = e.target.value;
                      setNodes((prev) =>
                        prev.map((n) => (n.id === selectedNode.id ? { ...n, title: val } : n))
                      );
                    }}
                    className="w-full px-2.5 py-1.5 rounded-xl bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 text-xs font-semibold text-slate-900 dark:text-slate-100 focus:outline-none focus:border-sky-500 shadow-2xs"
                  />
                </div>

                {/* Target Workspace Selector */}
                <div>
                  <label className="text-[10px] font-bold uppercase tracking-wider text-slate-600 dark:text-slate-400 block mb-1">
                    Target Workspace (Knowledge, Skills & Files)
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
                    className="w-full px-2.5 py-1.5 rounded-xl bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 border border-slate-300 dark:border-slate-700 text-xs font-mono focus:outline-none focus:border-sky-500 shadow-2xs"
                  >
                    {workspaceList.map((ws) => (
                      <option
                        key={ws.name}
                        value={ws.name}
                        className="bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100"
                      >
                        {ws.name}
                      </option>
                    ))}
                    {!workspaceList.some((w) => w.name === 'default') && (
                      <option value="default" className="bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100">
                        default
                      </option>
                    )}
                  </select>
                  <p className="text-[10px] text-slate-600 dark:text-slate-400 mt-1 leading-tight">
                    This agent will read context, installed skills, and workspace memory strictly from this workspace.
                  </p>
                </div>

                {/* Lane Domain Dropdown with explicitly styled options for dark mode */}
                <div>
                  <label className="text-[10px] font-bold uppercase tracking-wider text-slate-600 dark:text-slate-400 block mb-1">
                    Lane Domain
                  </label>
                  <select
                    value={selectedNode.lane}
                    onChange={(e) => {
                      const l = e.target.value as WorkflowLane;
                      setNodes((prev) =>
                        prev.map((n) => (n.id === selectedNode.id ? { ...n, lane: l } : n))
                      );
                    }}
                    className="w-full px-2.5 py-1.5 rounded-xl bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 border border-slate-300 dark:border-slate-700 text-xs focus:outline-none focus:border-sky-500 shadow-2xs"
                  >
                    <option value="ui" className="bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100">
                      Lane 1: UI / Intake
                    </option>
                    <option value="agent" className="bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100">
                      Lane 2: Agent Runtime
                    </option>
                    <option value="policy" className="bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100">
                      Lane 3: Policy & Safety Governance
                    </option>
                    <option value="tools" className="bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100">
                      Lane 4: Tool Execution
                    </option>
                    <option value="evidence" className="bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100">
                      Lane 5: Evidence & Memory
                    </option>
                  </select>
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
                      className="w-full px-2.5 py-1.5 rounded-xl bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 text-xs text-slate-900 dark:text-slate-100 focus:outline-none focus:border-sky-500 resize-none shadow-2xs"
                    />
                  </div>
                )}

                {/* Model Specification */}
                {selectedNode.config.model !== undefined && (
                  <div>
                    <label className="text-[10px] font-bold uppercase tracking-wider text-slate-600 dark:text-slate-400 block mb-1">
                      Model Specification
                    </label>
                    <input
                      type="text"
                      value={selectedNode.config.model}
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
                      className="w-full px-2.5 py-1.5 rounded-xl bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 text-xs font-mono text-slate-900 dark:text-slate-100 focus:outline-none focus:border-sky-500 shadow-2xs"
                    />
                  </div>
                )}

                {/* Directive */}
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
                      className="w-full px-2.5 py-1.5 rounded-xl bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 text-xs text-slate-900 dark:text-slate-100 focus:outline-none focus:border-sky-500 resize-none shadow-2xs"
                    />
                  </div>
                )}

                {/* Allocated Tools */}
                {selectedNode.config.tools !== undefined && (
                  <div>
                    <label className="text-[10px] font-bold uppercase tracking-wider text-slate-600 dark:text-slate-400 block mb-1">
                      Allocated Capability Tools
                    </label>
                    <div className="space-y-1">
                      {selectedNode.config.tools.map((t) => (
                        <div
                          key={t}
                          className="px-2 py-1 rounded-lg bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 font-mono text-[10px] text-slate-800 dark:text-slate-200 flex items-center justify-between"
                        >
                          <span>{t}</span>
                          <Check className="w-3 h-3 text-emerald-600 dark:text-emerald-400" />
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                <div className="pt-2">
                  <button
                    type="button"
                    onClick={() => handleDeleteNode(selectedNode.id)}
                    className="w-full py-2 px-3 rounded-xl border border-red-500/30 text-red-600 dark:text-red-400 hover:bg-red-500/10 text-xs font-semibold transition-colors flex items-center justify-center gap-1.5 cursor-pointer active:scale-[0.98]"
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

      {/* Live Flow Execution Console Drawer */}
      <AnimatePresence>
        {isDrawerOpen && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 180, opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ type: 'spring', stiffness: 350, damping: 30 }}
            className="w-full border-t border-slate-200 dark:border-slate-800 bg-white/95 dark:bg-slate-900/95 backdrop-blur-md z-30 flex flex-col shrink-0 shadow-lg"
          >
            <div className="h-8 px-3 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between text-xs">
              <div className="flex items-center gap-2">
                <Terminal className="w-3.5 h-3.5 text-slate-600 dark:text-slate-400" />
                <span className="font-bold text-slate-900 dark:text-slate-100">
                  Live Agent Pipeline Execution Log
                </span>
                {isExecuting ? (
                  <span className="flex items-center gap-1 text-[10px] font-mono text-amber-700 dark:text-amber-400 bg-amber-500/10 px-1.5 py-0.5 rounded-md font-semibold">
                    <span className="w-1.5 h-1.5 rounded-full bg-amber-500 animate-ping" />
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
                  No execution events recorded yet. Click &quot;Run Pipeline&quot; above to initiate live workflow execution.
                </p>
              ) : (
                executionLogs.map((log, i) => (
                  <div key={i} className="flex items-start gap-2 text-slate-800 dark:text-slate-200 leading-tight">
                    <span className="text-slate-500 dark:text-slate-400 shrink-0 select-none">
                      [{log.timestamp || new Date().toLocaleTimeString()}]
                    </span>
                    <span className="text-sky-700 dark:text-sky-400 font-bold shrink-0">
                      [{log.agent}]
                    </span>
                    <span className="flex-1 break-words">
                      {log.message}
                    </span>
                  </div>
                ))
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
