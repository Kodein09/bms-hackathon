/**
 * BMS Theme Manager
 * Простой и надёжный переключатель тёмной / светлой темы
 * Сохраняет выбор в localStorage
 */

(function () {
  const STORAGE_KEY = 'bms-theme';
  const ROOT = document.documentElement;

  function getPreferred() {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved === 'light' || saved === 'dark') return saved;
    return window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark';
  }

  function apply(theme) {
    ROOT.setAttribute('data-theme', theme);
    localStorage.setItem(STORAGE_KEY, theme);

    // Обновляем иконку на всех кнопках темы
    document.querySelectorAll('[data-theme-toggle]').forEach(btn => {
      const iconDark = btn.querySelector('[data-icon="dark"]');
      const iconLight = btn.querySelector('[data-icon="light"]');
      if (iconDark && iconLight) {
        if (theme === 'dark') {
          iconDark.classList.add('hidden');
          iconLight.classList.remove('hidden');
        } else {
          iconLight.classList.add('hidden');
          iconDark.classList.remove('hidden');
        }
      }
    });
  }

  function toggle() {
    const current = ROOT.getAttribute('data-theme') || 'dark';
    apply(current === 'dark' ? 'light' : 'dark');
  }

  // Инициализация как можно раньше
  apply(getPreferred());

  // Слушаем клики
  document.addEventListener('click', (e) => {
    if (e.target.closest('[data-theme-toggle]')) {
      toggle();
    }
  });

  // Экспортируем для удобства
  window.BMSTheme = { toggle, apply, get: () => ROOT.getAttribute('data-theme') };
})();