import { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { ChevronDown, ChevronUp } from 'lucide-react';
import {
  WORKSPACE_PRESET_COLORS,
  WORKSPACE_ICONS_LIST,
  WorkspaceIcon,
  type WorkspaceIconName
} from './WorkspaceIcon';

interface IconColorPickerProps {
  selectedIcon: string;
  selectedColor: string;
  onSelectIcon: (icon: WorkspaceIconName) => void;
  onSelectColor: (color: string) => void;
  onClose: () => void;
}

export function IconColorPicker({
  selectedIcon,
  selectedColor,
  onSelectIcon,
  onSelectColor,
  onClose
}: IconColorPickerProps) {
  const [showCustomColor, setShowCustomColor] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  // Close on outside click
  useEffect(() => {
    const handleOutsideClick = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        onClose();
      }
    };
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };

    document.addEventListener('mousedown', handleOutsideClick);
    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('mousedown', handleOutsideClick);
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [onClose]);

  return (
    <motion.div
      ref={containerRef}
      initial={{ opacity: 0, scale: 0.95, y: -6 }}
      animate={{ opacity: 1, scale: 1, y: 0 }}
      exit={{ opacity: 0, scale: 0.95, y: -6 }}
      transition={{ type: 'spring', stiffness: 450, damping: 26 }}
      className="w-[310px] p-4 rounded-[28px] bg-slate-900/95 dark:bg-[#121620]/95 backdrop-blur-2xl border border-white/15 dark:border-white/10 shadow-2xl shadow-black/60 z-50 text-slate-100 select-none"
    >
      {/* 1. Color Palette Row */}
      <div className="flex items-center justify-between gap-1.5 px-0.5">
        {WORKSPACE_PRESET_COLORS.map((col) => {
          const isSelected = selectedColor.toLowerCase() === col.toLowerCase();
          return (
            <button
              key={col}
              type="button"
              onClick={() => onSelectColor(col)}
              style={{ backgroundColor: col }}
              className={`w-7 h-7 rounded-full transition-transform cursor-pointer relative ${
                isSelected
                  ? 'scale-110 ring-2 ring-white ring-offset-2 ring-offset-slate-900 shadow-md'
                  : 'hover:scale-105 active:scale-95'
              }`}
              title={col}
              aria-label={`Select color ${col}`}
            />
          );
        })}
      </div>

      {/* 2. Custom Color Accordion */}
      <div className="mt-3">
        <button
          type="button"
          onClick={() => setShowCustomColor(prev => !prev)}
          className="w-full flex items-center justify-between py-1.5 px-2 rounded-xl hover:bg-white/5 transition-colors cursor-pointer text-xs font-medium text-slate-300"
        >
          <div className="flex items-center gap-2">
            <span
              className="w-5 h-5 rounded-full border border-white/20 shadow-sm"
              style={{
                background: selectedColor.startsWith('#')
                  ? selectedColor
                  : 'linear-gradient(135deg, #FF6B6B, #4ECDC4, #FFE66D)'
              }}
            />
            <span>Custom color</span>
          </div>
          {showCustomColor ? (
            <ChevronUp className="w-3.5 h-3.5 text-slate-400" />
          ) : (
            <ChevronDown className="w-3.5 h-3.5 text-slate-400" />
          )}
        </button>

        <AnimatePresence>
          {showCustomColor && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: 'auto', opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              className="overflow-hidden mt-1 px-2 pb-1"
            >
              <div className="flex items-center gap-2 pt-1">
                <input
                  type="color"
                  value={selectedColor.startsWith('#') ? selectedColor : '#3B82F6'}
                  onChange={(e) => onSelectColor(e.target.value)}
                  className="w-7 h-7 rounded-lg border-0 bg-transparent cursor-pointer"
                  title="Pick color"
                />
                <input
                  type="text"
                  value={selectedColor}
                  onChange={(e) => onSelectColor(e.target.value)}
                  placeholder="#3B82F6"
                  maxLength={7}
                  className="flex-1 bg-black/30 border border-white/10 rounded-xl px-2.5 py-1 text-xs text-white uppercase font-mono tracking-wider focus:outline-none focus:border-blue-400"
                />
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      <div className="my-3 h-px bg-white/10" />

      {/* 3. 6-column Grid of 30 Icons */}
      <div className="grid grid-cols-6 gap-1 max-h-56 overflow-y-auto pr-0.5 custom-scrollbar">
        {WORKSPACE_ICONS_LIST.map((iconName) => {
          const isSelected = selectedIcon === iconName;
          return (
            <button
              key={iconName}
              type="button"
              onClick={() => onSelectIcon(iconName)}
              className={`w-10 h-10 rounded-xl flex items-center justify-center transition-all cursor-pointer ${
                isSelected
                  ? 'bg-white/20 text-white ring-2 ring-blue-400 shadow-sm scale-105'
                  : 'text-slate-300 hover:text-white hover:bg-white/10 active:scale-95'
              }`}
              title={iconName}
              aria-label={`Select icon ${iconName}`}
            >
              <WorkspaceIcon icon={iconName} color={selectedColor} className="w-5.5 h-5.5" />
            </button>
          );
        })}
      </div>

      <div className="mt-3 pt-2 border-t border-white/10">
        <button
          type="button"
          onClick={onClose}
          className="w-full py-1.5 text-center text-xs font-semibold text-slate-400 hover:text-white transition-colors cursor-pointer"
        >
          Close menu
        </button>
      </div>
    </motion.div>
  );
}
