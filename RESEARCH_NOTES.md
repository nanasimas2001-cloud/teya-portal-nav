# Medium merchant research — decision notes

## Variant naming

Original exploration used A / A2 / A3 / B to signal that A2 and A3 were variants of A's thesis. On consolidation (post-C removal), renamed to A / B / C / D for flat peer labelling. Old → new mapping: A→A, A2→B, A3→C, B→D. All references below that pre-date the rename (e.g. "Option B strengthens…" in the decision discussion) refer to the original letters and are kept as audit trail.

## Source

Source: Elisa Volpato, Apr 2026. 18 participants (12 Teya, 6 non-Teya), UK and Portugal. Target: businesses ≥20k/month or 10+ employees.

## Target user personas

The portal is used by up to four distinct roles on a single account. Desktop users skew to personas 3 and 4.

1. **Strategic owner** — expansion, marketing, macro cashflow oversight. Checks balance obsessively on mobile (sometimes 15×/day). Desktop usage is secondary.
2. **Operational manager / "firefighter"** — live sales, staff, customer issues. Ad-hoc, mobile-first.
3. **Finance/admin person** — pays suppliers, reconciles, handles VAT. **Deep-work desktop sessions, often 4+ hours on Monday mornings.** Likely hidden in Amplitude's "(none)" role bucket (16,327 users vs 8,923 Owners).
4. **External accountant** — statements, VAT returns, reconciliation support. Read-only desktop user.

## Key workflows

- **Monday-morning supplier payments.** Medium merchants process 60–200 invoices/week against 20–60 suppliers. Takes 4+ hours weekly. Currently done in Excel + bank transfer, not Teya.
- **Manual over automated.** ~Half of interviewed merchants reject direct debit to preserve cash control, catch invoice errors, negotiate terms, and earn credit-card rewards. Implication: automation must give transparency, approval, discrepancy detection — not just remove the human.
- **Paper still matters.** Merchants print digital invoices for delivery verification, price checks, staff accountability, accountant handover. Desktop should make digital feel as trustworthy as paper (easy to download, print, annotate).
- **VAT ringfencing.** Some merchants manually move VAT amounts to a separate pot every Monday. Strategy is: hold money, pay obligations on time. A "tax pot" feature is implied by behaviour.
- **Reconciliation pain.** One payment often covers 30+ invoices; card transactions lack references; POS systems disagree with bank. Currently done in Excel or external software (Zonesoft/BIP).
- **Accountant handover.** UK merchants share statements/PDFs; Portuguese accountants demand physical paper. An "export pack for my accountant" feature is valuable.

## Feature implications

**Current (built or scoped for June 25):**
- Sales / Transactions / Settlements / Payment links / Subscriptions
- Bank account, Transfers, Funding, Financial documents (statements + Teya fee invoices)
- Teams and permissions, Stores, Integrations
- Teya AI MVP (assume Q&A + insights only, not actions)

**Roadmap (mark visually with ROADMAP badge — not scoped for June 25):**
- Supplier payments / bill pay workflow
- Reconciliation surface
- VAT / tax ringfencing ("tax pot")
- "Share with accountant" / accountant export pack
- AI taking actions (create link, send reminder, pay supplier)

## Nav direction favoured

**Option B (back-office grouped sidebar) strengthens significantly** after this research:
- Medium merchant finance admins are the primary desktop user
- Monday-morning deep work needs density, filterability, bulk actions — not jobs-based friendliness or search-first minimalism
- B's grouping (Operations / Money / Business / Records & insights) maps to how this user thinks

**Option C2 (verbs in nav, nouns on pages) remains viable as secondary** — wins for occasional/owner users who come to desktop less often.

**Options A, A2, C, C3 weaken:**
- A/A2: app parity removes desktop's reason to exist — admin persona needs what mobile can't do
- C: verb sub-tabs ("See what sold") patronising for finance users processing 200 invoices
- C3: hides reconciliation workflow; only works if AI can take actions (not scoped)

**A2 remains only as kill variant** for the decision matrix.

## Home content implications

The Home page (especially for Option B) should surface finance-admin concerns:
- Upcoming payments out (not just money in) — ROADMAP
- VAT quarter progress + ringfencing status — ROADMAP
- Softened settlement frequency messaging (some merchants deliberately prefer slower cadences for interest/VAT timing)
- Expanded business tiles (Plan / Card machines / Stores / Cashback)
- "Pay supplier" as primary hero action — ROADMAP

## Settlement frequency nudge — correction

Previous prototype versions pushed merchants toward Instant/Every Day. Research shows this is wrong for some — merchants deliberately use slower cadences to earn interest elsewhere or time VAT set-asides. Messaging should be neutral/informational, not promotional.

## Project status notes

- Generator (`generate.py`) superseded by direct file editing. Do not regenerate — per-variant files are source of truth.
- ROADMAP visual treatment: yellow-soft fill, green-dark text, yellow border, 9px uppercase. Always visible (unlike data-signal annotations which are toggle-gated).
