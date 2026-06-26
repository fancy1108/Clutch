import React from 'react';
import { useLanguage } from './LanguageContext';
import { LegacyIcon } from './ui/LegacyIcon';

export interface ThemePreset {
  id: string;
  name: string;
  description: string;
  icon: string;
  colors: {
    bg: string;
    surface: string;
    text: string;
    primary: string;
    border: string;
  };
  variables: Record<string, string>;
}

export const THEME_PRESETS: ThemePreset[] = [
  {
    id: 'pristine-light',
    name: 'Pristine Light',
    description: 'Clean Hanken aesthetic with spacious negative spaces and absolute neutral shades.',
    icon: 'light_mode',
    colors: {
      bg: '#ffffff',
      surface: '#f9f9f9',
      text: '#1a1c1c',
      primary: '#000000',
      border: '#e5e7eb',
    },
    variables: {
      '--color-background': '#ffffff',
      '--color-surface': '#f9f9f9',
      '--color-surface-container-low': '#f7f7f7',
      '--color-surface-container': '#f9f9f9',
      '--color-surface-container-high': '#f0f0f0',
      '--color-surface-container-highest': '#e2e2e2',
      '--color-surface-dim': '#f3f4f6',
      '--color-surface-bright': '#ffffff',
      '--color-on-surface': '#1a1c1c',
      '--color-on-surface-variant': '#71717a',
      '--color-on-background': '#1a1c1c',
      '--color-outline': '#e5e7eb',
      '--color-outline-variant': '#e5e7eb',
      '--color-primary': '#000000',
      '--color-on-primary': '#ffffff',
      '--color-secondary': '#5c5f60',
      '--color-on-secondary': '#ffffff',
    }
  },
  {
    id: 'nordic-frost',
    name: 'Nordic Frost',
    description: 'Crisp glacial blues with high-contrast marine components for focused environments.',
    icon: 'ac_unit',
    colors: {
      bg: '#f4f7fa',
      surface: '#eef2f7',
      text: '#1b2533',
      primary: '#2563eb',
      border: '#cbd5e1',
    },
    variables: {
      '--color-background': '#f4f7fa',
      '--color-surface': '#eef2f7',
      '--color-surface-container-low': '#e4ebf3',
      '--color-surface-container': '#eef2f7',
      '--color-surface-container-high': '#dae3ef',
      '--color-surface-container-highest': '#c9d6e7',
      '--color-surface-dim': '#e8eff7',
      '--color-surface-bright': '#f4f7fa',
      '--color-on-surface': '#1b2533',
      '--color-on-surface-variant': '#5a6e85',
      '--color-on-background': '#1b2533',
      '--color-outline': '#cbd5e1',
      '--color-outline-variant': '#cbd5e1',
      '--color-primary': '#2563eb',
      '--color-on-primary': '#ffffff',
      '--color-secondary': '#475569',
      '--color-on-secondary': '#ffffff',
    }
  },
  {
    id: 'amber-warm',
    name: 'Amber Warmth',
    description: 'Cozy academic tones. Reminiscent of fine parchment, sepia bindings, and warm gold.',
    icon: 'coffee',
    colors: {
      bg: '#faf6ee',
      surface: '#f4eedc',
      text: '#3a3328',
      primary: '#845209',
      border: '#d7caa6',
    },
    variables: {
      '--color-background': '#faf6ee',
      '--color-surface': '#f4eedc',
      '--color-surface-container-low': '#ebe4cf',
      '--color-surface-container': '#f4eedc',
      '--color-surface-container-high': '#dfd5b8',
      '--color-surface-container-highest': '#cfc29d',
      '--color-surface-dim': '#f2ebd5',
      '--color-surface-bright': '#faf6ee',
      '--color-on-surface': '#3a3328',
      '--color-on-surface-variant': '#7a6e5a',
      '--color-on-background': '#3a3328',
      '--color-outline': '#d7caa6',
      '--color-outline-variant': '#d7caa6',
      '--color-primary': '#845209',
      '--color-on-primary': '#ffffff',
      '--color-secondary': '#78350f',
      '--color-on-secondary': '#ffffff',
    }
  },
];

interface ThemeManagerProps {
  currentThemeId: string;
  setThemeId: (id: string) => void;
}

export const ThemeManager: React.FC<ThemeManagerProps> = ({
  currentThemeId,
  setThemeId,
}) => {
  const { t } = useLanguage();

  return (
    <div className="flex-1 flex flex-col h-full bg-surface-bright text-on-surface select-none leading-normal">
      {/* Container */}
      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        
        {/* Banner Headers */}
        <div className="flex flex-col gap-1">
          <div className="flex items-center gap-2">
            <LegacyIcon name="palette" className="text-[20px] text-on-surface" />
            <h2 className="text-base font-bold text-on-surface tracking-tight font-sans">{t("Workspace Theme Configurator")}</h2>
          </div>
          <p className="text-xs text-on-surface-variant font-sans leading-relaxed">
            {t("Customize the developer workspace environment with cohesive colors, borders, shadows, and eye-friendly presets.")}
          </p>
        </div>

        {/* Live Theme Preview Banner */}
        <div className="p-4 bg-surface-container border border-outline rounded-xl flex items-center justify-between text-left">
          <div className="space-y-1">
            <span className="text-[9px] font-extrabold text-[#ffffff] bg-primary border border-outline/30 px-2 py-0.5 rounded font-mono tracking-wider uppercase">{t("Active Theme")}</span>
            <h3 className="text-sm font-extrabold text-on-surface">
              {t(THEME_PRESETS.find(t => t.id === currentThemeId)?.name || 'Pristine Light')}
            </h3>
            <p className="text-[11px] text-on-surface-variant font-sans leading-relaxed">
              {t("Updates all buttons, panels, background layout variables, and typography states.")}
            </p>
          </div>
          <LegacyIcon name="palette" className="text-[36px] text-on-surface-variant" />
        </div>

        {/* Theme List Grid */}
        <div className="space-y-3 text-left">
          <span className="text-[10px] font-extrabold text-on-surface-variant uppercase tracking-widest block">{t("Available Preset Themes")}</span>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
            {THEME_PRESETS.map((theme) => {
              const matches = theme.id === currentThemeId;
              return (
                <div
                  key={theme.id}
                  onClick={() => setThemeId(theme.id)}
                  className={`p-4 rounded-xl border transition-all cursor-pointer text-left flex flex-col justify-between h-[160px] ${
                    matches
                      ? 'bg-surface-container border-primary shadow-xs'
                      : 'bg-surface hover:bg-surface-container-high/45 border-outline/60'
                  }`}
                >
                  <div className="space-y-1.5">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <LegacyIcon name={theme.icon} className="text-[16px] text-on-surface" />
                        <h4 className="text-xs font-bold text-on-surface">{t(theme.name)}</h4>
                      </div>
                      
                      {matches && (
                        <span className="text-[8.5px] uppercase font-mono bg-primary text-[#ffffff] px-1.5 py-0.2 rounded font-bold">
                          {t("Active")}
                        </span>
                      )}
                    </div>

                    <p className="text-[11px] text-on-surface-variant leading-relaxed font-sans line-clamp-2">
                      {t(theme.description)}
                    </p>
                  </div>

                  {/* Swatch Previews */}
                  <div className="flex items-center justify-between pt-2 border-t border-outline/40">
                    <div className="flex items-center gap-1.5">
                      <span className="text-[9px] font-mono text-on-surface-variant">{t("Palette:")}</span>
                      <div className="flex -space-x-1.5">
                        <span className="w-5 h-5 rounded-full border border-outline/40" style={{ backgroundColor: theme.colors.bg }} title={t("Background")} />
                        <span className="w-5 h-5 rounded-full border border-outline/40" style={{ backgroundColor: theme.colors.surface }} title={t("Surface")} />
                        <span className="w-5 h-5 rounded-full border border-outline/40" style={{ backgroundColor: theme.colors.text }} title={t("Text color")} />
                        <span className="w-5 h-5 rounded-full border border-outline/40" style={{ backgroundColor: theme.colors.primary }} title={t("Accent primary")} />
                      </div>
                    </div>

                    <span className="text-[10px] font-bold text-on-surface-variant hover:text-on-surface flex items-center gap-0.5 font-sans">
                      {t("Select")}
                      <LegacyIcon name="chevron_right" className="text-[12px]" />
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

      </div>

      {/* Footer bar */}
      <div className="h-10 bg-surface-container border-t border-outline flex items-center justify-between px-6 text-[10px] text-on-surface-variant select-none">
        <div className="flex items-center gap-1 font-mono font-bold uppercase tracking-wide">
          <span>{t("Active Palette Scheme:")}</span>
          <span className="text-on-surface font-extrabold">{currentThemeId.toUpperCase()}</span>
        </div>
        <div className="flex items-center gap-1">
          <span className="h-2 w-2 rounded-full bg-emerald-500 inline-block animate-pulse"></span>
          <span className="font-mono text-on-surface-variant text-[9.5px]">{t("STYLING ENGINE OK")}</span>
        </div>
      </div>
    </div>
  );
};
