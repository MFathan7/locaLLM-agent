import { useState, useEffect, useMemo } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import {
  X,
  Plus,
  Trash2,
  BookOpen,
  Code2,
  Languages,
  PenTool,
  Check,
  Download,
  GitBranch,
  Search,
  Loader2,
  AlertCircle
} from 'lucide-react';
import type { Workspace, WorkspaceSkill } from '../types';
import { WorkspaceIcon } from './WorkspaceIcon';
import { IconColorPicker } from './IconColorPicker';
import { api } from '../services/api';

interface WorkspaceModalProps {
  isOpen: boolean;
  mode: 'create' | 'edit';
  workspace?: Workspace | null;
  onSave: (data: {
    name: string;
    oldName?: string;
    description?: string;
    icon: string;
    color: string;
    custom_instructions: string;
    auto_memory?: boolean;
    skills: WorkspaceSkill[];
    deletedSkills?: WorkspaceSkill[];
  }) => Promise<void> | void;
  onClose: () => void;
  onReload?: () => Promise<any> | any;
}

const PRESET_SKILL_TEMPLATES: Array<{
  name: string;
  description: string;
  content: string;
  icon: React.ReactNode;
}> = [
  {
    name: 'Code Reviewer',
    description: 'Inspects code for bugs, performance bottlenecks, and security flaws.',
    content: 'Role: Senior Code Reviewer.\n- Carefully evaluate syntax, security vulnerabilities, edge cases, and algorithmic complexity.\n- Provide concrete suggestions and optimized code snippets.',
    icon: <Code2 className="w-3.5 h-3.5" />
  },
  {
    name: 'Translator & Localization',
    description: 'Translates and adapts text fluently across multiple languages.',
    content: 'Role: Expert Translator.\n- Translate text naturally while preserving tone, cultural nuances, and idioms.\n- Format bilingual side-by-side or clean target translations.',
    icon: <Languages className="w-3.5 h-3.5" />
  },
  {
    name: 'Research Assistant',
    description: 'Synthesizes complex data, papers, and facts into structured briefs.',
    content: 'Role: Academic & Market Research Assistant.\n- Synthesize findings into clear executive summaries.\n- Highlight methodology, key metrics, takeaways, and open questions.',
    icon: <BookOpen className="w-3.5 h-3.5" />
  },
  {
    name: 'Creative Copywriter',
    description: 'Crafts persuasive copy, marketing headlines, and engaging stories.',
    content: 'Role: Creative Copywriter.\n- Write punchy, memorable, and high-conversion copy.\n- Avoid generic buzzwords; emphasize distinct rhythm and clarity.',
    icon: <PenTool className="w-3.5 h-3.5" />
  }
];

export function WorkspaceModal({
  isOpen,
  mode,
  workspace,
  onSave,
  onClose,
  onReload
}: WorkspaceModalProps) {
  const [name, setName] = useState('');
  const [icon, setIcon] = useState('Folder');
  const [color, setColor] = useState('#3B82F6');
  const [instructions, setInstructions] = useState('');
  const [skills, setSkills] = useState<WorkspaceSkill[]>([]);
  const [autoMemory, setAutoMemory] = useState(true);
  const [memoryClearMsg, setMemoryClearMsg] = useState('');
  const [isPickerOpen, setIsPickerOpen] = useState(false);
  const [activeTab, setActiveTab] = useState<'details' | 'skills'>('details');

  // Inline skill creation
  const [isAddingSkill, setIsAddingSkill] = useState(false);
  const [skillName, setSkillName] = useState('');
  const [skillDesc, setSkillDesc] = useState('');
  const [skillContent, setSkillContent] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');

  // GitHub skill import
  const [isGithubImportOpen, setIsGithubImportOpen] = useState(false);
  const [githubRepo, setGithubRepo] = useState('');
  const [isInspecting, setIsInspecting] = useState(false);
  const [inspectError, setInspectError] = useState('');
  const [discoveredSkills, setDiscoveredSkills] = useState<string[]>([]);
  const [selectedGithubSkills, setSelectedGithubSkills] = useState<Set<string>>(new Set());
  const [githubSkillFilter, setGithubSkillFilter] = useState('');
  const [isInstalling, setIsInstalling] = useState(false);
  const [installSuccessMsg, setInstallSuccessMsg] = useState('');

  // Configured skills search & tracked deletions
  const [skillsSearch, setSkillsSearch] = useState('');
  const [removedSkills, setRemovedSkills] = useState<WorkspaceSkill[]>([]);

  useEffect(() => {
    let isCancelled = false;
    if (isOpen) {
      if (workspace && mode === 'edit') {
        setName(workspace.name || '');
        setIcon(workspace.icon || 'Folder');
        setColor(workspace.color || '#3B82F6');
        setInstructions(workspace.custom_instructions || '');
        setSkills(Array.isArray(workspace.skills) ? workspace.skills : []);
        setAutoMemory(workspace.auto_memory !== undefined ? !!workspace.auto_memory : true);

        // Fetch fresh skills for this workspace from backend to avoid missing or stale skills
        if (workspace.name) {
          api.getWorkspaces().then((allWs) => {
            if (isCancelled) return;
            const current = allWs.find(w => w.name.toLowerCase() === workspace.name.toLowerCase());
            if (current && Array.isArray(current.skills)) {
              setSkills(current.skills);
            }
          }).catch(() => {});
        }
      } else if (workspace && mode === 'create') {
        setName(workspace.name || '');
        setIcon(workspace.icon || 'Folder');
        setColor(workspace.color || '#3B82F6');
        setInstructions(workspace.custom_instructions || '');
        setSkills(Array.isArray(workspace.skills) ? workspace.skills : []);
        setAutoMemory(workspace.auto_memory !== undefined ? !!workspace.auto_memory : true);
      } else {
        setName('');
        setIcon('Folder');
        setColor('#3B82F6');
        setInstructions('');
        setSkills([]);
        setAutoMemory(true);
      }
      setRemovedSkills([]);
      setIsPickerOpen(false);
      setIsAddingSkill(false);
      setIsGithubImportOpen(false);
      setGithubRepo('');
      setInspectError('');
      setInstallSuccessMsg('');
      setDiscoveredSkills([]);
      setSelectedGithubSkills(new Set());
      setGithubSkillFilter('');
      setSkillsSearch('');
      setActiveTab('details');
      setErrorMsg('');
      setMemoryClearMsg('');
    }
    return () => {
      isCancelled = true;
    };
  }, [workspace?.name, mode, isOpen]);

  const handleInspectGithub = async () => {
    const cleanRepo = githubRepo.trim();
    if (!cleanRepo) return;
    setIsInspecting(true);
    setInspectError('');
    setInstallSuccessMsg('');
    setDiscoveredSkills([]);
    setSelectedGithubSkills(new Set());

    try {
      const res = await api.inspectSkills(cleanRepo);
      if (res.success && res.skills && res.skills.length > 0) {
        setDiscoveredSkills(res.skills);
        setSelectedGithubSkills(new Set(res.skills));
      } else {
        setInspectError(res.message || 'No installable skills were discovered in this repository.');
      }
    } catch (e: any) {
      setInspectError(e.message || 'Failed to inspect repository.');
    } finally {
      setIsInspecting(false);
    }
  };

  const handleToggleGithubSkill = (skill: string) => {
    setSelectedGithubSkills(prev => {
      const next = new Set(prev);
      if (next.has(skill)) next.delete(skill);
      else next.add(skill);
      return next;
    });
  };

  const handleSelectAllDiscovered = () => {
    setSelectedGithubSkills(new Set(discoveredSkills));
  };

  const handleDeselectAllDiscovered = () => {
    setSelectedGithubSkills(new Set());
  };

  const handleInstallGithubSkills = async () => {
    const cleanRepo = githubRepo.trim();
    const cleanWs = (name || workspace?.name || 'default').trim().replace(/[^a-zA-Z0-9_\- ]/g, '-');
    const toInstall = Array.from(selectedGithubSkills);
    if (!cleanRepo || toInstall.length === 0) return;

    setIsInstalling(true);
    setInspectError('');
    setInstallSuccessMsg('');

    try {
      const res = await api.installSkills(cleanWs, cleanRepo, toInstall);
      if (res.success) {
        setInstallSuccessMsg(`Successfully installed ${res.installed?.length || toInstall.length} skill(s) into '${cleanWs}'!`);
        if (onReload) {
          await onReload();
        }
        const freshWorkspaces = await api.getWorkspaces();
        const found = freshWorkspaces.find(w => w.name.toLowerCase() === cleanWs.toLowerCase());
        if (found && found.skills) {
          setSkills(found.skills);
        }
      } else {
        setInspectError(res.message || 'Failed to install selected skills.');
      }
    } catch (e: any) {
      setInspectError(e.message || 'Error installing skills.');
    } finally {
      setIsInstalling(false);
    }
  };

  const filteredDiscoveredSkills = useMemo(() => {
    if (!githubSkillFilter.trim()) return discoveredSkills;
    const q = githubSkillFilter.toLowerCase();
    return discoveredSkills.filter(s => s.toLowerCase().includes(q));
  }, [discoveredSkills, githubSkillFilter]);

  const displayedSkills = useMemo(() => {
    if (!skillsSearch.trim()) return skills;
    const q = skillsSearch.toLowerCase();
    return skills.filter(s =>
      s.name.toLowerCase().includes(q) ||
      s.id.toLowerCase().includes(q) ||
      (s.description && s.description.toLowerCase().includes(q))
    );
  }, [skills, skillsSearch]);

  const handleSaveSkill = () => {
    if (!skillName.trim()) return;
    const cleanId = skillName.trim().toLowerCase().replace(/[^a-z0-9_-]/g, '-');
    const newSkill: WorkspaceSkill = {
      id: cleanId,
      name: skillName.trim(),
      description: skillDesc.trim() || undefined,
      content: skillContent.trim(),
      enabled: true
    };
    setSkills(prev => [...prev.filter(s => s.id !== cleanId), newSkill]);
    setSkillName('');
    setSkillDesc('');
    setSkillContent('');
    setIsAddingSkill(false);
  };

  const handleToggleTemplate = (tpl: typeof PRESET_SKILL_TEMPLATES[0]) => {
    const cleanId = tpl.name.toLowerCase().replace(/[^a-z0-9_-]/g, '-');
    const existing = skills.find(
      s => s.id === cleanId || s.name.toLowerCase() === tpl.name.toLowerCase()
    );
    if (existing) {
      setRemovedSkills(prev => [...prev, existing]);
      setSkills(prev => prev.filter(
        s => s.id !== cleanId && s.name.toLowerCase() !== tpl.name.toLowerCase()
      ));
    } else {
      setRemovedSkills(prev => prev.filter(
        s => s.id !== cleanId && s.name.toLowerCase() !== tpl.name.toLowerCase()
      ));
      setSkills(prev => [
        ...prev,
        {
          id: cleanId,
          name: tpl.name,
          description: tpl.description,
          content: tpl.content,
          enabled: true
        }
      ]);
    }
  };

  const handleRemoveSkill = (id: string) => {
    const target = skills.find(s => s.id === id);
    if (target) {
      setRemovedSkills(prev => [...prev, target]);
    }
    setSkills(prev => prev.filter(s => s.id !== id));
  };

  const handleClearMemory = async () => {
    const targetWs = (workspace?.name || name || '').trim();
    if (!targetWs) return;
    if (!window.confirm(`Clear stored facts for workspace '${targetWs}'?`)) return;
    try {
      await api.deleteWorkspaceMemoryFact(targetWs);
      setMemoryClearMsg('Memory cleared');
      setTimeout(() => setMemoryClearMsg(''), 2500);
    } catch {
      setMemoryClearMsg('Failed to clear memory');
      setTimeout(() => setMemoryClearMsg(''), 2500);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const cleanName = name.trim().replace(/[^a-zA-Z0-9_\- ]/g, '-');
    if (!cleanName) {
      setErrorMsg('Workspace name is required');
      return;
    }

    setIsSubmitting(true);
    setErrorMsg('');
    try {
      await onSave({
        name: cleanName,
        oldName: mode === 'edit' ? workspace?.name : undefined,
        description: workspace?.description,
        icon,
        color,
        custom_instructions: instructions.trim(),
        auto_memory: autoMemory,
        skills,
        deletedSkills: removedSkills
      });
      onClose();
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to save workspace');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-4 select-none">
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 bg-black/50 backdrop-blur-sm transition-opacity"
          />

          {/* Modal Surface */}
          <motion.div
            initial={{ opacity: 0, scale: 0.96, y: 8 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.96, y: 8 }}
            transition={{ type: 'spring', stiffness: 420, damping: 28 }}
            className="relative w-full max-w-lg h-[580px] max-h-[88dvh] rounded-2xl bg-white/95 dark:bg-zinc-900/95 backdrop-blur-xl border border-slate-200 dark:border-zinc-800 p-5 sm:p-6 shadow-2xl z-10 text-slate-800 dark:text-slate-100 flex flex-col overflow-hidden"
          >
            {/* Header */}
            <div className="shrink-0 flex items-center justify-between pb-3.5 border-b border-slate-200 dark:border-zinc-800">
              <div>
                <h2 className="text-base sm:text-lg font-bold text-slate-900 dark:text-white">
                  {mode === 'create' ? 'Workspace Setup' : 'Edit Workspace'}
                </h2>
                <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                  Customize workspace identity, directives, and autonomous skills.
                </p>
              </div>
              <button
                type="button"
                onClick={onClose}
                className="p-1.5 rounded-lg text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 hover:bg-black/5 dark:hover:bg-white/10 transition-colors cursor-pointer"
                aria-label="Close"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Tab Switcher */}
            <div className="shrink-0 flex gap-1.5 my-3.5 p-1 rounded-xl bg-slate-100 dark:bg-zinc-800/70 border border-slate-200/80 dark:border-zinc-700/60">
              <button
                type="button"
                onClick={() => setActiveTab('details')}
                className={`flex-1 py-1.5 px-3 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
                  activeTab === 'details'
                    ? 'bg-white dark:bg-zinc-700 text-slate-900 dark:text-white shadow-xs'
                    : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
                }`}
              >
                General & Instructions
              </button>
              <button
                type="button"
                onClick={() => setActiveTab('skills')}
                className={`flex-1 py-1.5 px-3 rounded-lg text-xs font-semibold transition-all cursor-pointer flex items-center justify-center gap-1.5 ${
                  activeTab === 'skills'
                    ? 'bg-white dark:bg-zinc-700 text-slate-900 dark:text-white shadow-xs'
                    : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
                }`}
              >
                <span>Manage Skills</span>
                {skills.length > 0 && (
                  <span className="px-1.5 py-0.2 rounded-full text-[10px] bg-blue-500/20 text-blue-600 dark:text-blue-400 font-bold">
                    {skills.length}
                  </span>
                )}
              </button>
            </div>

            <form onSubmit={handleSubmit} className="flex-1 flex flex-col min-h-0">
              {errorMsg && (
                <div className="shrink-0 mb-3 p-3 rounded-xl text-xs bg-red-500/10 border border-red-500/20 text-red-600 dark:text-red-400">
                  {errorMsg}
                </div>
              )}

              {/* Scrollable Tab Body */}
              <div className="flex-1 overflow-y-auto min-h-0 pr-1 custom-scrollbar">
                {activeTab === 'details' ? (
                  <div className="space-y-4 pb-2">
                  {/* Row: Icon Picker button side-by-side with Workspace Name */}
                  <div>
                    <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
                      Workspace Identity
                    </label>
                    <div className="flex items-center gap-2.5">
                      {/* Left: Icon Selector Button */}
                      <div className="relative shrink-0">
                        <button
                          type="button"
                          onClick={() => setIsPickerOpen(prev => !prev)}
                          className="w-10 h-10 rounded-xl flex items-center justify-center cursor-pointer transition-transform hover:scale-105 active:scale-95 border border-slate-200 dark:border-zinc-700 bg-slate-100/80 dark:bg-zinc-800 shadow-xs group"
                          title="Click to customize icon & color"
                        >
                          <WorkspaceIcon
                            icon={icon}
                            color={color}
                            className="w-5 h-5"
                          />
                        </button>

                        {/* Popover Icon & Color Picker */}
                        <AnimatePresence>
                          {isPickerOpen && (
                            <div className="absolute left-0 top-12 z-50">
                              <IconColorPicker
                                selectedIcon={icon}
                                selectedColor={color}
                                onSelectIcon={(newIcon) => setIcon(newIcon)}
                                onSelectColor={(newColor) => setColor(newColor)}
                                onClose={() => setIsPickerOpen(false)}
                              />
                            </div>
                          )}
                        </AnimatePresence>
                      </div>

                      {/* Right: Workspace Name Field */}
                      <div className="flex-1 min-w-0">
                        <input
                          type="text"
                          value={name}
                          onChange={(e) => setName(e.target.value)}
                          placeholder="e.g. coding-agent, data-research"
                          required
                          className="w-full h-10 px-3 rounded-xl bg-slate-50 dark:bg-zinc-800/80 border border-slate-300 dark:border-zinc-700 text-xs sm:text-sm text-slate-900 dark:text-white placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500/30 focus:border-blue-500 transition-colors"
                        />
                      </div>
                    </div>
                    <span className="text-[11px] text-slate-400 dark:text-slate-500 mt-1 block">
                      Click the icon button to customize color and symbol.
                    </span>
                  </div>

                  {/* Workspace Instructions */}
                  <div>
                    <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
                      Workspace Instructions
                    </label>
                    <textarea
                      value={instructions}
                      onChange={(e) => setInstructions(e.target.value)}
                      placeholder="Provide system instructions, persona guidelines, or constraints for models in this workspace..."
                      rows={3}
                      className="w-full p-2.5 rounded-xl bg-slate-50 dark:bg-zinc-800/80 border border-slate-300 dark:border-zinc-700 text-xs text-slate-900 dark:text-white placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500/30 focus:border-blue-500 resize-none leading-relaxed transition-colors"
                    />
                    <span className="text-[11px] text-slate-400 dark:text-slate-500 mt-1 block">
                      Instructions are automatically synchronized with workspace directives and applied to all chats.
                    </span>
                  </div>

                  {/* Auto-Memory Extraction Row (Clean, no icon, no AI badge slop) */}
                  <div className="flex items-center justify-between p-3 rounded-xl bg-slate-50 dark:bg-zinc-800/50 border border-slate-200 dark:border-zinc-700">
                    <div className="min-w-0 pr-3">
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-semibold text-slate-900 dark:text-white">
                          Auto-Memory
                        </span>
                        {mode === 'edit' && (
                          <button
                            type="button"
                            onClick={handleClearMemory}
                            className="text-[11px] text-slate-400 hover:text-red-500 transition-colors cursor-pointer underline underline-offset-2 ml-1"
                          >
                            Clear stored facts
                          </button>
                        )}
                        {memoryClearMsg && (
                          <span className="text-[11px] text-blue-600 dark:text-blue-400 font-medium">
                            {memoryClearMsg}
                          </span>
                        )}
                      </div>
                      <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-0.5">
                        Remember key facts and preferences across chats in this workspace.
                      </p>
                    </div>

                    {/* Accessible Switch */}
                    <button
                      type="button"
                      role="switch"
                      aria-checked={autoMemory}
                      onClick={() => setAutoMemory(prev => !prev)}
                      className={`relative inline-flex h-5 w-9 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-blue-500/40 ${
                        autoMemory ? 'bg-blue-600' : 'bg-slate-300 dark:bg-zinc-600'
                      }`}
                    >
                      <span className="sr-only">Toggle Auto-Memory</span>
                      <span
                        aria-hidden="true"
                        className={`pointer-events-none inline-block h-4 w-4 transform rounded-full bg-white shadow-xs ring-0 transition duration-200 ease-in-out ${
                          autoMemory ? 'translate-x-4' : 'translate-x-0'
                        }`}
                      />
                    </button>
                  </div>
                </div>
              ) : (
                /* Tab: Manage Skills */
                <div className="space-y-3.5 pb-2">
                  {/* Presets Strip */}
                  <div>
                    <span className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-2">
                      Quick-Add Skill Presets
                    </span>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                      {PRESET_SKILL_TEMPLATES.map((tpl) => {
                        const cleanPresetId = tpl.name.toLowerCase().replace(/[^a-z0-9_-]/g, '-');
                        const isAdded = skills.some(
                          s => s.id === cleanPresetId || s.name.toLowerCase() === tpl.name.toLowerCase()
                        );
                        return (
                          <button
                            key={tpl.name}
                            type="button"
                            onClick={() => handleToggleTemplate(tpl)}
                            className={`p-2.5 rounded-xl text-left border transition-all flex items-start gap-2.5 cursor-pointer ${
                              isAdded
                                ? 'bg-blue-500/10 border-blue-500/30 text-blue-600 dark:text-blue-400 hover:bg-blue-500/15'
                                : 'bg-slate-50 dark:bg-zinc-800/50 border-slate-200 dark:border-zinc-700 hover:border-blue-500/40 hover:bg-blue-500/5'
                            }`}
                          >
                            <div className="p-1.5 rounded-lg bg-black/5 dark:bg-white/10 shrink-0 mt-0.5">
                              {isAdded ? <Check className="w-3.5 h-3.5" /> : tpl.icon}
                            </div>
                            <div className="min-w-0 flex-1">
                              <div className="text-xs font-semibold leading-tight truncate">
                                {tpl.name}
                              </div>
                              <div className="text-[11px] text-slate-400 dark:text-slate-500 line-clamp-1 mt-0.5">
                                {tpl.description}
                              </div>
                            </div>
                          </button>
                        );
                      })}
                    </div>
                  </div>

                  {/* Skills List Header & Action Buttons */}
                  <div className="flex flex-wrap items-center justify-between gap-2 pt-2 border-t border-slate-200 dark:border-zinc-800">
                    <span className="text-xs font-semibold text-slate-700 dark:text-slate-300">
                      Configured Skills ({skillsSearch.trim() ? `${displayedSkills.length} of ${skills.length}` : skills.length})
                    </span>
                    <div className="flex items-center gap-2">
                      <button
                        type="button"
                        onClick={() => { setIsGithubImportOpen(prev => !prev); setIsAddingSkill(false); }}
                        className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors cursor-pointer border ${
                          isGithubImportOpen
                            ? 'bg-blue-600 text-white border-blue-600 shadow-xs'
                            : 'bg-slate-100 dark:bg-zinc-800 border-slate-200 dark:border-zinc-700 text-slate-700 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-zinc-700'
                        }`}
                      >
                        <Download className="w-3.5 h-3.5" />
                        <span>Import from GitHub</span>
                      </button>
                      <button
                        type="button"
                        onClick={() => { setIsAddingSkill(prev => !prev); setIsGithubImportOpen(false); }}
                        className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors cursor-pointer border ${
                          isAddingSkill
                            ? 'bg-blue-600 text-white border-blue-600 shadow-xs'
                            : 'bg-slate-100 dark:bg-zinc-800 border-slate-200 dark:border-zinc-700 text-slate-700 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-zinc-700'
                        }`}
                      >
                        <Plus className="w-3.5 h-3.5" />
                        <span>Custom Skill</span>
                      </button>
                    </div>
                  </div>

                  {/* GitHub Import Drawer Form */}
                  <AnimatePresence>
                    {isGithubImportOpen && (
                      <motion.div
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: 'auto' }}
                        exit={{ opacity: 0, height: 0 }}
                        className="overflow-hidden p-3 rounded-xl bg-slate-50 dark:bg-zinc-800/80 border border-slate-200 dark:border-zinc-700 space-y-2.5"
                      >
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2 text-xs font-semibold text-slate-800 dark:text-slate-200">
                            <GitBranch className="w-3.5 h-3.5 text-blue-600 dark:text-blue-400" />
                            <span>Import Skills from GitHub Repository</span>
                          </div>
                          <span className="text-[11px] text-slate-400">
                            owner/repo or URL
                          </span>
                        </div>

                        <div className="flex gap-2">
                          <input
                            type="text"
                            value={githubRepo}
                            onChange={(e) => setGithubRepo(e.target.value)}
                            placeholder="e.g. anthropics/courses or owner/repo"
                            disabled={isInspecting || isInstalling}
                            onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); handleInspectGithub(); } }}
                            className="flex-1 px-3 py-1.5 rounded-lg bg-white dark:bg-zinc-900 border border-slate-300 dark:border-zinc-700 text-xs text-slate-900 dark:text-white placeholder:text-slate-400 focus:outline-none focus:border-blue-500"
                          />
                          <button
                            type="button"
                            onClick={handleInspectGithub}
                            disabled={isInspecting || isInstalling || !githubRepo.trim()}
                            className="px-3.5 py-1.5 rounded-lg text-xs font-semibold bg-blue-600 text-white hover:bg-blue-500 disabled:opacity-50 transition-colors cursor-pointer flex items-center gap-1.5 shrink-0 shadow-xs"
                          >
                            {isInspecting ? (
                              <>
                                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                                <span>Inspecting...</span>
                              </>
                            ) : (
                              <>
                                <Search className="w-3.5 h-3.5" />
                                <span>Inspect</span>
                              </>
                            )}
                          </button>
                        </div>

                        {inspectError && (
                          <div className="p-2.5 rounded-lg text-xs bg-red-500/10 border border-red-500/20 text-red-600 dark:text-red-400 flex items-center gap-2">
                            <AlertCircle className="w-3.5 h-3.5 shrink-0" />
                            <span>{inspectError}</span>
                          </div>
                        )}

                        {installSuccessMsg && (
                          <div className="p-2.5 rounded-lg text-xs bg-emerald-500/10 border border-emerald-500/20 text-emerald-600 dark:text-emerald-400 flex items-center gap-2">
                            <Check className="w-3.5 h-3.5 shrink-0" />
                            <span>{installSuccessMsg}</span>
                          </div>
                        )}

                        {discoveredSkills.length > 0 && (
                          <div className="space-y-2 pt-1 border-t border-slate-200 dark:border-zinc-700">
                            <div className="flex items-center justify-between text-xs">
                              <span className="font-semibold text-slate-700 dark:text-slate-300">
                                Discovered Skills ({discoveredSkills.length})
                              </span>
                              <div className="flex items-center gap-2 text-[11px]">
                                <button
                                  type="button"
                                  onClick={handleSelectAllDiscovered}
                                  className="text-blue-600 dark:text-blue-400 hover:underline cursor-pointer"
                                >
                                  Select All
                                </button>
                                <span className="text-slate-300 dark:text-slate-600">|</span>
                                <button
                                  type="button"
                                  onClick={handleDeselectAllDiscovered}
                                  className="text-slate-500 hover:underline cursor-pointer"
                                >
                                  Clear
                                </button>
                              </div>
                            </div>

                            {discoveredSkills.length > 6 && (
                              <input
                                type="text"
                                value={githubSkillFilter}
                                onChange={(e) => setGithubSkillFilter(e.target.value)}
                                placeholder="Filter discovered skills..."
                                className="w-full px-2.5 py-1 rounded-lg bg-white dark:bg-zinc-900 border border-slate-300 dark:border-zinc-700 text-[11px] text-slate-800 dark:text-slate-200 placeholder:text-slate-400 focus:outline-none focus:border-blue-500"
                              />
                            )}

                            <div className="max-h-36 overflow-y-auto space-y-1 pr-1 custom-scrollbar">
                              {filteredDiscoveredSkills.map(sk => {
                                const isSelected = selectedGithubSkills.has(sk);
                                return (
                                  <label
                                    key={sk}
                                    className={`flex items-center gap-2 p-1.5 rounded-lg text-xs cursor-pointer transition-colors ${
                                      isSelected
                                        ? 'bg-blue-500/15 text-blue-900 dark:text-blue-100 font-medium'
                                        : 'hover:bg-black/5 dark:hover:bg-white/5 text-slate-700 dark:text-slate-300'
                                    }`}
                                  >
                                    <input
                                      type="checkbox"
                                      checked={isSelected}
                                      onChange={() => handleToggleGithubSkill(sk)}
                                      className="rounded border-slate-300 text-blue-600 focus:ring-blue-500"
                                    />
                                    <span className="truncate">{sk}</span>
                                  </label>
                                );
                              })}
                            </div>

                            <div className="flex justify-end gap-2 pt-2">
                              <button
                                type="button"
                                onClick={() => setIsGithubImportOpen(false)}
                                className="h-8 px-3 rounded-lg text-xs font-semibold text-slate-600 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-zinc-700 transition-colors"
                              >
                                Close
                              </button>
                              <button
                                type="button"
                                onClick={handleInstallGithubSkills}
                                disabled={isInstalling || selectedGithubSkills.size === 0}
                                className="h-8 px-3.5 rounded-lg text-xs font-semibold bg-blue-600 text-white hover:bg-blue-500 disabled:opacity-50 cursor-pointer shadow-xs flex items-center gap-1.5"
                              >
                                {isInstalling ? (
                                  <>
                                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                                    <span>Installing...</span>
                                  </>
                                ) : (
                                  <>
                                    <Download className="w-3.5 h-3.5" />
                                    <span>Install ({selectedGithubSkills.size}) Skills</span>
                                  </>
                                )}
                              </button>
                            </div>
                          </div>
                        )}
                      </motion.div>
                    )}
                  </AnimatePresence>

                  {/* Custom Skill Drawer Form */}
                  <AnimatePresence>
                    {isAddingSkill && (
                      <motion.div
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: 'auto' }}
                        exit={{ opacity: 0, height: 0 }}
                        className="overflow-hidden p-3 rounded-xl bg-slate-50 dark:bg-zinc-800/80 border border-slate-200 dark:border-zinc-700 space-y-2.5"
                      >
                        <div className="text-xs font-semibold text-slate-800 dark:text-slate-200">
                          Add Custom Skill
                        </div>
                        <input
                          type="text"
                          value={skillName}
                          onChange={(e) => setSkillName(e.target.value)}
                          placeholder="Skill name (e.g. SQL Expert)"
                          className="w-full px-3 py-1.5 rounded-lg bg-white dark:bg-zinc-900 border border-slate-300 dark:border-zinc-700 text-xs text-slate-900 dark:text-white placeholder:text-slate-400 focus:outline-none focus:border-blue-500"
                        />
                        <input
                          type="text"
                          value={skillDesc}
                          onChange={(e) => setSkillDesc(e.target.value)}
                          placeholder="Brief description (optional)"
                          className="w-full px-3 py-1.5 rounded-lg bg-white dark:bg-zinc-900 border border-slate-300 dark:border-zinc-700 text-xs text-slate-900 dark:text-white placeholder:text-slate-400 focus:outline-none focus:border-blue-500"
                        />
                        <textarea
                          value={skillContent}
                          onChange={(e) => setSkillContent(e.target.value)}
                          placeholder="Skill instructions or guidelines for the agent..."
                          rows={3}
                          className="w-full p-2.5 rounded-lg bg-white dark:bg-zinc-900 border border-slate-300 dark:border-zinc-700 text-xs text-slate-900 dark:text-white placeholder:text-slate-400 focus:outline-none focus:border-blue-500 resize-none leading-relaxed"
                        />
                        <div className="flex justify-end gap-2 pt-1">
                          <button
                            type="button"
                            onClick={() => setIsAddingSkill(false)}
                            className="h-8 px-3 rounded-lg text-xs font-semibold text-slate-600 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-zinc-700 transition-colors"
                          >
                            Cancel
                          </button>
                          <button
                            type="button"
                            onClick={handleSaveSkill}
                            disabled={!skillName.trim()}
                            className="h-8 px-3.5 rounded-lg text-xs font-semibold bg-blue-600 text-white hover:bg-blue-500 disabled:opacity-50 cursor-pointer shadow-xs"
                          >
                            Save Skill
                          </button>
                        </div>
                      </motion.div>
                    )}
                  </AnimatePresence>

                  {/* Filter configured skills if large list */}
                  {skills.length > 5 && (
                    <div className="relative">
                      <Search className="w-3.5 h-3.5 absolute left-3 top-2.5 text-slate-400 pointer-events-none" />
                      <input
                        type="text"
                        value={skillsSearch}
                        onChange={(e) => setSkillsSearch(e.target.value)}
                        placeholder="Search skills in this workspace..."
                        className="w-full pl-8 pr-3 py-1.5 rounded-lg bg-white dark:bg-zinc-900 border border-slate-300 dark:border-zinc-700 text-xs text-slate-900 dark:text-white placeholder:text-slate-400 focus:outline-none focus:border-blue-500"
                      />
                    </div>
                  )}

                  {/* Skills List Items */}
                  <div className="space-y-2 max-h-48 overflow-y-auto pr-1 custom-scrollbar">
                    {skills.length === 0 ? (
                      <div className="text-center py-6 text-xs text-slate-400 dark:text-slate-500">
                        No skills configured in this workspace yet. Select a preset above, import from GitHub, or add a custom skill.
                      </div>
                    ) : displayedSkills.length === 0 ? (
                      <div className="text-center py-6 text-xs text-slate-400 dark:text-slate-500">
                        No skills match '{skillsSearch}'.
                      </div>
                    ) : (
                      displayedSkills.map((s) => (
                        <div
                          key={s.id}
                          className="p-2.5 rounded-xl bg-slate-50 dark:bg-zinc-800/40 border border-slate-200 dark:border-zinc-700/80 flex items-start justify-between gap-3"
                        >
                          <div className="min-w-0 flex-1">
                            <div className="flex items-center gap-2">
                              <span className="text-xs font-semibold text-slate-900 dark:text-white truncate">
                                {s.name}
                              </span>
                              {s.path ? (
                                <span className="px-1.5 py-0.2 rounded text-[10px] font-mono bg-black/5 dark:bg-white/10 text-slate-500 dark:text-slate-400 shrink-0">
                                  Directory
                                </span>
                              ) : (
                                <span className="px-1.5 py-0.2 rounded text-[10px] bg-blue-500/10 text-blue-600 dark:text-blue-400 font-medium shrink-0">
                                  Custom
                                </span>
                              )}
                            </div>
                            {s.description && (
                              <div className="text-[11px] text-slate-400 dark:text-slate-500 mt-0.5 line-clamp-1">
                                {s.description}
                              </div>
                            )}
                            {s.content && (
                              <div className="text-[11px] font-mono text-slate-500 dark:text-slate-400 mt-1 line-clamp-2 bg-black/5 dark:bg-black/30 p-1.5 rounded-lg">
                                {s.content}
                              </div>
                            )}
                          </div>
                          <button
                            type="button"
                            onClick={() => handleRemoveSkill(s.id)}
                            className="p-1 rounded-lg text-slate-400 hover:text-red-600 dark:hover:text-red-400 hover:bg-red-500/10 transition-colors cursor-pointer shrink-0"
                            title="Delete skill"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      ))
                    )}
                  </div>
                </div>
              )}
              </div>

              {/* Action Buttons */}
              <div className="shrink-0 flex items-center justify-end gap-2.5 pt-3.5 border-t border-slate-200 dark:border-zinc-800 mt-2">
                <button
                  type="button"
                  onClick={onClose}
                  disabled={isSubmitting}
                  className="h-9 px-4 rounded-xl text-xs font-semibold text-slate-700 dark:text-slate-300 bg-slate-100 hover:bg-slate-200 dark:bg-zinc-800 dark:hover:bg-zinc-700 border border-slate-200 dark:border-zinc-700 transition-colors cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting || !name.trim()}
                  className="h-9 px-4 rounded-xl text-xs font-semibold bg-blue-600 text-white hover:bg-blue-500 active:scale-98 transition-all cursor-pointer shadow-xs disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {isSubmitting
                    ? 'Saving...'
                    : mode === 'create'
                    ? 'Create Workspace'
                    : 'Save Workspace'}
                </button>
              </div>
            </form>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
}
