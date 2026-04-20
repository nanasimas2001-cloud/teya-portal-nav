(function() {
  'use strict';

  // ---------- Annotations (persisted) ----------
  function applyAnnot(on) {
    document.body.classList.toggle('show-annot', on);
    var btn = document.getElementById('annotBtn');
    if (btn) {
      btn.classList.toggle('on', on);
      btn.textContent = on ? 'Hide data signals' : 'Show data signals';
    }
  }
  var annotOn = localStorage.getItem('teyaAnnot') === '1';
  applyAnnot(annotOn);

  var annotBtn = document.getElementById('annotBtn');
  if (annotBtn) {
    annotBtn.addEventListener('click', function() {
      annotOn = !annotOn;
      localStorage.setItem('teyaAnnot', annotOn ? '1' : '0');
      applyAnnot(annotOn);
    });
  }

  // ---------- Biz modal ----------
  var bizModal = document.getElementById('bizModal');
  function openBizModal() { if (bizModal) bizModal.classList.add('open'); }
  function closeBizModal() { if (bizModal) bizModal.classList.remove('open'); }

  document.querySelectorAll('[data-action="open-biz-modal"]').forEach(function(el) {
    el.addEventListener('click', function(e) { e.preventDefault(); openBizModal(); });
  });
  document.querySelectorAll('[data-action="close-biz-modal"]').forEach(function(el) {
    el.addEventListener('click', function(e) { e.preventDefault(); closeBizModal(); });
  });
  if (bizModal) {
    bizModal.addEventListener('click', function(e) {
      if (e.target === bizModal) closeBizModal();
    });
  }

  // ---------- Parent toggle (expandable sidebar sections) ----------
  document.querySelectorAll('[data-action="toggle-children"]').forEach(function(parent) {
    parent.addEventListener('click', function(e) {
      e.preventDefault();
      parent.classList.toggle('open');
      var next = parent.nextElementSibling;
      if (next && next.classList.contains('nav-children')) {
        next.classList.toggle('open');
      }
    });
  });

  // ---------- Stub links ----------
  document.querySelectorAll('a[data-stub="true"]').forEach(function(a) {
    a.addEventListener('click', function(e) {
      e.preventDefault();
      a.style.transition = 'background 0.15s';
      var orig = a.style.background;
      a.style.background = 'var(--teya-yellow-soft)';
      setTimeout(function() { a.style.background = orig; }, 180);
    });
  });

  // ---------- Variant switcher: preserve current page when possible ----------
  // Build-time hrefs already use data-current-page; no further JS needed.
})();
