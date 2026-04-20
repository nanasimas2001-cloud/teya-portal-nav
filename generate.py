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

VARIANTS = ["A", "A2", "B", "C", "C2", "C3"]
VARIANT_SLUGS = {v: v.lower() for v in VARIANTS}

PAGES = ["home", "sales", "money", "financial-documents", "settings"]

# Canonical inner SVG markup per nav label. Clean Lucide-style icons.
# Keyed by lowercased label; matched by prefix so "Sales & terminals" uses "sales".
ICONS = {
    "home":                '<path d="M3 12L12 4l9 8v9a1 1 0 01-1 1h-5v-7h-6v7H4a1 1 0 01-1-1v-9z"/>',
    "today":               '<circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/>',
    "sales":               '<rect x="3" y="12" width="4" height="9"/><rect x="10" y="6" width="4" height="15"/><rect x="17" y="9" width="4" height="12"/>',
    "transactions":        '<path d="M4 4h16v4H4zM4 12h16v4H4zM4 20h8"/>',
    "payment links":       '<path d="M10 13a5 5 0 007.54.54l3-3a5 5 0 00-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 00-7.54-.54l-3 3a5 5 0 007.07 7.07l1.71-1.71"/>',
    "subscriptions":       '<rect x="2" y="4" width="20" height="16" rx="2"/><path d="M8 2v4M16 2v4M2 10h20"/>',
    "products and pricing": '<path d="M20.59 13.41l-7.17 7.17a2 2 0 01-2.83 0L2 12V2h10l8.59 8.59a2 2 0 010 2.82z"/><circle cx="7" cy="7" r="1.5" fill="currentColor"/>',
    "money":               '<rect x="2" y="7" width="20" height="14" rx="2"/><path d="M2 11h20M6 15h4"/>',
    "money overview":      '<rect x="2" y="7" width="20" height="14" rx="2"/><path d="M2 11h20M6 15h4"/>',
    "settlements":         '<path d="M12 2v20M17 5H9.5a3.5 3.5 0 000 7h5a3.5 3.5 0 010 7H6"/>',
    "settlements & payouts": '<path d="M12 2v20M17 5H9.5a3.5 3.5 0 000 7h5a3.5 3.5 0 010 7H6"/>',
    "bank accounts":       '<path d="M3 21h18M3 10l9-7 9 7M5 10v11M19 10v11M9 21V14h6v7"/>',
    "transfers":           '<path d="M17 1l4 4-4 4M3 11V9a4 4 0 014-4h14M7 23l-4-4 4-4M21 13v2a4 4 0 01-4 4H3"/>',
    "funding":             '<path d="M12 1v22M17 5H9.5a3.5 3.5 0 000 7h5a3.5 3.5 0 010 7H6"/>',
    "funding & advances":  '<path d="M12 1v22M17 5H9.5a3.5 3.5 0 000 7h5a3.5 3.5 0 010 7H6"/>',
    "teya ai":             '<path d="M12 3l2.39 5.82L20 10l-4.47 3.88L17 20l-5-3-5 3 1.47-6.12L4 10l5.61-1.18z"/>',
    "teams and permissions": '<path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 00-3-3.87"/><path d="M16 3.13a4 4 0 010 7.75"/>',
    "teams & access":      '<path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 00-3-3.87"/>',
    "stores":              '<path d="M3 7h18l-2 13H5L3 7z"/><path d="M8 7V5a2 2 0 012-2h4a2 2 0 012 2v2"/>',
    "stores & terminals":  '<path d="M3 7h18l-2 13H5L3 7z"/><path d="M8 7V5a2 2 0 012-2h4a2 2 0 012 2v2"/>',
    "integrations":        '<rect x="3" y="3" width="18" height="18" rx="2"/><path d="M12 3v18M3 12h18"/>',
    "financial documents": '<path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><path d="M14 2v6h6M9 13h6M9 17h4"/>',
    "reports":             '<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M7 8h10M7 12h10M7 16h6"/>',
    "reports & exports":   '<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M7 8h10M7 12h10M7 16h6"/>',
    "settings":            '<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 11-2.83 2.83l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-4 0v-.09a1.65 1.65 0 00-1-1.51 1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 11-2.83-2.83l.06-.06a1.65 1.65 0 00.33-1.82 1.65 1.65 0 00-1.51-1H3a2 2 0 010-4h.09a1.65 1.65 0 001.51-1 1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 012.83-2.83l.06.06a1.65 1.65 0 001.82.33h0a1.65 1.65 0 001-1.51V3a2 2 0 014 0v.09a1.65 1.65 0 001 1.51h0a1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 2.83l-.06.06a1.65 1.65 0 00-.33 1.82v0a1.65 1.65 0 001.51 1H21a2 2 0 010 4h-.09a1.65 1.65 0 00-1.51 1z"/>',
    "account & security":  '<rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0110 0v4"/>',
    "help":                '<circle cx="12" cy="12" r="10"/><path d="M9.09 9a3 3 0 015.83 1c0 2-3 3-3 3M12 17h.01"/>',
    "help & support":      '<circle cx="12" cy="12" r="10"/><path d="M9.09 9a3 3 0 015.83 1c0 2-3 3-3 3M12 17h.01"/>',
    "more":                '<circle cx="5" cy="12" r="1"/><circle cx="12" cy="12" r="1"/><circle cx="19" cy="12" r="1"/>',
    "business menu":       '<circle cx="5" cy="12" r="1"/><circle cx="12" cy="12" r="1"/><circle cx="19" cy="12" r="1"/>',
    "documents":           '<path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><path d="M14 2v6h6"/>',
}

def icon_for(label):
    lbl = label.lower().strip()
    if lbl in ICONS:
        return ICONS[lbl]
    # prefix match
    for key, svg in ICONS.items():
        if lbl.startswith(key):
            return svg
    return None


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
    "C":  "C · Jobs-based",
    "C2": "C2 · Verbs in nav",
    "C3": "C3 · Search-first",
}

VARIANT_DESCS = {
    "A":  "Home, Sales, Money, Teya AI. Business admin in a tray. Closest match to mobile app.",
    "A2": "Strict 4-tab parity with the app. Everything else in More.",
    "B":  "Grouped sidebar back office. Financial documents promoted.",
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
        label = label_of_nav_item(body)
        # Parents stay as <div> buttons that toggle children (no nav)
        if "parent" in classes:
            cls = re.sub(r"\bactive\b", "", classes).strip()
            new_body = replace_icon_in_body(body, label)
            # Auto-open parent if current page matches one of its children (set below based on context)
            return f'<div class="{cls}" data-action="toggle-children" data-parent-label="{label}">{new_body}</div>'
        # Extract onclick handler if any (e.g., selectPage('settings'))
        onclick_m = re.search(r'onclick="([^"]+)"', attrs)
        onclick = onclick_m.group(1) if onclick_m else ""
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
        new_attrs = ""
        stub_attr = ' data-stub="true"' if is_stub else ""
        # Replace the SVG's inner markup with the canonical icon for this label
        new_body = replace_icon_in_body(body, label)
        return f'<a class="{cls}" href="{href}"{new_attrs}{stub_attr}>{new_body}</a>'

    # Match top-level nav-items. Pattern: <div class="nav-item[ ...]" [attrs]>inner</div>
    # We need to be careful not to match divs-within-divs. The inner content has no nested <div class="nav-item">.
    aside_inner = re.sub(
        r'<div class="(nav-item[^"]*)"([^>]*)>((?:(?!</div>).)*?)</div>',
        rewrite_nav_item,
        aside_inner,
        flags=re.S,
    )

    # Rewrite nav-children blocks: each .nav-child becomes an anchor.
    # Special-case labels: Overview → sales.html (Sales parent); otherwise map_label_to_href.
    def rewrite_children_block(match):
        inner = match.group(1)
        def rewrite_child(cm):
            label = label_of_nav_item(cm.group(1))
            lbl = label.lower().strip()
            if lbl == "overview":
                href, is_stub = "./sales.html", False
            else:
                href, is_stub = map_label_to_href(label)
            active_cls = " active" if not is_stub and href == f"./{current_page}.html" else ""
            stub_attr = ' data-stub="true"' if is_stub else ""
            return f'<a class="nav-child{active_cls}" href="{href}"{stub_attr}>{label}</a>'
        new_inner = re.sub(
            r'<div class="nav-child"[^>]*>(.*?)</div>',
            rewrite_child,
            inner,
            flags=re.S,
        )
        # Mark the block open if it contains an active child (so page loads already expanded)
        open_cls = " open" if 'nav-child active' in new_inner else ""
        return f'<div class="nav-children{open_cls}">{new_inner}</div>'

    aside_inner = re.sub(
        r'<div class="nav-children"[^>]*>((?:\s*<div class="nav-child"[^>]*>.*?</div>)+\s*)</div>',
        rewrite_children_block,
        aside_inner,
        flags=re.S,
    )

    # After children rewrite, auto-open the preceding parent if its children block is open.
    # We do this by walking the HTML and marking any parent whose *immediately following*
    # nav-children block has the 'open' class.
    def open_matching_parent(match):
        parent_html = match.group(1)
        following = match.group(2)
        if 'class="nav-children open"' in following:
            parent_html = parent_html.replace(
                'data-action="toggle-children"',
                'data-action="toggle-children" data-open="true"',
                1,
            )
            parent_html = re.sub(
                r'class="([^"]*parent[^"]*)"',
                lambda m: f'class="{m.group(1)} open"',
                parent_html,
                count=1,
            )
        return parent_html + following

    aside_inner = re.sub(
        r'(<div class="[^"]*parent[^"]*"[^>]*>(?:(?!</div>).)*</div>)(\s*<div class="nav-children[^"]*"[^>]*>(?:(?!</div>).)*</div>)',
        open_matching_parent,
        aside_inner,
        flags=re.S,
    )

    # Also normalize icons inside icon-only nav-items (C3). These are <div class="icon-only nav-item" title="..."> blocks.
    def rewrite_icon_only(match):
        full = match.group(0)
        # Extract title (label source for icon-only items)
        title_m = re.search(r'title="([^"]*)"', full)
        title = title_m.group(1) if title_m else ""
        body = match.group(1)
        # Rewrite onclick=openBizModal to data-action
        full = full.replace('onclick="openBizModal()"', 'data-action="open-biz-modal"')
        # Rewrite onclick=selectPage('settings') to href
        if "selectPage('settings')" in full:
            # Convert the whole div to an anchor pointing at settings
            full = re.sub(
                r'onclick="selectPage\(\'settings\'\)"',
                '',
                full,
            )
        # Replace icon
        new_body = replace_icon_in_body(body, title)
        return full.replace(body, new_body, 1) if new_body != body else full

    # Process already-transformed anchors + remaining icon-only divs for icon replacement.
    # The icon-only items weren't caught by the nav-item regex above because they were re-matched
    # inside that broader replace. Normalize any remaining icon-only <div class="icon-only nav-item">.
    aside_inner = re.sub(
        r'<div class="icon-only nav-item[^"]*"[^>]*>((?:(?!</div>).)*?)</div>',
        rewrite_icon_only,
        aside_inner,
        flags=re.S,
    )

    return aside_inner


def replace_icon_in_body(body, label):
    """Replace the inner markup of the first <svg> in body with the canonical icon for label.
    If no canonical icon is found, leave body unchanged.
    """
    icon = icon_for(label)
    if not icon:
        return body
    return re.sub(
        r'(<svg\b[^>]*>).*?(</svg>)',
        lambda m: f"{m.group(1)}{icon}{m.group(2)}",
        body,
        count=1,
        flags=re.S,
    )


def build_control_bar(variant, current_page, depth_prefix=""):
    """Build the top control bar with variant switcher buttons as anchors.
    depth_prefix is '' (landing) or '../' (inside variant folder).
    """
    buttons = []
    groups = [
        [("A", False), ("A2", True)],
        [("B", False)],
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

    return f"""<div class="control-bar">
  <h1>Teya portal — nav <span>v6 · multi-file</span></h1>
  <div style="display:flex;gap:8px;flex-wrap:wrap;">
{chr(10).join(buttons)}
  </div>
  <div class="controls-right">
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


def build_page(variant, page, aside_inner_with_links, main_content, depth_prefix="../", aside_open=None):
    control_bar = build_control_bar(variant, page, depth_prefix=depth_prefix)
    biz_modal = BIZ_MODAL_HTML
    if aside_open is None:
        aside_open = '<aside class="sidebar">'
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
    <p class="lead">Six navigation structures for the desktop portal, each available as a browsable prototype with home, sales, money, financial documents, and settings pages. Use the top bar to switch variants while browsing; use "Show data signals" to see the reasoning behind each placement.</p>
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
"""


def main():
    src = read_source()
    css = extract_css(src)

    # Write styles.css — prepend a small reset so <a> nav items match <div> styling
    # Also scale up icons in the collapsed-search (C3) icon rail so they don't look like dots.
    css_prefix = (
        "/* Multi-file additions: reset anchors used as nav items */\n"
        "a { text-decoration: none; color: inherit; }\n"
        ".nav-item, .control-btn, .biz-menu-item, .variant-card, .nav-child { text-decoration: none; color: inherit; }\n"
        ".sidebar.collapsed-search .nav-icon { width: 22px; height: 22px; }\n"
        ".sidebar.collapsed-search .icon-only { padding: 12px 0; }\n"
        "/* Expandable parent nav items */\n"
        ".nav-item.parent { cursor: pointer; }\n"
        ".nav-item.parent::after { transition: transform 0.15s ease; }\n"
        ".nav-item.parent.open::after { transform: rotate(90deg); }\n"
        ".nav-children { display: none; padding: 2px 0 6px 28px; }\n"
        ".nav-children.open { display: block; }\n"
        ".nav-child { display: block; padding: 6px 10px; font-size: 12.5px; color: var(--teya-ink-2); border-radius: 4px; cursor: pointer; }\n"
        ".nav-child:hover { background: var(--teya-surface); color: var(--teya-ink); }\n"
        ".nav-child.active { color: var(--teya-ink); font-weight: 500; background: var(--teya-surface); }\n\n"
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
            "aside_open": parts["aside_open"],
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
            page_html = build_page(v, page, aside_inner_links, main_content, depth_prefix="../", aside_open=frames[v]["aside_open"])
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
