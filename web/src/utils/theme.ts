// Theme Management for VQ8 Data Profiler
// Implements VisiQuate UI Standards for dark mode

export type Theme = 'light' | 'dark' | 'auto';

const THEME_KEY = 'vq8-theme';

function getSystemTheme(): 'light' | 'dark' {
  return window.matchMedia('(prefers-color-scheme: dark)').matches
    ? 'dark'
    : 'light';
}

export function getStoredTheme(): Theme {
  const stored = localStorage.getItem(THEME_KEY);
  if (stored === 'light' || stored === 'dark' || stored === 'auto') {
    return stored;
  }
  return 'dark'; // Default to dark mode per VisiQuate standards
}

export function setStoredTheme(theme: Theme): void {
  localStorage.setItem(THEME_KEY, theme);
}

export function applyTheme(theme: Theme): void {
  const root = document.documentElement;

  if (theme === 'auto') {
    const systemTheme = getSystemTheme();
    root.classList.toggle('dark', systemTheme === 'dark');
  } else {
    root.classList.toggle('dark', theme === 'dark');
  }
}

export function initializeTheme(): Theme {
  const theme = getStoredTheme();
  applyTheme(theme);

  // Listen for system theme changes when in auto mode
  const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
  mediaQuery.addEventListener('change', () => {
    const currentTheme = getStoredTheme();
    if (currentTheme === 'auto') {
      applyTheme('auto');
    }
  });

  return theme;
}
