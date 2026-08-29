# KAVACH — Design System (as implemented)

> "A calm field instrument that tells one honest story."
> Premium agricultural decision-support, not an enterprise admin dashboard.

The decision funnel **Farm State → Problems → Recommendations → Optimized Plan** is the
product. It appears as a vertical numbered spine (desktop), a bottom nav (tablet),
and a progress echo in every page header.

---

## 1. Themes

Two first-class themes. Light is default. Tokens live in `src/styles/tokens.css`
and are surfaced to Tailwind in `tailwind.config.ts`. Brand green is **structure
and action only — never a status encoding**.

### Greenhouse Daylight (light)

| Token | Value |
|---|---|
| `--bg` | `#F6F5EF` |
| `--surface` | `#FFFFFF` |
| `--surface-sunken` | `#EFEEE4` |
| `--border-hairline` | `#E1E0D2` |
| `--ink` | `#16261B` |
| `--body` | `#2B372E` |
| `--muted` | `#5C6B5E` |
| `--brand-900` | `#0F3D2E` |
| `--brand-700` | `#1B7F4C` |
| `--brand-tint` | `#DDEFE2` |
| `--accent-gold` | `#B0791F` |
| `--accent-gold-soft` | `#F0E4CC` |

### Field Console (dark)

| Token | Value |
|---|---|
| `--bg` | `#10140F` |
| `--surface` | `#171C15` |
| `--surface-raised` | `#1E251B` |
| `--border-hairline` | `#2C352A` |
| `--ink` | `#EAF0E4` |
| `--body` | `#C4CFBC` |
| `--muted` | `#8A9681` |
| `--brand-700` | `#3FB56E` |
| `--accent-gold` | `#D8A94A` |

Theme resolution: explicit `data-theme="light|dark"` on `<html>`, else
`prefers-color-scheme`. Toggle cycles light → dark → system, persisted to
`localStorage["kavach-theme"]`.

---

## 2. Typography

| Role | Family | Usage |
|---|---|---|
| Display | **Fraunces** | hero numbers, stage titles, wordmark |
| UI | **Lexend** | headings, labels, nav, buttons |
| Body | **Source Sans 3** | prose, descriptions, verbatim limitations |
| Mono | **IBM Plex Mono** | every measured value / numeric readout |

Scale (1.25): 12 / 14 / 16 base / 20 / 25 / 31 / 39 / 49. Body 16 / 1.5. Never
below 12px. Hero numbers 39–49px Fraunces.

---

## 3. Spacing, layout, surfaces

- 4px base: `4 · 8 · 12 · 16 · 24 · 32 · 48 · 64 · 96`.
- Content column `max-width: 1280px`, centered; card grids 1 / 2 / 3 cols.
- Card: `--surface`, 1px `--border-hairline`, 14px radius, `shadow-card` resting,
  `shadow-lift` on hover (180ms).
- One primary (gold/brand) action per screen; everything else secondary/ghost.
- Every funnel screen ends with a `BridgeCard` to the next step.

### Responsive

| Width | Spine | Nav |
|---|---|---|
| ≥1280 (`xl`) | full left spine + Reference menu | — |
| 1024–1279 (`lg`) | 64px icon spine | — |
| 768–1023 (`md`) | hidden | bottom nav (5 funnel items) + header echo |
| <768 | hidden | bottom nav; context bar compacts; Sheet = bottom sheet |

Touch targets ≥44px. Charts scroll inside `overflow-x:auto`, never squish.

---

## 4. Status visual language — five strictly separate systems

| System | Encoding | Component |
|---|---|---|
| **Evidence** (`insufficient_data` / `no_evidence` / `weak_evidence` / `corroborated_evidence`) | monochrome signal bars 0–3 + chip. **Never hue.** | `EvidenceIndicator` |
| **Severity** (`insufficient_data` / `LOW` / `MODERATE` / `HIGH` / `CRITICAL`) | hue ramp `#5B7CA6` → `#B9812B` → `#C4531F` → `#B3261E`; CRITICAL pulses once (reduced-motion respected) | `SeverityBadge` |
| **Outcome** (`ACTION_RECOMMENDED` / `MONITOR` / `NO_ACTION` / `INSUFFICIENT_SUPPORT` / `CONFLICT`) | pill + icon + priority number | `OutcomeBadge` |
| **Provenance** (`SOURCED` / `PROJECT_DEFINED` / `MODELED`) | dot: ● filled / ◐ half-amber / ○ hollow — on **every** number | `ProvenanceDot`, `ValueWithProvenance` |
| **Feasibility** (`PASS` / `FAIL` / `NOT_EVALUATED`) | green check / red pill / grey dashed dash — three distinct pills | `FeasibilityPill` |

Evidence and severity are always shown under explicit "Evidence" / "Severity"
labels so the two axes can never be conflated.

### Missing data — `UnavailableValue`, three kinds, never `0`/blank/green

| Kind | Source signal | Copy |
|---|---|---|
| `unavailable` | `null` / `cost.status === "UNAVAILABLE"` | "Unavailable" + why-link |
| `unknown` | `plant_population.source === "UNKNOWN"` | "Unknown — set plant population" + CTA |
| `not-evaluated` | `feasibility[].status === "NOT_EVALUATED"` | "Not evaluated" (visually ≠ PASS) |

Eligibility checks are tri-state: `true` → Met, `false` → Not met (orange, not
red), `null` → "Can't evaluate" (grey).

---

## 5. Chart grammar (`VariableTrendChart`, `MiniReferenceChart`, `Sparkline`)

One language everywhere:

- shaded band = deviation between value and ICAR reference
- solid line = **daily mean of raw sensor readings** (real data, labelled as such)
- dashed line = ICAR reference
- series separated by line style + direct labels, never hue alone
- every full chart has keyboard-focusable points and a `<details>` data table
- no gauges, no radial meters, no fake real-time streaming

---

## 6. Prototype presentation (Phase 6)

Phase 6 has no backend route. The Optimized Plan + Farm Setup views always show:

- `PrototypeBanner` — non-dismissible, verbatim limitation copy
- `SampleDataTag` — while `VITE_MOCK_OPTIMIZATION !== "false"`
- savings in **modeled blue** (`--modeled-blue`), never success green
- a provenance dot on every figure
- top-level `limitations[]` rendered verbatim by `LimitationsList`

---

## 7. Accessibility baseline

Radix primitives for dialog / tabs / tooltip / popover (focus trap, Esc, ARIA).
`role="alert"` on errors, `aria-busy` on skeletons, `aria-describedby` on form
errors, visible focus ring (`--focus-ring`), `prefers-reduced-motion` honoured
globally, Lucide SVG icons only (no emoji), 4.5:1 contrast target.

---

## 8. "Why did KAVACH say this?" (`ReasoningPanel`)

One shared component for Problems and Recommendations. Right slide-over (desktop),
bottom sheet (mobile). Fixed sections: Verdict · The signals (Phase 3 + mini
reference chart) · Evidence assessment (status, corroboration notes, severity
factors, abnormal duration + tier) · Decision logic (outcome, eligibility checks,
conflict, priority + reason) · Provenance & limits (verbatim).
