try {
  const theme = localStorage.getItem('adrobot.theme');
  if (theme === 'light' || theme === 'dark') document.documentElement.dataset.theme = theme;
} catch {
  // The page follows the system theme when storage is unavailable.
}
