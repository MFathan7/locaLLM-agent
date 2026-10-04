import { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import {
  X,
  Check,
  Cpu,
  Sliders,
  Shield,
  Globe,
  Server,
  Palette,
  RotateCcw,
  RefreshCw
} from 'lucide-react';
import type { LocaLLMConfig, CustomPlatformConfig, ModelInfo } from '../types';
import { api } from '../services/api';

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
  config: LocaLLMConfig | null;
  onSave: (config: LocaLLMConfig) => void;
  isSyncing: boolean;
  onRefreshModels?: (backend?: string) => Promise<ModelInfo[]>;
}

type SettingsTab = 'backend' | 'inference' | 'agent' | 'search' | 'server' | 'appearance';

const TABS: { id: SettingsTab; label: string; icon: typeof Cpu }[] = [
  { id: 'backend', label: 'Backend & Model', icon: Cpu },
  { id: 'inference', label: 'Inference', icon: Sliders },
  { id: 'agent', label: 'Agent Policies', icon: Shield },
  { id: 'search', label: 'Web Search', icon: Globe },
  { id: 'server', label: 'API Gateway', icon: Server },
  { id: 'appearance', label: 'Theme & Bots', icon: Palette },
];

export function SettingsModal({
  isOpen,
  onClose,
  config,
  onSave,
  isSyncing,
  onRefreshModels
}: SettingsModalProps) {
  const [localConfig, setLocalConfig] = useState<LocaLLMConfig | null>(config);
  const [activeTab, setActiveTab] = useState<SettingsTab>('backend');
  const [saved, setSaved] = useState(false);
  const [showAddPlatform, setShowAddPlatform] = useState(false);
  const [backendModels, setBackendModels] = useState<ModelInfo[]>([]);
  const [isLoadingModels, setIsLoadingModels] = useState(false);
  const [newPlatform, setNewPlatform] = useState<CustomPlatformConfig>({
    name: '',
    api_base: 'http://127.0.0.1:8000/v1',
    api_key: '',
    default_model: ''
  });

  // Load models for a specific backend platform
  const loadModelsForBackend = useCallback(async (backendName: string) => {
    setIsLoadingModels(true);
    try {
      const fetched = await api.getModels(backendName);
      setBackendModels(fetched);
      if (onRefreshModels) {
        onRefreshModels(backendName);
      }
      return fetched;
    } finally {
      setIsLoadingModels(false);
    }
  }, [onRefreshModels]);

  useEffect(() => {
    setLocalConfig(config);
    if (config?.active_backend && isOpen) {
      loadModelsForBackend(config.active_backend);
    }
  }, [config, isOpen, loadModelsForBackend]);

  if (!isOpen || !localConfig) return null;

  // When active backend is changed, fetch models, update local state, and refresh models in parent
  const handleBackendChange = async (newBackend: string) => {
    const isOllama = newBackend === 'ollama';
    const fetched = await loadModelsForBackend(newBackend);

    // Pick first non-auto model as sensible default, or fallback to auto/first
    const fallbackModel = fetched.find(m => m.id !== 'auto')?.id || fetched[0]?.id || localConfig.default_model;

    const updated: LocaLLMConfig = {
      ...localConfig,
      active_backend: newBackend,
      provider: isOllama ? 'ollama' : 'openai',
      default_model: fallbackModel,
      model: fallbackModel,
      ...(isOllama ? { ollama_model: fallbackModel } : {})
    };
    setLocalConfig(updated);

    if (onRefreshModels) {
      await onRefreshModels(newBackend);
    }
  };

  const handleSave = () => {
    onSave(localConfig);
    setSaved(true);
    if (onRefreshModels) {
      onRefreshModels(localConfig.active_backend);
    }
    setTimeout(() => setSaved(false), 2000);
  };

  const handleResetDefaults = () => {
    if (!window.confirm('Reset settings to default CLI values?')) return;
    const resetCfg: LocaLLMConfig = {
      ...localConfig,
      active_backend: 'ollama',
      ollama_host: 'http://127.0.0.1:11434',
      ollama_model: 'gemma4:12b',
      default_model: 'gemma4:12b',
      temperature: 0.7,
      context_window: 8192,
      system_prompt: 'You are locaLLM, a helpful, fast, and intelligent local AI assistant.',
      agent_permission_policy: 'ask',
      agent_max_steps: 25,
      search_provider: 'auto',
      search_api_url: '',
      ui_theme: 'cyber_neon',
      server_enabled: false,
      server_host: '127.0.0.1',
      server_port: 8080,
      server_api_key: ''
    };
    setLocalConfig(resetCfg);
    loadModelsForBackend('ollama');
  };

  const handleAddPlatform = () => {
    if (!newPlatform.name.trim() || !newPlatform.api_base.trim()) return;
    const cleanName = newPlatform.name.trim();
    const updatedPlatforms = [
      ...(localConfig.custom_platforms || []),
      { ...newPlatform, name: cleanName }
    ];
    setLocalConfig({
      ...localConfig,
      custom_platforms: updatedPlatforms
    });
    setNewPlatform({ name: '', api_base: 'http://127.0.0.1:8000/v1', api_key: '', default_model: '' });
    setShowAddPlatform(false);
  };

  const handleDeletePlatform = (platformName: string) => {
    const updated = (localConfig.custom_platforms || []).filter(p => p.name !== platformName);
    const newActiveBackend = localConfig.active_backend === platformName ? 'ollama' : localConfig.active_backend;
    setLocalConfig({
      ...localConfig,
      custom_platforms: updated,
      active_backend: newActiveBackend
    });
    if (localConfig.active_backend === platformName) {
      loadModelsForBackend('ollama');
    }
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-4 bg-black/50 backdrop-blur-md">
          <motion.div
            initial={{ opacity: 0, scale: 0.96, y: 8 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.96, y: 8 }}
            className="w-full max-w-3xl bg-white/95 dark:bg-zinc-900/95 backdrop-blur-2xl rounded-[24px] shadow-2xl overflow-hidden flex flex-col max-h-[88dvh] border border-slate-300 dark:border-white/10"
          >
            {/* Header: High contrast for both Light and Dark modes */}
            <div className="flex items-center justify-between px-5 py-3.5 border-b border-slate-200 dark:border-white/[0.08] bg-slate-50 dark:bg-transparent">
              <div>
                <h2 className="font-bold text-base text-slate-950 dark:text-white">Settings & Configuration</h2>
              </div>
              <button
                onClick={onClose}
                className="p-1.5 rounded-lg text-slate-700 hover:text-slate-950 dark:text-slate-300 dark:hover:text-white hover:bg-black/8 dark:hover:bg-white/10 transition-colors cursor-pointer"
                aria-label="Close settings"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Body: Left Tab Menu + Right Content Panel */}
            <div className="flex-1 flex flex-col md:flex-row overflow-hidden min-h-[400px]">
              {/* Category Navigation Bar with Bold, High-Contrast Text in Light Mode */}
              <div className="w-full md:w-56 shrink-0 p-2.5 md:p-3.5 border-b md:border-b-0 md:border-r border-slate-200 dark:border-white/[0.08] bg-slate-100/90 dark:bg-black/20 flex md:flex-col gap-1.5 overflow-x-auto md:overflow-x-visible">
                {TABS.map((tab) => {
                  const Icon = tab.icon;
                  const isActive = activeTab === tab.id;
                  return (
                    <button
                      key={tab.id}
                      onClick={() => setActiveTab(tab.id)}
                      className={`flex items-center gap-2.5 px-3.5 py-2.5 rounded-xl text-xs font-bold transition-all text-left whitespace-nowrap cursor-pointer ${
                        isActive
                          ? 'bg-blue-600 text-white shadow-md'
                          : 'text-slate-900 dark:text-slate-100 hover:bg-slate-200/90 dark:hover:bg-white/10 hover:text-slate-950 dark:hover:text-white'
                      }`}
                    >
                      <Icon className={`w-4 h-4 shrink-0 ${isActive ? 'text-white' : 'text-slate-800 dark:text-slate-200'}`} />
                      <span>{tab.label}</span>
                    </button>
                  );
                })}
              </div>

              {/* Tab Content Area */}
              <div className="flex-1 p-4 md:p-6 overflow-y-auto space-y-4 text-xs bg-white dark:bg-transparent">
                {/* 1. Backend & Model */}
                {activeTab === 'backend' && (
                  <div className="space-y-4">
                    <div>
                      <div className="flex items-center justify-between mb-1">
                        <h3 className="text-[13px] font-bold text-slate-950 dark:text-white">Active Backend Platform</h3>
                        {isLoadingModels && (
                          <span className="text-[11px] font-bold text-blue-600 dark:text-blue-400 flex items-center gap-1">
                            <RefreshCw className="w-3 h-3 animate-spin" /> Loading models...
                          </span>
                        )}
                      </div>
                      <p className="text-xs font-semibold text-slate-700 dark:text-slate-300 mb-2">Select the primary local service (Ollama) or custom OpenAI-compatible server.</p>
                      <select
                        value={localConfig.active_backend}
                        onChange={(e) => handleBackendChange(e.target.value)}
                        className="w-full bg-white dark:bg-zinc-800 text-slate-950 dark:text-white font-bold border border-slate-300 dark:border-zinc-700 rounded-xl px-3 py-2.5 text-xs focus:outline-none focus:ring-2 focus:ring-blue-500 shadow-xs cursor-pointer [color-scheme:light] dark:[color-scheme:dark]"
                      >
                        <option value="ollama" className="bg-white dark:bg-zinc-800 text-slate-950 dark:text-white py-1.5 font-semibold">Ollama (Native Local Service)</option>
                        {(localConfig.custom_platforms || []).map((p) => (
                          <option key={p.name} value={p.name} className="bg-white dark:bg-zinc-800 text-slate-950 dark:text-white py-1.5 font-semibold">
                            {p.name} (Custom Platform)
                          </option>
                        ))}
                      </select>
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
                      {/* Default Active Model: NOW A SELECT BOX POPULATED DYNAMICALLY */}
                      <div className="space-y-1.5">
                        <div className="flex items-center justify-between">
                          <label className="font-bold text-slate-950 dark:text-white text-xs">Default Active Model</label>
                          <span className="text-[10px] font-bold text-slate-600 dark:text-slate-400">{backendModels.length} models</span>
                        </div>
                        <select
                          value={localConfig.default_model}
                          onChange={(e) => {
                            const val = e.target.value;
                            setLocalConfig({
                              ...localConfig,
                              default_model: val,
                              model: val,
                              ...(localConfig.active_backend === 'ollama' ? { ollama_model: val } : {})
                            });
                          }}
                          className="w-full bg-white dark:bg-zinc-800 text-slate-950 dark:text-white font-bold border border-slate-300 dark:border-zinc-700 rounded-xl px-3 py-2.5 text-xs focus:outline-none focus:ring-2 focus:ring-blue-500 shadow-xs cursor-pointer [color-scheme:light] dark:[color-scheme:dark]"
                        >
                          {/* If current model is not yet in fetched list, keep it visible */}
                          {localConfig.default_model && !backendModels.some(m => m.id === localConfig.default_model) && (
                            <option value={localConfig.default_model} className="bg-white dark:bg-zinc-800 text-slate-950 dark:text-white py-1.5 font-semibold">
                              {localConfig.default_model} (Current)
                            </option>
                          )}
                          {backendModels.map((m) => (
                            <option key={m.id} value={m.id} className="bg-white dark:bg-zinc-800 text-slate-950 dark:text-white py-1.5 font-semibold">
                              {m.name || m.id}
                            </option>
                          ))}
                        </select>
                      </div>

                      <div className="space-y-1.5">
                        <label className="font-bold text-slate-950 dark:text-white text-xs">Ollama Host Address</label>
                        <input
                          type="text"
                          value={localConfig.ollama_host}
                          onChange={(e) => setLocalConfig({ ...localConfig, ollama_host: e.target.value })}
                          className="w-full bg-white dark:bg-zinc-800 text-slate-950 dark:text-white font-bold border border-slate-300 dark:border-zinc-700 rounded-xl px-3 py-2 text-xs focus:outline-none focus:ring-2 focus:ring-blue-500 shadow-xs"
                          placeholder="http://127.0.0.1:11434"
                        />
                      </div>
                    </div>

                    {/* Custom Platforms List */}
                    <div className="pt-2 border-t border-slate-200 dark:border-white/[0.08]">
                      <div className="flex items-center justify-between mb-2">
                        <span className="font-bold text-slate-950 dark:text-white text-xs">Custom OpenAI Platforms</span>
                        <button
                          type="button"
                          onClick={() => setShowAddPlatform(!showAddPlatform)}
                          className="text-xs text-blue-600 dark:text-blue-400 font-bold hover:underline cursor-pointer"
                        >
                          {showAddPlatform ? 'Cancel' : '+ Add Platform'}
                        </button>
                      </div>

                      {showAddPlatform && (
                        <div className="p-3.5 bg-slate-50 dark:bg-zinc-900/60 rounded-xl border border-slate-300 dark:border-zinc-700 space-y-2 mb-3">
                          <input
                            type="text"
                            placeholder="Platform Name (e.g. vLLM, LocalAI, GPU-Cluster)"
                            value={newPlatform.name}
                            onChange={(e) => setNewPlatform({ ...newPlatform, name: e.target.value })}
                            className="w-full bg-white dark:bg-zinc-800 border border-slate-300 dark:border-zinc-700 rounded-lg px-3 py-1.5 text-xs text-slate-950 dark:text-white font-bold focus:outline-none focus:ring-2 focus:ring-blue-500"
                          />
                          <input
                            type="text"
                            placeholder="API Base URL (e.g. http://127.0.0.1:8000/v1)"
                            value={newPlatform.api_base}
                            onChange={(e) => setNewPlatform({ ...newPlatform, api_base: e.target.value })}
                            className="w-full bg-white dark:bg-zinc-800 border border-slate-300 dark:border-zinc-700 rounded-lg px-3 py-1.5 text-xs text-slate-950 dark:text-white font-bold focus:outline-none focus:ring-2 focus:ring-blue-500"
                          />
                          <input
                            type="password"
                            placeholder="API Key (optional)"
                            value={newPlatform.api_key}
                            onChange={(e) => setNewPlatform({ ...newPlatform, api_key: e.target.value })}
                            className="w-full bg-white dark:bg-zinc-800 border border-slate-300 dark:border-zinc-700 rounded-lg px-3 py-1.5 text-xs text-slate-950 dark:text-white font-bold focus:outline-none focus:ring-2 focus:ring-blue-500"
                          />
                          <button
                            type="button"
                            onClick={handleAddPlatform}
                            className="px-3.5 py-1.5 bg-blue-600 text-white rounded-lg text-xs font-bold hover:bg-blue-700 cursor-pointer shadow-xs"
                          >
                            Save Platform
                          </button>
                        </div>
                      )}

                      {(localConfig.custom_platforms || []).length > 0 ? (
                        <div className="space-y-2">
                          {localConfig.custom_platforms.map((p) => (
                            <div
                              key={p.name}
                              className="flex items-center justify-between p-3 rounded-xl bg-slate-50 dark:bg-zinc-900/60 border border-slate-300 dark:border-zinc-700/80 shadow-xs"
                            >
                              <div>
                                <span className="font-bold text-slate-950 dark:text-white text-xs">{p.name}</span>
                                <div className="text-[11px] text-slate-700 dark:text-slate-400 font-mono mt-0.5">{p.api_base}</div>
                              </div>
                              <button
                                type="button"
                                onClick={() => handleDeletePlatform(p.name)}
                                className="text-red-600 hover:text-red-700 dark:text-red-400 text-xs font-bold px-2 py-1 rounded cursor-pointer"
                              >
                                Delete
                              </button>
                            </div>
                          ))}
                        </div>
                      ) : (
                        <p className="text-xs font-semibold text-slate-600 dark:text-slate-400">No custom platforms registered yet.</p>
                      )}
                    </div>
                  </div>
                )}

                {/* 2. Inference & Sampling */}
                {activeTab === 'inference' && (
                  <div className="space-y-4">
                    <div className="space-y-1.5">
                      <div className="flex justify-between items-center text-xs">
                        <span className="font-bold text-slate-950 dark:text-white">Sampling Temperature</span>
                        <span className="text-blue-600 dark:text-blue-400 font-mono font-bold">{localConfig.temperature.toFixed(2)}</span>
                      </div>
                      <input
                        type="range"
                        min="0"
                        max="2"
                        step="0.05"
                        value={localConfig.temperature}
                        onChange={(e) => setLocalConfig({ ...localConfig, temperature: parseFloat(e.target.value) })}
                        className="w-full accent-blue-600 h-2 bg-slate-300 dark:bg-zinc-700 rounded-lg cursor-pointer"
                      />
                      <p className="text-xs font-semibold text-slate-700 dark:text-slate-300">Lower values (0.2) are analytical and deterministic; higher values (0.8+) are creative.</p>
                    </div>

                    <div className="space-y-1.5">
                      <div className="flex justify-between items-center text-xs">
                        <span className="font-bold text-slate-950 dark:text-white">Context Window Limit (Tokens)</span>
                        <span className="text-blue-600 dark:text-blue-400 font-mono font-bold">{localConfig.context_window.toLocaleString()}</span>
                      </div>
                      <input
                        type="number"
                        min="512"
                        max="262144"
                        step="1024"
                        value={localConfig.context_window}
                        onChange={(e) =>
                          setLocalConfig({
                            ...localConfig,
                            context_window: parseInt(e.target.value) || 8192,
                            contextLength: parseInt(e.target.value) || 8192
                          })
                        }
                        className="w-full bg-white dark:bg-zinc-800 text-slate-950 dark:text-white font-bold border border-slate-300 dark:border-zinc-700 rounded-xl px-3 py-2 text-xs focus:outline-none focus:ring-2 focus:ring-blue-500 shadow-xs"
                      />
                      <div className="flex gap-1.5 pt-1">
                        {[4096, 8192, 16384, 32768, 120000].map((preset) => (
                          <button
                            key={preset}
                            type="button"
                            onClick={() =>
                              setLocalConfig({
                                ...localConfig,
                                context_window: preset,
                                contextLength: preset
                              })
                            }
                            className={`px-2.5 py-1 rounded-lg text-[11px] font-mono font-bold cursor-pointer transition-colors ${
                              localConfig.context_window === preset
                                ? 'bg-blue-600 text-white shadow-xs'
                                : 'bg-slate-200 dark:bg-zinc-800 text-slate-900 dark:text-slate-200 hover:bg-slate-300 dark:hover:bg-zinc-700'
                            }`}
                          >
                            {preset >= 1000 ? `${preset / 1000}k` : preset}
                          </button>
                        ))}
                      </div>
                    </div>

                    <div className="space-y-1.5">
                      <label className="font-bold text-slate-950 dark:text-white text-xs">System Directives</label>
                      <textarea
                        value={localConfig.system_prompt}
                        onChange={(e) => setLocalConfig({ ...localConfig, system_prompt: e.target.value })}
                        rows={4}
                        className="w-full bg-white dark:bg-zinc-800 text-slate-950 dark:text-white font-medium border border-slate-300 dark:border-zinc-700 rounded-xl p-3 text-xs focus:outline-none focus:ring-2 focus:ring-blue-500 shadow-xs resize-y"
                        placeholder="Default system prompt instructions for the agent..."
                      />
                    </div>
                  </div>
                )}

                {/* 3. Agent Policies */}
                {activeTab === 'agent' && (
                  <div className="space-y-4">
                    <div>
                      <h3 className="text-[13px] font-bold text-slate-950 dark:text-white mb-1">Permission Policy</h3>
                      <p className="text-xs font-semibold text-slate-700 dark:text-slate-300 mb-2">Controls command execution authority for autonomous tool operations.</p>
                      <div className="space-y-2">
                        {[
                          { id: 'ask', label: 'Ask Permission', desc: 'Prompts confirmation before executing modifying terminal commands or writes' },
                          { id: 'always_allow', label: 'Autonomous (Auto-Approve)', desc: 'Directly executes system operations without confirmation' },
                          { id: 'deny', label: 'Strict Read-Only', desc: 'Blocks all modifying commands, allows only inspections and reads' }
                        ].map((policy) => (
                          <label
                            key={policy.id}
                            className={`flex items-start gap-3 p-3.5 rounded-xl border cursor-pointer transition-colors ${
                              localConfig.agent_permission_policy === policy.id
                                ? 'bg-blue-50 dark:bg-blue-950/40 border-blue-600 text-slate-950 dark:text-white shadow-xs'
                                : 'bg-white dark:bg-zinc-900/60 border-slate-300 dark:border-zinc-700/80 hover:bg-slate-100 dark:hover:bg-zinc-800/80'
                            }`}
                          >
                            <input
                              type="radio"
                              name="permission_policy"
                              value={policy.id}
                              checked={localConfig.agent_permission_policy === policy.id}
                              onChange={() =>
                                setLocalConfig({
                                  ...localConfig,
                                  agent_permission_policy: policy.id as any,
                                  agent_auto_approve_commands: policy.id === 'always_allow'
                                })
                              }
                              className="mt-0.5 text-blue-600 focus:ring-blue-500"
                            />
                            <div>
                              <div className="font-bold text-xs text-slate-950 dark:text-white">{policy.label}</div>
                              <div className="text-[11px] font-semibold text-slate-700 dark:text-slate-300 mt-0.5">{policy.desc}</div>
                            </div>
                          </label>
                        ))}
                      </div>
                    </div>

                    <div className="space-y-1.5 pt-2 border-t border-slate-200 dark:border-white/[0.08]">
                      <div className="flex justify-between items-center text-xs">
                        <span className="font-bold text-slate-950 dark:text-white">Agent Max Steps</span>
                        <span className="text-blue-600 dark:text-blue-400 font-mono font-bold">{localConfig.agent_max_steps} steps</span>
                      </div>
                      <input
                        type="range"
                        min="1"
                        max="100"
                        value={localConfig.agent_max_steps}
                        onChange={(e) => setLocalConfig({ ...localConfig, agent_max_steps: parseInt(e.target.value) || 25 })}
                        className="w-full accent-blue-600 h-2 bg-slate-300 dark:bg-zinc-700 rounded-lg cursor-pointer"
                      />
                      <p className="text-xs font-semibold text-slate-700 dark:text-slate-300">Maximum autonomous reasoning and tool execution loop cycles.</p>
                    </div>
                  </div>
                )}

                {/* 4. Web Search */}
                {activeTab === 'search' && (
                  <div className="space-y-4">
                    <div>
                      <h3 className="text-[13px] font-bold text-slate-950 dark:text-white mb-1">Search Provider</h3>
                      <p className="text-xs font-semibold text-slate-700 dark:text-slate-300 mb-2">Engine used for real-time web research queries.</p>
                      <select
                        value={localConfig.search_provider}
                        onChange={(e) => setLocalConfig({ ...localConfig, search_provider: e.target.value as any })}
                        className="w-full bg-white dark:bg-zinc-800 text-slate-950 dark:text-white font-bold border border-slate-300 dark:border-zinc-700 rounded-xl px-3 py-2.5 text-xs focus:outline-none focus:ring-2 focus:ring-blue-500 shadow-xs cursor-pointer [color-scheme:light] dark:[color-scheme:dark]"
                      >
                        <option value="auto" className="bg-white dark:bg-zinc-800 text-slate-950 dark:text-white py-1.5 font-semibold">Auto (DuckDuckGo with Bing Fallback)</option>
                        <option value="bing" className="bg-white dark:bg-zinc-800 text-slate-950 dark:text-white py-1.5 font-semibold">Bing (Fast, High Availability)</option>
                        <option value="duckduckgo" className="bg-white dark:bg-zinc-800 text-slate-950 dark:text-white py-1.5 font-semibold">DuckDuckGo (Direct API)</option>
                        <option value="custom" className="bg-white dark:bg-zinc-800 text-slate-950 dark:text-white py-1.5 font-semibold">Custom (Self-Hosted SearXNG / Proxy)</option>
                      </select>
                    </div>

                    {localConfig.search_provider === 'custom' && (
                      <div className="space-y-1.5">
                        <label className="font-bold text-slate-950 dark:text-white text-xs">Custom Search Endpoint URL</label>
                        <input
                          type="text"
                          value={localConfig.search_api_url || ''}
                          onChange={(e) => setLocalConfig({ ...localConfig, search_api_url: e.target.value })}
                          className="w-full bg-white dark:bg-zinc-800 text-slate-950 dark:text-white font-bold border border-slate-300 dark:border-zinc-700 rounded-xl px-3 py-2 text-xs focus:outline-none focus:ring-2 focus:ring-blue-500 shadow-xs"
                          placeholder="https://searx.example.com/search?q={query}&format=json"
                        />
                        <p className="text-[11px] font-semibold text-slate-700 dark:text-slate-300">Include {'{query}'} placeholder in the URL.</p>
                      </div>
                    )}
                  </div>
                )}

                {/* 5. API Server Gateway */}
                {activeTab === 'server' && (
                  <div className="space-y-4">
                    <div className="flex items-center justify-between p-3.5 rounded-xl bg-slate-50 dark:bg-zinc-900/60 border border-slate-300 dark:border-zinc-700 shadow-xs">
                      <div>
                        <div className="font-bold text-xs text-slate-950 dark:text-white">OpenAI-Compatible Gateway</div>
                        <div className="text-[11px] font-semibold text-slate-700 dark:text-slate-300">Exposes /v1/chat/completions and /v1/models locally</div>
                      </div>
                      <label className="relative inline-flex items-center cursor-pointer">
                        <input
                          type="checkbox"
                          checked={localConfig.server_enabled}
                          onChange={(e) => setLocalConfig({ ...localConfig, server_enabled: e.target.checked })}
                          className="sr-only peer"
                        />
                        <div className="w-9 h-5 bg-slate-300 dark:bg-slate-700 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-blue-600"></div>
                      </label>
                    </div>

                    <div className="grid grid-cols-2 gap-3.5">
                      <div className="space-y-1.5">
                        <label className="font-bold text-slate-950 dark:text-white text-xs">Server Host</label>
                        <input
                          type="text"
                          value={localConfig.server_host}
                          onChange={(e) => setLocalConfig({ ...localConfig, server_host: e.target.value })}
                          className="w-full bg-white dark:bg-zinc-800 text-slate-950 dark:text-white font-bold border border-slate-300 dark:border-zinc-700 rounded-xl px-3 py-2 text-xs focus:outline-none focus:ring-2 focus:ring-blue-500 shadow-xs"
                        />
                      </div>

                      <div className="space-y-1.5">
                        <label className="font-bold text-slate-950 dark:text-white text-xs">Server Port</label>
                        <input
                          type="number"
                          value={localConfig.server_port}
                          onChange={(e) => setLocalConfig({ ...localConfig, server_port: parseInt(e.target.value) || 8080 })}
                          className="w-full bg-white dark:bg-zinc-800 text-slate-950 dark:text-white font-bold border border-slate-300 dark:border-zinc-700 rounded-xl px-3 py-2 text-xs focus:outline-none focus:ring-2 focus:ring-blue-500 shadow-xs"
                        />
                      </div>
                    </div>

                    <div className="space-y-1.5">
                      <label className="font-bold text-slate-950 dark:text-white text-xs">Bearer API Key (Security)</label>
                      <input
                        type="text"
                        value={localConfig.server_api_key || ''}
                        onChange={(e) => setLocalConfig({ ...localConfig, server_api_key: e.target.value })}
                        className="w-full bg-white dark:bg-zinc-800 text-slate-950 dark:text-white font-mono font-bold border border-slate-300 dark:border-zinc-700 rounded-xl px-3 py-2 text-xs focus:outline-none focus:ring-2 focus:ring-blue-500 shadow-xs"
                        placeholder="Optional bearer key, e.g. testing"
                      />
                    </div>
                  </div>
                )}

                {/* 6. Appearance & Integrations */}
                {activeTab === 'appearance' && (
                  <div className="space-y-4">
                    <div>
                      <h3 className="text-[13px] font-bold text-slate-950 dark:text-white mb-1">CLI UI Theme</h3>
                      <p className="text-xs font-semibold text-slate-700 dark:text-slate-300 mb-2">Palette applied to the interactive terminal console.</p>
                      <select
                        value={localConfig.ui_theme || 'cyber_neon'}
                        onChange={(e) => setLocalConfig({ ...localConfig, ui_theme: e.target.value })}
                        className="w-full bg-white dark:bg-zinc-800 text-slate-950 dark:text-white font-bold border border-slate-300 dark:border-zinc-700 rounded-xl px-3 py-2.5 text-xs focus:outline-none focus:ring-2 focus:ring-blue-500 shadow-xs cursor-pointer [color-scheme:light] dark:[color-scheme:dark]"
                      >
                        <option value="cyber_neon" className="bg-white dark:bg-zinc-800 text-slate-950 dark:text-white py-1.5 font-semibold">Cyber Neon (Cyan & Electric Blue)</option>
                        <option value="tokyo_night" className="bg-white dark:bg-zinc-800 text-slate-950 dark:text-white py-1.5 font-semibold">Tokyo Night (Deep Indigo & Soft Cyan)</option>
                        <option value="monokai" className="bg-white dark:bg-zinc-800 text-slate-950 dark:text-white py-1.5 font-semibold">Monokai Pro (Warm Amber & Green)</option>
                        <option value="matrix" className="bg-white dark:bg-zinc-800 text-slate-950 dark:text-white py-1.5 font-semibold">Matrix (Classic Terminal Green)</option>
                        <option value="nordic_frost" className="bg-white dark:bg-zinc-800 text-slate-950 dark:text-white py-1.5 font-semibold">Nordic Frost (Clean Ice Blue)</option>
                      </select>
                    </div>

                    <div className="space-y-1.5 pt-2 border-t border-slate-200 dark:border-white/[0.08]">
                      <label className="font-bold text-slate-950 dark:text-white text-xs">Telegram Bot Token</label>
                      <input
                        type="password"
                        value={localConfig.telegram_token || ''}
                        onChange={(e) => setLocalConfig({ ...localConfig, telegram_token: e.target.value })}
                        className="w-full bg-white dark:bg-zinc-800 text-slate-950 dark:text-white font-mono font-bold border border-slate-300 dark:border-zinc-700 rounded-xl px-3 py-2 text-xs focus:outline-none focus:ring-2 focus:ring-blue-500 shadow-xs"
                        placeholder="e.g. 7241323727:AAGip8Ze4..."
                      />
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* Footer: Bold, High Contrast Buttons */}
            <div className="px-5 py-3 border-t border-slate-200 dark:border-white/[0.08] bg-slate-100/90 dark:bg-black/25 flex items-center justify-between">
              <button
                type="button"
                onClick={handleResetDefaults}
                className="inline-flex items-center gap-1.5 text-slate-800 hover:text-slate-950 dark:text-slate-200 dark:hover:text-white text-xs font-bold transition-colors cursor-pointer"
              >
                <RotateCcw className="w-3.5 h-3.5" />
                <span>Reset Defaults</span>
              </button>

              <div className="flex items-center gap-2.5">
                <button
                  type="button"
                  onClick={onClose}
                  className="px-4 py-1.5 rounded-xl text-xs font-bold text-slate-800 dark:text-slate-200 hover:bg-slate-200/90 dark:hover:bg-white/10 border border-slate-300 dark:border-zinc-700 transition-colors cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={handleSave}
                  disabled={isSyncing}
                  className="px-4 py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded-xl text-xs font-bold transition-colors flex items-center gap-1.5 cursor-pointer shadow-md disabled:opacity-50"
                >
                  {saved ? (
                    <>
                      <Check className="w-3.5 h-3.5" />
                      <span>Saved</span>
                    </>
                  ) : (
                    <span>Save Settings</span>
                  )}
                </button>
              </div>
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
}
