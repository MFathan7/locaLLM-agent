/**
 * Property schema and dynamic variable binding definitions for visual workflow activities.
 * Provides schema specifications, property types, and default configurations
 * for Common, Input Arguments, Options, and Output Variable binding.
 */

export type PropertyInputType =
  | 'text'
  | 'multiline'
  | 'select'
  | 'number'
  | 'slider'
  | 'boolean'
  | 'json'
  | 'tags';

export interface PropertyFieldOption {
  label: string;
  value: string | number | boolean;
}

export interface PropertyFieldDefinition {
  name: string;
  label: string;
  type: PropertyInputType;
  description: string;
  defaultValue: any;
  placeholder?: string;
  supportVariables?: boolean;
  options?: PropertyFieldOption[];
  min?: number;
  max?: number;
  step?: number;
}

export interface ActivityPropertySchema {
  tag: string;
  title: string;
  humanTitle?: string;
  category: string;
  supportsAutoMode?: boolean;
  autoModeDescription?: string;
  inputs: PropertyFieldDefinition[];
  options: PropertyFieldDefinition[];
  defaultOutputVariable: string;
  outputDescription: string;
}

export interface CommonProperties {
  displayName: string;
  description: string;
  continueOnError: boolean;
  timeoutSeconds: number;
}

export interface OutputProperties {
  outputVariable: string;
}

export interface NodeProperties {
  common: CommonProperties;
  inputs: Record<string, any>;
  options: Record<string, any>;
  output: OutputProperties;
}

export const COMMON_PROPERTY_FIELDS: PropertyFieldDefinition[] = [
  {
    name: 'displayName',
    label: 'Display Name',
    type: 'text',
    description: 'Human-readable activity name displayed on canvas.',
    defaultValue: '',
    placeholder: 'e.g. Inbound Webhook Listener',
  },
  {
    name: 'description',
    label: 'Description',
    type: 'multiline',
    description: 'Purpose and operational notes for this activity instance.',
    defaultValue: '',
    placeholder: 'Describe what this activity executes...',
  },
  {
    name: 'continueOnError',
    label: 'Continue on Error',
    type: 'boolean',
    description: 'If true, the workflow will continue execution even if this activity fails.',
    defaultValue: false,
  },
  {
    name: 'timeoutSeconds',
    label: 'Timeout (Seconds)',
    type: 'number',
    description: 'Maximum allowable execution time before terminating activity.',
    defaultValue: 60,
    min: 1,
    max: 3600,
  },
];

export const ACTIVITY_PROPERTY_SCHEMAS: Record<string, ActivityPropertySchema> = {
  // 1. Triggers
  intake: {
    tag: 'intake',
    title: 'User Objective Input',
    category: 'triggers',
    inputs: [
      {
        name: 'query',
        label: 'Task Objective',
        type: 'multiline',
        description: 'Primary objective or task directive to execute.',
        defaultValue: 'Analyze project codebase',
        placeholder: 'e.g. Conduct full audit on repository...',
        supportVariables: true,
      },
      {
        name: 'workspace',
        label: 'Workspace Boundary',
        type: 'text',
        description: 'Target project workspace for file and context operations.',
        defaultValue: 'default',
        supportVariables: true,
      },
    ],
    options: [
      {
        name: 'sourceType',
        label: 'Input Source',
        type: 'select',
        description: 'Channel through which user prompt was initiated.',
        defaultValue: 'manual',
        options: [
          { label: 'Manual Web Entry', value: 'manual' },
          { label: 'API Dispatch', value: 'api' },
        ],
      },
    ],
    defaultOutputVariable: 'out_user_objective',
    outputDescription: 'Stores the captured user objective string into blackboard state.',
  },

  'messaging-trigger': {
    tag: 'messaging-trigger',
    title: 'Messaging Trigger',
    category: 'triggers',
    inputs: [
      {
        name: 'messageTemplate',
        label: 'Simulated Inbound Message',
        type: 'multiline',
        description: 'Inbound message content from Telegram or WhatsApp bridge.',
        defaultValue: 'Tolong carikan surat Al-Kahfi ayat 1 sampai 10',
        placeholder: 'Enter inbound message text...',
        supportVariables: true,
      },
      {
        name: 'allowedUsers',
        label: 'Allowed User IDs / Handles',
        type: 'text',
        description: 'Comma-separated authorized chat IDs or usernames.',
        defaultValue: '@ops_admin, @lead_dev',
        placeholder: '@ops_admin, 12345678',
        supportVariables: false,
      },
    ],
    options: [
      {
        name: 'platform',
        label: 'Messaging Platform',
        type: 'select',
        description: 'Source messaging platform bridge.',
        defaultValue: 'telegram',
        options: [
          { label: 'Telegram Bot', value: 'telegram' },
          { label: 'WhatsApp Bridge', value: 'whatsapp' },
          { label: 'Discord Webhook', value: 'discord' },
        ],
      },
    ],
    defaultOutputVariable: 'out_trigger_payload',
    outputDescription: 'Stores the parsed incoming message text and sender details.',
  },

  'schedule-trigger': {
    tag: 'schedule-trigger',
    title: 'Schedule Trigger',
    category: 'triggers',
    inputs: [
      {
        name: 'cron',
        label: 'Cron Expression',
        type: 'text',
        description: 'Standard 5-field cron syntax (minute hour day month weekday).',
        defaultValue: '0 2 * * *',
        placeholder: '0 2 * * *',
        supportVariables: false,
      },
      {
        name: 'query',
        label: 'Routine Mission Description',
        type: 'text',
        description: 'Automated maintenance or audit description.',
        defaultValue: 'Automated System Audit & Maintenance Routine',
        supportVariables: true,
      },
    ],
    options: [
      {
        name: 'timezone',
        label: 'Timezone',
        type: 'select',
        description: 'Scheduler reference timezone.',
        defaultValue: 'Asia/Jakarta',
        options: [
          { label: 'Asia/Jakarta (WIB, UTC+7)', value: 'Asia/Jakarta' },
          { label: 'UTC', value: 'UTC' },
          { label: 'America/New_York (EST)', value: 'America/New_York' },
          { label: 'Europe/London (GMT)', value: 'Europe/London' },
        ],
      },
    ],
    defaultOutputVariable: 'out_schedule_event',
    outputDescription: 'Stores cron timestamp, scheduled run ID, and routine metadata.',
  },

  webhook: {
    tag: 'webhook',
    title: 'Webhook Trigger',
    category: 'triggers',
    inputs: [
      {
        name: 'endpoint',
        label: 'REST Endpoint Path',
        type: 'text',
        description: 'HTTP path to listen for incoming POST requests.',
        defaultValue: '/api/v1/webhook',
        supportVariables: false,
      },
      {
        name: 'workspace',
        label: 'Workspace',
        type: 'text',
        description: 'Target workspace for handling received webhook payloads.',
        defaultValue: 'default',
        supportVariables: true,
      },
    ],
    options: [
      {
        name: 'httpMethod',
        label: 'HTTP Method',
        type: 'select',
        description: 'Expected HTTP method.',
        defaultValue: 'POST',
        options: [
          { label: 'POST', value: 'POST' },
          { label: 'GET', value: 'GET' },
        ],
      },
    ],
    defaultOutputVariable: 'out_webhook_payload',
    outputDescription: 'Stores parsed JSON request body and HTTP headers.',
  },

  // 2. Orchestration
  supervisor: {
    tag: 'supervisor',
    title: 'Supervisor / Coordinator',
    category: 'orchestration',
    inputs: [
      {
        name: 'directive',
        label: 'Supervisor Directive',
        type: 'multiline',
        description: 'Strategic system prompt guiding mission decomposition and delegations.',
        defaultValue: 'Coordinate tasks and maintain blackboard state',
        supportVariables: true,
      },
      {
        name: 'workspace',
        label: 'Workspace',
        type: 'text',
        description: 'Active project workspace boundary.',
        defaultValue: 'default',
        supportVariables: true,
      },
    ],
    options: [
      {
        name: 'model',
        label: 'AI Reasoning Model',
        type: 'select',
        description: 'Model assigned to coordinator.',
        defaultValue: 'auto',
        options: [
          { label: 'Automatic (Router / Default)', value: 'auto' },
          { label: 'qwen3.5:9b', value: 'qwen3.5:9b' },
          { label: 'gemma4:12b', value: 'gemma4:12b' },
          { label: 'gemma4:26b', value: 'gemma4:26b' },
          { label: 'nemotron3-super', value: 'nemotron3-super' },
        ],
      },
      {
        name: 'temperature',
        label: 'Temperature',
        type: 'slider',
        description: 'Sampling temperature for coordinator reasoning.',
        defaultValue: 0.2,
        min: 0,
        max: 1,
        step: 0.05,
      },
      {
        name: 'maxRetries',
        label: 'Max Subtask Retries',
        type: 'number',
        description: 'Maximum subtask recovery attempts on failure.',
        defaultValue: 2,
        min: 0,
        max: 5,
      },
    ],
    defaultOutputVariable: 'out_supervisor_directive',
    outputDescription: 'Stores coordinator synthesis, delegated plan, and subtask status.',
  },

  'task-decomposer': {
    tag: 'task-decomposer',
    title: 'Task Decomposer (Planner)',
    category: 'orchestration',
    inputs: [
      {
        name: 'objective',
        label: 'Objective to Decompose',
        type: 'multiline',
        description: 'High-level mission prompt to partition into ordered steps.',
        defaultValue: '{{out_user_objective}}',
        supportVariables: true,
      },
    ],
    options: [
      {
        name: 'max_subtasks',
        label: 'Max Subtasks',
        type: 'number',
        description: 'Upper bound on discrete subtasks generated.',
        defaultValue: 4,
        min: 1,
        max: 10,
      },
      {
        name: 'strategy',
        label: 'Decomposition Strategy',
        type: 'select',
        description: 'Planning paradigm used to generate subtasks.',
        defaultValue: 'hierarchical',
        options: [
          { label: 'Hierarchical (Coordinator & Specialists)', value: 'hierarchical' },
          { label: 'Sequential (Linear Pipeline)', value: 'sequential' },
          { label: 'Dynamic (Adaptive Expansion)', value: 'dynamic' },
        ],
      },
    ],
    defaultOutputVariable: 'out_task_queue',
    outputDescription: 'Array of discrete subtask description strings ready for iteration.',
  },

  'model-router': {
    tag: 'model-router',
    title: 'Dynamic Model Router',
    category: 'orchestration',
    inputs: [],
    options: [
      {
        name: 'vram_threshold_mb',
        label: 'VRAM Threshold (MB)',
        type: 'number',
        description: 'GPU VRAM headroom needed to switch into deep reasoning tier.',
        defaultValue: 8192,
        min: 2048,
        max: 49152,
        step: 1024,
      },
      {
        name: 'fast_model',
        label: 'Fast Tier Model',
        type: 'text',
        description: 'Lightweight model used when VRAM or latency is constrained.',
        defaultValue: 'gemma4:12b',
      },
      {
        name: 'deep_model',
        label: 'Deep Tier Model',
        type: 'text',
        description: 'High-capacity model used when VRAM headroom is abundant.',
        defaultValue: 'gemma4:26b',
      },
    ],
    defaultOutputVariable: 'out_selected_model',
    outputDescription: 'Selected LLM identifier string based on hardware telemetry.',
  },

  'intent-switch': {
    tag: 'intent-switch',
    title: 'Semantic Intent Switch',
    category: 'orchestration',
    inputs: [
      {
        name: 'query',
        label: 'Input Prompt for Classification',
        type: 'multiline',
        description: 'Text string analyzed to decide execution branch.',
        defaultValue: '{{out_user_objective}}',
        supportVariables: true,
      },
    ],
    options: [
      {
        name: 'branches',
        label: 'Supported Intent Branches',
        type: 'tags',
        description: 'Available routing categories.',
        defaultValue: ['CODING', 'REASONING', 'TOOLS', 'FAST_CHAT'],
      },
    ],
    defaultOutputVariable: 'out_detected_intent',
    outputDescription: 'Detected intent label string matching outgoing branch label.',
  },

  'parallel-aggregator': {
    tag: 'parallel-aggregator',
    title: 'Parallel Aggregator',
    category: 'orchestration',
    inputs: [
      {
        name: 'mergeFields',
        label: 'Blackboard Fields to Merge',
        type: 'text',
        description: 'Comma-separated state attributes to consolidate.',
        defaultValue: 'findings, artifacts, context_variables',
      },
    ],
    options: [
      {
        name: 'join_strategy',
        label: 'Join Strategy',
        type: 'select',
        description: 'Condition required before propagating flow downstream.',
        defaultValue: 'all_completed',
        options: [
          { label: 'Wait for All Parallel Streams', value: 'all_completed' },
          { label: 'First Successful Stream', value: 'first_success' },
        ],
      },
      {
        name: 'timeout',
        label: 'Join Timeout (Seconds)',
        type: 'number',
        description: 'Maximum time to wait for converging branches.',
        defaultValue: 60,
        min: 5,
        max: 600,
      },
    ],
    defaultOutputVariable: 'out_aggregated_data',
    outputDescription: 'Merged dictionary containing consolidated specialist outputs.',
  },

  // 3. Specialists
  researcher: {
    tag: 'researcher',
    title: 'Researcher Agent',
    category: 'specialists',
    inputs: [
      {
        name: 'searchQuery',
        label: 'Research Query / Target',
        type: 'multiline',
        description: 'Target query, API endpoint, or topic to investigate.',
        defaultValue: '{{out_user_objective}}',
        placeholder: 'e.g. Surat Al-Kahfi or open-weight benchmarks',
        supportVariables: true,
      },
      {
        name: 'api_base',
        label: 'External API Base URL (Optional)',
        type: 'text',
        description: 'REST API base for domain queries (e.g. equran.id v2).',
        defaultValue: 'https://equran.id/api/v2',
        supportVariables: true,
      },
      {
        name: 'reciter',
        label: 'Audio Reciter Stream',
        type: 'text',
        description: 'Audio reciter identifier for scripture tasks.',
        defaultValue: 'Misyari-Rasyid-Al-Afasi',
      },
    ],
    options: [
      {
        name: 'model',
        label: 'Agent Model',
        type: 'select',
        description: 'LLM model utilized for research synthesis.',
        defaultValue: 'auto',
        options: [
          { label: 'Automatic (Router / Default)', value: 'auto' },
          { label: 'qwen3.5:9b', value: 'qwen3.5:9b' },
          { label: 'gemma4:12b', value: 'gemma4:12b' },
          { label: 'nemotron3-super', value: 'nemotron3-super' },
        ],
      },
      {
        name: 'temperature',
        label: 'Temperature',
        type: 'slider',
        description: 'Sampling temperature for researcher.',
        defaultValue: 0.3,
        min: 0,
        max: 1,
        step: 0.05,
      },
      {
        name: 'retrievalTopK',
        label: 'Retrieval Top K',
        type: 'number',
        description: 'Number of documentation passages to fetch.',
        defaultValue: 4,
        min: 1,
        max: 20,
      },
      {
        name: 'tools',
        label: 'Active Tools',
        type: 'tags',
        description: 'Tool capabilities enabled for this agent.',
        defaultValue: ['search_web', 'fetch_web', 'read_file'],
      },
    ],
    defaultOutputVariable: 'out_research_data',
    outputDescription: 'List of research findings, facts, and retrieved API records.',
  },

  coder: {
    tag: 'coder',
    title: 'Coder Agent',
    category: 'specialists',
    inputs: [
      {
        name: 'taskDescription',
        label: 'Coding Task / Instruction',
        type: 'multiline',
        description: 'Specification of code patch, refactor, or generation.',
        defaultValue: '{{out_user_objective}}',
        placeholder: 'e.g. Refactor handler and patch regressions...',
        supportVariables: true,
      },
      {
        name: 'output_file',
        label: 'Patch Output File Path',
        type: 'text',
        description: 'Destination file path for generated diff patch.',
        defaultValue: 'docs/patch_revision.diff',
        supportVariables: true,
      },
    ],
    options: [
      {
        name: 'model',
        label: 'Coding Model',
        type: 'select',
        description: 'Model assigned for code authoring.',
        defaultValue: 'auto',
        options: [
          { label: 'Automatic (Router / Default)', value: 'auto' },
          { label: 'qwen3.5:9b', value: 'qwen3.5:9b' },
          { label: 'gemma4:26b', value: 'gemma4:26b' },
          { label: 'nemotron3-super', value: 'nemotron3-super' },
        ],
      },
      {
        name: 'temperature',
        label: 'Temperature',
        type: 'slider',
        description: 'Sampling temperature for precise syntax authoring.',
        defaultValue: 0.1,
        min: 0,
        max: 1,
        step: 0.05,
      },
      {
        name: 'tools',
        label: 'Active Tools',
        type: 'tags',
        description: 'Filesystem and execution tools enabled for coder.',
        defaultValue: ['patch_file', 'write_file', 'check_syntax'],
      },
    ],
    defaultOutputVariable: 'out_patch_diff',
    outputDescription: 'Unified diff patch content and list of touched file paths.',
  },

  'data-analyst': {
    tag: 'data-analyst',
    title: 'Data/DB Analyst',
    category: 'specialists',
    inputs: [
      {
        name: 'sqlQuery',
        label: 'SQL Diagnostic Query',
        type: 'multiline',
        description: 'SQL statement to execute against local SQLite database.',
        defaultValue: 'SELECT service, status, last_heartbeat FROM system_services ORDER BY last_heartbeat DESC LIMIT 10;',
        supportVariables: true,
      },
      {
        name: 'db_path',
        label: 'Database File Path',
        type: 'text',
        description: 'Path to SQLite database file.',
        defaultValue: 'locallm_ops.db',
        supportVariables: true,
      },
    ],
    options: [
      {
        name: 'maxRows',
        label: 'Max Return Rows',
        type: 'number',
        description: 'Limit on returned query records.',
        defaultValue: 50,
        min: 1,
        max: 1000,
      },
      {
        name: 'readOnly',
        label: 'Enforce Read-Only',
        type: 'boolean',
        description: 'Prevents UPDATE/DROP/DELETE mutations.',
        defaultValue: true,
      },
    ],
    defaultOutputVariable: 'out_query_results',
    outputDescription: 'Array of result rows and column headers from executed SQL.',
  },

  critic: {
    tag: 'critic',
    title: 'Critic / QA Agent',
    category: 'specialists',
    inputs: [
      {
        name: 'validationCriteria',
        label: 'Verification Criteria',
        type: 'multiline',
        description: 'Quality standards and test suites required to pass.',
        defaultValue: 'Verify AST syntax, unit tests, and regression safety.',
        supportVariables: true,
      },
      {
        name: 'targetArtifact',
        label: 'Target Artifact Reference',
        type: 'text',
        description: 'Artifact to score and validate.',
        defaultValue: '{{out_patch_diff}}',
        supportVariables: true,
      },
    ],
    options: [
      {
        name: 'pass_threshold',
        label: 'Passing Score Threshold (0-100)',
        type: 'slider',
        description: 'Minimum score required to issue a PASS verdict.',
        defaultValue: 85,
        min: 50,
        max: 100,
        step: 5,
      },
      {
        name: 'model',
        label: 'Evaluation Model',
        type: 'select',
        description: 'Model performing QA grading.',
        defaultValue: 'auto',
        options: [
          { label: 'Automatic (Router / Default)', value: 'auto' },
          { label: 'qwen3.5:9b', value: 'qwen3.5:9b' },
          { label: 'gemma4:26b', value: 'gemma4:26b' },
        ],
      },
    ],
    defaultOutputVariable: 'out_qa_verdict',
    outputDescription: 'Object containing { passed: boolean, score: number, feedback: string }.',
  },

  writer: {
    tag: 'writer',
    title: 'Writer Agent',
    category: 'specialists',
    inputs: [
      {
        name: 'systemPrompt',
        label: 'System Prompt / Persona',
        type: 'multiline',
        description: 'Persona and style guidelines for drafting deliverables.',
        defaultValue: 'You are an elite technical documentation specialist. Author comprehensive, structured reports.',
        supportVariables: true,
      },
      {
        name: 'messageTemplate',
        label: 'Report Body Template',
        type: 'multiline',
        description: 'Template with dynamic variable tokens for deliverable content.',
        defaultValue: '# Deliverable for {{out_user_objective}}\n\n## Summary\n{{out_research_data}}',
        supportVariables: true,
      },
      {
        name: 'output_file',
        label: 'Document Destination Path',
        type: 'text',
        description: 'Destination file path where report is saved.',
        defaultValue: 'docs/market_intelligence_report.md',
        supportVariables: true,
      },
    ],
    options: [
      {
        name: 'format',
        label: 'Export Format',
        type: 'select',
        description: 'Document serialization format.',
        defaultValue: 'markdown',
        options: [
          { label: 'Markdown (.md)', value: 'markdown' },
          { label: 'JSON structured (.json)', value: 'json' },
          { label: 'HTML formatted (.html)', value: 'html' },
        ],
      },
      {
        name: 'model',
        label: 'Drafting Model',
        type: 'select',
        description: 'LLM utilized for document prose synthesis.',
        defaultValue: 'auto',
        options: [
          { label: 'Automatic (Router / Default)', value: 'auto' },
          { label: 'qwen3.5:9b', value: 'qwen3.5:9b' },
          { label: 'gemma4:12b', value: 'gemma4:12b' },
        ],
      },
      {
        name: 'temperature',
        label: 'Temperature',
        type: 'slider',
        description: 'Creativity / variation index for writing.',
        defaultValue: 0.35,
        min: 0,
        max: 1,
        step: 0.05,
      },
    ],
    defaultOutputVariable: 'out_written_doc',
    outputDescription: 'Full markdown or HTML content string of drafted deliverable.',
  },

  'custom-specialist': {
    tag: 'custom-specialist',
    title: 'Custom Specialist',
    category: 'specialists',
    inputs: [
      {
        name: 'role',
        label: 'Specialist Role Designation',
        type: 'text',
        description: 'Designated role identity.',
        defaultValue: 'Domain Specialist',
        supportVariables: true,
      },
      {
        name: 'directive',
        label: 'Operating Directive',
        type: 'multiline',
        description: 'System instructions guiding this specialist agent.',
        defaultValue: 'Execute specialized domain instructions',
        supportVariables: true,
      },
      {
        name: 'inputContext',
        label: 'Input Arguments',
        type: 'multiline',
        description: 'Data or instructions passed into this specialist.',
        defaultValue: '{{out_user_objective}}',
        supportVariables: true,
      },
    ],
    options: [
      {
        name: 'model',
        label: 'Model',
        type: 'select',
        description: 'Assigned LLM model.',
        defaultValue: 'auto',
        options: [
          { label: 'Automatic', value: 'auto' },
          { label: 'qwen3.5:9b', value: 'qwen3.5:9b' },
          { label: 'gemma4:12b', value: 'gemma4:12b' },
        ],
      },
      {
        name: 'temperature',
        label: 'Temperature',
        type: 'slider',
        description: 'Sampling temperature.',
        defaultValue: 0.3,
        min: 0,
        max: 1,
        step: 0.05,
      },
    ],
    defaultOutputVariable: 'out_specialist_result',
    outputDescription: 'Execution result returned by custom specialist.',
  },

  // 4. State & Knowledge
  blackboard: {
    tag: 'blackboard',
    title: 'Blackboard Hub (Shared State)',
    category: 'state_knowledge',
    inputs: [
      {
        name: 'workspace',
        label: 'Workspace Key',
        type: 'text',
        description: 'Workspace owning the blackboard state.',
        defaultValue: 'default',
        supportVariables: true,
      },
    ],
    options: [
      {
        name: 'syncIntervalSeconds',
        label: 'Sync Interval (Seconds)',
        type: 'number',
        description: 'Frequency of shared state synchronization.',
        defaultValue: 5,
        min: 1,
        max: 60,
      },
    ],
    defaultOutputVariable: 'out_blackboard_state',
    outputDescription: 'Full snapshot of the central blackboard state dictionary.',
  },

  'rag-retriever': {
    tag: 'rag-retriever',
    title: 'RAG Retriever',
    category: 'state_knowledge',
    inputs: [
      {
        name: 'searchQuery',
        label: 'Knowledge Query',
        type: 'multiline',
        description: 'Search query for vector and lexical retrieval.',
        defaultValue: '{{out_user_objective}}',
        supportVariables: true,
      },
      {
        name: 'workspace',
        label: 'Target Knowledge Workspace',
        type: 'text',
        description: 'Workspace index holding knowledge documents.',
        defaultValue: 'default',
        supportVariables: true,
      },
    ],
    options: [
      {
        name: 'top_k',
        label: 'Passages to Retrieve (Top K)',
        type: 'slider',
        description: 'Number of relevant context excerpts to return.',
        defaultValue: 4,
        min: 1,
        max: 20,
        step: 1,
      },
    ],
    defaultOutputVariable: 'out_rag_passages',
    outputDescription: 'Array of ranked passages with file sources and relevance scores.',
  },

  'memory-rw': {
    tag: 'memory-rw',
    title: 'Memory R/W',
    category: 'state_knowledge',
    inputs: [
      {
        name: 'key',
        label: 'Memory Key',
        type: 'text',
        description: 'Identifier of fact or configuration to read/write.',
        defaultValue: 'system_preferences',
        supportVariables: true,
      },
      {
        name: 'value',
        label: 'Memory Value (for Write)',
        type: 'multiline',
        description: 'Value to persist when in write mode.',
        defaultValue: '',
        supportVariables: true,
      },
    ],
    options: [
      {
        name: 'mode',
        label: 'Access Mode',
        type: 'select',
        description: 'Read or write operation.',
        defaultValue: 'read_write',
        options: [
          { label: 'Read & Write', value: 'read_write' },
          { label: 'Read Only', value: 'read' },
          { label: 'Write Only', value: 'write' },
        ],
      },
      {
        name: 'scope',
        label: 'Storage Scope',
        type: 'select',
        description: 'Workspace-isolated or global memory.',
        defaultValue: 'workspace',
        options: [
          { label: 'Workspace Scoped', value: 'workspace' },
          { label: 'Global Scoped', value: 'global' },
        ],
      },
    ],
    defaultOutputVariable: 'out_memory_value',
    outputDescription: 'Retrieved value from persistent memory.',
  },

  'context-compressor': {
    tag: 'context-compressor',
    title: 'Context Compressor',
    category: 'state_knowledge',
    inputs: [
      {
        name: 'contextInput',
        label: 'Context to Compress',
        type: 'multiline',
        description: 'Input transcript or document text.',
        defaultValue: '{{out_research_data}}',
        supportVariables: true,
      },
    ],
    options: [
      {
        name: 'max_tokens',
        label: 'Target Token Budget',
        type: 'number',
        description: 'Target maximum token length after compression.',
        defaultValue: 3000,
        min: 500,
        max: 16000,
        step: 500,
      },
    ],
    defaultOutputVariable: 'out_compressed_context',
    outputDescription: 'Concise bulleted summary suitable for token-limited prompts.',
  },

  // 5. Tools & Plugins
  'mcp-tool': {
    tag: 'mcp-tool',
    title: 'MCP Tool',
    category: 'tools_plugins',
    inputs: [
      {
        name: 'server',
        label: 'MCP Server ID',
        type: 'text',
        description: 'Configured Model Context Protocol server name.',
        defaultValue: 'local',
        supportVariables: false,
      },
      {
        name: 'tool_name',
        label: 'Tool Function Name',
        type: 'text',
        description: 'Name of the tool exposed by the MCP server.',
        defaultValue: 'inspect',
        supportVariables: true,
      },
      {
        name: 'arguments',
        label: 'Tool Call Arguments (JSON)',
        type: 'json',
        description: 'JSON object payload passed into tool function.',
        defaultValue: '{}',
        supportVariables: true,
      },
    ],
    options: [],
    defaultOutputVariable: 'out_mcp_result',
    outputDescription: 'Raw output string or structured JSON returned by MCP server.',
  },

  filesystem: {
    tag: 'filesystem',
    title: 'Filesystem',
    category: 'tools_plugins',
    inputs: [
      {
        name: 'path',
        label: 'File / Directory Path',
        type: 'text',
        description: 'Relative path in workspace.',
        defaultValue: '.',
        supportVariables: true,
      },
      {
        name: 'fileContent',
        label: 'Content (for Write/Patch)',
        type: 'multiline',
        description: 'Text content to write or patch.',
        defaultValue: '',
        supportVariables: true,
      },
    ],
    options: [
      {
        name: 'operation',
        label: 'Operation Mode',
        type: 'select',
        description: 'Filesystem operation to perform.',
        defaultValue: 'read',
        options: [
          { label: 'Read File', value: 'read' },
          { label: 'Write File', value: 'write' },
          { label: 'List Directory', value: 'list' },
        ],
      },
      {
        name: 'workspace',
        label: 'Workspace',
        type: 'text',
        description: 'Target workspace boundary.',
        defaultValue: 'default',
        supportVariables: true,
      },
    ],
    defaultOutputVariable: 'out_fs_result',
    outputDescription: 'File content string or directory item list.',
  },

  subprocess: {
    tag: 'subprocess',
    title: 'Shell Runner',
    category: 'tools_plugins',
    inputs: [
      {
        name: 'command',
        label: 'Terminal Shell Command',
        type: 'multiline',
        description: 'Shell command executed in project environment.',
        defaultValue: 'pytest -q',
        placeholder: 'e.g. pytest -q tests/',
        supportVariables: true,
      },
      {
        name: 'workingDir',
        label: 'Working Directory',
        type: 'text',
        description: 'Execution working directory relative to project root.',
        defaultValue: '.',
        supportVariables: true,
      },
    ],
    options: [],
    defaultOutputVariable: 'out_shell_stdout',
    outputDescription: 'Captured stdout, stderr, and integer exit code.',
  },

  'online-web': {
    tag: 'online-web',
    title: 'Web Search',
    category: 'tools_plugins',
    inputs: [
      {
        name: 'query',
        label: 'Search Query',
        type: 'multiline',
        description: 'Query submitted to web search engine.',
        defaultValue: '{{out_user_objective}}',
        placeholder: 'e.g. latest release specs...',
        supportVariables: true,
      },
    ],
    options: [
      {
        name: 'provider',
        label: 'Search Provider',
        type: 'select',
        description: 'Engine used for web search.',
        defaultValue: 'auto',
        options: [
          { label: 'Automatic Discovery', value: 'auto' },
          { label: 'Bing Web API', value: 'bing' },
          { label: 'DuckDuckGo HTML', value: 'duckduckgo' },
        ],
      },
      {
        name: 'max_results',
        label: 'Max Search Results',
        type: 'number',
        description: 'Number of web citations to return.',
        defaultValue: 5,
        min: 1,
        max: 20,
      },
    ],
    defaultOutputVariable: 'out_web_results',
    outputDescription: 'Array of search citations with titles, URLs, and snippets.',
  },

  'plugin-executor': {
    tag: 'plugin-executor',
    title: 'Plugin Executor',
    category: 'tools_plugins',
    inputs: [
      {
        name: 'plugin_id',
        label: 'Plugin Identifier',
        type: 'text',
        description: 'Identifier of installed plugin.',
        defaultValue: 'default',
        supportVariables: true,
      },
      {
        name: 'actionPayload',
        label: 'Action Parameters (JSON)',
        type: 'json',
        description: 'Parameters forwarded to the plugin action.',
        defaultValue: '{}',
        supportVariables: true,
      },
    ],
    options: [],
    defaultOutputVariable: 'out_plugin_result',
    outputDescription: 'Execution result object returned by plugin function.',
  },

  // 6. Flow Control
  'quality-gate': {
    tag: 'quality-gate',
    title: 'Quality Gate (If/Else)',
    category: 'flow_control',
    inputs: [
      {
        name: 'condition',
        label: 'Condition Expression',
        type: 'text',
        description: 'Evaluation rule determining pass vs retry branch.',
        defaultValue: 'verdict.passed == true',
        placeholder: 'e.g. score >= 85 or admin_action_approved == true',
        supportVariables: true,
      },
    ],
    options: [
      {
        name: 'max_retries',
        label: 'Max Retry Iterations',
        type: 'number',
        description: 'Maximum revision attempts before terminating loop.',
        defaultValue: 2,
        min: 0,
        max: 10,
      },
      {
        name: 'min_score',
        label: 'Minimum Pass Score',
        type: 'slider',
        description: 'Threshold score (0-100) needed to branch to Pass.',
        defaultValue: 80,
        min: 50,
        max: 100,
        step: 5,
      },
    ],
    defaultOutputVariable: 'out_gate_decision',
    outputDescription: 'Branch selection ("true" for pass, "loop" for retry).',
  },

  'task-iterator': {
    tag: 'task-iterator',
    title: 'Sub-Task Iterator (ForEach)',
    category: 'flow_control',
    inputs: [
      {
        name: 'queueVariable',
        label: 'Target Queue Variable',
        type: 'text',
        description: 'Blackboard variable name containing array of subtasks.',
        defaultValue: 'task_queue',
        supportVariables: true,
      },
    ],
    options: [
      {
        name: 'batch_size',
        label: 'Batch Size',
        type: 'number',
        description: 'Number of subtasks dispatched per iteration.',
        defaultValue: 1,
        min: 1,
        max: 10,
      },
    ],
    defaultOutputVariable: 'out_current_item',
    outputDescription: 'Active subtask item extracted for the current iteration.',
  },

  'policy-gate': {
    tag: 'policy-gate',
    title: 'Human Approval',
    category: 'flow_control',
    inputs: [
      {
        name: 'promptMessage',
        label: 'Approval Prompt / Summary',
        type: 'multiline',
        description: 'Summary presented to user when authorization is requested.',
        defaultValue: 'Action Required: Pending maintenance update ready. Awaiting admin approval via web console.',
        supportVariables: true,
      },
    ],
    options: [
      {
        name: 'policy',
        label: 'Policy Mode',
        type: 'select',
        description: 'Behavioral security gate policy.',
        defaultValue: 'ask',
        options: [
          { label: 'Ask for confirmation (Human-in-the-Loop)', value: 'ask' },
          { label: 'Auto-approve (Autonomous Execution)', value: 'auto' },
        ],
      },
      {
        name: 'timeout_seconds',
        label: 'Approval Timeout (Seconds)',
        type: 'number',
        description: 'Maximum time to wait before auto-rejecting.',
        defaultValue: 120,
        min: 10,
        max: 3600,
      },
    ],
    defaultOutputVariable: 'out_approval_status',
    outputDescription: 'Status of human approval ("approved" or "rejected").',
  },

  'try-catch': {
    tag: 'try-catch',
    title: 'Try-Catch',
    category: 'flow_control',
    inputs: [],
    options: [
      {
        name: 'max_error_retries',
        label: 'Max Error Retries',
        type: 'number',
        description: 'Number of attempts before branching to error recovery.',
        defaultValue: 1,
        min: 0,
        max: 5,
      },
    ],
    defaultOutputVariable: 'out_error_info',
    outputDescription: 'Captured exception message, stack trace, and failing node ID.',
  },

  // 7. Outputs
  'chat-output': {
    tag: 'chat-output',
    title: 'Chat & Artifact Output',
    category: 'outputs',
    inputs: [
      {
        name: 'message',
        label: 'Final Chat Message Template',
        type: 'multiline',
        description: 'Message displayed in chat upon pipeline completion.',
        defaultValue: 'Objective accomplished: {{out_user_objective}}.',
        supportVariables: true,
      },
      {
        name: 'output_file',
        label: 'Audit Report Deliverable Path',
        type: 'text',
        description: 'Path where delivery receipt is saved to disk.',
        defaultValue: 'docs/audit_report.md',
        supportVariables: true,
      },
    ],
    options: [
      {
        name: 'notify_user',
        label: 'Notify User',
        type: 'boolean',
        description: 'Display UI toast notification when deliverable is created.',
        defaultValue: true,
      },
    ],
    defaultOutputVariable: 'out_chat_deliverable',
    outputDescription: 'Final conversation response message and created file details.',
  },

  'doc-exporter': {
    tag: 'doc-exporter',
    title: 'Document Exporter',
    category: 'outputs',
    inputs: [
      {
        name: 'output_path',
        label: 'Output File Path',
        type: 'text',
        description: 'Target file path to export deliverable to.',
        defaultValue: 'docs/workflow_report.md',
        supportVariables: true,
      },
      {
        name: 'contentTemplate',
        label: 'Custom Content Template (Optional)',
        type: 'multiline',
        description: 'Optional content template. If empty, uses synthesized state artifacts.',
        defaultValue: '',
        supportVariables: true,
      },
    ],
    options: [
      {
        name: 'format',
        label: 'Export Format',
        type: 'select',
        description: 'File serialization format.',
        defaultValue: 'markdown',
        options: [
          { label: 'Markdown (.md)', value: 'markdown' },
          { label: 'JSON structured (.json)', value: 'json' },
          { label: 'HTML web view (.html)', value: 'html' },
        ],
      },
      {
        name: 'notify_user',
        label: 'Send Completion Notification',
        type: 'boolean',
        description: 'Send notification alert via Telegram if configured.',
        defaultValue: true,
      },
    ],
    defaultOutputVariable: 'out_exported_file',
    outputDescription: 'Saved file metadata including path, size in bytes, and timestamp.',
  },

  'messaging-dispatcher': {
    tag: 'messaging-dispatcher',
    title: 'Messaging Dispatcher',
    category: 'outputs',
    inputs: [
      {
        name: 'recipient',
        label: 'Recipient Chat ID / Handle',
        type: 'text',
        description: 'Target chat ID or recipient username.',
        defaultValue: '@ops_admin',
        supportVariables: true,
      },
      {
        name: 'messageTemplate',
        label: 'Message Content Template',
        type: 'multiline',
        description: 'Template or custom alert text to send.',
        defaultValue: '',
        placeholder: 'Message automatically synthesized from upstream workflow context...',
        supportVariables: true,
      },
    ],
    options: [
      {
        name: 'channel',
        label: 'Delivery Channel',
        type: 'select',
        description: 'Target messaging channel.',
        defaultValue: 'telegram',
        options: [
          { label: 'Telegram Bot API', value: 'telegram' },
          { label: 'WhatsApp Bridge', value: 'whatsapp' },
          { label: 'Discord Webhook', value: 'discord' },
        ],
      },
    ],
    defaultOutputVariable: 'out_dispatch_receipt',
    outputDescription: 'Delivery receipt confirming dispatch status and timestamp.',
  },
};

/**
 * Returns the property schema for a given activity tag with safe fallback.
 */
export function getPropertySchemaForActivity(
  tag: string,
  defaultTitle?: string,
  _defaultSubtitle?: string
): ActivityPropertySchema {
  const cleanTag = (tag || '').toLowerCase().trim();
  if (ACTIVITY_PROPERTY_SCHEMAS[cleanTag]) {
    return ACTIVITY_PROPERTY_SCHEMAS[cleanTag];
  }

  // Fallback for custom or unmapped activities
  return {
    tag: cleanTag || 'custom',
    title: defaultTitle || 'Activity Properties',
    category: 'custom',
    inputs: [
      {
        name: 'query',
        label: 'Task Directive / Query',
        type: 'multiline',
        description: 'Primary instruction for this activity.',
        defaultValue: '',
        supportVariables: true,
      },
    ],
    options: [
      {
        name: 'model',
        label: 'AI Model',
        type: 'select',
        description: 'Model assigned to activity.',
        defaultValue: 'auto',
        options: [
          { label: 'Automatic', value: 'auto' },
          { label: 'qwen3.5:9b', value: 'qwen3.5:9b' },
          { label: 'gemma4:12b', value: 'gemma4:12b' },
        ],
      },
    ],
    defaultOutputVariable: `out_${cleanTag.replace(/[^a-z0-9_]/g, '_') || 'custom'}_result`,
    outputDescription: 'Stores result of this activity execution.',
  };
}

/**
 * Instantiates complete default properties for a given activity node.
 */
export function getDefaultPropertiesForActivity(
  tag: string,
  initialTitle?: string,
  initialSubtitle?: string,
  legacyConfig?: Record<string, any>
): NodeProperties {
  const schema = getPropertySchemaForActivity(tag);
  const cfg = legacyConfig || {};

  const inputs: Record<string, any> = {};
  schema.inputs.forEach((f) => {
    inputs[f.name] = cfg[f.name] !== undefined ? cfg[f.name] : f.defaultValue;
  });

  const options: Record<string, any> = {};
  schema.options.forEach((f) => {
    options[f.name] = cfg[f.name] !== undefined ? cfg[f.name] : f.defaultValue;
  });

  // Carry over any extra legacy config keys into options
  Object.keys(cfg).forEach((k) => {
    if (inputs[k] === undefined && options[k] === undefined) {
      options[k] = cfg[k];
    }
  });

  // Smart default parameterMode: 'auto' for AI/tools/specialists/outputs, 'custom' for triggers or when set
  if (options.parameterMode === undefined) {
    options.parameterMode = cfg.parameterMode || (schema.supportsAutoMode !== false && schema.category !== 'triggers' ? 'auto' : 'custom');
  }

  return {
    common: {
      displayName: initialTitle || schema.title,
      description: initialSubtitle || '',
      continueOnError: cfg.continueOnError ?? false,
      timeoutSeconds: cfg.timeoutSeconds ?? cfg.timeout ?? 60,
    },
    inputs,
    options,
    output: {
      outputVariable: cfg.outputVariable || schema.defaultOutputVariable,
    },
  };
}

/**
 * Ensures a node has properly formed dynamic properties, backfilling from legacy config if missing.
 */
export function ensureNodeDynamicProperties(node: any): any {
  if (!node) return node;

  const tag = node.tag || '';
  const existingProps = node.properties;

  if (
    existingProps &&
    existingProps.common &&
    existingProps.inputs &&
    existingProps.options &&
    existingProps.output
  ) {
    return node;
  }

  const defaultProps = getDefaultPropertiesForActivity(
    tag,
    node.title,
    node.subtitle,
    node.config
  );

  return {
    ...node,
    properties: {
      common: {
        ...defaultProps.common,
        ...(existingProps?.common || {}),
      },
      inputs: {
        ...defaultProps.inputs,
        ...(existingProps?.inputs || {}),
      },
      options: {
        ...defaultProps.options,
        ...(existingProps?.options || {}),
      },
      output: {
        ...defaultProps.output,
        ...(existingProps?.output || {}),
      },
    },
  };
}
