# Dev Agent Brief — EarningsAI marketing hero

## 0. Objective

Build the redesigned landing **navigation + hero section** as production React
components in the existing `web` Next.js app. The reference file
`earningsai_hero_mockup.html` is the **pixel-accurate source of truth** — port it
faithfully. This brief carries every token, string, and the full diagram SVG so
the result must not drift from the mockup.

Scope is **nav + hero only**. Do not build other page sections, do not wire any
API, do not touch Clerk auth config.

---

## 1. Stack (use exactly this — do not add libraries)

- Next.js **16.1.6**, App Router, `src/` directory, `@/*` → `./src/*`
- React **19.2.3**, TypeScript **strict**
- Tailwind CSS **v4** (CSS-first `@theme`, via `@tailwindcss/postcss`) — **no `tailwind.config.js`**
- Fonts via **`next/font/google`** — do **not** use `<link>` tags to Google Fonts
- No component library, no CSS-in-JS, no animation library. Plain Tailwind + a
  small amount of CSS for keyframes.

### Hard rules (no shims)
- Create the **real** files listed in §3. Do **not** dump everything into
  `page.tsx`; do **not** create wrapper/placeholder components that re-export a
  TODO.
- Every color, font, and size comes from the tokens in §4 — **no ad-hoc hex
  values** inside components.
- CTAs are real links (`next/link` or `<a href="#">` stubs). Do not fake buttons
  with `<div onClick>`.
- Illustrative data (`AVGO`, `Beat & raise`, `72%`, `ANALYZING`) is passed as
  **props with defaults**, not hardcoded inside JSX.

---

## 2. What changed vs. the old page (context, don't reintroduce)

- Old headline/subhead/CTAs bled off the left edge (no container padding) → all
  content now lives inside a centered `max-w` container with horizontal padding.
- Type scale had no rhythm → fixed scale in §4.
- Old orbit "diagram" was decorative → replaced by a real left-to-right pipeline:
  **Bull / Quant / Bear + Your Research → Debate → Consensus (AI agent) → Verdict.**
- Old had two mismatched "start" CTAs → **one** primary action, and the nav CTA
  uses the **same label** as the hero primary CTA.

---

## 3. File plan (create exactly these)

```
src/lib/fonts.ts                          # next/font definitions
src/app/layout.tsx                        # apply font CSS variables to <html>  (edit if exists)
src/app/globals.css                       # Tailwind v4 @theme tokens + keyframes (edit if exists)
src/app/page.tsx                          # composes <SiteNav/> + <Hero/>        (edit if exists)
src/components/marketing/SiteNav.tsx
src/components/marketing/Hero.tsx
src/components/marketing/PipelineDiagram.tsx
src/components/marketing/pipeline.types.ts # PipelineData type + default value
```

All are Server Components except where interactivity requires `"use client"`.
Nothing here needs client JS — the diagram animation is pure CSS — so **do not add
`"use client"`** unless a lint/build error forces it.

---

## 4. Design tokens (authoritative)

### 4.1 Color — put in `globals.css` `@theme`

| Token | Hex | Use |
|---|---|---|
| `--color-bg` | `#070A12` | page background base |
| `--color-panel` | `#0E1524` | chips, cards |
| `--color-panel-line` | `#1B2436` | borders, hairlines |
| `--color-ink` | `#F5F8FF` | primary text |
| `--color-ink-mute` | `#9AA7BE` | body / subhead |
| `--color-ink-dim` | `#5E6B84` | captions, mono labels |
| `--color-teal` | `#2DD4BF` | brand / CTA / Consensus |
| `--color-teal-deep` | `#12A594` | CTA gradient end |
| `--color-bull` | `#34D399` | Bull agent |
| `--color-bear` | `#F87171` | Bear agent |
| `--color-quant` | `#60A5FA` | Quant agent |
| `--color-human` | `#FBBF24` | Your Research (optional/human) |

Background is layered radial glows over `--color-bg`:
```css
background:
  radial-gradient(1100px 600px at 78% 34%, rgba(45,212,191,.10), transparent 60%),
  radial-gradient(900px 500px at 12% 8%, rgba(96,165,250,.06), transparent 55%),
  var(--color-bg);
```

### 4.2 Type — three roles via `next/font`

| Role | Family | Token | Where |
|---|---|---|---|
| Display | Space Grotesk (400–700) | `--font-display` | H1, node labels, brand, buttons |
| Body | Inter (400/500/600) | `--font-body` | subhead, nav links (default `<body>`) |
| Mono | Space Mono (400/700) | `--font-mono` | eyebrow, data labels, proof line, diagram tags |

Type scale (don't deviate):
- **H1**: `font-display`, weight 600, `clamp(2.4rem, 4.4vw, 3.7rem)`, line-height 1.04, letter-spacing `-0.025em`. White→`#B9C4DA` vertical gradient text clip; "debate." word is a teal gradient clip.
- **Subhead**: 17.5px, line-height 1.62, `--color-ink-mute`, `max-width: 46ch`. Bold spans use `--color-ink`.
- **Eyebrow / proof / diagram tags**: `font-mono`, 11–12.5px, letter-spacing `0.14em`, uppercase where shown.
- **Nav links**: 14.5px, `--color-ink-mute` → `--color-ink` on hover.

### 4.3 Layout
- Container `max-width: 1240px`, centered, `padding-inline: 40px` (24px on mobile).
- Hero grid: `grid-template-columns: minmax(0,0.86fr) minmax(0,1.14fr)`, gap 56px, vertical align center, padding `56px 40px 90px`.
- Radius: chips/buttons 12px, diagram panel 20px.

### 4.4 Motion (CSS keyframes in `globals.css`)
- `dash`: `stroke-dashoffset` 0 → −22, 1.1s linear infinite (flow-line marching ants).
- `pulse`: opacity .55↔1, 3s ease-in-out infinite (Consensus ring).
- `blink`: opacity 1↔.35, 2.2s ease-in-out infinite (eyebrow + status dots).
- **Wrap all three in `@media (prefers-reduced-motion: reduce) { animation: none }`.**

### 4.5 Fonts setup (`src/lib/fonts.ts`)
```ts
import { Space_Grotesk, Inter, Space_Mono } from "next/font/google";
export const display = Space_Grotesk({ subsets: ["latin"], variable: "--font-space-grotesk", weight: ["400","500","600","700"] });
export const body    = Inter({ subsets: ["latin"], variable: "--font-inter", display: "swap" });
export const mono    = Space_Mono({ subsets: ["latin"], variable: "--font-space-mono", weight: ["400","700"] });
```
In `layout.tsx` add all three `.variable` classes to `<html>`. In `globals.css` `@theme`, map:
```css
--font-display: var(--font-space-grotesk);
--font-body: var(--font-inter);
--font-mono: var(--font-space-mono);
```
Set `body { font-family: var(--font-body); }`. Then use `font-display` / `font-mono`
utilities in components.

---

## 5. Component specs

### 5.1 `SiteNav.tsx`
- Left: brand — a 30px teal-gradient rounded square logo (inline SVG, the stacked-diamond mark from the mockup) + `EarningsAI` in `font-display` 700/19px.
- Center: links (`font-body`, 14.5px): **How it works · Live · Predictions · Leaderboard · API**. Hidden below 940px.
- Right: one CTA pill **"Run a prediction"** — teal→teal-deep gradient, `#04231F` text, radius 10, subtle teal glow shadow, `translateY(-1px)` on hover.
- Nav is inside the same `max-w` container as the hero.

### 5.2 `Hero.tsx`
Left column (copy):
- **Eyebrow** pill: blinking teal dot + `MULTI-AGENT EARNINGS INTELLIGENCE` (mono, uppercase, rounded border, faint teal fill).
- **H1** (two lines): `Earnings predictions,` / `settled by ` + teal-gradient `debate.`
- **Subhead** (verbatim, keep the `<strong>` spans):
  > Bull, Bear, and Quant agents each build a case, then argue it out in a rebuttal round — with **your own research** thrown into the debate. A **Consensus agent** weighs the arguments into one confidence-scored call. And it's not a one-shot verdict: keep questioning the Consensus agent to unpack its reasoning until you trust the decision.
- **CTA row**: primary **"Run a live prediction"** (gradient pill, matches nav) + secondary ghost **"Watch 2-min demo"** with a small ▶ chip. Both keyboard-focusable with visible focus ring.
- **Proof line** (mono, dim): green live dot + `Every call scored on a public Brier leaderboard — no cherry-picking.`

Right column: `<PipelineDiagram />` inside `.diagram-wrap` — bordered panel, faint 34px grid background (`::before` overlay), inner header row: left `PIPELINE · AVGO Q3` / right teal `● ANALYZING`. On mobile the diagram stacks **below** the copy.

### 5.3 `PipelineDiagram.tsx`
- Accepts `data: PipelineData` (see §5.4) with a default. Render the SVG in
  **Appendix A verbatim**, substituting `data.ticker`, `data.verdict`,
  `data.confidence`, `data.status` in the four labeled slots.
- Convert the mockup's `style="stroke:var(--…)"` and CSS classes into Tailwind /
  inline styles using the §4 tokens. Keep the `viewBox="0 0 700 600"` and all path
  `d` values **exactly** — the geometry is tuned.
- Node structure that must be preserved:
  - Three agent chips left: **Bull** (green, `BUYSIDE CASE`), **Quant** (blue, `OPTIONS · MAX PAIN`), **Bear** (red, `SHORT CASE`).
  - **Debate** node center-left (`& REBUTTAL`, `round 1 of 1`).
  - **Your research** amber dashed chip (`OPTIONAL HUMAN INPUT`) → dashed amber line **into the Debate node** (not into Consensus).
  - **Consensus** glowing teal core with the **`● AI AGENT`** badge above it and `CONFIDENCE-WEIGHTED` sublabel.
  - **Verdict** card: `VERDICT · {ticker}`, `{verdict}`, `CONFIDENCE`, `{confidence}`.

### 5.4 `pipeline.types.ts`
```ts
export type PipelineData = {
  ticker: string;
  status: string;      // e.g. "ANALYZING"
  verdict: string;     // e.g. "Beat & raise"
  confidence: string;  // e.g. "72%"
};

export const DEFAULT_PIPELINE: PipelineData = {
  ticker: "AVGO",
  status: "ANALYZING",
  verdict: "Beat & raise",
  confidence: "72%",
};
```

---

## 6. Responsive & accessibility (quality floor)

- Single breakpoint at **940px**: hero collapses to one column, nav center-links
  hidden, container padding drops to 24px, diagram stacks under copy.
- No horizontal scroll and **no text clipping at any width ≥ 320px** (this was the
  original page's core failure — verify the H1 wraps, never overflows).
- Every interactive element has a visible keyboard focus ring (teal, ≥2px).
- `prefers-reduced-motion: reduce` disables all animation (§4.4).
- Color contrast: body/subhead text ≥ 4.5:1 on the dark bg (the `--color-ink-mute`
  value already clears this; don't dim it further).
- Diagram SVG gets `role="img"` and an `aria-label` describing the pipeline, e.g.
  *"Pipeline: Bull, Quant, and Bear agents plus your research feed a debate round, weighed by the Consensus agent into a confidence-scored verdict."*

---

## 7. Verification (must pass before you report done)

Run and paste output:
```bash
npm run build      # zero errors
npm run lint       # zero errors/warnings
```
Content assertions (all must return a match):
```bash
grep -rq "Run a prediction"                     src/components/marketing/SiteNav.tsx
grep -rq "Run a live prediction"                src/components/marketing/Hero.tsx
grep -rq "settled by"                           src/components/marketing/Hero.tsx
grep -rq "keep questioning"                      src/components/marketing/Hero.tsx     # interactive-consensus line present
grep -rq "AI AGENT"                             src/components/marketing/PipelineDiagram.tsx
grep -rq "OPTIONAL HUMAN INPUT"                 src/components/marketing/PipelineDiagram.tsx
grep -rq 'viewBox="0 0 700 600"'                src/components/marketing/PipelineDiagram.tsx
! grep -rq "tailwind.config"                    .                                      # confirm v4 CSS-first, no config file added
```
Manual checks (confirm each):
1. Resize 320px → 1440px: H1 never clips or overflows; layout collapses cleanly at 940px.
2. Nav CTA text === hero primary CTA verb ("Run a…").
3. Your Research dashed amber line terminates at the **Debate** node.
4. Consensus core shows the **AI AGENT** badge and teal glow.
5. Toggle OS "reduce motion" → flow lines and pulse stop animating.
6. Tab through the page → focus ring visible on nav links, both CTAs.

---

## 8. Out of scope (do not do)
- No real prediction API, websockets, or live data.
- No changes to Clerk auth, middleware, or `.env`.
- No additional marketing sections (features, pricing, footer) — nav + hero only.
- Do not restyle global app chrome outside `globals.css` tokens + the two components.

---

## Appendix A — Diagram SVG (source of truth)

Port this verbatim into `PipelineDiagram.tsx`. Replace `var(--x)` with the matching
§4 token, keep every `d`, `cx/cy/r`, and `x/y` value. Substitute the four data slots
(`AVGO`, `ANALYZING`, `Beat & raise`, `72%`) with props.

```html
<svg class="flow" viewBox="0 0 700 600" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <radialGradient id="coreGlow" cx="50%" cy="50%" r="50%">
      <stop offset="0%" stop-color="#2DD4BF" stop-opacity="0.35"/>
      <stop offset="70%" stop-color="#2DD4BF" stop-opacity="0.05"/>
      <stop offset="100%" stop-color="#2DD4BF" stop-opacity="0"/>
    </radialGradient>
  </defs>

  <!-- connectors: agents -> debate -->
  <path class="flowline" style="stroke:var(--bull)"  d="M170,116 C230,116 235,270 292,285"/>
  <path class="flowline" style="stroke:var(--quant)" d="M170,300 C220,300 235,300 292,300"/>
  <path class="flowline" style="stroke:var(--bear)"  d="M170,484 C230,484 235,330 292,315"/>
  <!-- debate -> consensus -->
  <path class="flowline" style="stroke:var(--teal)"  d="M420,300 C470,300 480,270 502,258"/>
  <!-- your research -> debate (optional) -->
  <path class="flowline dashed-opt" style="stroke:var(--human)" d="M368,472 C368,432 356,392 356,350"/>
  <!-- consensus -> verdict -->
  <path class="flowline" style="stroke:var(--teal)"  d="M565,330 C565,370 565,388 565,410"/>

  <!-- AGENT CHIPS -->
  <g class="node">
    <rect x="30" y="82" width="140" height="68" rx="12" fill="var(--panel)" stroke="var(--bull)" stroke-opacity="0.55"/>
    <circle cx="52" cy="106" r="5" fill="var(--bull)"/>
    <text x="68" y="111" class="node-label">Bull</text>
    <text x="46" y="132" class="node-sub">BUYSIDE CASE</text>
  </g>
  <g class="node">
    <rect x="30" y="266" width="140" height="68" rx="12" fill="var(--panel)" stroke="var(--quant)" stroke-opacity="0.55"/>
    <circle cx="52" cy="290" r="5" fill="var(--quant)"/>
    <text x="68" y="295" class="node-label">Quant</text>
    <text x="46" y="316" class="node-sub">OPTIONS · MAX PAIN</text>
  </g>
  <g class="node">
    <rect x="30" y="450" width="140" height="68" rx="12" fill="var(--panel)" stroke="var(--bear)" stroke-opacity="0.55"/>
    <circle cx="52" cy="474" r="5" fill="var(--bear)"/>
    <text x="68" y="479" class="node-label">Bear</text>
    <text x="46" y="500" class="node-sub">SHORT CASE</text>
  </g>

  <!-- DEBATE -->
  <g class="node">
    <rect x="292" y="252" width="128" height="96" rx="12" fill="var(--panel)" stroke="var(--panel-line)"/>
    <text x="356" y="292" text-anchor="middle" class="node-label">Debate</text>
    <text x="356" y="312" text-anchor="middle" class="node-sub">&amp; REBUTTAL</text>
    <text x="356" y="330" text-anchor="middle" class="node-tag" fill="var(--ink-dim)">round 1 of 1</text>
  </g>

  <!-- CONSENSUS CORE -->
  <circle cx="565" cy="255" r="115" fill="url(#coreGlow)"/>
  <circle class="core-ring" cx="565" cy="255" r="82" fill="none" stroke="var(--teal)" stroke-opacity="0.5" stroke-width="1.3"/>
  <circle cx="565" cy="255" r="66" fill="var(--panel)" stroke="var(--teal)" stroke-opacity="0.8" stroke-width="1.6"/>
  <text x="565" y="250" text-anchor="middle" class="core-title">Consensus</text>
  <text x="565" y="270" text-anchor="middle" class="core-sub">CONFIDENCE-WEIGHTED</text>
  <!-- AI AGENT badge -->
  <rect x="524" y="158" width="82" height="21" rx="10.5" fill="rgba(45,212,191,.12)" stroke="var(--teal)" stroke-opacity="0.7"/>
  <circle cx="540" cy="168.5" r="3.3" fill="var(--teal)"/>
  <text x="550" y="172" class="node-tag" fill="var(--teal)">AI AGENT</text>

  <!-- YOUR RESEARCH (optional / human) -->
  <g class="node">
    <rect x="300" y="472" width="140" height="66" rx="12" fill="rgba(251,191,36,.04)" stroke="var(--human)" stroke-opacity="0.6" stroke-dasharray="4 4"/>
    <text x="316" y="500" class="node-label" style="fill:var(--human)">Your research</text>
    <text x="316" y="520" class="node-sub" style="fill:var(--human);opacity:.8">OPTIONAL HUMAN INPUT</text>
  </g>

  <!-- VERDICT CARD -->
  <g class="node">
    <rect x="470" y="410" width="190" height="130" rx="14" fill="var(--panel)" stroke="var(--teal)" stroke-opacity="0.35"/>
    <text x="490" y="440" class="verdict-k">VERDICT · AVGO</text>
    <text x="490" y="470" class="verdict-v">Beat &amp; raise</text>
    <line x1="490" y1="484" x2="640" y2="484" stroke="var(--panel-line)"/>
    <text x="490" y="508" class="verdict-k">CONFIDENCE</text>
    <text x="490" y="530" class="verdict-c">72%</text>
  </g>
</svg>
```

### SVG text-class → token map
| class | font | size | fill |
|---|---|---|---|
| `.node-label` | display 600 | 15 | `--color-ink` |
| `.node-sub` | mono | 9.5 | `--color-ink-dim` |
| `.node-tag` | mono | 9 | inherit (set per-use) |
| `.core-title` | display 700 | 15 | `--color-teal` |
| `.core-sub` | mono | 9 | `--color-ink-mute` |
| `.verdict-k` | mono | 9 | `--color-ink-dim` |
| `.verdict-v` | display 700 | 18 | `--color-ink` |
| `.verdict-c` | display 700 | 22 | `--color-teal` |
| `.flowline` | — | stroke-width 1.6, dasharray `5 6`, `dash` anim | per-line stroke |
| `.flowline.dashed-opt` | — | dasharray `3 5`, opacity .9 | `--color-human` |
