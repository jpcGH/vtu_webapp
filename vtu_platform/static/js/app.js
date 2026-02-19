(function () {
  var sidebar = document.getElementById('app-sidebar');
  var toggle = document.querySelector('[data-sidebar-toggle]');

  if (toggle && sidebar) {
    toggle.addEventListener('click', function () {
      sidebar.classList.toggle('is-open');
    });
  }

  var toasts = document.querySelectorAll('[data-toast]');
  toasts.forEach(function (toast) {
    var closeBtn = toast.querySelector('[data-toast-close]');
    var dismiss = function () {
      toast.classList.add('is-leaving');
      window.setTimeout(function () {
        toast.remove();
      }, 260);
    };

    if (closeBtn) {
      closeBtn.addEventListener('click', dismiss);
    }

    window.setTimeout(dismiss, 4200);
  });

  var copyButtons = document.querySelectorAll('[data-copy-value]');
  copyButtons.forEach(function (button) {
    button.addEventListener('click', function () {
      var value = button.getAttribute('data-copy-value') || '';
      if (!value) {
        return;
      }

      navigator.clipboard.writeText(value).then(function () {
        var original = button.textContent;
        button.textContent = 'Copied';
        button.classList.add('is-copied');
        window.setTimeout(function () {
          button.textContent = original;
          button.classList.remove('is-copied');
        }, 1500);
      });
    });
  });
})();
