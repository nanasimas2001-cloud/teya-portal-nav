#!/usr/bin/env python3
"""
Generate a multi-file static site from the single-file v6 prototype (index.html).

Reads index.html once, extracts CSS + JS, parses each variant's sidebar and main
content, and writes one folder per variant containing home/sales/money/
financial-documents/settings HTML pages. Shared styles.css + app.js at root.

Run: python3 generate.py
Idempotent — safe to re-run; overwrites output.
"""
import os
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).parent
SRC = ROOT / "index.v6.html"

VARIANTS = ["A", "A2", "B", "B3", "C", "C2", "C3"]
VARIANT_SLUGS = {v: v.lower() for v in VARIANTS}

PAGES = ["home", "sales", "money", "financial-documents", "settings"]

# Label -> page mapping. Case-insensitive, strip whitespace, match exact or partial.
# Anything not matched here becomes a data-stub link.
LABEL_TO_PAGE = {
    "home": "home",
    "today": "home",
    "sales": "sales",
    "sales & terminals": "sales",
    "money": "money",
    "money overview": "money",
    "financial documents": "financial-documents",
    "settings": "settings",
    "account & security": "settings",
}

VARIANT_TITLES = {
    "A":  "A · App-faithful",
    "A2": "A2 · Strict 4-tab",
    "B":  "B · Back office",
    "B3": "B3 · Role-aware",
    "C":  "C · Jobs-based",
    "C2": "C2 · Verbs in nav",
    "C3": "C3 · Search-first",
}

VARIANT_DESCS = {
    "A":  "Home, Sales, Money, Teya AI. Business admin in a tray. Closest match to mobile app.",
    "A2": "Strict 4-tab parity with the app. Everything else in More.",
    "B":  "Grouped sidebar back office. Financial documents promoted.",
    "B3": "Role-aware variant of B with hybrid Settings. Use the role switcher to compare owner/member/reader.",
    "C":  "Jobs-based groups: Get paid / Money / Run the business / Grow.",
    "C2": "Verbs at group level, nouns on items. Strongest label consistency.",
    "C3": "Icon rail + AI-dominant home. Search-first.",
}


def read_source():
    return SRC.read_text(encoding="utf-8")


def extract_css(src):
    m = re.search(r"<style>(.*?)</style>", src, re.S)
    if not m:
        raise RuntimeError("CSS block not found")
    return m.group(1).strip()


def find_frame(src, variant):
    """Return the raw HTML of the frame div (aside + main)."""
    pattern = rf'<div class="portal-frame[^"]*" id="frame-{variant}">(.*?)</div>\s*\n\s*<!-- ===== FRAME|<div class="portal-frame[^"]*" id="frame-{variant}">(.*?)</div>\s*\n\s*<script>'
    m = re.search(
        rf'<div class="portal-frame[^"]*" id="frame-{variant}">',
        src,
    )
    if not m:
        raise RuntimeError(f"Frame {variant} not found")
    start = m.end()
    # Find matching </div> by balancing. We know the frame contains one aside + one main.
    # Simpler: find the next `<!-- ===== FRAME` or `<script>` marker, then walk back to </div>.
    next_marker = re.search(r"<!-- ===== FRAME|<script>", src[start:])
    if not next_marker:
        raise RuntimeError(f"No marker after frame {variant}")
    end_region = start + next_marker.start()
    # Walk back to the last </div> before the marker.
    close_idx = src.rfind("</div>", start, end_region)
    if close_idx < 0:
        raise RuntimeError(f"No closing </div> for frame {variant}")
    return src[start:close_idx]


def extract_aside_and_main(frame_html):
    """Split frame content into sidebar (<aside>...</aside>) and main (<main>...</main>)."""
    aside_m = re.search(r"<aside\b[^>]*>(.*?)</aside>", frame_html, re.S)
    main_m  = re.search(r"<main\b[^>]*>(.*?)</main>", frame_html, re.S)
    if not aside_m or not main_m:
        raise RuntimeError("aside or main not found in frame")
    # Preserve the attributes on aside and main so we can re-wrap later.
    aside_open = re.search(r"<aside\b[^>]*>", frame_html).group(0)
    main_open  = re.search(r"<main\b[^>]*>", frame_html).group(0)
    return {
        "aside_open": aside_open,
        "aside_inner": aside_m.group(1),
        "main_open": main_open,
        "main_inner": main_m.group(1),
    }


def split_pages_from_main(main_inner):
    """If main_inner contains page-home + page-settings wrappers, extract them.
    Otherwise treat the whole main as the home page content (unwrapped)."""
    # Pattern: match <div class="page-home ..."> ... </div> <div class="page-settings"> ... </div>
    # We need to find the top-level page-home and page-settings divs.
    ph_start = re.search(r'<div class="page-home[^"]*">', main_inner)
    ps_start = re.search(r'<div class="page-settings[^"]*">', main_inner)
    if ph_start and ps_start:
        # find end of page-home by finding the start of page-settings, then walking back to </div>
        ph_content_start = ph_start.end()
        ps_content_start = ps_start.end()
        # end of page-home = last </div> before ps_start.start()
        ph_end = main_inner.rfind("</div>", ph_content_start, ps_start.start())
        # end of page-settings = last </div> in main_inner
        ps_end = main_inner.rfind("</div>")
        return {
            "home": main_inner[ph_content_start:ph_end].strip(),
            "settings": main_inner[ps_content_start:ps_end].strip(),
        }
    # No page wrappers — whole main is home content.
    return {"home": main_inner.strip(), "settings": None}


def label_of_nav_item(html):
    """Extract the text label from a nav-item HTML blob by stripping tags and taking the first meaningful text."""
    # Remove nested <svg>...</svg>
    h = re.sub(r"<svg\b[^>]*>.*?</svg>", "", html, flags=re.S)
    # Remove annot / badge spans
    h = re.sub(r"<span\b[^>]*>.*?</span>", "", h, flags=re.S)
    # Strip remaining tags
    h = re.sub(r"<[^>]+>", "", h)
    return h.strip()


def map_label_to_href(label):
    """Return (href, is_stub) for a given nav label."""
    lbl = label.lower().strip()
    # Exact first
    if lbl in LABEL_TO_PAGE:
        return (f"./{LABEL_TO_PAGE[lbl]}.html", False)
    # Prefix/partial
    for key, page in LABEL_TO_PAGE.items():
        # Match if lbl starts with key or key starts with lbl (handles "Sales & terminals" vs "Sales")
        if lbl.startswith(key) or lbl.startswith(key + " "):
            return (f"./{page}.html", False)
    return ("#", True)


def rewrite_sidebar_links(aside_inner, current_page):
    """Turn <div class="nav-item">...LABEL...</div> into <a class="nav-item" href="...">...LABEL...</a>.
    Also rewrites biz-switcher's onclick and any <div onclick="selectPage('settings')"> handlers.
    Marks the active item by matching href to current_page.
    """
    # First, rewrite biz-switcher: leave onclick as data-action for app.js to pick up.
    aside_inner = re.sub(
        r'<div class="biz-switcher"[^>]*onclick="openBizModal\(\)"',
        '<div class="biz-switcher" data-action="open-biz-modal"',
        aside_inner,
    )

    # Strip active class from all nav-items; we'll re-apply based on current_page match.
    # Rewrite every <div class="nav-item ..."> ... </div> (non-parent, non-More) to <a>.
    def rewrite_nav_item(match):
        full = match.group(0)
        classes = match.group(1) or ""
        attrs = match.group(2) or ""
        body = match.group(3) or ""
        # Extract onclick handler if any (e.g., selectPage('settings'))
        onclick_m = re.search(r'onclick="([^"]+)"', attrs)
        onclick = onclick_m.group(1) if onclick_m else ""
        label = label_of_nav_item(body)
        # Determine href — selectPage('settings') handler wins over label mapping
        if "selectPage('settings')" in onclick:
            href = "./settings.html"
            is_stub = False
        else:
            href, is_stub = map_label_to_href(label)
        # Build class list — drop the original 'active' since we're resetting
        cls = re.sub(r"\bactive\b", "", classes).strip()
        if not is_stub and href == f"./{current_page}.html":
            cls = (cls + " active").strip()
        # Preserve data-roles if present (for B3)
        new_attrs = ""
        m_roles = re.search(r'data-roles="([^"]*)"', full)
        if m_roles:
            new_attrs += f' data-roles="{m_roles.group(1)}"'
        stub_attr = ' data-stub="true"' if is_stub else ""
        return f'<a class="{cls}" href="{href}"{new_attrs}{stub_attr}>{body}</a>'

    # Match top-level nav-items. Pattern: <div class="nav-item[ ...]" [attrs]>inner</div>
    # We need to be careful not to match divs-within-divs. The inner content has no nested <div class="nav-item">.
    aside_inner = re.sub(
        r'<div class="(nav-item[^"]*)"([^>]*)>((?:(?!</div>).)*?)</div>',
        rewrite_nav_item,
        aside_inner,
        flags=re.S,
    )

    return aside_inner


def build_control_bar(variant, current_page, depth_prefix=""):
    """Build the top control bar with variant switcher buttons as anchors.
    depth_prefix is '' (landing) or '../' (inside variant folder).
    """
    buttons = []
    groups = [
        [("A", False), ("A2", True)],
        [("B", False), ("B3", True)],
        [("C", False), ("C2", True), ("C3", True)],
    ]
    for group in groups:
        group_html = '    <div class="control-group">\n'
        for v, is_sub in group:
            active = " active" if v == variant else ""
            sub = " sub" if is_sub else ""
            label = VARIANT_TITLES[v] if is_sub else v
            href = f"{depth_prefix}{VARIANT_SLUGS[v]}/{current_page}.html"
            group_html += (
                f'      <a class="control-btn{sub}{active}" data-opt="{v}" '
                f'data-current-page="{current_page}" '
                f'href="{href}">{label}</a>\n'
            )
        group_html += "    </div>"
        buttons.append(group_html)

    role_group = ""
    if variant == "B3":
        role_group = (
            '    <div class="control-group" id="roleGroup" style="background:#1F1F1F">\n'
            '      <button class="control-btn active" data-role="owner" type="button">Owner</button>\n'
            '      <button class="control-btn" data-role="member" type="button">Member</button>\n'
            '      <button class="control-btn" data-role="reader" type="button">Reader</button>\n'
            "    </div>"
        )

    return f"""<div class="control-bar">
  <h1>Teya portal — nav <span>v6 · multi-file</span></h1>
  <div style="display:flex;gap:8px;flex-wrap:wrap;">
{chr(10).join(buttons)}
  </div>
  <div class="controls-right">
{role_group}
    <button class="toggle-btn" id="annotBtn" type="button">Show data signals</button>
  </div>
</div>

<div class="legend-strip">
  <strong>Annotations on.</strong>
  <span>Purple tags = data signals behind each placement.</span>
</div>
"""


BIZ_MODAL_HTML = '''<div class="biz-modal-backdrop" id="bizModal">
  <div class="biz-modal">
    <div class="biz-modal-close" data-action="close-biz-modal">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 6L6 18M6 6l12 12"/></svg>
    </div>
    <div class="biz-hero">
      <div class="biz-hero-avatar">🧅</div>
      <div class="biz-hero-name">Onion Garden</div>
      <div class="biz-hero-sub">Starter plan · 4 stores</div>
    </div>
    <div class="biz-featured">
      <div class="biz-feature-card">
        <div class="biz-feature-icon plan"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2L2 7l10 5 10-5z"/></svg></div>
        <div class="biz-feature-title">Starter plan</div>
        <div class="biz-feature-sub">Your plan</div>
      </div>
      <div class="biz-feature-card">
        <div class="biz-feature-machine"></div>
        <div class="biz-feature-title">Card machines</div>
        <div class="biz-feature-sub">4 units</div>
      </div>
    </div>
    <div class="biz-menu-group">
      <div class="biz-menu-item"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 7h18l-2 13H5L3 7z"/><path d="M8 7V5a2 2 0 012-2h4a2 2 0 012 2v2"/></svg>Stores <span class="chev">›</span></div>
      <div class="biz-menu-item"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 21h18M3 10l9-7 9 7M5 10v11M19 10v11M9 21V14h6v7"/></svg>Bank accounts <span class="chev">›</span></div>
      <div class="biz-menu-item"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 00-3-3.87"/></svg>Teams and permissions <span class="chev">›</span></div>
      <div class="biz-menu-item"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2"/><path d="M12 3v18M3 12h18"/></svg>Integrations <span class="chev">›</span></div>
      <div class="biz-menu-item"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><path d="M14 2v6h6M16 13H8M16 17H8"/></svg>Financial documents <span class="chev">›</span></div>
    </div>
    <div class="biz-menu-group">
      <a class="biz-menu-item" href="./settings.html"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 00.33 1.82"/></svg>Settings <span class="chev">›</span></a>
      <div class="biz-menu-item"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M9.09 9a3 3 0 015.83 1c0 2-3 3-3 3M12 17h.01"/></svg>Help <span class="chev">›</span></div>
      <div class="biz-menu-item"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4M16 17l5-5-5-5M21 12H9"/></svg>Logout <span class="chev">›</span></div>
    </div>
  </div>
</div>
'''


def stub_main_content(page):
    """Stub body for pages that have no real content yet."""
    labels = {
        "sales": ("Sales", "Sales dashboard placeholder — where Overview, Transactions, and Payment links would live."),
        "money": ("Money", "Money placeholder — Bank account, Settlements, Transfers, Funding would live here."),
        "financial-documents": ("Financial documents", "Statements and invoices placeholder."),
        "settings": ("Settings", "Account settings placeholder."),
    }
    title, sub = labels.get(page, (page.title(), f"{page} placeholder."))
    return f'''<div class="content-header">
  <div><h2 class="content-title">{title}</h2><div class="content-sub">Placeholder — content not yet built</div></div>
  <div class="page-actions"><div class="avatar-sm">NN</div></div>
</div>
<div class="panel" style="margin-top:16px;padding:32px;text-align:center;">
  <div style="font-size:13px;color:var(--teya-ink-3);text-transform:uppercase;letter-spacing:.4px;margin-bottom:6px;">Placeholder</div>
  <div style="font-size:20px;font-weight:500;margin-bottom:8px;">{title}</div>
  <div style="font-size:13px;color:var(--teya-ink-2);max-width:420px;margin:0 auto;">{sub}</div>
</div>
'''


def build_page(variant, page, aside_inner_with_links, main_content, depth_prefix="../"):
    control_bar = build_control_bar(variant, page, depth_prefix=depth_prefix)
    biz_modal = BIZ_MODAL_HTML
    aside_open = '<aside class="sidebar">'
    if variant == "B3":
        # B3 uses id=sidebarB3 for the role filter script
        aside_open = '<aside class="sidebar" id="sidebarB3">'
    main_open = '<main class="main">'
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Teya portal · {VARIANT_TITLES[variant]} · {page}</title>
<link rel="stylesheet" href="{depth_prefix}styles.css">
</head>
<body data-variant="{variant}" data-page="{page}">

{control_bar}
{biz_modal}
<div class="portal-frame active" id="frame-{variant}">
  {aside_open}
{aside_inner_with_links}
  </aside>
  {main_open}
{main_content}
  </main>
</div>

<script src="{depth_prefix}app.js"></script>
</body>
</html>
"""


def build_landing(variant_cards_html):
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Teya portal · nav exploration</title>
<link rel="stylesheet" href="./styles.css">
<style>
  .landing {{ max-width: 980px; margin: 0 auto; padding: 48px 24px; }}
  .landing h1 {{ font-size: 28px; font-weight: 500; margin: 0 0 8px; }}
  .landing .lead {{ font-size: 15px; color: var(--teya-ink-2); margin: 0 0 32px; max-width: 640px; line-height: 1.6; }}
  .variant-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 16px; }}
  .variant-card {{ background: #fff; border: 1px solid var(--teya-border); border-radius: 12px; padding: 20px; text-decoration: none; color: inherit; display: block; transition: border-color 0.15s; }}
  .variant-card:hover {{ border-color: #B8B7AE; }}
  .variant-card h2 {{ font-size: 14px; font-weight: 500; margin: 0 0 4px; color: var(--teya-ink); }}
  .variant-card p {{ font-size: 12px; color: var(--teya-ink-2); margin: 0; line-height: 1.5; }}
  .variant-card .tag {{ display: inline-block; background: var(--teya-yellow); color: var(--teya-black); padding: 2px 8px; border-radius: 3px; font-size: 10px; font-weight: 500; letter-spacing: 0.3px; margin-bottom: 10px; text-transform: uppercase; }}
</style>
</head>
<body class="landing-body" style="background: var(--teya-surface);">
  <div class="landing">
    <h1>Teya portal — nav exploration</h1>
    <p class="lead">Seven navigation structures for the desktop portal, each available as a browsable prototype with home, sales, money, financial documents, and settings pages. Use the top bar to switch variants while browsing; use "Show data signals" to see the reasoning behind each placement.</p>
    <div class="variant-grid">
{variant_cards_html}
    </div>
  </div>
</body>
</html>
"""


APP_JS = """(function() {
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
      var roles = (item.dataset.roles || '').split(/\\s+/);
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
"""


def main():
    src = read_source()
    css = extract_css(src)

    # Write styles.css — prepend a small reset so <a> nav items match <div> styling
    css_prefix = (
        "/* Multi-file additions: reset anchors used as nav items */\n"
        "a { text-decoration: none; color: inherit; }\n"
        ".nav-item, .control-btn, .biz-menu-item, .variant-card { text-decoration: none; color: inherit; }\n\n"
    )
    (ROOT / "styles.css").write_text(css_prefix + css, encoding="utf-8")

    # Write app.js
    (ROOT / "app.js").write_text(APP_JS, encoding="utf-8")

    # Parse each variant's frame
    frames = {}
    for v in VARIANTS:
        frame_html = find_frame(src, v)
        parts = extract_aside_and_main(frame_html)
        pages = split_pages_from_main(parts["main_inner"])
        frames[v] = {
            "aside_inner": parts["aside_inner"],
            "pages": pages,  # {'home': str, 'settings': str | None}
        }

    # Generate each variant folder
    for v in VARIANTS:
        vdir = ROOT / VARIANT_SLUGS[v]
        vdir.mkdir(parents=True, exist_ok=True)
        for page in PAGES:
            # Determine main content
            if page == "home":
                main_content = frames[v]["pages"]["home"]
            elif page == "settings" and frames[v]["pages"]["settings"]:
                main_content = frames[v]["pages"]["settings"]
            else:
                main_content = stub_main_content(page)
            # Rewrite sidebar links for this target page
            aside_inner_links = rewrite_sidebar_links(frames[v]["aside_inner"], page)
            page_html = build_page(v, page, aside_inner_links, main_content, depth_prefix="../")
            (vdir / f"{page}.html").write_text(page_html, encoding="utf-8")

    # Generate landing page
    cards = []
    for v in VARIANTS:
        href = f"./{VARIANT_SLUGS[v]}/home.html"
        desc = VARIANT_DESCS[v]
        tag = VARIANT_TITLES[v].split(" · ")[1] if " · " in VARIANT_TITLES[v] else v
        cards.append(
            f'      <a class="variant-card" href="{href}">'
            f'<span class="tag">{v}</span>'
            f'<h2>{tag}</h2>'
            f'<p>{desc}</p>'
            f'</a>'
        )
    landing_html = build_landing("\n".join(cards))
    (ROOT / "index.html").write_text(landing_html, encoding="utf-8")

    print(f"Generated: styles.css, app.js, index.html, {len(VARIANTS)} variants × {len(PAGES)} pages = {len(VARIANTS)*len(PAGES)} HTML files")


if __name__ == "__main__":
    main()
