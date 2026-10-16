import React, { useState, useEffect, useCallback } from 'react';
import {
  History,
  X,
  RefreshCw,
  CheckCircle2,
  XCircle,
  Clock,
  Play,
  Globe,
  MessageSquare,
  ArrowLeft,
  Download,
  FileText,
  AlertCircle,
  Terminal
} from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';
import { api } from '../services/api';
import type { WorkflowExecutionRecord } from '../types';

interface WorkflowHistoryPanelProps {
  isOpen: boolean;
  onClose: () => void;
  activeWorkflowId?: string;
  activeWorkflowTitle?: string;
}

export const WorkflowHistoryPanel: React.FC<WorkflowHistoryPanelProps> = ({
  isOpen,
  onClose,
  activeWorkflowId,
  activeWorkflowTitle
}) => {
  const [history, setHistory] = useState<WorkflowExecutionRecord[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [filterMode, setFilterMode] = useState<'current' | 'all'>('all');
  const [selectedRun, setSelectedRun] = useState<WorkflowExecutionRecord | null>(null);

  const fetchHistory = useCallback(async () => {
    setIsLoading(true);
    try {
      const records = await api.getWorkflowHistory(
        filterMode === 'current' ? activeWorkflowId : undefined,
        50
      );
      setHistory(records);
    } catch (e) {
      console.warn('Failed to load workflow history:', e);
    } finally {
      setIsLoading(false);
    }
  }, [filterMode, activeWorkflowId]);

  useEffect(() => {
    if (isOpen) {
      fetchHistory();
      const handleKeyDown = (e: KeyboardEvent) => {
        if (e.key === 'Escape') onClose();
      };
      window.addEventListener('keydown', handleKeyDown);
      return () => window.removeEventListener('keydown', handleKeyDown);
    } else {
      setSelectedRun(null);
    }
  }, [isOpen, fetchHistory, onClose]);

  const handleDownloadArtifact = (name: string, content?: string) => {
    if (!content) return;
    const blob = new Blob([content], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = name;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const renderTriggerIcon = (source?: string) => {
    const s = (source || '').toLowerCase();
    if (s.includes('tele')) return <MessageSquare className="w-3.5 h-3.5 text-sky-400" />;
    if (s.includes('what')) return <MessageSquare className="w-3.5 h-3.5 text-emerald-400" />;
    if (s.includes('sched') || s.includes('cron')) return <Clock className="w-3.5 h-3.5 text-amber-400" />;
    if (s.includes('web')) return <Globe className="w-3.5 h-3.5 text-purple-400" />;
    return <Play className="w-3.5 h-3.5 text-cyan-400" />;
  };

  if (!isOpen) return null;

  return (
    <AnimatePresence>
      <div
        className="fixed inset-0 z-50 flex justify-end bg-slate-950/60 backdrop-blur-xs"
        onClick={onClose}
      >
        <motion.div
          initial={{ x: '100%', opacity: 0.5 }}
          animate={{ x: 0, opacity: 1 }}
          exit={{ x: '100%', opacity: 0 }}
          transition={{ type: 'spring', damping: 28, stiffness: 300 }}
          onClick={(e) => e.stopPropagation()}
          className="w-full max-w-xl h-full bg-white dark:bg-slate-900 border-l border-slate-200 dark:border-slate-800 shadow-2xl flex flex-col z-50 overflow-hidden"
        >
          {/* Header */}
          <div className="p-4 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between bg-slate-50/50 dark:bg-slate-900/50">
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-xl bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center text-cyan-600 dark:text-cyan-400">
                <History className="w-4 h-4" />
              </div>
              <div>
                <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100">
                  Execution History & Telemetry
                </h3>
                <p className="text-[11px] text-slate-500 dark:text-slate-400">
                  {filterMode === 'current' && activeWorkflowTitle
                    ? `Filtered for: ${activeWorkflowTitle}`
                    : 'Server-persisted workflow pipeline execution records'}
                </p>
              </div>
            </div>

            <div className="flex items-center gap-1.5">
              <button
                type="button"
                onClick={fetchHistory}
                disabled={isLoading}
                className="p-2 rounded-xl hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-500 hover:text-slate-700 dark:hover:text-slate-300 transition-colors cursor-pointer"
                title="Refresh history"
              >
                <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
              </button>
              <button
                type="button"
                data-testid="close-history-btn"
                onClick={onClose}
                className="p-2 rounded-xl hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-500 hover:text-slate-700 dark:hover:text-slate-300 transition-colors cursor-pointer"
                title="Close history"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* Filter Bar (When in list view) */}
          {!selectedRun && (
            <div className="px-4 py-2.5 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between gap-2 bg-slate-50/30 dark:bg-slate-900/30">
              <div className="flex items-center gap-1.5 bg-slate-100 dark:bg-slate-800/80 p-0.5 rounded-xl text-xs">
                <button
                  type="button"
                  onClick={() => setFilterMode('all')}
                  className={`px-3 py-1 rounded-lg font-semibold transition-all cursor-pointer ${
                    filterMode === 'all'
                      ? 'bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 shadow-2xs'
                      : 'text-slate-500 hover:text-slate-800 dark:hover:text-slate-200'
                  }`}
                >
                  All Pipelines
                </button>
                <button
                  type="button"
                  onClick={() => setFilterMode('current')}
                  className={`px-3 py-1 rounded-lg font-semibold transition-all cursor-pointer ${
                    filterMode === 'current'
                      ? 'bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 shadow-2xs'
                      : 'text-slate-500 hover:text-slate-800 dark:hover:text-slate-200'
                  }`}
                >
                  Current Flow
                </button>
              </div>

              <span className="text-[11px] font-semibold text-slate-400">
                {history.length} {history.length === 1 ? 'run' : 'runs'} recorded
              </span>
            </div>
          )}

          {/* Content Area */}
          <div className="flex-1 overflow-y-auto p-4">
            {selectedRun ? (
              /* Detail View for Selected Run */
              <div className="space-y-4">
                <button
                  type="button"
                  onClick={() => setSelectedRun(null)}
                  className="flex items-center gap-1.5 text-xs font-semibold text-cyan-600 dark:text-cyan-400 hover:underline cursor-pointer"
                >
                  <ArrowLeft className="w-3.5 h-3.5" />
                  <span>Back to all executions</span>
                </button>

                {/* Run Overview Card */}
                <div className="p-3.5 rounded-2xl bg-slate-50 dark:bg-slate-800/50 border border-slate-200 dark:border-slate-800 space-y-3">
                  <div className="flex items-center justify-between">
                    <div>
                      <h4 className="text-sm font-bold text-slate-900 dark:text-slate-100">
                        {selectedRun.workflow_title || selectedRun.workflow_id}
                      </h4>
                      <p className="text-[11px] font-mono text-slate-400 mt-0.5">
                        Run ID: {selectedRun.run_id}
                      </p>
                    </div>
                    <span
                      className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-bold ${
                        selectedRun.status === 'success'
                          ? 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20'
                          : 'bg-rose-500/10 text-rose-600 dark:text-rose-400 border border-rose-500/20'
                      }`}
                    >
                      {selectedRun.status === 'success' ? (
                        <CheckCircle2 className="w-3.5 h-3.5" />
                      ) : (
                        <XCircle className="w-3.5 h-3.5" />
                      )}
                      <span className="capitalize">{selectedRun.status}</span>
                    </span>
                  </div>

                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-2 border-t border-slate-200 dark:border-slate-700/50 text-xs">
                    <div>
                      <span className="text-[10px] uppercase font-bold text-slate-400 block">Trigger</span>
                      <span className="font-semibold capitalize text-slate-700 dark:text-slate-200 flex items-center gap-1 mt-0.5">
                        {renderTriggerIcon(selectedRun.trigger_source)}
                        {selectedRun.trigger_source || 'manual'}
                      </span>
                    </div>
                    <div>
                      <span className="text-[10px] uppercase font-bold text-slate-400 block">Duration</span>
                      <span className="font-semibold text-slate-700 dark:text-slate-200 mt-0.5 block">
                        {selectedRun.duration_seconds}s
                      </span>
                    </div>
                    <div>
                      <span className="text-[10px] uppercase font-bold text-slate-400 block">Steps</span>
                      <span className="font-semibold text-slate-700 dark:text-slate-200 mt-0.5 block">
                        {selectedRun.steps_executed} steps
                      </span>
                    </div>
                    <div>
                      <span className="text-[10px] uppercase font-bold text-slate-400 block">Timestamp</span>
                      <span className="font-semibold text-slate-700 dark:text-slate-200 mt-0.5 block text-[11px]">
                        {new Date(selectedRun.started_at).toLocaleTimeString()}
                      </span>
                    </div>
                  </div>

                  {selectedRun.error && (
                    <div className="p-2.5 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-600 dark:text-rose-400 text-xs flex items-start gap-2">
                      <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
                      <div>
                        <span className="font-bold block">Execution Error</span>
                        <span>{selectedRun.error}</span>
                      </div>
                    </div>
                  )}
                </div>

                {/* Artifacts Produced */}
                {selectedRun.artifacts && selectedRun.artifacts.length > 0 && (
                  <div className="space-y-2">
                    <h5 className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 flex items-center gap-1.5">
                      <FileText className="w-3.5 h-3.5 text-cyan-500" />
                      <span>Generated Artifacts & Files ({selectedRun.artifacts.length})</span>
                    </h5>
                    <div className="space-y-1.5">
                      {selectedRun.artifacts.map((art, idx) => {
                        const name = art.name || art.path?.split('/').pop() || `artifact_${idx + 1}`;
                        return (
                          <div
                            key={idx}
                            className="p-2.5 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-800 flex items-center justify-between text-xs"
                          >
                            <div className="min-w-0 pr-2">
                              <span className="font-semibold text-slate-900 dark:text-slate-100 truncate block">
                                {name}
                              </span>
                              {art.path && (
                                <span className="font-mono text-[10px] text-slate-400 truncate block mt-0.5">
                                  {art.path}
                                </span>
                              )}
                            </div>
                            {art.content && (
                              <button
                                type="button"
                                onClick={() => handleDownloadArtifact(name, art.content)}
                                className="px-2.5 py-1 rounded-lg bg-cyan-500/10 hover:bg-cyan-500/20 text-cyan-600 dark:text-cyan-400 font-semibold flex items-center gap-1 transition-colors cursor-pointer"
                              >
                                <Download className="w-3 h-3" />
                                <span>Download</span>
                              </button>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}

                {/* Step Trace Logs */}
                <div className="space-y-2">
                  <h5 className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 flex items-center gap-1.5">
                    <Terminal className="w-3.5 h-3.5 text-emerald-500" />
                    <span>Real-Time Execution Steps & Logs ({selectedRun.logs?.length || 0})</span>
                  </h5>
                  <div className="rounded-2xl bg-slate-950 border border-slate-800 p-3 space-y-2 max-h-80 overflow-y-auto font-mono text-[11px]">
                    {selectedRun.logs && selectedRun.logs.length > 0 ? (
                      selectedRun.logs.map((log, lIdx) => (
                        <div key={lIdx} className="flex items-start gap-2 text-slate-300">
                          <span className="text-slate-500 shrink-0 select-none">
                            {log.timestamp || '00:00:00'}
                          </span>
                          <span className="text-cyan-400 font-semibold shrink-0">
                            [{log.agent || 'Agent'}]
                          </span>
                          <span className="text-slate-400 shrink-0">
                            ({log.event_type || 'step'}):
                          </span>
                          <span className="text-slate-200 break-words flex-1">
                            {log.message}
                          </span>
                        </div>
                      ))
                    ) : (
                      <p className="text-slate-500 text-xs italic">No step logs recorded for this run.</p>
                    )}
                  </div>
                </div>
              </div>
            ) : (
              /* List View */
              <div className="space-y-2">
                {isLoading ? (
                  <div className="py-12 flex flex-col items-center justify-center text-slate-400 space-y-2">
                    <RefreshCw className="w-6 h-6 animate-spin text-cyan-500" />
                    <p className="text-xs">Fetching execution records from server...</p>
                  </div>
                ) : history.length === 0 ? (
                  <div className="py-16 text-center space-y-3">
                    <div className="w-12 h-12 rounded-2xl bg-slate-100 dark:bg-slate-800 mx-auto flex items-center justify-center text-slate-400">
                      <History className="w-6 h-6" />
                    </div>
                    <div>
                      <p className="text-sm font-semibold text-slate-700 dark:text-slate-300">
                        No Execution Records Yet
                      </p>
                      <p className="text-xs text-slate-400 mt-1 max-w-xs mx-auto">
                        Run a workflow from the canvas, trigger via cron schedule, webhook, or messaging to generate telemetry.
                      </p>
                    </div>
                  </div>
                ) : (
                  history.map((record) => (
                    <div
                      key={record.run_id}
                      data-testid="history-run-item"
                      onClick={() => setSelectedRun(record)}
                      className="p-3.5 rounded-2xl bg-slate-50/80 dark:bg-slate-800/40 hover:bg-slate-100 dark:hover:bg-slate-800/80 border border-slate-200/80 dark:border-slate-800 transition-all cursor-pointer group space-y-2"
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2 min-w-0">
                          {record.status === 'success' ? (
                            <CheckCircle2 className="w-4 h-4 text-emerald-500 shrink-0" />
                          ) : (
                            <XCircle className="w-4 h-4 text-rose-500 shrink-0" />
                          )}
                          <span className="text-xs font-bold text-slate-900 dark:text-slate-100 truncate">
                            {record.workflow_title || record.workflow_id}
                          </span>
                        </div>
                        <span className="font-mono text-[10px] text-slate-400 group-hover:text-cyan-500 transition-colors">
                          {record.run_id} →
                        </span>
                      </div>

                      <div className="flex items-center gap-3 text-[11px] text-slate-500 dark:text-slate-400">
                        <span className="flex items-center gap-1 capitalize font-medium">
                          {renderTriggerIcon(record.trigger_source)}
                          {record.trigger_source || 'manual'}
                        </span>
                        <span>•</span>
                        <span>{record.duration_seconds}s</span>
                        <span>•</span>
                        <span>{record.steps_executed} steps</span>
                        <span>•</span>
                        <span>{new Date(record.started_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                      </div>
                    </div>
                  ))
                )}
              </div>
            )}
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  );
};
