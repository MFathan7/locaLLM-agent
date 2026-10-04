import { X, Check } from 'lucide-react';
import type { LocaLLMConfig } from '../types';
import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'motion/react';

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
  config: LocaLLMConfig | null;
  onSave: (config: LocaLLMConfig) => void;
  isSyncing: boolean;
}

export function SettingsModal({ isOpen, onClose, config, onSave, isSyncing }: SettingsModalProps) {
  const [localConfig, setLocalConfig] = useState<LocaLLMConfig | null>(config);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    setLocalConfig(config);
  }, [config]);

  if (!isOpen || !localConfig) return null;

  const handleSave = () => {
    onSave(localConfig);
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40 backdrop-blur-sm">
          <motion.div
            initial={{ opacity: 0, scale: 0.96, y: 8 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.96, y: 8 }}
            className="w-full max-w-lg liquid-glass-strong rounded-[28px] shadow-2xl overflow-hidden flex flex-col max-h-[85dvh]"
          >
            <div className="flex items-center justify-between px-4 py-3 border-b border-black/[0.05] dark:border-white/[0.06]">
              <div className="flex items-center gap-2">
                <span className="font-semibold text-sm text-slate-800 dark:text-slate-100">LocaLLM Settings</span>
                <span className="text-[10px] px-1.5 py-0.5 rounded bg-blue-500/10 text-blue-600 dark:text-blue-400 font-medium">CLI Sync</span>
              </div>
              <button 
                onClick={onClose} 
                className="p-1 rounded-md text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 hover:bg-black/5 dark:hover:bg-white/5 transition-colors cursor-pointer"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
            
            <div className="p-4 overflow-y-auto space-y-4 flex-1 text-xs">
              <div className="space-y-3">
                <h3 className="text-[11px] font-semibold text-slate-400 dark:text-slate-500 uppercase tracking-wider">Model & Engine</h3>
                
                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-1">
                    <label className="font-medium text-slate-700 dark:text-slate-300">Provider</label>
                    <select
                      value={localConfig.provider}
                      onChange={e => setLocalConfig({...localConfig, provider: e.target.value as any})}
                      className="w-full bg-black/5 dark:bg-white/5 border border-black/10 dark:border-white/10 rounded-lg px-2.5 py-1.5 text-xs text-slate-800 dark:text-slate-200 focus:outline-none focus:ring-1.5 focus:ring-blue-500"
                    >
                      <option value="ollama">Ollama (Local)</option>
                      <option value="openai">OpenAI</option>
                      <option value="anthropic">Anthropic</option>
                      <option value="gemini">Gemini</option>
                    </select>
                  </div>

                  <div className="space-y-1">
                    <label className="font-medium text-slate-700 dark:text-slate-300">Model Name</label>
                    <input
                      type="text"
                      value={localConfig.model}
                      onChange={e => setLocalConfig({...localConfig, model: e.target.value})}
                      className="w-full bg-black/5 dark:bg-white/5 border border-black/10 dark:border-white/10 rounded-lg px-2.5 py-1.5 text-xs text-slate-800 dark:text-slate-200 focus:outline-none focus:ring-1.5 focus:ring-blue-500"
                    />
                  </div>
                </div>
                
                {localConfig.provider === 'ollama' && (
                  <div className="space-y-1">
                    <label className="font-medium text-slate-700 dark:text-slate-300">Ollama Base URL</label>
                    <input
                      type="text"
                      value={localConfig.ollamaBaseUrl}
                      onChange={e => setLocalConfig({...localConfig, ollamaBaseUrl: e.target.value})}
                      className="w-full bg-black/5 dark:bg-white/5 border border-black/10 dark:border-white/10 rounded-lg px-2.5 py-1.5 text-xs text-slate-800 dark:text-slate-200 focus:outline-none focus:ring-1.5 focus:ring-blue-500"
                    />
                  </div>
                )}
                
                <label className="flex items-center gap-2 cursor-pointer pt-0.5">
                  <input
                    type="checkbox"
                    checked={localConfig.dynamicRouting}
                    onChange={e => setLocalConfig({...localConfig, dynamicRouting: e.target.checked})}
                    className="rounded text-blue-600 focus:ring-blue-500 w-3.5 h-3.5"
                  />
                  <span className="text-slate-700 dark:text-slate-300 text-xs">Enable Dynamic Model Routing</span>
                </label>
              </div>

              <div className="space-y-3 pt-2">
                <h3 className="text-[11px] font-semibold text-slate-400 dark:text-slate-500 uppercase tracking-wider">Inference Parameters</h3>
                
                <div className="space-y-1">
                  <div className="flex justify-between text-xs">
                    <span className="font-medium text-slate-700 dark:text-slate-300">Temperature</span>
                    <span className="text-slate-400 font-mono">{localConfig.temperature.toFixed(2)}</span>
                  </div>
                  <input
                    type="range"
                    min="0" max="2" step="0.05"
                    value={localConfig.temperature}
                    onChange={e => setLocalConfig({...localConfig, temperature: parseFloat(e.target.value)})}
                    className="w-full accent-blue-600 h-1.5 bg-black/10 dark:bg-white/10 rounded-lg cursor-pointer"
                  />
                </div>

                <div className="space-y-1">
                  <div className="flex justify-between text-xs">
                    <span className="font-medium text-slate-700 dark:text-slate-300">Top-P</span>
                    <span className="text-slate-400 font-mono">{localConfig.topP.toFixed(2)}</span>
                  </div>
                  <input
                    type="range"
                    min="0" max="1" step="0.05"
                    value={localConfig.topP}
                    onChange={e => setLocalConfig({...localConfig, topP: parseFloat(e.target.value)})}
                    className="w-full accent-blue-600 h-1.5 bg-black/10 dark:bg-white/10 rounded-lg cursor-pointer"
                  />
                </div>
                
                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-1">
                    <label className="font-medium text-slate-700 dark:text-slate-300">Max Tokens</label>
                    <input
                      type="number"
                      value={localConfig.maxTokens}
                      onChange={e => setLocalConfig({...localConfig, maxTokens: parseInt(e.target.value) || 2048})}
                      className="w-full bg-black/5 dark:bg-white/5 border border-black/10 dark:border-white/10 rounded-lg px-2.5 py-1.5 text-xs text-slate-800 dark:text-slate-200 focus:outline-none focus:ring-1.5 focus:ring-blue-500"
                    />
                  </div>
                  <div className="space-y-1">
                    <label className="font-medium text-slate-700 dark:text-slate-300">Context Length</label>
                    <input
                      type="number"
                      value={localConfig.contextLength}
                      onChange={e => setLocalConfig({...localConfig, contextLength: parseInt(e.target.value) || 4096})}
                      className="w-full bg-black/5 dark:bg-white/5 border border-black/10 dark:border-white/10 rounded-lg px-2.5 py-1.5 text-xs text-slate-800 dark:text-slate-200 focus:outline-none focus:ring-1.5 focus:ring-blue-500"
                    />
                  </div>
                </div>
                
                <div className="space-y-1">
                  <label className="font-medium text-slate-700 dark:text-slate-300">System Directives</label>
                  <textarea
                    value={localConfig.systemPrompt}
                    onChange={e => setLocalConfig({...localConfig, systemPrompt: e.target.value})}
                    className="w-full bg-black/5 dark:bg-white/5 border border-black/10 dark:border-white/10 rounded-lg px-2.5 py-1.5 text-xs text-slate-800 dark:text-slate-200 focus:outline-none focus:ring-1.5 focus:ring-blue-500 min-h-[70px] resize-y"
                  />
                </div>
              </div>
            </div>

            <div className="px-4 py-2.5 border-t border-black/[0.05] dark:border-white/[0.06] bg-black/[0.02] dark:bg-white/[0.02] flex items-center justify-between">
              <div className="text-[11px] text-slate-400 flex items-center gap-1.5">
                {isSyncing ? (
                  <span className="animate-pulse flex items-center gap-1.5 text-amber-500 font-medium">
                    <span className="w-1.5 h-1.5 rounded-full bg-amber-500 animate-ping" /> Syncing with CLI...
                  </span>
                ) : (
                  <span className="flex items-center gap-1.5 text-emerald-500 font-medium">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" /> CLI synchronized
                  </span>
                )}
              </div>
              <button
                onClick={handleSave}
                disabled={isSyncing}
                className="px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-xs font-medium transition-colors flex items-center gap-1.5 cursor-pointer shadow-xs"
              >
                {saved && <Check className="w-3.5 h-3.5" />}
                <span>{saved ? 'Saved' : 'Save Config'}</span>
              </button>
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
}
