/**
 * BMS Header — dropdowns + logout
 */
(function () {
  function closeAll() {
    document.querySelectorAll('[data-dropdown]').forEach(m => m.classList.add('hidden'));
  }

  document.addEventListener('click', (e) => {
    const btn = e.target.closest('[data-dropdown-btn]');
    if (btn) {
      e.stopPropagation();
      const id = btn.getAttribute('data-dropdown-btn');
      const menu = document.querySelector(`[data-dropdown="${id}"]`);
      const wasHidden = menu?.classList.contains('hidden');
      closeAll();
      if (menu && wasHidden) menu.classList.remove('hidden');
      return;
    }

    // Logout
    if (e.target.closest('[data-logout]')) {
      e.preventDefault();
      localStorage.removeItem('bms-auth');
      window.location.href = 'login.html';
      return;
    }

    closeAll();
  });
})();
