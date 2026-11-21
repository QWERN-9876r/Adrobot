import { useState } from 'react';
import type { Catalog } from '../api/types';

type Theme = 'system' | 'light' | 'dark';

const themeOptions = {
  system: { next: 'light', label: 'Системная тема', icon: <>
    <rect x="3" y="4" width="18" height="13" rx="2" />
    <path d="M12 17v3m-4 0h8" />
  </> },
  light: { next: 'dark', label: 'Светлая тема', icon: <>
    <circle cx="12" cy="12" r="4" />
    <path d="M12 2v2m0 16v2M2 12h2m16 0h2M5 5l1.5 1.5m11 11L19 19M19 5l-1.5 1.5m-11 11L5 19" />
  </> },
  dark: { next: 'system', label: 'Тёмная тема', icon:
    <path d="M20.8 14.2A9 9 0 0 1 9.8 3.2a9 9 0 1 0 11 11Z" /> },
} as const;

export function AppHeader({ mode }: { mode: Catalog['mode'] | undefined }) {
  const [theme, setTheme] = useState<Theme>(() => {
    const saved = document.documentElement.dataset.theme;
    return saved === 'light' || saved === 'dark' ? saved : 'system';
  });
  const { label, next, icon } = themeOptions[theme];
  const buttonLabel = `${label}. Следующая — ${themeOptions[next].label.toLowerCase()}.`;

  function changeTheme(next: Theme) {
    const root = document.documentElement;
    if (next === 'system') delete root.dataset.theme;
    else root.dataset.theme = next;
    setTheme(next);
    try {
      if (next === 'system') localStorage.removeItem('adrobot.theme');
      else localStorage.setItem('adrobot.theme', next);
    } catch {
      // The current page still applies the chosen theme.
    }
  }

  return <header className="topbar">
    <div className="shell topbar-content">
      <div className="brand">
        <img className="brand-mark" src="/brand/adrobot-icon.png" width={36} height={36} alt="" />
        <span>Adrobot</span>
      </div>
      <div className="topbar-actions">
        {mode && <span className="mode"><span className="mode-dot" />
          {mode === 'demo' ? 'Демо-режим' : 'Подключено к Keitaro'}
        </span>}
        <button type="button" className="theme-toggle" aria-label={buttonLabel} title={buttonLabel}
          onClick={() => changeTheme(next)}>
          <svg viewBox="0 0 24 24" width="19" height="19" fill="none" stroke="currentColor" strokeWidth="1.7"
            strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{icon}</svg>
        </button>
      </div>
    </div>
  </header>;
}
