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

  // ---------- Role switcher (B3 only, persisted) ----------
  var variant = document.body.getAttribute('data-variant');
  var roleLabels = {
    owner:  { sub: 'Starter · 4 stores · Owner',     context: 'Owner view',  desc: 'Full access · Onion Garden · 4 stores' },
    member: { sub: "Staff · King's Cross",           context: 'Member view', desc: 'Operations only · no finance or admin' },
    reader: { sub: 'Accountant · external',           context: 'Reader view', desc: 'Read-only · finance & statements' }
  };

  function applyRole(role) {
    var sidebar = document.getElementById('sidebarB3');
    if (!sidebar) return;
    var items = sidebar.querySelectorAll('[data-roles]');
    items.forEach(function(item) {
      var roles = (item.dataset.roles || '').split(/\s+/);
      item.classList.toggle('hidden-role', !roles.includes(role));
    });
    document.querySelectorAll('#roleGroup .control-btn').forEach(function(b) {
      b.classList.toggle('active', b.dataset.role === role);
    });

    // Optional dynamic bits — only if these elements exist on the current page
    var bizSub = document.querySelector('.biz-sub[data-role-sub]');
    if (bizSub) bizSub.textContent = roleLabels[role].sub;
    var ctx = document.getElementById('b3RoleContext');
    if (ctx) ctx.textContent = roleLabels[role].context;
    var desc = document.getElementById('b3RoleDesc');
    if (desc) desc.textContent = roleLabels[role].desc;
  }

  if (variant === 'B3') {
    var role = localStorage.getItem('teyaRole') || 'owner';
    applyRole(role);
    document.querySelectorAll('#roleGroup .control-btn').forEach(function(btn) {
      btn.addEventListener('click', function() {
        var r = btn.dataset.role;
        localStorage.setItem('teyaRole', r);
        applyRole(r);
      });
    });
  }

  // ---------- Variant switcher: preserve current page when possible ----------
  // Build-time hrefs already use data-current-page; no further JS needed.
})();
