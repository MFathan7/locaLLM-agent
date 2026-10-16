/**
 * Pre-built workflow presets with full dynamic property schemas and in/out variable binding.
 */

import type { WorkflowLaneConfig, WorkflowNode, WorkflowEdge } from '../types';

export const INITIAL_LANES: WorkflowLaneConfig[] = [
  { id: 'ui', num: '01', label: 'User Interface Sequence', description: 'Handles user prompts, input validation, and conversational deliverables', color: 'blue', x: 30, y: 70, width: 1750, height: 135 },
  { id: 'agent', num: '02', label: 'Agent Runtime Sequence', description: 'Cognitive reasoning loop, model inference, and tool call planning', color: 'blue', x: 30, y: 225, width: 1750, height: 145 },
  { id: 'policy', num: '03', label: 'Policy & Guardrail Sequence', description: 'Safety screening, human authorization gates, and retry recovery loops', color: 'red', x: 30, y: 390, width: 1750, height: 135 },
  { id: 'tools', num: '04', label: 'Tool Execution Sequence', description: 'Sandboxed code interpretation, terminal commands, and API execution', color: 'yellow', x: 30, y: 545, width: 1750, height: 145 },
  { id: 'evidence', num: '05', label: 'Evidence & Context Sequence', description: 'Vector embeddings, short-term scratchpad, and memory grounding', color: 'blue', x: 30, y: 710, width: 1750, height: 135 }
];

export interface WorkflowPreset {
  id: string;
  name: string;
  description: string;
  lanes: WorkflowLaneConfig[];
  nodes: WorkflowNode[];
  edges: WorkflowEdge[];
}

export const WORKFLOW_PRESETS: WorkflowPreset[] = [
  {
    id: 'fullstack-code-audit',
    name: 'Full-Stack Code Audit & Auto-Refactor',
    description: 'QA Loop Pattern: automated repository audit with hierarchical decomposition, Coder Specialist tooling, Critic verification, and Quality Gate revision loops.',
    lanes: INITIAL_LANES,
    nodes: [
      {
        id: 'audit-intake',
        lane: 'ui',
        category: 'triggers',
        type: 'frontend',
        title: 'User Objective Input',
        subtitle: 'Repository target & audit directives',
        tag: 'intake',
        x: 60,
        y: 105,
        status: 'idle',
        config: {
          query: 'Perform full-stack audit across backend modules and test suite. Detect failing assertions, memory bottlenecks, and syntax regressions, patch affected source files, and verify 100% test coverage with pytest.',
          workspace: 'default'
        },
        properties: {
          common: {
            displayName: 'User Objective Input',
            description: 'Repository target & audit directives',
            continueOnError: false,
            timeoutSeconds: 30
          },
          inputs: {
            query: 'Perform full-stack audit across backend modules and test suite. Detect failing assertions, memory bottlenecks, and syntax regressions, patch affected source files, and verify 100% test coverage with pytest.',
            workspace: 'default'
          },
          options: {
            sourceType: 'manual'
          },
          output: {
            outputVariable: 'out_user_objective'
          }
        }
      },
      {
        id: 'audit-decomposer',
        lane: 'agent',
        category: 'orchestration',
        type: 'backend',
        title: 'Task Decomposer (Planner)',
        subtitle: 'Splits audit into ordered task queue',
        tag: 'task-decomposer',
        x: 320,
        y: 265,
        status: 'idle',
        config: {
          strategy: 'hierarchical',
          max_subtasks: 4
        },
        properties: {
          common: {
            displayName: 'Task Decomposer (Planner)',
            description: 'Splits audit into ordered task queue',
            continueOnError: false,
            timeoutSeconds: 60
          },
          inputs: {
            objective: '{{out_user_objective}}'
          },
          options: {
            max_subtasks: 4,
            strategy: 'hierarchical'
          },
          output: {
            outputVariable: 'out_task_queue'
          }
        }
      },
      {
        id: 'audit-supervisor',
        lane: 'agent',
        category: 'orchestration',
        type: 'backend',
        title: 'Supervisor / Coordinator',
        subtitle: 'Multi-agent orchestration hub',
        tag: 'supervisor',
        x: 600,
        y: 265,
        status: 'idle',
        config: {
          directive: 'Coordinate code audit mission: query model router for high-VRAM coder, delegate patch generation to Coder Agent, aggregate AST diffs into Blackboard, and submit final candidate to QA Critic for objective: {{out_user_objective}}',
          workspace: 'default'
        },
        properties: {
          common: {
            displayName: 'Supervisor / Coordinator',
            description: 'Multi-agent orchestration hub',
            continueOnError: false,
            timeoutSeconds: 120
          },
          inputs: {
            directive: 'Coordinate code audit mission: query model router for high-VRAM coder, delegate patch generation to Coder Agent, aggregate AST diffs into Blackboard, and submit final candidate to QA Critic for objective: {{out_user_objective}}',
            workspace: 'default'
          },
          options: {
            model: 'auto',
            temperature: 0.2,
            maxRetries: 3
          },
          output: {
            outputVariable: 'out_supervisor_directive'
          }
        }
      },
      {
        id: 'audit-critic',
        lane: 'agent',
        category: 'specialists',
        type: 'security',
        title: 'Critic / QA Agent',
        subtitle: 'Scores AST patches and test matrix',
        tag: 'critic',
        x: 880,
        y: 265,
        status: 'idle',
        config: {
          pass_threshold: 85,
          workspace: 'default'
        },
        properties: {
          common: {
            displayName: 'Critic / QA Agent',
            description: 'Scores AST patches and test matrix',
            continueOnError: false,
            timeoutSeconds: 60
          },
          inputs: {
            validationCriteria: 'Verify AST diffs, test assertions, and syntax regressions for: {{out_user_objective}}',
            targetArtifact: '{{out_patch_diff}}'
          },
          options: {
            pass_threshold: 85,
            model: 'auto'
          },
          output: {
            outputVariable: 'out_qa_verdict'
          }
        }
      },
      {
        id: 'audit-gate',
        lane: 'policy',
        category: 'flow_control',
        type: 'security',
        title: 'Quality Gate (If/Else)',
        subtitle: 'Pass deliverable or loop to Supervisor',
        tag: 'quality-gate',
        x: 1160,
        y: 425,
        status: 'idle',
        config: {
          max_retries: 3,
          min_score: 85
        },
        properties: {
          common: {
            displayName: 'Quality Gate (If/Else)',
            description: 'Pass deliverable or loop to Supervisor',
            continueOnError: false,
            timeoutSeconds: 15
          },
          inputs: {
            condition: 'verdict.passed == true && verdict.score >= 85'
          },
          options: {
            max_retries: 3,
            min_score: 85
          },
          output: {
            outputVariable: 'out_gate_decision'
          }
        }
      },
      {
        id: 'audit-output',
        lane: 'ui',
        category: 'outputs',
        type: 'frontend',
        title: 'Chat & Artifact Output',
        subtitle: 'Verified patches, test logs, and diff receipts',
        tag: 'chat-output',
        x: 1440,
        y: 105,
        status: 'idle',
        config: {
          notify_user: true,
          format: 'markdown'
        },
        properties: {
          common: {
            displayName: 'Chat & Artifact Output',
            description: 'Verified patches, test logs, and diff receipts',
            continueOnError: false,
            timeoutSeconds: 30
          },
          inputs: {
            message: 'Audit completed for {{out_user_objective}} with verdict score {{out_qa_verdict.score}}.',
            output_file: 'docs/audit_report.md'
          },
          options: {
            notify_user: true
          },
          output: {
            outputVariable: 'out_chat_deliverable'
          }
        }
      },
      {
        id: 'audit-router',
        lane: 'tools',
        category: 'orchestration',
        type: 'cloud',
        title: 'Dynamic Model Router',
        subtitle: 'Inspects GPU VRAM for coder model',
        tag: 'model-router',
        x: 440,
        y: 585,
        status: 'idle',
        config: {
          vram_threshold_mb: 8192,
          fast_model: 'gemma4:12b',
          deep_model: 'gemma4:26b'
        },
        properties: {
          common: {
            displayName: 'Dynamic Model Router',
            description: 'Inspects GPU VRAM for coder model',
            continueOnError: true,
            timeoutSeconds: 15
          },
          inputs: {},
          options: {
            vram_threshold_mb: 8192,
            fast_model: 'gemma4:12b',
            deep_model: 'gemma4:26b'
          },
          output: {
            outputVariable: 'out_selected_model'
          }
        }
      },
      {
        id: 'audit-blackboard',
        lane: 'evidence',
        category: 'state_knowledge',
        type: 'database',
        title: 'Blackboard Hub (Shared State)',
        subtitle: 'Shared AST diffs and test results',
        tag: 'blackboard',
        x: 600,
        y: 745,
        status: 'idle',
        config: {
          workspace: 'default'
        },
        properties: {
          common: {
            displayName: 'Blackboard Hub (Shared State)',
            description: 'Shared AST diffs and test results',
            continueOnError: true,
            timeoutSeconds: 30
          },
          inputs: {
            workspace: 'default'
          },
          options: {
            syncIntervalSeconds: 5
          },
          output: {
            outputVariable: 'out_blackboard_state'
          }
        }
      },
      {
        id: 'audit-coder',
        lane: 'tools',
        category: 'specialists',
        type: 'backend',
        title: 'Coder Agent',
        subtitle: 'Generates AST patches and code fixes',
        tag: 'coder',
        x: 760,
        y: 585,
        status: 'idle',
        config: {
          tools: ['patch_file', 'write_file', 'read_file', 'check_syntax'],
          workspace: 'default'
        },
        properties: {
          common: {
            displayName: 'Coder Agent',
            description: 'Generates AST patches and code fixes',
            continueOnError: false,
            timeoutSeconds: 120
          },
          inputs: {
            taskDescription: 'Implement required code refactoring and diff patches for: {{out_user_objective}}',
            output_file: 'docs/patch_revision.diff'
          },
          options: {
            model: 'auto',
            temperature: 0.1,
            tools: ['patch_file', 'write_file', 'read_file', 'check_syntax']
          },
          output: {
            outputVariable: 'out_patch_diff'
          }
        }
      },
      {
        id: 'audit-fs',
        lane: 'evidence',
        category: 'tools_plugins',
        type: 'messagebus',
        title: 'Filesystem',
        subtitle: 'Local repository file sandbox',
        tag: 'filesystem',
        x: 760,
        y: 745,
        status: 'idle',
        config: {
          path: '.',
          workspace: 'default'
        },
        properties: {
          common: {
            displayName: 'Filesystem',
            description: 'Local repository file sandbox',
            continueOnError: false,
            timeoutSeconds: 30
          },
          inputs: {
            path: '.',
            fileContent: ''
          },
          options: {
            operation: 'read',
            workspace: 'default'
          },
          output: {
            outputVariable: 'out_fs_result'
          }
        }
      },
      {
        id: 'audit-shell',
        lane: 'evidence',
        category: 'tools_plugins',
        type: 'messagebus',
        title: 'Shell Runner',
        subtitle: 'Executes pytest and syntax checks',
        tag: 'subprocess',
        x: 940,
        y: 745,
        status: 'idle',
        config: {
          command: 'pytest -q tests/',
          workspace: 'default'
        },
        properties: {
          common: {
            displayName: 'Shell Runner',
            description: 'Executes pytest and syntax checks',
            continueOnError: false,
            timeoutSeconds: 60
          },
          inputs: {
            command: 'pytest -q tests/',
            workingDir: '.'
          },
          options: {},
          output: {
            outputVariable: 'out_shell_stdout'
          }
        }
      }
    ],
    edges: [
      { id: 'ae-main-1', from: 'audit-intake', to: 'audit-decomposer', fromSide: 'right', toSide: 'left', kind: 'main', label: 'objective', variant: 'emphasis' },
      { id: 'ae-main-2', from: 'audit-decomposer', to: 'audit-supervisor', fromSide: 'right', toSide: 'left', kind: 'main', label: 'task queue', variant: 'emphasis' },
      { id: 'ae-main-3', from: 'audit-supervisor', to: 'audit-critic', fromSide: 'right', toSide: 'left', kind: 'main', label: 'code diffs & patches', variant: 'emphasis' },
      { id: 'ae-main-4', from: 'audit-critic', to: 'audit-gate', fromSide: 'right', toSide: 'left', kind: 'main', label: 'verdict', variant: 'security' },
      { id: 'ae-gate-pass', from: 'audit-gate', to: 'audit-output', fromSide: 'right', toSide: 'left', kind: 'conditional', conditionBranch: 'true', label: 'Pass (Score >= 85)', variant: 'emphasis' },
      { id: 'ae-gate-loop', from: 'audit-gate', to: 'audit-supervisor', fromSide: 'left', toSide: 'bottom', kind: 'conditional', conditionBranch: 'loop', label: 'Revision Loop (retry <= 3)', variant: 'security' },
      { id: 'ae-sub-router', from: 'audit-router', to: 'audit-supervisor', fromSide: 'top', toSide: 'bottom', kind: 'sub', label: 'vram model', variant: 'dashed' },
      { id: 'ae-sub-blackboard', from: 'audit-blackboard', to: 'audit-supervisor', fromSide: 'top', toSide: 'bottom', kind: 'sub', label: 'shared state', variant: 'dashed' },
      { id: 'ae-sub-coder', from: 'audit-coder', to: 'audit-supervisor', fromSide: 'top', toSide: 'bottom', kind: 'sub', label: 'code generator', variant: 'dashed' },
      { id: 'ae-sub-fs', from: 'audit-fs', to: 'audit-coder', fromSide: 'top', toSide: 'bottom', kind: 'sub', label: 'file patches', variant: 'dashed' },
      { id: 'ae-sub-shell', from: 'audit-shell', to: 'audit-coder', fromSide: 'top', toSide: 'bottom', kind: 'sub', label: 'test execution', variant: 'dashed' }
    ]
  },
  {
    id: 'deep-tech-intelligence',
    name: 'Deep Tech & Market Intelligence Report',
    description: 'Hub-and-Spoke Pattern: multi-source intelligence gathering, Blackboard data consolidation, and structured document publishing.',
    lanes: INITIAL_LANES,
    nodes: [
      {
        id: 'intel-intake',
        lane: 'ui',
        category: 'triggers',
        type: 'frontend',
        title: 'User Objective Input',
        subtitle: 'Research mission & market scope',
        tag: 'intake',
        x: 60,
        y: 105,
        status: 'idle',
        config: {
          query: 'Conduct an exhaustive market and competitive intelligence report on open-weight local LLM orchestrators (Ollama, vLLM, llama.cpp, and locaLLM). Extract benchmark latency, hardware VRAM footprints, and feature matrices into the shared Blackboard, then generate an executive summary report.',
          workspace: 'default'
        },
        properties: {
          common: {
            displayName: 'User Objective Input',
            description: 'Research mission & market scope',
            continueOnError: false,
            timeoutSeconds: 30
          },
          inputs: {
            query: 'Conduct an exhaustive market and competitive intelligence report on open-weight local LLM orchestrators (Ollama, vLLM, llama.cpp, and locaLLM). Extract benchmark latency, hardware VRAM footprints, and feature matrices into the shared Blackboard, then generate an executive summary report.',
            workspace: 'default'
          },
          options: {
            sourceType: 'manual'
          },
          output: {
            outputVariable: 'out_user_objective'
          }
        }
      },
      {
        id: 'intel-supervisor',
        lane: 'agent',
        category: 'orchestration',
        type: 'backend',
        title: 'Supervisor / Coordinator',
        subtitle: 'Research coordination & subtask delegation',
        tag: 'supervisor',
        x: 380,
        y: 265,
        status: 'idle',
        config: {
          directive: 'Coordinate deep research: assign online retrieval tasks to Researcher Agent, cross-check against internal documentation via RAG Retriever, synchronize verified findings on the Blackboard, and dispatch data to Parallel Aggregator for: {{out_user_objective}}',
          workspace: 'default'
        },
        properties: {
          common: {
            displayName: 'Supervisor / Coordinator',
            description: 'Research coordination & subtask delegation',
            continueOnError: false,
            timeoutSeconds: 120
          },
          inputs: {
            directive: 'Coordinate deep research: assign online retrieval tasks to Researcher Agent, cross-check against internal documentation via RAG Retriever, synchronize verified findings on the Blackboard, and dispatch data to Parallel Aggregator for: {{out_user_objective}}',
            workspace: 'default'
          },
          options: {
            model: 'auto',
            temperature: 0.2,
            maxRetries: 2
          },
          output: {
            outputVariable: 'out_supervisor_directive'
          }
        }
      },
      {
        id: 'intel-aggregator',
        lane: 'agent',
        category: 'orchestration',
        type: 'messagebus',
        title: 'Parallel Aggregator',
        subtitle: 'Joins concurrent research streams',
        tag: 'parallel-aggregator',
        x: 720,
        y: 265,
        status: 'idle',
        config: {
          join_strategy: 'all_completed',
          timeout: 90
        },
        properties: {
          common: {
            displayName: 'Parallel Aggregator',
            description: 'Joins concurrent research streams',
            continueOnError: false,
            timeoutSeconds: 90
          },
          inputs: {
            mergeFields: 'findings, artifacts, context_variables'
          },
          options: {
            join_strategy: 'all_completed',
            timeout: 90
          },
          output: {
            outputVariable: 'out_aggregated_data'
          }
        }
      },
      {
        id: 'intel-writer',
        lane: 'agent',
        category: 'specialists',
        type: 'frontend',
        title: 'Writer Agent',
        subtitle: 'Synthesizes findings into executive report',
        tag: 'writer',
        x: 1000,
        y: 265,
        status: 'idle',
        config: {
          format: 'markdown',
          output_file: 'docs/market_intelligence_report.md'
        },
        properties: {
          common: {
            displayName: 'Writer Agent',
            description: 'Synthesizes findings into executive report',
            continueOnError: false,
            timeoutSeconds: 90
          },
          inputs: {
            systemPrompt: 'You are an executive technical writer synthesizing benchmark intelligence.',
            messageTemplate: '# Market & Technical Intelligence Report\n\nObjective: {{out_user_objective}}\n\n## Findings\n{{out_research_data}}',
            output_file: 'docs/market_intelligence_report.md'
          },
          options: {
            format: 'markdown',
            model: 'auto',
            temperature: 0.35
          },
          output: {
            outputVariable: 'out_written_doc'
          }
        }
      },
      {
        id: 'intel-doc-exporter',
        lane: 'ui',
        category: 'outputs',
        type: 'external',
        title: 'Document Exporter',
        subtitle: 'Saves structured report to markdown file',
        tag: 'doc-exporter',
        x: 1320,
        y: 75,
        status: 'idle',
        config: {
          output_path: 'docs/market_intelligence_report.md',
          format: 'markdown'
        },
        properties: {
          common: {
            displayName: 'Document Exporter',
            description: 'Saves structured report to markdown file',
            continueOnError: false,
            timeoutSeconds: 30
          },
          inputs: {
            output_path: 'docs/market_intelligence_report.md',
            contentTemplate: '{{out_written_doc}}'
          },
          options: {
            format: 'markdown',
            notify_user: true
          },
          output: {
            outputVariable: 'out_exported_file'
          }
        }
      },
      {
        id: 'intel-chat-output',
        lane: 'ui',
        category: 'outputs',
        type: 'frontend',
        title: 'Chat & Artifact Output',
        subtitle: 'Displays key findings and download link',
        tag: 'chat-output',
        x: 1320,
        y: 145,
        status: 'idle',
        config: {
          notify_user: true
        },
        properties: {
          common: {
            displayName: 'Chat & Artifact Output',
            description: 'Displays key findings and download link',
            continueOnError: false,
            timeoutSeconds: 30
          },
          inputs: {
            message: 'Executive intelligence deliverable published to {{out_exported_file}} for objective: {{out_user_objective}}.',
            output_file: 'docs/market_intelligence_report.md'
          },
          options: {
            notify_user: true
          },
          output: {
            outputVariable: 'out_chat_deliverable'
          }
        }
      },
      {
        id: 'intel-router',
        lane: 'tools',
        category: 'orchestration',
        type: 'cloud',
        title: 'Dynamic Model Router',
        subtitle: 'Assigns high-context reasoning LLM',
        tag: 'model-router',
        x: 240,
        y: 585,
        status: 'idle',
        config: {
          vram_threshold_mb: 12288,
          fast_model: 'gemma4:12b',
          deep_model: 'nemotron3-super'
        },
        properties: {
          common: {
            displayName: 'Dynamic Model Router',
            description: 'Assigns high-context reasoning LLM',
            continueOnError: true,
            timeoutSeconds: 15
          },
          inputs: {},
          options: {
            vram_threshold_mb: 12288,
            fast_model: 'gemma4:12b',
            deep_model: 'nemotron3-super'
          },
          output: {
            outputVariable: 'out_selected_model'
          }
        }
      },
      {
        id: 'intel-blackboard',
        lane: 'evidence',
        category: 'state_knowledge',
        type: 'database',
        title: 'Blackboard Hub (Shared State)',
        subtitle: 'Benchmark telemetry and comparison matrix',
        tag: 'blackboard',
        x: 380,
        y: 745,
        status: 'idle',
        config: {
          workspace: 'default'
        },
        properties: {
          common: {
            displayName: 'Blackboard Hub (Shared State)',
            description: 'Benchmark telemetry and comparison matrix',
            continueOnError: true,
            timeoutSeconds: 30
          },
          inputs: {
            workspace: 'default'
          },
          options: {
            syncIntervalSeconds: 5
          },
          output: {
            outputVariable: 'out_blackboard_state'
          }
        }
      },
      {
        id: 'intel-researcher',
        lane: 'tools',
        category: 'specialists',
        type: 'messagebus',
        title: 'Researcher Agent',
        subtitle: 'Online data gathering and extraction',
        tag: 'researcher',
        x: 520,
        y: 585,
        status: 'idle',
        config: {
          tools: ['search_web', 'fetch_web', 'read_file'],
          workspace: 'default'
        },
        properties: {
          common: {
            displayName: 'Researcher Agent',
            description: 'Online data gathering and extraction',
            continueOnError: false,
            timeoutSeconds: 90
          },
          inputs: {
            searchQuery: '{{out_user_objective}}'
          },
          options: {
            model: 'auto',
            temperature: 0.3,
            tools: ['search_web', 'fetch_web', 'read_file']
          },
          output: {
            outputVariable: 'out_research_data'
          }
        }
      },
      {
        id: 'intel-web-search',
        lane: 'evidence',
        category: 'tools_plugins',
        type: 'cloud',
        title: 'Web Search',
        subtitle: 'Queries online search engines',
        tag: 'online-web',
        x: 520,
        y: 745,
        status: 'idle',
        config: {
          provider: 'auto',
          max_results: 8
        },
        properties: {
          common: {
            displayName: 'Web Search',
            description: 'Queries online search engines',
            continueOnError: true,
            timeoutSeconds: 45
          },
          inputs: {
            query: '{{out_user_objective}}'
          },
          options: {
            provider: 'auto',
            max_results: 8
          },
          output: {
            outputVariable: 'out_web_results'
          }
        }
      },
      {
        id: 'intel-rag',
        lane: 'evidence',
        category: 'state_knowledge',
        type: 'database',
        title: 'RAG Retriever',
        subtitle: 'Cross-references local docs and whitepapers',
        tag: 'rag-retriever',
        x: 680,
        y: 745,
        status: 'idle',
        config: {
          top_k: 5,
          workspace: 'default'
        },
        properties: {
          common: {
            displayName: 'RAG Retriever',
            description: 'Cross-references local docs and whitepapers',
            continueOnError: false,
            timeoutSeconds: 45
          },
          inputs: {
            searchQuery: '{{out_user_objective}}',
            workspace: 'default'
          },
          options: {
            top_k: 5
          },
          output: {
            outputVariable: 'out_rag_passages'
          }
        }
      }
    ],
    edges: [
      { id: 'be-main-1', from: 'intel-intake', to: 'intel-supervisor', fromSide: 'right', toSide: 'left', kind: 'main', label: 'market prompt', variant: 'emphasis' },
      { id: 'be-main-2', from: 'intel-supervisor', to: 'intel-aggregator', fromSide: 'right', toSide: 'left', kind: 'main', label: 'research streams', variant: 'emphasis' },
      { id: 'be-main-3', from: 'intel-aggregator', to: 'intel-writer', fromSide: 'right', toSide: 'left', kind: 'main', label: 'consolidated facts', variant: 'emphasis' },
      { id: 'be-main-4', from: 'intel-writer', to: 'intel-doc-exporter', fromSide: 'right', toSide: 'left', kind: 'main', label: 'export file', variant: 'default' },
      { id: 'be-main-5', from: 'intel-writer', to: 'intel-chat-output', fromSide: 'right', toSide: 'left', kind: 'main', label: 'chat summary', variant: 'emphasis' },
      { id: 'be-sub-router', from: 'intel-router', to: 'intel-supervisor', fromSide: 'top', toSide: 'bottom', kind: 'sub', label: 'vram model', variant: 'dashed' },
      { id: 'be-sub-blackboard', from: 'intel-blackboard', to: 'intel-supervisor', fromSide: 'top', toSide: 'bottom', kind: 'sub', label: 'shared state', variant: 'dashed' },
      { id: 'be-sub-researcher', from: 'intel-researcher', to: 'intel-supervisor', fromSide: 'top', toSide: 'bottom', kind: 'sub', label: 'intelligence feed', variant: 'dashed' },
      { id: 'be-sub-search', from: 'intel-web-search', to: 'intel-researcher', fromSide: 'top', toSide: 'bottom', kind: 'sub', label: 'live web queries', variant: 'dashed' },
      { id: 'be-sub-rag', from: 'intel-rag', to: 'intel-supervisor', fromSide: 'top', toSide: 'bottom', kind: 'sub', label: 'workspace RAG', variant: 'dashed' }
    ]
  },
  {
    id: 'automated-ops-messaging',
    name: 'Automated Ops & DB Assistant via Messaging',
    description: 'Event-Driven Pattern: messaging bridge with semantic intent routing, executing fast database metrics and safe operational interventions with human approval.',
    lanes: INITIAL_LANES,
    nodes: [
      {
        id: 'ops-trigger',
        lane: 'ui',
        category: 'triggers',
        type: 'external',
        title: 'Messaging Trigger',
        subtitle: 'Inbound Telegram & WhatsApp webhooks',
        tag: 'messaging-trigger',
        x: 60,
        y: 105,
        status: 'idle',
        config: {
          platform: 'telegram',
          allowed_users: '@ops_admin, @lead_dev'
        },
        properties: {
          common: {
            displayName: 'Messaging Trigger',
            description: 'Inbound Telegram & WhatsApp webhooks',
            continueOnError: false,
            timeoutSeconds: 30
          },
          inputs: {
            messageTemplate: 'System status inquiry and database health diagnostics',
            allowedUsers: '@ops_admin, @lead_dev'
          },
          options: {
            platform: 'telegram'
          },
          output: {
            outputVariable: 'out_trigger_payload'
          }
        }
      },
      {
        id: 'ops-intent',
        lane: 'agent',
        category: 'orchestration',
        type: 'messagebus',
        title: 'Semantic Intent Switch',
        subtitle: 'Classifies query vs complex ops task',
        tag: 'intent-switch',
        x: 320,
        y: 265,
        status: 'idle',
        config: {
          branches: ['DATA_QUERY', 'OPS_COMPLEX']
        },
        properties: {
          common: {
            displayName: 'Semantic Intent Switch',
            description: 'Classifies query vs complex ops task',
            continueOnError: false,
            timeoutSeconds: 30
          },
          inputs: {
            query: '{{out_trigger_payload}}'
          },
          options: {
            branches: ['DATA_QUERY', 'OPS_COMPLEX']
          },
          output: {
            outputVariable: 'out_detected_intent'
          }
        }
      },
      {
        id: 'ops-data-analyst',
        lane: 'agent',
        category: 'specialists',
        type: 'database',
        title: 'Data/DB Analyst',
        subtitle: 'Executes read-only SQL queries and summaries',
        tag: 'data-analyst',
        x: 620,
        y: 205,
        status: 'idle',
        config: {
          db_path: 'locallm_ops.db',
          query: 'SELECT service, status, last_heartbeat FROM system_services ORDER BY last_heartbeat DESC LIMIT 10;'
        },
        properties: {
          common: {
            displayName: 'Data/DB Analyst',
            description: 'Executes read-only SQL queries and summaries',
            continueOnError: false,
            timeoutSeconds: 60
          },
          inputs: {
            sqlQuery: 'SELECT service, status, last_heartbeat FROM system_services ORDER BY last_heartbeat DESC LIMIT 10;',
            db_path: 'locallm_ops.db'
          },
          options: {
            maxRows: 10,
            readOnly: true
          },
          output: {
            outputVariable: 'out_query_results'
          }
        }
      },
      {
        id: 'ops-plugin-exec',
        lane: 'tools',
        category: 'tools_plugins',
        type: 'messagebus',
        title: 'Plugin Executor',
        subtitle: 'Executes SQLite & Calendar plugin functions',
        tag: 'plugin-executor',
        x: 620,
        y: 585,
        status: 'idle',
        config: {
          plugin_id: 'sqlite_ops_calendar'
        },
        properties: {
          common: {
            displayName: 'Plugin Executor',
            description: 'Executes SQLite & Calendar plugin functions',
            continueOnError: false,
            timeoutSeconds: 60
          },
          inputs: {
            plugin_id: 'sqlite_ops_calendar',
            actionPayload: '{}'
          },
          options: {},
          output: {
            outputVariable: 'out_plugin_result'
          }
        }
      },
      {
        id: 'ops-supervisor',
        lane: 'agent',
        category: 'orchestration',
        type: 'backend',
        title: 'Supervisor / Coordinator',
        subtitle: 'Multi-step ops reasoning engine',
        tag: 'supervisor',
        x: 620,
        y: 325,
        status: 'idle',
        config: {
          directive: 'Evaluate incoming ops prompt from messaging channel: read user preferences and system history from Memory R/W, query live web status if needed, prepare execution plan, and request human approval prior to mutation for: {{out_trigger_payload}}',
          workspace: 'default'
        },
        properties: {
          common: {
            displayName: 'Supervisor / Coordinator',
            description: 'Multi-step ops reasoning engine',
            continueOnError: false,
            timeoutSeconds: 120
          },
          inputs: {
            directive: 'Evaluate incoming ops prompt from messaging channel: read user preferences and system history from Memory R/W, query live web status if needed, prepare execution plan, and request human approval prior to mutation for: {{out_trigger_payload}}',
            workspace: 'default'
          },
          options: {
            model: 'auto',
            temperature: 0.2
          },
          output: {
            outputVariable: 'out_supervisor_directive'
          }
        }
      },
      {
        id: 'ops-memory',
        lane: 'evidence',
        category: 'state_knowledge',
        type: 'database',
        title: 'Memory R/W',
        subtitle: 'Maintains persistent ops facts and runbooks',
        tag: 'memory-rw',
        x: 480,
        y: 745,
        status: 'idle',
        config: {
          scope: 'workspace',
          mode: 'read_write'
        },
        properties: {
          common: {
            displayName: 'Memory R/W',
            description: 'Maintains persistent ops facts and runbooks',
            continueOnError: false,
            timeoutSeconds: 30
          },
          inputs: {
            key: 'ops_runbooks',
            value: ''
          },
          options: {
            scope: 'workspace',
            mode: 'read_write'
          },
          output: {
            outputVariable: 'out_memory_value'
          }
        }
      },
      {
        id: 'ops-web-search',
        lane: 'tools',
        category: 'tools_plugins',
        type: 'cloud',
        title: 'Web Search',
        subtitle: 'Checks external cloud status & incident boards',
        tag: 'online-web',
        x: 780,
        y: 585,
        status: 'idle',
        config: {
          provider: 'auto',
          max_results: 5
        },
        properties: {
          common: {
            displayName: 'Web Search',
            description: 'Checks external cloud status & incident boards',
            continueOnError: true,
            timeoutSeconds: 45
          },
          inputs: {
            query: 'Cloud service status outages'
          },
          options: {
            provider: 'auto',
            max_results: 5
          },
          output: {
            outputVariable: 'out_web_results'
          }
        }
      },
      {
        id: 'ops-approval',
        lane: 'policy',
        category: 'flow_control',
        type: 'security',
        title: 'Human Approval',
        subtitle: 'Pauses execution for admin confirmation',
        tag: 'policy-gate',
        x: 920,
        y: 425,
        status: 'idle',
        config: {
          policy: 'ask',
          timeout_seconds: 120
        },
        properties: {
          common: {
            displayName: 'Human Approval',
            description: 'Pauses execution for admin confirmation',
            continueOnError: false,
            timeoutSeconds: 120
          },
          inputs: {
            promptMessage: 'Admin authorization required for operational plan triggered by: {{out_trigger_payload}}'
          },
          options: {
            policy: 'ask',
            timeout_seconds: 120
          },
          output: {
            outputVariable: 'out_approval_status'
          }
        }
      },
      {
        id: 'ops-dispatcher',
        lane: 'ui',
        category: 'outputs',
        type: 'external',
        title: 'Messaging Dispatcher',
        subtitle: 'Dispatches answers & alerts to Telegram/WA',
        tag: 'messaging-dispatcher',
        x: 1240,
        y: 105,
        status: 'idle',
        config: {
          channel: 'telegram',
          recipient: '@ops_admin'
        },
        properties: {
          common: {
            displayName: 'Messaging Dispatcher',
            description: 'Dispatches answers & alerts to Telegram/WA',
            continueOnError: true,
            timeoutSeconds: 45
          },
          inputs: {
            recipient: '@ops_admin',
            messageTemplate: 'Ops Alert: {{out_trigger_payload}}\n\nDetails: {{out_query_results}}'
          },
          options: {
            channel: 'telegram'
          },
          output: {
            outputVariable: 'out_dispatch_receipt'
          }
        }
      }
    ],
    edges: [
      { id: 'ce-main-trigger', from: 'ops-trigger', to: 'ops-intent', fromSide: 'right', toSide: 'left', kind: 'main', label: 'inbound chat', variant: 'emphasis' },
      { id: 'ce-branch-db', from: 'ops-intent', to: 'ops-data-analyst', fromSide: 'right', toSide: 'left', kind: 'main', label: 'DATA_QUERY', variant: 'default' },
      { id: 'ce-branch-ops', from: 'ops-intent', to: 'ops-supervisor', fromSide: 'right', toSide: 'left', kind: 'main', label: 'OPS_COMPLEX', variant: 'emphasis' },
      { id: 'ce-db-output', from: 'ops-data-analyst', to: 'ops-dispatcher', fromSide: 'right', toSide: 'left', kind: 'main', label: 'query results', variant: 'default' },
      { id: 'ce-ops-approval', from: 'ops-supervisor', to: 'ops-approval', fromSide: 'right', toSide: 'left', kind: 'main', label: 'mutation plan', variant: 'security' },
      { id: 'ce-approval-output', from: 'ops-approval', to: 'ops-dispatcher', fromSide: 'right', toSide: 'left', kind: 'main', label: 'approved result', variant: 'emphasis' },
      { id: 'ce-sub-plugin', from: 'ops-plugin-exec', to: 'ops-data-analyst', fromSide: 'top', toSide: 'bottom', kind: 'sub', label: 'sqlite plugin', variant: 'dashed' },
      { id: 'ce-sub-memory', from: 'ops-memory', to: 'ops-supervisor', fromSide: 'top', toSide: 'bottom', kind: 'sub', label: 'persistent state', variant: 'dashed' },
      { id: 'ce-sub-search', from: 'ops-web-search', to: 'ops-supervisor', fromSide: 'top', toSide: 'bottom', kind: 'sub', label: 'service status', variant: 'dashed' }
    ]
  },
  {
    id: 'auto-grab-quran',
    name: "Auto Grab Al-Qur'an & Tafsir (equran.id API)",
    description: "Inbound Messaging Trigger -> NLU Surah Classifier -> API Fetcher (equran.id) -> Arabic Typography Staging -> Critic QA -> Telegram Dispatcher",
    lanes: INITIAL_LANES,
    nodes: [
      {
        id: 'quran-trigger',
        lane: 'ui',
        category: 'triggers',
        type: 'external',
        title: 'Messaging Trigger',
        subtitle: 'Inbound chat request from Telegram/WA',
        tag: 'messaging-trigger',
        x: 60,
        y: 105,
        status: 'idle',
        config: {
          platform: 'telegram',
          query: 'Tolong carikan surat Al-Kahfi ayat 1 sampai 10 beserta artinya dan audio murottal'
        },
        properties: {
          common: {
            displayName: 'Messaging Trigger',
            description: 'Inbound chat request from Telegram/WA',
            continueOnError: false,
            timeoutSeconds: 30
          },
          inputs: {
            messageTemplate: 'Tolong carikan surat Al-Kahfi ayat 1 sampai 10 beserta artinya dan audio murottal',
            allowedUsers: '@telegram_user'
          },
          options: {
            platform: 'telegram'
          },
          output: {
            outputVariable: 'out_trigger_payload'
          }
        }
      },
      {
        id: 'quran-supervisor',
        lane: 'agent',
        category: 'orchestration',
        type: 'backend',
        title: 'Supervisor / Coordinator',
        subtitle: 'Extracts target surah & coordinates API fetch',
        tag: 'supervisor',
        x: 360,
        y: 265,
        status: 'idle',
        config: {
          directive: 'Identify requested Surah and verse range, query equran.id v2 API, and orchestrate Arabic typography formatting'
        },
        properties: {
          common: {
            displayName: 'Supervisor / Coordinator',
            description: 'Extracts target surah & coordinates API fetch',
            continueOnError: false,
            timeoutSeconds: 120
          },
          inputs: {
            directive: 'Identify requested Surah and verse range from: {{out_trigger_payload}}, query equran.id v2 API, and orchestrate Arabic typography formatting',
            workspace: 'default'
          },
          options: {
            model: 'auto',
            temperature: 0.2
          },
          output: {
            outputVariable: 'out_supervisor_directive'
          }
        }
      },
      {
        id: 'quran-api-fetcher',
        lane: 'agent',
        category: 'specialists',
        type: 'cloud',
        title: 'Researcher Agent',
        subtitle: 'Fetches Arabic text, audio & translation from equran.id',
        tag: 'researcher',
        x: 680,
        y: 265,
        status: 'idle',
        config: {
          api_base: 'https://equran.id/api/v2',
          reciter: 'Misyari-Rasyid-Al-Afasi'
        },
        properties: {
          common: {
            displayName: 'Researcher Agent',
            description: 'Fetches Arabic text, audio & translation from equran.id',
            continueOnError: false,
            timeoutSeconds: 90
          },
          inputs: {
            searchQuery: '{{out_trigger_payload}}',
            api_base: 'https://equran.id/api/v2',
            reciter: 'Misyari-Rasyid-Al-Afasi'
          },
          options: {
            model: 'auto'
          },
          output: {
            outputVariable: 'out_research_data'
          }
        }
      },
      {
        id: 'quran-writer',
        lane: 'agent',
        category: 'specialists',
        type: 'frontend',
        title: 'Writer Agent',
        subtitle: 'Formats calligraphy layout, translation & audio link',
        tag: 'writer',
        x: 980,
        y: 265,
        status: 'idle',
        config: {
          format: 'markdown',
          output_file: 'docs/quran_surah_output.md'
        },
        properties: {
          common: {
            displayName: 'Writer Agent',
            description: 'Formats calligraphy layout, translation & audio link',
            continueOnError: false,
            timeoutSeconds: 90
          },
          inputs: {
            systemPrompt: 'Author elegant holy scripture document with Arabic calligraphy and Indonesian translation.',
            messageTemplate: 'Format scripture for: {{out_trigger_payload}}\n\nData:\n{{out_research_data}}',
            output_file: 'docs/quran_surah_output.md'
          },
          options: {
            format: 'markdown',
            model: 'auto',
            temperature: 0.2
          },
          output: {
            outputVariable: 'out_written_doc'
          }
        }
      },
      {
        id: 'quran-critic',
        lane: 'policy',
        category: 'specialists',
        type: 'security',
        title: 'Critic / QA Agent',
        subtitle: 'Validates verse completeness & translation integrity',
        tag: 'critic',
        x: 1140,
        y: 425,
        status: 'idle',
        config: {
          pass_threshold: 90
        },
        properties: {
          common: {
            displayName: 'Critic / QA Agent',
            description: 'Validates verse completeness & translation integrity',
            continueOnError: false,
            timeoutSeconds: 60
          },
          inputs: {
            validationCriteria: 'Validate verse sequence, translation completeness, and audio links.',
            targetArtifact: '{{out_written_doc}}'
          },
          options: {
            pass_threshold: 90
          },
          output: {
            outputVariable: 'out_qa_verdict'
          }
        }
      },
      {
        id: 'quran-doc-exporter',
        lane: 'ui',
        category: 'outputs',
        type: 'external',
        title: 'Document Exporter',
        subtitle: 'Saves complete scripture to markdown file',
        tag: 'doc-exporter',
        x: 1320,
        y: 75,
        status: 'idle',
        config: {
          output_path: 'docs/quran_surah_output.md',
          format: 'markdown'
        },
        properties: {
          common: {
            displayName: 'Document Exporter',
            description: 'Saves complete scripture to markdown file',
            continueOnError: false,
            timeoutSeconds: 30
          },
          inputs: {
            output_path: 'docs/quran_surah_output.md',
            contentTemplate: '{{out_written_doc}}'
          },
          options: {
            format: 'markdown',
            notify_user: true
          },
          output: {
            outputVariable: 'out_exported_file'
          }
        }
      },
      {
        id: 'quran-dispatcher',
        lane: 'ui',
        category: 'outputs',
        type: 'external',
        title: 'Messaging Dispatcher',
        subtitle: 'Dispatches holy verses & audio player to Telegram',
        tag: 'messaging-dispatcher',
        x: 1320,
        y: 155,
        status: 'idle',
        config: {
          channel: 'telegram',
          recipient: '@telegram_user'
        },
        properties: {
          common: {
            displayName: 'Messaging Dispatcher',
            description: 'Dispatches holy verses & audio player to Telegram',
            continueOnError: true,
            timeoutSeconds: 45
          },
          inputs: {
            recipient: '@telegram_user',
            messageTemplate: 'Laporan Al-Quran untuk {{out_trigger_payload}} telah tersedia di docs/quran_surah_output.md'
          },
          options: {
            channel: 'telegram'
          },
          output: {
            outputVariable: 'out_dispatch_receipt'
          }
        }
      },
      {
        id: 'quran-router',
        lane: 'tools',
        category: 'orchestration',
        type: 'cloud',
        title: 'Dynamic Model Router',
        subtitle: 'Routes to high-context Arabic reasoning model',
        tag: 'model-router',
        x: 240,
        y: 585,
        status: 'idle',
        config: {
          vram_threshold_mb: 8192,
          fast_model: 'qwen3.5:9b',
          deep_model: 'nemotron3-super'
        },
        properties: {
          common: {
            displayName: 'Dynamic Model Router',
            description: 'Routes to high-context Arabic reasoning model',
            continueOnError: true,
            timeoutSeconds: 15
          },
          inputs: {},
          options: {
            vram_threshold_mb: 8192,
            fast_model: 'qwen3.5:9b',
            deep_model: 'nemotron3-super'
          },
          output: {
            outputVariable: 'out_selected_model'
          }
        }
      },
      {
        id: 'quran-blackboard',
        lane: 'evidence',
        category: 'state_knowledge',
        type: 'database',
        title: 'Blackboard Hub (Shared State)',
        subtitle: 'Stores cached verses, translations & reciter stream',
        tag: 'blackboard',
        x: 480,
        y: 745,
        status: 'idle',
        config: {
          workspace: 'default'
        },
        properties: {
          common: {
            displayName: 'Blackboard Hub (Shared State)',
            description: 'Stores cached verses, translations & reciter stream',
            continueOnError: true,
            timeoutSeconds: 30
          },
          inputs: {
            workspace: 'default'
          },
          options: {
            syncIntervalSeconds: 5
          },
          output: {
            outputVariable: 'out_blackboard_state'
          }
        }
      },
      {
        id: 'quran-web-search',
        lane: 'tools',
        category: 'tools_plugins',
        type: 'cloud',
        title: 'Web Search',
        subtitle: 'equran.id v2 API client bridge',
        tag: 'online-web',
        x: 680,
        y: 585,
        status: 'idle',
        config: {
          provider: 'equran.id',
          api_url: 'https://equran.id/api/v2'
        },
        properties: {
          common: {
            displayName: 'Web Search',
            description: 'equran.id v2 API client bridge',
            continueOnError: true,
            timeoutSeconds: 45
          },
          inputs: {
            query: 'https://equran.id/api/v2'
          },
          options: {
            provider: 'auto',
            max_results: 5
          },
          output: {
            outputVariable: 'out_web_results'
          }
        }
      }
    ],
    edges: [
      { id: 'qe-main-1', from: 'quran-trigger', to: 'quran-supervisor', fromSide: 'right', toSide: 'left', kind: 'main', label: 'inbound query', variant: 'emphasis' },
      { id: 'qe-main-2', from: 'quran-supervisor', to: 'quran-api-fetcher', fromSide: 'right', toSide: 'left', kind: 'main', label: 'fetch surah', variant: 'emphasis' },
      { id: 'qe-main-3', from: 'quran-api-fetcher', to: 'quran-writer', fromSide: 'right', toSide: 'left', kind: 'main', label: 'verses & audio', variant: 'default' },
      { id: 'qe-main-4', from: 'quran-writer', to: 'quran-critic', fromSide: 'right', toSide: 'left', kind: 'main', label: 'verify format', variant: 'default' },
      { id: 'qe-main-5', from: 'quran-critic', to: 'quran-doc-exporter', fromSide: 'right', toSide: 'left', kind: 'main', label: 'publish doc', variant: 'default' },
      { id: 'qe-main-6', from: 'quran-doc-exporter', to: 'quran-dispatcher', fromSide: 'right', toSide: 'left', kind: 'main', label: 'send to telegram', variant: 'emphasis' },
      { id: 'qe-sub-1', from: 'quran-router', to: 'quran-supervisor', fromSide: 'top', toSide: 'bottom', kind: 'sub', label: 'arabic model', variant: 'dashed' },
      { id: 'qe-sub-2', from: 'quran-blackboard', to: 'quran-supervisor', fromSide: 'top', toSide: 'bottom', kind: 'sub', label: 'scripture cache', variant: 'dashed' },
      { id: 'qe-sub-3', from: 'quran-web-search', to: 'quran-api-fetcher', fromSide: 'top', toSide: 'bottom', kind: 'sub', label: 'equran.id v2 API', variant: 'dashed' }
    ]
  },
  {
    id: 'scheduled-audit-human-gate',
    name: 'Scheduled System Audit & Human Approval Gate',
    description: 'Recurring Schedule Trigger -> Coordinator pre-check -> Interactive Web Action Request -> Quality Gate (If/Else) -> Automated Patch Runner -> Telegram Notification',
    lanes: INITIAL_LANES,
    nodes: [
      {
        id: 'sched-trigger',
        lane: 'ui',
        category: 'triggers',
        type: 'external',
        title: 'Schedule Trigger',
        subtitle: 'Cron timer: Daily 02:00 AM system audit',
        tag: 'schedule-trigger',
        x: 60,
        y: 105,
        status: 'idle',
        config: {
          cron: '0 2 * * *',
          timezone: 'Asia/Jakarta'
        },
        properties: {
          common: {
            displayName: 'Schedule Trigger',
            description: 'Cron timer: Daily 02:00 AM system audit',
            continueOnError: false,
            timeoutSeconds: 30
          },
          inputs: {
            cron: '0 2 * * *',
            query: 'Automated Daily Infrastructure Audit Routine'
          },
          options: {
            timezone: 'Asia/Jakarta'
          },
          output: {
            outputVariable: 'out_schedule_event'
          }
        }
      },
      {
        id: 'sched-supervisor',
        lane: 'agent',
        category: 'orchestration',
        type: 'backend',
        title: 'Supervisor / Coordinator',
        subtitle: 'Scans infrastructure health & stages maintenance update',
        tag: 'supervisor',
        x: 360,
        y: 265,
        status: 'idle',
        config: {
          directive: 'Scan system logs, database integrity, and package CVEs. Prepare automated patch plan and request admin sign-off.'
        },
        properties: {
          common: {
            displayName: 'Supervisor / Coordinator',
            description: 'Scans infrastructure health & stages maintenance update',
            continueOnError: false,
            timeoutSeconds: 120
          },
          inputs: {
            directive: 'Scan system logs, database integrity, and package CVEs. Prepare automated patch plan and request admin sign-off for: {{out_schedule_event}}',
            workspace: 'default'
          },
          options: {
            model: 'auto',
            temperature: 0.2
          },
          output: {
            outputVariable: 'out_supervisor_directive'
          }
        }
      },
      {
        id: 'sched-action-notify',
        lane: 'ui',
        category: 'outputs',
        type: 'frontend',
        title: 'Chat & Artifact Output',
        subtitle: 'Notifies administrator that approval is required',
        tag: 'chat-output',
        x: 680,
        y: 105,
        status: 'idle',
        config: {
          notify_user: true,
          message: 'Action Required: Pending maintenance update ready. Awaiting admin approval via web console.'
        },
        properties: {
          common: {
            displayName: 'Chat & Artifact Output',
            description: 'Notifies administrator that approval is required',
            continueOnError: false,
            timeoutSeconds: 30
          },
          inputs: {
            message: 'Action Required: Pending maintenance update ready for {{out_schedule_event}}. Awaiting admin approval via web console.',
            output_file: 'docs/maintenance_notification.md'
          },
          options: {
            notify_user: true
          },
          output: {
            outputVariable: 'out_chat_deliverable'
          }
        }
      },
      {
        id: 'sched-approval-gate',
        lane: 'policy',
        category: 'flow_control',
        type: 'security',
        title: 'Quality Gate (If/Else)',
        subtitle: 'Evaluates admin approval token before applying patch',
        tag: 'quality-gate',
        x: 720,
        y: 425,
        status: 'idle',
        config: {
          condition: 'admin_action_approved == true',
          max_retries: 2,
          pass_threshold: 85
        },
        properties: {
          common: {
            displayName: 'Quality Gate (If/Else)',
            description: 'Evaluates admin approval token before applying patch',
            continueOnError: false,
            timeoutSeconds: 15
          },
          inputs: {
            condition: 'admin_action_approved == true'
          },
          options: {
            max_retries: 2,
            min_score: 85
          },
          output: {
            outputVariable: 'out_gate_decision'
          }
        }
      },
      {
        id: 'sched-coder-agent',
        lane: 'agent',
        category: 'specialists',
        type: 'backend',
        title: 'Coder Agent',
        subtitle: 'Applies authorized maintenance patches & migrations',
        tag: 'coder',
        x: 980,
        y: 265,
        status: 'idle',
        config: {
          tools: ['patch_file', 'write_file', 'execute_command'],
          output_file: 'docs/maintenance_audit_signoff.md'
        },
        properties: {
          common: {
            displayName: 'Coder Agent',
            description: 'Applies authorized maintenance patches & migrations',
            continueOnError: false,
            timeoutSeconds: 120
          },
          inputs: {
            taskDescription: 'Apply authorized maintenance patches based on: {{out_supervisor_directive}}',
            output_file: 'docs/maintenance_audit_signoff.md'
          },
          options: {
            tools: ['patch_file', 'write_file', 'execute_command']
          },
          output: {
            outputVariable: 'out_patch_diff'
          }
        }
      },
      {
        id: 'sched-doc-exporter',
        lane: 'ui',
        category: 'outputs',
        type: 'external',
        title: 'Document Exporter',
        subtitle: 'Archives verified maintenance sign-off log',
        tag: 'doc-exporter',
        x: 1320,
        y: 75,
        status: 'idle',
        config: {
          output_path: 'docs/maintenance_audit_signoff.md',
          format: 'markdown'
        },
        properties: {
          common: {
            displayName: 'Document Exporter',
            description: 'Archives verified maintenance sign-off log',
            continueOnError: false,
            timeoutSeconds: 30
          },
          inputs: {
            output_path: 'docs/maintenance_audit_signoff.md',
            contentTemplate: '{{out_patch_diff}}'
          },
          options: {
            format: 'markdown',
            notify_user: true
          },
          output: {
            outputVariable: 'out_exported_file'
          }
        }
      },
      {
        id: 'sched-dispatcher',
        lane: 'ui',
        category: 'outputs',
        type: 'external',
        title: 'Messaging Dispatcher',
        subtitle: 'Pushes execution summary alert to Telegram on-call',
        tag: 'messaging-dispatcher',
        x: 1320,
        y: 155,
        status: 'idle',
        config: {
          channel: 'telegram',
          recipient: '@admin_ops'
        },
        properties: {
          common: {
            displayName: 'Messaging Dispatcher',
            description: 'Pushes execution summary alert to Telegram on-call',
            continueOnError: true,
            timeoutSeconds: 45
          },
          inputs: {
            recipient: '@admin_ops',
            messageTemplate: 'System maintenance routine finished for {{out_schedule_event}}. Sign-off archived.'
          },
          options: {
            channel: 'telegram'
          },
          output: {
            outputVariable: 'out_dispatch_receipt'
          }
        }
      },
      {
        id: 'sched-router',
        lane: 'tools',
        category: 'orchestration',
        type: 'cloud',
        title: 'Dynamic Model Router',
        subtitle: 'Assigns low-latency telemetry analysis model',
        tag: 'model-router',
        x: 240,
        y: 585,
        status: 'idle',
        config: {
          vram_threshold_mb: 8192,
          fast_model: 'qwen3.5:9b',
          deep_model: 'nemotron3-super'
        },
        properties: {
          common: {
            displayName: 'Dynamic Model Router',
            description: 'Assigns low-latency telemetry analysis model',
            continueOnError: true,
            timeoutSeconds: 15
          },
          inputs: {},
          options: {
            vram_threshold_mb: 8192,
            fast_model: 'qwen3.5:9b',
            deep_model: 'nemotron3-super'
          },
          output: {
            outputVariable: 'out_selected_model'
          }
        }
      },
      {
        id: 'sched-blackboard',
        lane: 'evidence',
        category: 'state_knowledge',
        type: 'database',
        title: 'Blackboard Hub (Shared State)',
        subtitle: 'Shared audit records & human authorization token',
        tag: 'blackboard',
        x: 520,
        y: 745,
        status: 'idle',
        config: {
          workspace: 'default'
        },
        properties: {
          common: {
            displayName: 'Blackboard Hub (Shared State)',
            description: 'Shared audit records & human authorization token',
            continueOnError: true,
            timeoutSeconds: 30
          },
          inputs: {
            workspace: 'default'
          },
          options: {
            syncIntervalSeconds: 5
          },
          output: {
            outputVariable: 'out_blackboard_state'
          }
        }
      },
      {
        id: 'sched-shell-runner',
        lane: 'tools',
        category: 'tools_plugins',
        type: 'backend',
        title: 'Subprocess / Shell Runner',
        subtitle: 'Runs test suite & system maintenance commands',
        tag: 'subprocess',
        x: 980,
        y: 585,
        status: 'idle',
        config: {
          command: 'pytest -q && echo "Maintenance patches verified"'
        },
        properties: {
          common: {
            displayName: 'Subprocess / Shell Runner',
            description: 'Runs test suite & system maintenance commands',
            continueOnError: false,
            timeoutSeconds: 60
          },
          inputs: {
            command: 'pytest -q && echo "Maintenance patches verified"',
            workingDir: '.'
          },
          options: {},
          output: {
            outputVariable: 'out_shell_stdout'
          }
        }
      }
    ],
    edges: [
      { id: 'se-main-1', from: 'sched-trigger', to: 'sched-supervisor', fromSide: 'right', toSide: 'left', kind: 'main', label: 'cron tick (02:00)', variant: 'emphasis' },
      { id: 'se-main-2', from: 'sched-supervisor', to: 'sched-action-notify', fromSide: 'right', toSide: 'left', kind: 'main', label: 'action required', variant: 'security' },
      { id: 'se-main-3', from: 'sched-action-notify', to: 'sched-approval-gate', fromSide: 'right', toSide: 'left', kind: 'main', label: 'evaluate approval', variant: 'default' },
      { id: 'se-main-4', from: 'sched-approval-gate', to: 'sched-coder-agent', fromSide: 'right', toSide: 'left', kind: 'main', label: 'APPROVED (Pass)', conditionBranch: 'pass', variant: 'emphasis' },
      { id: 'se-main-5', from: 'sched-approval-gate', to: 'sched-supervisor', fromSide: 'left', toSide: 'bottom', kind: 'main', label: 'HOLD / REVISE (Loop)', conditionBranch: 'loop', variant: 'dashed' },
      { id: 'se-main-6', from: 'sched-coder-agent', to: 'sched-doc-exporter', fromSide: 'right', toSide: 'left', kind: 'main', label: 'save audit log', variant: 'default' },
      { id: 'se-main-7', from: 'sched-doc-exporter', to: 'sched-dispatcher', fromSide: 'right', toSide: 'left', kind: 'main', label: 'notify telegram', variant: 'emphasis' },
      { id: 'se-sub-1', from: 'sched-router', to: 'sched-supervisor', fromSide: 'top', toSide: 'bottom', kind: 'sub', label: 'telemetry model', variant: 'dashed' },
      { id: 'se-sub-2', from: 'sched-blackboard', to: 'sched-approval-gate', fromSide: 'top', toSide: 'bottom', kind: 'sub', label: 'approval token', variant: 'dashed' },
      { id: 'se-sub-3', from: 'sched-shell-runner', to: 'sched-coder-agent', fromSide: 'top', toSide: 'bottom', kind: 'sub', label: 'run commands', variant: 'dashed' }
    ]
  }
];
