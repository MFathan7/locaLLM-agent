import React from 'react';
import {
  Folder,
  CircleDollarSign,
  Book,
  GraduationCap,
  Pencil,
  PenTool,
  Code,
  Terminal,
  Music,
  Cake,
  Wand2,
  Palette,
  Stethoscope,
  HeartHandshake,
  Flower2,
  Briefcase,
  BarChart3,
  Dumbbell,
  Activity,
  BookOpen,
  Scale,
  Globe,
  Plane,
  Compass,
  Wrench,
  PawPrint,
  FlaskConical,
  Brain,
  Heart,
  Sprout
} from 'lucide-react';

export const WORKSPACE_PRESET_COLORS = [
  '#FFFFFF',
  '#EF4444',
  '#F97316',
  '#EAB308',
  '#22C55E',
  '#3B82F6',
  '#A855F7',
  '#EC4899'
] as const;

export const WORKSPACE_ICONS_LIST = [
  'Folder',
  'CircleDollarSign',
  'Book',
  'GraduationCap',
  'Pencil',
  'PenTool',
  'Code',
  'Terminal',
  'Music',
  'Cake',
  'Wand2',
  'Palette',
  'Stethoscope',
  'HeartHandshake',
  'Flower2',
  'Briefcase',
  'BarChart3',
  'Dumbbell',
  'Activity',
  'BookOpen',
  'Scale',
  'Globe',
  'Plane',
  'Compass',
  'Wrench',
  'PawPrint',
  'FlaskConical',
  'Brain',
  'Heart',
  'Sprout'
] as const;

export type WorkspaceIconName = typeof WORKSPACE_ICONS_LIST[number];

const ICON_MAP: Record<string, React.ComponentType<{ className?: string }>> = {
  Folder,
  CircleDollarSign,
  Book,
  GraduationCap,
  Pencil,
  PenTool,
  Code,
  Terminal,
  Music,
  Cake,
  Wand2,
  Palette,
  Stethoscope,
  HeartHandshake,
  Flower2,
  Briefcase,
  BarChart3,
  Dumbbell,
  Activity,
  BookOpen,
  Scale,
  Globe,
  Plane,
  Compass,
  Wrench,
  PawPrint,
  FlaskConical,
  Brain,
  Heart,
  Sprout
};

export function isLightColor(hexColor?: string): boolean {
  if (!hexColor) return false;
  const hex = hexColor.replace('#', '');
  if (hex.length === 3) {
    const r = parseInt(hex[0] + hex[0], 16);
    const g = parseInt(hex[1] + hex[1], 16);
    const b = parseInt(hex[2] + hex[2], 16);
    return (r * 299 + g * 587 + b * 114) / 1000 > 186;
  }
  if (hex.length === 6) {
    const r = parseInt(hex.substring(0, 2), 16);
    const g = parseInt(hex.substring(2, 4), 16);
    const b = parseInt(hex.substring(4, 6), 16);
    return (r * 299 + g * 587 + b * 114) / 1000 > 186;
  }
  return false;
}

interface WorkspaceIconProps {
  icon?: string;
  color?: string;
  className?: string;
  containerClassName?: string;
  withContainer?: boolean;
}

export function WorkspaceIcon({
  icon = 'Folder',
  color = '#3B82F6',
  className = 'w-4 h-4',
  containerClassName = 'w-7 h-7 rounded-xl flex items-center justify-center shrink-0 shadow-sm',
  withContainer = false
}: WorkspaceIconProps) {
  const IconComponent = ICON_MAP[icon] || Folder;
  const light = isLightColor(color);

  if (!withContainer) {
    return <IconComponent className={className} />;
  }

  const textColor = light ? '#0F172A' : '#FFFFFF';

  return (
    <div
      className={containerClassName}
      style={{
        backgroundColor: color,
        color: textColor,
        boxShadow: `0 2px 8px -2px ${color}66`
      }}
    >
      <IconComponent className={className} />
    </div>
  );
}
