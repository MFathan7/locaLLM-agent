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

export function hexToHsl(hexColor: string): [number, number, number] {
  let hex = (hexColor || '').replace('#', '').trim();
  if (hex.length === 3) {
    hex = hex[0] + hex[0] + hex[1] + hex[1] + hex[2] + hex[2];
  }
  if (hex.length !== 6) return [217, 91, 60]; // default vibrant blue
  const r = parseInt(hex.substring(0, 2), 16) / 255;
  const g = parseInt(hex.substring(2, 4), 16) / 255;
  const b = parseInt(hex.substring(4, 6), 16) / 255;

  const max = Math.max(r, g, b);
  const min = Math.min(r, g, b);
  let h = 0;
  let s = 0;
  const l = (max + min) / 2;

  if (max !== min) {
    const d = max - min;
    s = l > 0.5 ? d / (2 - max - min) : d / (max + min);
    switch (max) {
      case r: h = (g - b) / d + (g < b ? 6 : 0); break;
      case g: h = (b - r) / d + 2; break;
      case b: h = (r - g) / d + 4; break;
    }
    h /= 6;
  }
  return [Math.round(h * 360), Math.round(s * 100), Math.round(l * 100)];
}

export function hslToHex(h: number, s: number, l: number): string {
  s /= 100;
  l /= 100;
  const a = s * Math.min(l, 1 - l);
  const f = (n: number) => {
    const k = (n + h / 30) % 12;
    const color = l - a * Math.max(Math.min(k - 3, 9 - k, 1), -1);
    return Math.round(255 * color).toString(16).padStart(2, '0');
  };
  return `#${f(0)}${f(8)}${f(4)}`;
}

/**
 * Auto-cancel/adjust colors that would blend into light or dark mode backgrounds.
 * - In light mode: light/white colors are darkened or mapped to high-contrast slate.
 * - In dark mode: dark/black colors are brightened or mapped to luminous white/slate.
 */
export function getSafeContrastColors(hexColor: string = '#3B82F6'): { light: string; dark: string } {
  try {
    const [h, s, l] = hexToHsl(hexColor);

    // Light mode safe color (against white/near-white backgrounds)
    let safeLight = hexColor;
    if (l > 68) {
      if (s < 18) {
        // Monochrome white / near-white -> auto-cancel to dark slate
        safeLight = '#0F172A';
      } else {
        // High lightness color -> shift down to punchy readable tone
        safeLight = hslToHex(h, Math.max(s, 65), 38);
      }
    }

    // Dark mode safe color (against dark backgrounds)
    let safeDark = hexColor;
    if (l < 42) {
      if (s < 18) {
        // Monochrome black / dark slate -> auto-cancel to crisp bright slate
        safeDark = '#F8FAFC';
      } else {
        // Dark saturated color -> shift up to luminous tone
        safeDark = hslToHex(h, Math.max(s, 70), 65);
      }
    }

    return { light: safeLight, dark: safeDark };
  } catch {
    return { light: '#2563EB', dark: '#60A5FA' };
  }
}

interface WorkspaceIconProps extends React.HTMLAttributes<HTMLSpanElement> {
  icon?: string;
  color?: string;
  className?: string;
  containerClassName?: string;
  withContainer?: boolean;
}

export function WorkspaceIcon({
  icon = 'Folder',
  color = '#3B82F6',
  className = 'w-5 h-5',
  containerClassName,
  withContainer = false,
  style,
  ...rest
}: WorkspaceIconProps) {
  const IconComponent = ICON_MAP[icon] || Folder;
  const { light, dark } = getSafeContrastColors(color);

  // If container explicitly requested (e.g. legacy/special view)
  if (withContainer) {
    const lightBg = isLightColor(color);
    return (
      <div
        className={containerClassName || 'w-7 h-7 rounded-xl flex items-center justify-center shrink-0 shadow-sm'}
        style={{
          backgroundColor: color,
          color: lightBg ? '#0F172A' : '#FFFFFF',
          boxShadow: `0 2px 8px -2px ${color}66`,
          ...style
        }}
      >
        <IconComponent className={className || 'w-4 h-4'} />
      </div>
    );
  }

  // Default: Direct icon coloring without background box, with light/dark contrast protection
  return (
    <span
      className={`inline-flex items-center justify-center shrink-0 transition-colors ${className}`}
      style={{
        color: 'var(--ws-icon-color)',
        // @ts-expect-error CSS variable custom properties
        '--ws-icon-color': light,
        '--ws-icon-color-dark': dark,
        ...style
      }}
      {...rest}
    >
      <IconComponent className="w-full h-full stroke-[2.2] text-[var(--ws-icon-color)] dark:text-[var(--ws-icon-color-dark)]" />
    </span>
  );
}
