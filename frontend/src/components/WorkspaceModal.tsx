import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import {
  X,
  Plus,
  Trash2,
  BookOpen,
  Code2,
  Languages,
  PenTool,
  Check
} from 'lucide-react';
import type { Workspace, WorkspaceSkill } from '../types';
import { WorkspaceIcon } from './WorkspaceIcon';
import { IconColorPicker } from './IconColorPicker';

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
    skills: WorkspaceSkill[];
  }) => Promise<void> | void;
  onClose: () => void;
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
  onClose
}: WorkspaceModalProps) {
  const [name, setName] = useState('');
  const [icon, setIcon] = useState('Folder');
  const [color, setColor] = useState('#3B82F6');
  const [instructions, setInstructions] = useState('');
  const [skills, setSkills] = useState<WorkspaceSkill[]>([]);
  const [isPickerOpen, setIsPickerOpen] = useState(false);
  const [activeTab, setActiveTab] = useState<'details' | 'skills'>('details');

  // Inline skill creation
  const [isAddingSkill, setIsAddingSkill] = useState(false);
  const [skillName, setSkillName] = useState('');
  const [skillDesc, setSkillDesc] = useState('');
  const [skillContent, setSkillContent] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');

  useEffect(() => {
    if (workspace && mode === 'edit') {
      setName(workspace.name || '');
      setIcon(workspace.icon || 'Folder');
      setColor(workspace.color || '#3B82F6');
      setInstructions(workspace.custom_instructions || '');
      setSkills(workspace.skills || []);
    } else if (workspace && mode === 'create') {
      setName(workspace.name || '');
      setIcon(workspace.icon || 'Folder');
      setColor(workspace.color || '#3B82F6');
      setInstructions(workspace.custom_instructions || '');
      setSkills(workspace.skills || []);
    } else {
      setName('');
      setIcon('Folder');
      setColor('#3B82F6');
      setInstructions('');
      setSkills([]);
    }
    setIsPickerOpen(false);
    setIsAddingSkill(false);
    setActiveTab('details');
    setErrorMsg('');
  }, [workspace, mode, isOpen]);

  if (!isOpen) return null;

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

  const handleAddTemplate = (tpl: typeof PRESET_SKILL_TEMPLATES[0]) => {
    const cleanId = tpl.name.toLowerCase().replace(/[^a-z0-9_-]/g, '-');
    if (skills.some(s => s.id === cleanId)) return;
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
  };

  const handleRemoveSkill = (id: string) => {
    setSkills(prev => prev.filter(s => s.id !== id));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const cleanName = name.trim().replace(/[^a-zA-Z0-9_\-]/g, '-').toLowerCase();
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
        skills
      });
      onClose();
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to save workspace');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        onClick={onClose}
        className="fixed inset-0 bg-black/60 backdrop-blur-sm"
      />

      {/* Modal Surface */}
      <motion.div
        initial={{ opacity: 0, scale: 0.94, y: 14 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.94, y: 14 }}
        transition={{ type: 'spring', stiffness: 420, damping: 28 }}
        className="relative w-full max-w-xl max-h-[90dvh] overflow-y-auto rounded-[32px] bg-white/95 dark:bg-[#0f1420]/95 backdrop-blur-2xl border border-slate-200/80 dark:border-white/10 p-6 md:p-8 shadow-2xl shadow-black/40 z-10 text-slate-800 dark:text-slate-100 flex flex-col custom-scrollbar"
      >
        {/* Header */}
        <div className="flex items-center justify-between pb-4 border-b border-slate-200 dark:border-white/10">
          <div>
            <h2 className="text-xl md:text-2xl font-bold tracking-tight text-slate-900 dark:text-white">
              {mode === 'create' ? 'Workspace Setup' : 'Edit Workspace'}
            </h2>
            <p className="text-xs md:text-sm text-slate-500 dark:text-slate-400 mt-0.5">
              Customize workspace identity, directives, and autonomous skills.
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-2 rounded-full hover:bg-black/5 dark:hover:bg-white/10 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 transition-colors cursor-pointer"
            aria-label="Close"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Tab Switcher */}
        <div className="flex gap-2 my-4 p-1 rounded-2xl bg-black/[0.04] dark:bg-white/5 border border-black/5 dark:border-white/5">
          <button
            type="button"
            onClick={() => setActiveTab('details')}
            className={`flex-1 py-1.5 px-3 rounded-xl text-xs md:text-sm font-semibold transition-all cursor-pointer ${
              activeTab === 'details'
                ? 'bg-white dark:bg-white/15 text-slate-900 dark:text-white shadow-sm'
                : 'text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
            }`}
          >
            General & Instructions
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('skills')}
            className={`flex-1 py-1.5 px-3 rounded-xl text-xs md:text-sm font-semibold transition-all cursor-pointer flex items-center justify-center gap-1.5 ${
              activeTab === 'skills'
                ? 'bg-white dark:bg-white/15 text-slate-900 dark:text-white shadow-sm'
                : 'text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
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

        <form onSubmit={handleSubmit} className="flex-1 flex flex-col space-y-5">
          {errorMsg && (
            <div className="p-3 rounded-xl text-xs bg-red-500/10 border border-red-500/20 text-red-600 dark:text-red-400">
              {errorMsg}
            </div>
          )}

          {activeTab === 'details' ? (
            <>
              {/* Row: Icon Picker button side-by-side with Workspace Name */}
              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-slate-600 dark:text-slate-400 mb-2">
                  Workspace Identity
                </label>
                <div className="flex items-center gap-3">
                  {/* Left: Icon Selector Button */}
                  <div className="relative shrink-0">
                    <button
                      type="button"
                      onClick={() => setIsPickerOpen(prev => !prev)}
                      style={{
                        backgroundColor: color,
                        boxShadow: `0 4px 14px -3px ${color}80`
                      }}
                      className="w-12 h-12 rounded-2xl flex items-center justify-center cursor-pointer transition-transform hover:scale-105 active:scale-95 border border-white/20 shadow-md group"
                      title="Click to customize icon & color"
                    >
                      <WorkspaceIcon
                        icon={icon}
                        color={color}
                        className="w-6 h-6"
                      />
                    </button>

                    {/* Popover Icon & Color Picker */}
                    <AnimatePresence>
                      {isPickerOpen && (
                        <div className="absolute left-0 top-14 z-50">
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
                      className="w-full h-12 px-4 rounded-2xl bg-black/[0.04] dark:bg-white/5 border border-slate-300/80 dark:border-white/10 text-sm md:text-base text-slate-900 dark:text-white placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500/40 focus:border-blue-500"
                    />
                  </div>
                </div>
                <span className="text-[11px] text-slate-400 dark:text-slate-500 mt-1 block">
                  Click the icon button to customize color and symbol.
                </span>
              </div>

              {/* Workspace Instructions */}
              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-slate-600 dark:text-slate-400 mb-1.5">
                  Workspace Instructions
                </label>
                <textarea
                  value={instructions}
                  onChange={(e) => setInstructions(e.target.value)}
                  placeholder="Provide system instructions, persona guidelines, or constraints for models in this workspace..."
                  rows={4}
                  className="w-full p-3.5 rounded-2xl bg-black/[0.04] dark:bg-white/5 border border-slate-300/80 dark:border-white/10 text-xs md:text-sm text-slate-900 dark:text-white placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500/40 focus:border-blue-500 resize-none leading-relaxed"
                />
                <span className="text-[11px] text-slate-400 dark:text-slate-500 mt-1 block">
                  Instructions are automatically synchronized with workspace directives and applied to all chats.
                </span>
              </div>
            </>
          ) : (
            /* Tab: Manage Skills */
            <div className="space-y-4">
              {/* Presets Strip */}
              <div>
                <span className="block text-xs font-semibold uppercase tracking-wider text-slate-600 dark:text-slate-400 mb-2">
                  Quick-Add Skill Presets
                </span>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                  {PRESET_SKILL_TEMPLATES.map((tpl) => {
                    const isAdded = skills.some(
                      s => s.id === tpl.name.toLowerCase().replace(/[^a-z0-9_-]/g, '-')
                    );
                    return (
                      <button
                        key={tpl.name}
                        type="button"
                        onClick={() => handleAddTemplate(tpl)}
                        disabled={isAdded}
                        className={`p-2.5 rounded-2xl text-left border transition-all flex items-start gap-2.5 cursor-pointer ${
                          isAdded
                            ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-600 dark:text-emerald-400 cursor-default'
                            : 'bg-black/[0.02] dark:bg-white/[0.03] border-slate-200 dark:border-white/10 hover:border-blue-500/40 hover:bg-blue-500/5'
                        }`}
                      >
                        <div className="p-1.5 rounded-xl bg-black/5 dark:bg-white/10 shrink-0 mt-0.5">
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

              {/* Skills List Header & Add Button */}
              <div className="flex items-center justify-between pt-2 border-t border-slate-200 dark:border-white/10">
                <span className="text-xs font-semibold uppercase tracking-wider text-slate-600 dark:text-slate-400">
                  Configured Skills ({skills.length})
                </span>
                <button
                  type="button"
                  onClick={() => setIsAddingSkill(prev => !prev)}
                  className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold text-blue-600 dark:text-blue-400 bg-blue-500/10 hover:bg-blue-500/20 transition-colors cursor-pointer"
                >
                  <Plus className="w-3.5 h-3.5" />
                  <span>Custom Skill</span>
                </button>
              </div>

              {/* Custom Skill Drawer Form */}
              <AnimatePresence>
                {isAddingSkill && (
                  <motion.div
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: 'auto' }}
                    exit={{ opacity: 0, height: 0 }}
                    className="overflow-hidden p-3.5 rounded-2xl bg-black/[0.04] dark:bg-white/5 border border-slate-300 dark:border-white/10 space-y-2.5"
                  >
                    <div className="text-xs font-bold text-slate-700 dark:text-slate-300">
                      Add Custom Skill
                    </div>
                    <input
                      type="text"
                      value={skillName}
                      onChange={(e) => setSkillName(e.target.value)}
                      placeholder="Skill name (e.g. SQL Expert)"
                      className="w-full px-3 py-1.5 rounded-xl bg-white dark:bg-black/40 border border-slate-300 dark:border-white/10 text-xs text-slate-900 dark:text-white placeholder:text-slate-400 focus:outline-none focus:border-blue-500"
                    />
                    <input
                      type="text"
                      value={skillDesc}
                      onChange={(e) => setSkillDesc(e.target.value)}
                      placeholder="Brief description (optional)"
                      className="w-full px-3 py-1.5 rounded-xl bg-white dark:bg-black/40 border border-slate-300 dark:border-white/10 text-xs text-slate-900 dark:text-white placeholder:text-slate-400 focus:outline-none focus:border-blue-500"
                    />
                    <textarea
                      value={skillContent}
                      onChange={(e) => setSkillContent(e.target.value)}
                      placeholder="Skill instructions or guidelines for the agent..."
                      rows={3}
                      className="w-full p-2.5 rounded-xl bg-white dark:bg-black/40 border border-slate-300 dark:border-white/10 text-xs text-slate-900 dark:text-white placeholder:text-slate-400 focus:outline-none focus:border-blue-500 resize-none leading-relaxed"
                    />
                    <div className="flex justify-end gap-2 pt-1">
                      <button
                        type="button"
                        onClick={() => setIsAddingSkill(false)}
                        className="px-3 py-1 rounded-xl text-xs text-slate-500 hover:text-slate-800 dark:hover:text-white"
                      >
                        Cancel
                      </button>
                      <button
                        type="button"
                        onClick={handleSaveSkill}
                        disabled={!skillName.trim()}
                        className="px-3.5 py-1 rounded-xl text-xs font-semibold bg-blue-600 text-white hover:bg-blue-500 disabled:opacity-50 cursor-pointer shadow-sm"
                      >
                        Save Skill
                      </button>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>

              {/* Skills List Items */}
              <div className="space-y-2 max-h-48 overflow-y-auto pr-1 custom-scrollbar">
                {skills.length === 0 ? (
                  <div className="text-center py-6 text-xs text-slate-400 dark:text-slate-500">
                    No custom skills attached yet. Select a preset above or add a custom skill.
                  </div>
                ) : (
                  skills.map((s) => (
                    <div
                      key={s.id}
                      className="p-3 rounded-2xl bg-black/[0.02] dark:bg-white/[0.04] border border-slate-200 dark:border-white/10 flex items-start justify-between gap-3"
                    >
                      <div className="min-w-0 flex-1">
                        <div className="text-xs font-semibold text-slate-900 dark:text-white truncate">
                          {s.name}
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
                        className="p-1.5 rounded-xl text-slate-400 hover:text-red-600 dark:hover:text-red-400 hover:bg-red-500/10 transition-colors cursor-pointer shrink-0"
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

          {/* Action Buttons */}
          <div className="flex items-center justify-end gap-3 pt-4 border-t border-slate-200 dark:border-white/10">
            <button
              type="button"
              onClick={onClose}
              disabled={isSubmitting}
              className="px-5 py-2.5 rounded-2xl text-xs md:text-sm font-semibold liquid-glass text-slate-700 dark:text-slate-200 hover:bg-black/5 dark:hover:bg-white/10 transition-colors cursor-pointer"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting || !name.trim()}
              className="px-6 py-2.5 rounded-2xl text-xs md:text-sm font-semibold bg-blue-600 text-white shadow-[inset_0_1px_1px_rgba(255,255,255,0.45),0_6px_14px_-4px_rgba(37,99,235,0.6)] hover:bg-blue-500 active:scale-98 transition-all cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
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
  );
}
