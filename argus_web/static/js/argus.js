(function () {
  'use strict';
  var toggle = document.getElementById('sidebar-toggle');
  var sidebar = document.getElementById('argus-sidebar');
  if (!toggle || !sidebar) return;

  toggle.addEventListener('click', function (e) {
    e.stopPropagation();
    sidebar.classList.toggle('open');
  });

  document.addEventListener('click', function (e) {
    if (sidebar.classList.contains('open')
        && !sidebar.contains(e.target)
        && !toggle.contains(e.target)) {
      sidebar.classList.remove('open');
    }
  });
})();
