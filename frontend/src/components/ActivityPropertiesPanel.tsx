import React, { useState, useMemo } from 'react';
import type {
  WorkflowNode,
  WorkflowEdge,
  WorkflowLaneConfig,
  NodeProperties,
  PropertyFieldDefinition
} from '../types';
import { getPropertySchemaForActivity } from '../types';
import {
  X,
  Settings2,
  Sparkles,
  Bot,
  Sliders,
  ChevronDown,
  ChevronRight,
  ArrowDownRight,
  GitFork,
  BookOpen,
  Trash2,
  Check,
  Copy,
  RefreshCw
} from 'lucide-react';

interface ActivityPropertiesPanelProps {
  node: WorkflowNode;
  nodes: WorkflowNode[];
  edges: WorkflowEdge[];
  lanes: WorkflowLaneConfig[];
  isExecuting: boolean;
  apiModels: { id: string; provider?: string }[];
  isLoadingModels: boolean;
  currentBackend: string;
  workspaceList: { name: string }[];
  activeWorkspace: string;
  onUpdateProperties: (nodeId: string, nextProperties: NodeProperties) => void;
  onUpdateNodeTitle: (nodeId: string, title: string) => void;
  onUpdateNodeLane: (nodeId: string, laneId: string) => void;
  onSnapLane: (nodeId: string) => void;
  onRequestDeleteNode: (node: WorkflowNode) => void;
  onFetchModels: (backend: string) => void;
  onClose: () => void;
  onOpenDocs?: (catalogItem: any) => void;
  catalogItem?: any;
  onAddEdge?: (from: string, to: string) => void;
  onDeleteEdge?: (edgeId: string) => void;
}

const ToggleSwitch: React.FC<{
  checked: boolean;
  onChange: (val: boolean) => void;
  disabled?: boolean;
}> = ({ checked, onChange, disabled }) => (
  <button
    type="button"
    role="switch"
    aria-checked={checked}
    disabled={disabled}
    onClick={() => onChange(!checked)}
    className={`relative inline-flex h-5 w-9 shrink-0 cursor-pointer items-center rounded-full transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:ring-offset-1 disabled:opacity-50 ${
      checked ? 'bg-cyan-600' : 'bg-slate-300 dark:bg-slate-700'
    }`}
  >
    <span
      className={`pointer-events-none inline-block h-4 w-4 transform rounded-full bg-white shadow-sm ring-0 transition duration-200 ease-in-out ${
        checked ? 'translate-x-4' : 'translate-x-0.5'
      }`}
    />
  </button>
);

export const ActivityPropertiesPanel: React.FC<ActivityPropertiesPanelProps> = ({
  node,
  nodes,
  edges,
  lanes,
  isExecuting,
  apiModels,
  isLoadingModels,
  currentBackend,
  workspaceList: _workspaceList,
  activeWorkspace: _activeWorkspace,
  onUpdateProperties,
  onUpdateNodeTitle,
  onUpdateNodeLane,
  onSnapLane,
  onRequestDeleteNode,
  onFetchModels,
  onClose,
  onOpenDocs,
  catalogItem,
  onAddEdge,
  onDeleteEdge
}) => {
  // Progressive disclosure: Advanced settings collapsed by default
  const [isAdvancedOpen, setIsAdvancedOpen] = useState<boolean>(false);
  const [copiedKey, setCopiedKey] = useState<string | null>(null);
  const [jsonErrors, setJsonErrors] = useState<Record<string, string>>({});

  const schema = useMemo(() => {
    return getPropertySchemaForActivity(node.tag || '', node.title, node.subtitle);
  }, [node.tag, node.title, node.subtitle]);

  // Compute direct predecessor nodes flowing into this node (Zero-Variable Implicit Flow)
  const incomingPredecessors = useMemo(() => {
    const directEdgeFromIds = edges.filter((e) => e.to === node.id).map((e) => e.from);
    return nodes.filter((n) => directEdgeFromIds.includes(n.id));
  }, [edges, node.id, nodes]);

  // Normalized properties state
  const properties: NodeProperties = useMemo(() => {
    const cat = schema.category;
    const isTrigger = cat === 'triggers';
    const initialMode =
      node.properties?.options?.parameterMode ||
      (isTrigger ? 'custom' : 'auto');

    return {
      common: {
        displayName: node.properties?.common?.displayName || node.title || '',
        description: node.properties?.common?.description || node.subtitle || '',
        continueOnError: Boolean(node.properties?.common?.continueOnError),
        timeoutSeconds: node.properties?.common?.timeoutSeconds ?? 60
      },
      inputs: node.properties?.inputs || {},
      options: {
        parameterMode: initialMode,
        ...(node.properties?.options || {})
      },
      output: {
        outputVariable:
          node.properties?.output?.outputVariable ||
          schema.defaultOutputVariable ||
          `out_${node.id.replace(/-/g, '_')}`
      }
    };
  }, [node.properties, node.title, node.subtitle, node.id, schema.category, schema.defaultOutputVariable]);

  const parameterMode: 'auto' | 'custom' = properties.options.parameterMode === 'custom' ? 'custom' : 'auto';

  // Handler to update a single input field
  const handleUpdateInput = (fieldName: string, value: any) => {
    const nextProps: NodeProperties = {
      ...properties,
      inputs: {
        ...properties.inputs,
        [fieldName]: value
      }
    };
    onUpdateProperties(node.id, nextProps);
  };

  // Handler to update a single option field
  const handleUpdateOption = (optionName: string, value: any) => {
    const nextProps: NodeProperties = {
      ...properties,
      options: {
        ...properties.options,
        [optionName]: value
      }
    };
    onUpdateProperties(node.id, nextProps);
  };

  // Handler to update common settings
  const handleUpdateCommon = (key: keyof NodeProperties['common'], value: any) => {
    const nextProps: NodeProperties = {
      ...properties,
      common: {
        ...properties.common,
        [key]: value
      }
    };
    onUpdateProperties(node.id, nextProps);
  };

  // Handler to update output variable
  const handleUpdateOutput = (variableName: string) => {
    const sanitized = variableName.replace(/[^a-zA-Z0-9_]/g, '_');
    const nextProps: NodeProperties = {
      ...properties,
      output: {
        outputVariable: sanitized
      }
    };
    onUpdateProperties(node.id, nextProps);
  };

  // Toggle Parameter Mode between Auto by AI and Custom
  const handleSetMode = (mode: 'auto' | 'custom') => {
    handleUpdateOption('parameterMode', mode);
  };

  const handleCopyVariable = (varKey: string) => {
    navigator.clipboard.writeText(`{{${varKey}}}`);
    setCopiedKey(varKey);
    setTimeout(() => setCopiedKey(null), 1800);
  };

  // Render form field input
  const renderFieldInput = (
    field: PropertyFieldDefinition,
    currentValue: any,
    onChange: (val: any) => void
  ) => {
    const val = currentValue !== undefined ? currentValue : field.defaultValue;

    switch (field.type) {
      case 'multiline':
        return (
          <textarea
            rows={3}
            disabled={isExecuting}
            value={val !== undefined ? String(val) : ''}
            onChange={(e) => onChange(e.target.value)}
            placeholder={field.placeholder || String(field.defaultValue || '')}
            className="w-full px-2.5 py-1.5 rounded-xl bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 text-xs font-sans text-slate-900 dark:text-slate-100 focus:outline-none focus:border-cyan-500 resize-y shadow-2xs disabled:opacity-50"
          />
        );

      case 'select':
        return (
          <select
            disabled={isExecuting}
            value={String(val !== undefined ? val : '')}
            onChange={(e) => {
              const selectedOpt = field.options?.find((o) => String(o.value) === e.target.value);
              onChange(selectedOpt ? selectedOpt.value : e.target.value);
            }}
            className="w-full px-2.5 py-1.5 rounded-xl bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 text-xs text-slate-900 dark:text-slate-100 focus:outline-none focus:border-cyan-500 shadow-2xs cursor-pointer disabled:opacity-50"
          >
            {field.options?.map((opt) => (
              <option key={String(opt.value)} value={String(opt.value)}>
                {opt.label}
              </option>
            ))}
          </select>
        );

      case 'slider':
      case 'number':
        return (
          <div className="flex items-center gap-2">
            <input
              type={field.type === 'slider' ? 'range' : 'number'}
              min={field.min ?? 0}
              max={field.max ?? 100}
              step={field.step ?? 1}
              disabled={isExecuting}
              value={Number(val ?? field.defaultValue ?? 0)}
              onChange={(e) => onChange(Number(e.target.value))}
              className="flex-1 accent-cyan-600 dark:accent-cyan-400 cursor-pointer disabled:opacity-50"
            />
            <span className="text-xs font-mono font-bold text-slate-700 dark:text-slate-300 min-w-8 text-right px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700">
              {Number(val ?? field.defaultValue ?? 0)}
            </span>
          </div>
        );

      case 'boolean':
        return (
          <div className="flex items-center justify-between py-1">
            <span className="text-xs text-slate-700 dark:text-slate-300 font-medium">{field.label}</span>
            <ToggleSwitch
              disabled={isExecuting}
              checked={Boolean(val)}
              onChange={(checked) => onChange(checked)}
            />
          </div>
        );

      case 'json':
        const jsonString = typeof val === 'object' ? JSON.stringify(val, null, 2) : String(val || '{}');
        const hasJsonErr = Boolean(jsonErrors[field.name]);
        return (
          <div className="space-y-1">
            <textarea
              rows={4}
              disabled={isExecuting}
              defaultValue={jsonString}
              onBlur={(e) => {
                try {
                  const parsed = JSON.parse(e.target.value);
                  setJsonErrors((prev) => {
                    const c = { ...prev };
                    delete c[field.name];
                    return c;
                  });
                  onChange(parsed);
                } catch (err: any) {
                  setJsonErrors((prev) => ({ ...prev, [field.name]: err.message }));
                }
              }}
              className={`w-full px-2.5 py-1.5 rounded-xl bg-slate-900 text-slate-100 font-mono text-[11px] border ${
                hasJsonErr ? 'border-rose-500' : 'border-slate-700'
              } focus:outline-none focus:border-cyan-500 resize-y shadow-2xs`}
            />
            {hasJsonErr && <p className="text-[10px] text-rose-500 font-mono">{jsonErrors[field.name]}</p>}
          </div>
        );

      default:
        return (
          <input
            type="text"
            disabled={isExecuting}
            value={val !== undefined ? String(val) : ''}
            onChange={(e) => onChange(e.target.value)}
            placeholder={field.placeholder || String(field.defaultValue || '')}
            className="w-full px-2.5 py-1.5 rounded-xl bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 text-xs text-slate-900 dark:text-slate-100 focus:outline-none focus:border-cyan-500 shadow-2xs disabled:opacity-50"
          />
        );
    }
  };

  const isTriggerCategory = schema.category === 'triggers';

  return (
    <div className="w-80 h-full bg-white dark:bg-slate-900 border-l border-slate-200 dark:border-slate-800 flex flex-col z-20 shadow-xl overflow-hidden select-none animate-in slide-in-from-right duration-200">
      {/* Top Header */}
      <div className="p-3 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between bg-slate-50/80 dark:bg-slate-950/60 backdrop-blur-md">
        <div className="flex items-center gap-2 min-w-0">
          <div className="p-1.5 rounded-xl bg-cyan-500/10 text-cyan-600 dark:text-cyan-400">
            <Settings2 className="w-4 h-4" />
          </div>
          <div className="min-w-0">
            <h3 className="text-xs font-bold text-slate-900 dark:text-slate-100 truncate">
              {properties.common.displayName || node.title}
            </h3>
            <p className="text-[10px] text-slate-500 dark:text-slate-400 truncate">
              {schema.humanTitle || schema.title}
            </p>
          </div>
        </div>

        <button
          type="button"
          onClick={onClose}
          className="p-1 rounded-lg text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 hover:bg-slate-200/50 dark:hover:bg-slate-800 transition-colors cursor-pointer"
          title="Close Panel"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Main Content Body */}
      <div className="flex-1 overflow-y-auto p-3 space-y-3.5 text-xs text-slate-800 dark:text-slate-200 custom-scrollbar">
        {/* 1. IMPLICIT DATA FLOW STATUS CARD (ZERO-VARIABLE) */}
        <div className="p-2.5 rounded-xl bg-slate-50 dark:bg-slate-800/50 border border-slate-200 dark:border-slate-700/80 space-y-1.5">
          <div className="flex items-center justify-between">
            <span className="text-[10.5px] font-bold text-slate-700 dark:text-slate-300 flex items-center gap-1.5">
              <GitFork className="w-3.5 h-3.5 text-cyan-500" />
              <span>Context Stream</span>
            </span>
            <span className="text-[9.5px] font-semibold px-1.5 py-0.5 rounded bg-cyan-100 dark:bg-cyan-950/60 text-cyan-700 dark:text-cyan-300">
              Zero-Variable Flow
            </span>
          </div>

          {incomingPredecessors.length > 0 ? (
            <div className="space-y-1">
              <p className="text-[10px] text-slate-500 dark:text-slate-400">
                Receiving direct output context from:
              </p>
              <div className="flex flex-wrap gap-1">
                {incomingPredecessors.map((p) => (
                  <span
                    key={p.id}
                    className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 text-[10px] font-medium text-slate-800 dark:text-slate-200 shadow-2xs"
                  >
                    <ArrowDownRight className="w-2.5 h-2.5 text-cyan-500" />
                    <span>{p.properties?.common?.displayName || p.title}</span>
                  </span>
                ))}
              </div>
            </div>
          ) : isTriggerCategory ? (
            <div className="space-y-1 text-[10px] text-slate-500 dark:text-slate-400">
              <p className="flex items-center gap-1 font-medium text-slate-700 dark:text-slate-300">
                <span>⚡</span>
                <span>Workflow Trigger Entrypoint</span>
              </p>
              <p className="text-[9.5px] leading-relaxed text-slate-500 dark:text-slate-400">
                • <b>Run Pipeline:</b> Immediate manual test run on canvas.<br />
                • <b>Live / Active:</b> Fires in background daemon when toggle is ON.
              </p>
            </div>
          ) : (
            <p className="text-[10px] italic text-amber-600 dark:text-amber-400">
              Connect predecessor steps to stream context here.
            </p>
          )}
        </div>

        {/* 2. TIER 1: CORE SETTINGS (BASIC) */}
        <div className="space-y-3">
          <div className="flex items-center justify-between border-b border-slate-200 dark:border-slate-800 pb-1">
            <span className="text-[11px] font-bold text-slate-900 dark:text-slate-100 uppercase tracking-wider">
              Core Settings
            </span>
            <span className="text-[10px] text-slate-500 dark:text-slate-400 font-medium">Basic</span>
          </div>

          {/* Editable Display Name */}
          <div className="space-y-1">
            <label className="text-[10.5px] font-semibold text-slate-700 dark:text-slate-300 block">
              Step Name
            </label>
            <input
              type="text"
              disabled={isExecuting}
              value={properties.common.displayName}
              onChange={(e) => {
                handleUpdateCommon('displayName', e.target.value);
                onUpdateNodeTitle(node.id, e.target.value);
              }}
              placeholder="e.g. Market Document Analysis"
              className="w-full px-2.5 py-1.5 rounded-xl bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 text-xs text-slate-900 dark:text-slate-100 focus:outline-none focus:border-cyan-500 shadow-2xs disabled:opacity-50"
            />
          </div>

          {/* PARAMETER MODE SELECTOR (Auto AI vs Custom) */}
          {!isTriggerCategory && (
            <div className="space-y-2 pt-1">
              <label className="text-[10.5px] font-semibold text-slate-700 dark:text-slate-300 block">
                Parameter Execution Mode
              </label>
              <div className="grid grid-cols-2 gap-1 p-1 bg-slate-100 dark:bg-slate-800 rounded-xl">
                <button
                  type="button"
                  onClick={() => handleSetMode('auto')}
                  className={`py-1.5 px-2 rounded-lg text-[10.5px] font-semibold transition-all flex items-center justify-center gap-1.5 cursor-pointer ${
                    parameterMode === 'auto'
                      ? 'bg-white dark:bg-slate-900 text-cyan-600 dark:text-cyan-400 shadow-xs'
                      : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200'
                  }`}
                >
                  <Bot className="w-3 h-3" />
                  <span>🤖 Auto (AI Managed)</span>
                </button>
                <button
                  type="button"
                  onClick={() => handleSetMode('custom')}
                  className={`py-1.5 px-2 rounded-lg text-[10.5px] font-semibold transition-all flex items-center justify-center gap-1.5 cursor-pointer ${
                    parameterMode === 'custom'
                      ? 'bg-white dark:bg-slate-900 text-cyan-600 dark:text-cyan-400 shadow-xs'
                      : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200'
                  }`}
                >
                  <span>✏️ Custom Input</span>
                </button>
              </div>

              {/* Auto Mode Reassuring Banner */}
              {parameterMode === 'auto' && (
                <div className="p-2.5 rounded-xl bg-cyan-50/80 dark:bg-cyan-950/25 border border-cyan-200/80 dark:border-cyan-800/60 space-y-1">
                  <div className="flex items-center gap-1.5 text-cyan-800 dark:text-cyan-300 font-bold text-[10.5px]">
                    <Sparkles className="w-3.5 h-3.5 text-cyan-600 dark:text-cyan-400 shrink-0" />
                    <span>Auto Mode Active</span>
                  </div>
                  <p className="text-[10px] text-slate-600 dark:text-slate-300 leading-relaxed">
                    {schema.autoModeDescription ||
                      'AI automatically determines search queries, file paths, and instructions from upstream context.'}
                  </p>
                </div>
              )}

              {/* Optional Custom Directive / Notes field */}
              {parameterMode === 'auto' && (
                <div className="space-y-1 pt-1">
                  <label className="text-[10px] font-semibold text-slate-600 dark:text-slate-400 flex items-center justify-between">
                    <span>Additional Directives (Optional)</span>
                    <span className="text-[9px] text-slate-400">Optional</span>
                  </label>
                  <textarea
                    rows={2}
                    disabled={isExecuting}
                    value={properties.inputs.notes || ''}
                    onChange={(e) => handleUpdateInput('notes', e.target.value)}
                    placeholder="e.g. Focus on memory efficiency and test coverage..."
                    className="w-full px-2.5 py-1.5 rounded-xl bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 text-xs text-slate-900 dark:text-slate-100 focus:outline-none focus:border-cyan-500 resize-y shadow-2xs disabled:opacity-50"
                  />
                </div>
              )}
            </div>
          )}

          {/* CUSTOM INPUT FIELDS (Shown when Mode === 'custom' OR node is a Trigger) */}
          {(parameterMode === 'custom' || isTriggerCategory) && (
            <div className="space-y-2.5 pt-1">
              {schema.inputs.map((field) => (
                <div key={field.name} className="space-y-1">
                  <label className="text-[10.5px] font-semibold text-slate-700 dark:text-slate-300 block">
                    {field.label}
                  </label>
                  {renderFieldInput(field, properties.inputs[field.name], (val) =>
                    handleUpdateInput(field.name, val)
                  )}
                  {field.description && (
                    <p className="text-[9.5px] text-slate-500 dark:text-slate-400 leading-tight">
                      {field.description}
                    </p>
                  )}
                </div>
              ))}
            </div>
          )}

          {/* CORE ESSENTIAL OPTIONS (Specialized per Node Type) */}
          {schema.tag === 'doc-exporter' && (
            <div className="space-y-2 pt-1">
              <div className="space-y-1">
                <label className="text-[10.5px] font-semibold text-slate-700 dark:text-slate-300 block">
                  Deliverable Format
                </label>
                <select
                  disabled={isExecuting}
                  value={properties.options.exportFormat || 'markdown'}
                  onChange={(e) => handleUpdateOption('exportFormat', e.target.value)}
                  className="w-full px-2.5 py-1.5 rounded-xl bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 text-xs text-slate-900 dark:text-slate-100 focus:outline-none focus:border-cyan-500 shadow-2xs"
                >
                  <option value="markdown">Markdown (.md) - Standard Clean</option>
                  <option value="html">HTML Document (.html) - Web Page</option>
                  <option value="pdf">PDF Document (.pdf) - Formal Report</option>
                </select>
              </div>

              <div className="space-y-1">
                <label className="text-[10.5px] font-semibold text-slate-700 dark:text-slate-300 block">
                  File Output Destination
                </label>
                <input
                  type="text"
                  disabled={isExecuting}
                  value={properties.inputs.filePath || 'docs/workflow_report.md'}
                  onChange={(e) => handleUpdateInput('filePath', e.target.value)}
                  placeholder="docs/workflow_report.md"
                  className="w-full px-2.5 py-1.5 rounded-xl bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 text-xs font-mono text-slate-900 dark:text-slate-100 focus:outline-none focus:border-cyan-500 shadow-2xs"
                />
              </div>

              <div className="flex items-center justify-between py-1">
                <span className="text-xs text-slate-700 dark:text-slate-300 font-medium">
                  Dispatch Telegram Notification
                </span>
                <ToggleSwitch
                  disabled={isExecuting}
                  checked={properties.options.notifyUser !== false}
                  onChange={(checked) => handleUpdateOption('notifyUser', checked)}
                />
              </div>
            </div>
          )}

          {schema.tag === 'model-router' && (
            <div className="space-y-1 pt-1">
              <label className="text-[10.5px] font-semibold text-slate-700 dark:text-slate-300 block">
                Model Allocation Strategy
              </label>
              <select
                disabled={isExecuting}
                value={properties.options.routingStrategy || 'balanced'}
                onChange={(e) => handleUpdateOption('routingStrategy', e.target.value)}
                className="w-full px-2.5 py-1.5 rounded-xl bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 text-xs text-slate-900 dark:text-slate-100 focus:outline-none focus:border-cyan-500 shadow-2xs"
              >
                <option value="vram_saver">VRAM Saver (1B-3B Fast Models)</option>
                <option value="balanced">Balanced (7B-9B General Purpose)</option>
                <option value="high_perf">High Performance (14B+ Reasoning Models)</option>
              </select>
            </div>
          )}
        </div>

        {/* 3. TIER 2: ADVANCED CONFIGURATION (PROGRESSIVE DISCLOSURE) */}
        <div className="pt-2 border-t border-slate-200 dark:border-slate-800 space-y-2">
          <button
            type="button"
            onClick={() => setIsAdvancedOpen(!isAdvancedOpen)}
            className="w-full flex items-center justify-between p-2 rounded-xl bg-slate-100 dark:bg-slate-800/70 hover:bg-slate-200/70 dark:hover:bg-slate-800 text-slate-800 dark:text-slate-200 transition-colors cursor-pointer"
          >
            <div className="flex items-center gap-1.5">
              <Sliders className="w-3.5 h-3.5 text-cyan-600 dark:text-cyan-400" />
              <span className="text-[11px] font-bold">Advanced Configuration</span>
            </div>
            {isAdvancedOpen ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />}
          </button>

          {isAdvancedOpen && (
            <div className="p-3 rounded-2xl bg-slate-50 dark:bg-slate-950/40 border border-slate-200 dark:border-slate-800 space-y-3 animate-in fade-in-50 duration-150">
              {/* Model Override Selection */}
              <div className="space-y-1">
                <div className="flex items-center justify-between">
                  <label className="text-[10px] font-bold uppercase tracking-wider text-slate-600 dark:text-slate-400">
                    OVERRIDE MODEL LLM
                  </label>
                  <button
                    type="button"
                    disabled={isLoadingModels}
                    onClick={() => onFetchModels(currentBackend)}
                    className="text-[9.5px] text-cyan-600 dark:text-cyan-400 hover:underline flex items-center gap-1 cursor-pointer disabled:opacity-50"
                  >
                    <RefreshCw className={`w-2.5 h-2.5 ${isLoadingModels ? 'animate-spin' : ''}`} />
                    <span>Refresh</span>
                  </button>
                </div>
                <select
                  disabled={isExecuting}
                  value={properties.options.model || ''}
                  onChange={(e) => handleUpdateOption('model', e.target.value)}
                  className="w-full px-2.5 py-1.5 rounded-xl bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 text-xs font-mono text-slate-900 dark:text-slate-100 focus:outline-none focus:border-cyan-500 shadow-2xs"
                >
                  <option value="">Automatic (Router Assigned)</option>
                  {apiModels.map((m) => (
                    <option key={m.id} value={m.id}>
                      {m.id}
                    </option>
                  ))}
                </select>
                <p className="text-[9.5px] text-slate-500 dark:text-slate-400">
                  Leave unselected to follow dynamic router assignment.
                </p>
              </div>

              {/* Temperature Slider */}
              <div className="space-y-1">
                <div className="flex items-center justify-between">
                  <label className="text-[10px] font-bold uppercase tracking-wider text-slate-600 dark:text-slate-400">
                    Temperature (Creativity Level)
                  </label>
                  <span className="text-[10px] font-mono font-bold text-cyan-600 dark:text-cyan-400">
                    {Number(properties.options.temperature ?? 0.2).toFixed(2)}
                  </span>
                </div>
                <input
                  type="range"
                  min={0}
                  max={1}
                  step={0.05}
                  disabled={isExecuting}
                  value={Number(properties.options.temperature ?? 0.2)}
                  onChange={(e) => handleUpdateOption('temperature', Number(e.target.value))}
                  className="w-full accent-cyan-600 dark:accent-cyan-400 cursor-pointer"
                />
                <div className="flex justify-between text-[9px] text-slate-400 font-medium">
                  <span>0.0 (Strict / Factual)</span>
                  <span>1.0 (Creative / Exploratory)</span>
                </div>
              </div>

              {/* Full System Prompt Override */}
              <div className="space-y-1">
                <label className="text-[10px] font-bold uppercase tracking-wider text-slate-600 dark:text-slate-400 block">
                  Custom System Prompt Override
                </label>
                <textarea
                  rows={3}
                  disabled={isExecuting}
                  value={properties.inputs.systemPrompt || ''}
                  onChange={(e) => handleUpdateInput('systemPrompt', e.target.value)}
                  placeholder="Enter specialized system instructions to override default agent persona..."
                  className="w-full px-2.5 py-1.5 rounded-xl bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 text-xs font-mono text-slate-900 dark:text-slate-100 focus:outline-none focus:border-cyan-500 resize-y shadow-2xs"
                />
              </div>

              {/* Resilience: Continue on Error */}
              <div className="pt-2 border-t border-slate-200 dark:border-slate-800 space-y-2">
                <div className="flex items-center justify-between">
                  <div>
                    <span className="text-xs font-semibold text-slate-800 dark:text-slate-200 block">
                      Continue on Error
                    </span>
                    <span className="text-[9.5px] text-slate-500 dark:text-slate-400">
                      Pipeline execution will not halt if this step encounters an error
                    </span>
                  </div>
                  <ToggleSwitch
                    disabled={isExecuting}
                    checked={Boolean(properties.common.continueOnError)}
                    onChange={(checked) => handleUpdateCommon('continueOnError', checked)}
                  />
                </div>

                {/* Timeout Seconds */}
                <div className="flex items-center justify-between pt-1">
                  <div>
                    <span className="text-xs font-semibold text-slate-800 dark:text-slate-200 block">
                      Execution Timeout
                    </span>
                    <span className="text-[9.5px] text-slate-500 dark:text-slate-400">
                      Maximum duration in seconds
                    </span>
                  </div>
                  <input
                    type="number"
                    min={1}
                    max={3600}
                    disabled={isExecuting}
                    value={Number(properties.common.timeoutSeconds || 60)}
                    onChange={(e) => handleUpdateCommon('timeoutSeconds', Number(e.target.value))}
                    className="w-20 px-2 py-1 rounded-lg bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 text-xs font-mono text-center font-bold text-slate-800 dark:text-slate-200 focus:outline-none focus:border-cyan-500"
                  />
                </div>
              </div>

              {/* Internal Output Variable (Optional for Power Users) */}
              <div className="pt-2 border-t border-slate-200 dark:border-slate-800 space-y-1">
                <label className="text-[10px] font-bold uppercase tracking-wider text-slate-600 dark:text-slate-400 block">
                  Internal State Variable (Optional)
                </label>
                <div className="flex items-center gap-1.5">
                  <input
                    type="text"
                    disabled={isExecuting}
                    value={properties.output.outputVariable}
                    onChange={(e) => handleUpdateOutput(e.target.value)}
                    placeholder="out_result"
                    className="flex-1 px-2.5 py-1.5 rounded-xl bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 text-xs font-mono text-cyan-700 dark:text-cyan-400 focus:outline-none focus:border-cyan-500 shadow-2xs"
                  />
                  <button
                    type="button"
                    onClick={() => handleCopyVariable(properties.output.outputVariable)}
                    className="p-1.5 rounded-lg border border-slate-300 dark:border-slate-700 hover:bg-slate-200/60 dark:hover:bg-slate-800 text-slate-600 dark:text-slate-300 transition-colors cursor-pointer"
                    title="Copy Variable Key"
                  >
                    {copiedKey === properties.output.outputVariable ? (
                      <Check className="w-3.5 h-3.5 text-emerald-500" />
                    ) : (
                      <Copy className="w-3.5 h-3.5" />
                    )}
                  </button>
                </div>
                <p className="text-[9.5px] text-slate-500 dark:text-slate-400">
                  Managed automatically in shared context. Modifying this is strictly optional.
                </p>
              </div>
            </div>
          )}
        </div>

        {/* 4. SEQUENCE & LANE ASSIGNMENT */}
        <div className="space-y-1.5 pt-2 border-t border-slate-200 dark:border-slate-800">
          <label className="text-[10px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 block">
            Sequence Swimlane
          </label>
          <div className="flex items-center gap-1.5">
            <select
              disabled={isExecuting}
              value={node.lane || 'agent'}
              onChange={(e) => onUpdateNodeLane(node.id, e.target.value)}
              className="flex-1 px-2.5 py-1.5 rounded-xl bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 text-xs font-semibold text-slate-800 dark:text-slate-200 focus:outline-none focus:border-cyan-500 shadow-2xs cursor-pointer"
            >
              {lanes.map((l) => (
                <option key={l.id} value={l.id}>
                  {l.num}: {l.label}
                </option>
              ))}
            </select>
            <button
              type="button"
              disabled={isExecuting}
              onClick={() => onSnapLane(node.id)}
              className="px-2.5 py-1.5 rounded-xl bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-[10.5px] font-semibold text-slate-700 dark:text-slate-300 transition-colors cursor-pointer"
              title="Snap activity into selected lane"
            >
              Snap
            </button>
          </div>
        </div>

        {/* 5. OUTGOING CONNECTIONS */}
        <div className="space-y-2 pt-2 border-t border-slate-200 dark:border-slate-800">
          <label className="text-[10px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 block">
            Downstream Connections
          </label>
          <div className="space-y-1.5">
            {edges.filter((e) => e.from === node.id).length === 0 ? (
              <p className="text-[10.5px] italic text-slate-400">No outgoing connections from this step</p>
            ) : (
              edges
                .filter((e) => e.from === node.id)
                .map((edge) => {
                  const target = nodes.find((n) => n.id === edge.to);
                  return (
                    <div
                      key={edge.id}
                      className="p-1.5 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700/80 flex items-center justify-between text-[11px]"
                    >
                      <div className="min-w-0">
                        <span className="font-semibold text-slate-900 dark:text-slate-100 truncate block">
                          &rarr; {target?.properties?.common?.displayName || target?.title || edge.to}
                        </span>
                        <span className="text-[9.5px] font-mono text-cyan-600 dark:text-cyan-400">
                          label: &quot;{edge.label || 'next'}&quot;
                        </span>
                      </div>
                      {onDeleteEdge && (
                        <button
                          type="button"
                          onClick={() => onDeleteEdge(edge.id)}
                          className="p-1 rounded-lg text-slate-400 hover:text-rose-500 transition-colors cursor-pointer"
                          title="Remove connection"
                        >
                          <Trash2 className="w-3 h-3" />
                        </button>
                      )}
                    </div>
                  );
                })
            )}
          </div>

          {onAddEdge && (
            <select
              disabled={isExecuting}
              value=""
              onChange={(e) => {
                if (e.target.value) {
                  onAddEdge(node.id, e.target.value);
                }
              }}
              className="w-full px-2.5 py-1.5 rounded-xl bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-xs font-semibold text-slate-700 dark:text-slate-200 cursor-pointer focus:outline-none"
            >
              <option value="">+ Connect to Downstream Step...</option>
              {nodes
                .filter((n) => n.id !== node.id && !edges.some((e) => e.from === node.id && e.to === n.id))
                .map((n) => (
                  <option key={n.id} value={n.id}>
                    &rarr; {n.properties?.common?.displayName || n.title} ({n.lane})
                  </option>
                ))}
            </select>
          )}
        </div>

        {/* 6. DOCUMENTATION CARD */}
        {catalogItem && (
          <div className="p-3 rounded-2xl bg-cyan-50/70 dark:bg-cyan-950/25 border border-cyan-200/80 dark:border-cyan-800/60 space-y-1.5">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-1.5 text-cyan-800 dark:text-cyan-300 font-bold text-[11px]">
                <BookOpen className="w-3.5 h-3.5 shrink-0" />
                <span>Step Documentation</span>
              </div>
              {onOpenDocs && (
                <button
                  type="button"
                  onClick={() => onOpenDocs(catalogItem)}
                  className="text-[10px] text-cyan-700 dark:text-cyan-400 hover:underline font-semibold cursor-pointer"
                >
                  Details &rarr;
                </button>
              )}
            </div>
            <p className="text-[10.5px] leading-relaxed text-slate-700 dark:text-slate-300">
              {catalogItem.doc?.description}
            </p>
          </div>
        )}
      </div>

      {/* Delete Activity Node Action */}
      <div className="p-3 border-t border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900">
        <button
          type="button"
          disabled={isExecuting}
          onClick={() => onRequestDeleteNode(node)}
          className="w-full py-2 px-3 rounded-xl border border-rose-500/30 text-rose-600 dark:text-rose-400 hover:bg-rose-500/10 disabled:opacity-40 disabled:cursor-not-allowed text-xs font-semibold transition-colors flex items-center justify-center gap-1.5 cursor-pointer active:scale-[0.98]"
        >
          <Trash2 className="w-3.5 h-3.5" />
          <span>Delete Step</span>
        </button>
      </div>
    </div>
  );
};
