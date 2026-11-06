# Image prompts

Prompts for the logo and README illustrations. They are written for general text-to-image models (GPT Image, Midjourney, Ideogram, Firefly, Figma AI, …).

## How to use

1. Paste the **shared style** block in front of each prompt, so every image looks like part of one set.
2. Generate at the size listed, then save it to `docs/images/<file>`.
3. Uncomment the matching `<!-- … -->` placeholder in `README.md`, or add the `<img>` tag shown.

**Tips**
- Image models are bad at small text. Keep words out of the image and put labels in the README instead. Only the logo wordmark and the banner title use text; Ideogram or GPT Image handle text best. You can also add the text afterwards in Figma.
- GitHub shows the README on both light and dark backgrounds. Ask for a **transparent background**, or generate a light and a dark version and use `<picture>` (example at the end).
- Don't use real brand marks (Anthropic/Claude, GitHub, Django, Next.js logos). They are trademarks, and they would make the project look official.

## Shared style

```text
Style: clean flat vector illustration, soft rounded geometric shapes, consistent 2px rounded strokes,
generous whitespace, subtle soft shadows, no gradients except very soft ones, no photorealism, no 3D render.
Palette: deep teal #0F766E (primary), warm amber #F59E0B (accent), slate #1E293B (lines and text),
off-white #F8FAFC (surfaces), mint #10B981 (success), coral #EF4444 (error), cool grey #94A3B8 (unknown).
No real company logos or brand marks. No text unless the prompt asks for it.
```

---

## 0. Logo

**File:** `docs/images/logo.png` (plus `logo-mark.svg` if you vectorise it) · **Size:** 1024×1024, transparent background
**README:** `<img src="docs/images/logo.png" width="96" alt="dev-skills logo">` above the title
**Plugin icon:** save a copy as `plugins/dev-workflow/.claude-plugin/icon.png`. It must be a square PNG, 512–2048 px per side and under 2 MB; `claude plugin validate` looks for it there. If the plugin is ever submitted to the plugin directory, the icon is captured once at the first submission, so finalise it before then.

**Primary concept: "toolbox of skills"**

```text
A minimal app-icon style logo mark for a developer tool called "dev-skills".
A rounded-square toolbox seen from the front, lid slightly open, with three small rounded
tiles rising out of it like cards: one teal, one amber, one mint. The tiles represent
modular skills or plugins. The toolbox handle forms a gentle arc above.
Bold simple silhouette that stays readable at 32×32 px (favicon) and at 512×512 px.
Solid flat shapes, at most 3–4 colors from the palette, centered composition,
even padding, transparent background. No text, no letters, no tiny details.
```

**Variant B: "plug piece"**

```text
A minimal logo mark: a rounded puzzle piece whose tab is shaped like a two-pin electrical plug,
symbolising a plugin that snaps into place. Teal body, amber plug pins, a small mint spark
at the connection point. Flat geometric shapes, thick confident outlines, works as a favicon,
centered on a transparent background, no text.
```

**Variant C: "check + wrench monogram"**

```text
A minimal monogram logo mark combining a wrench and a checkmark: the wrench's handle sweeps
into the long stroke of a checkmark, suggesting "tools that verify". Teal wrench, mint check,
one small amber dot as an accent. Flat vector, balanced negative space, readable at 32 px,
transparent background, no text.
```

**Wordmark lockup** (optional; best made in Figma from the chosen mark)

```text
Horizontal logo lockup: the chosen icon on the left, the wordmark "dev-skills" on the right
in a lowercase geometric sans-serif (similar to Inter or Manrope, semibold), slate #1E293B,
the hyphen in amber #F59E0B. Icon height equals the wordmark cap height × 1.6.
Transparent background, generous clear space, 1600×480.
```

---

## 1. Hero banner (GitHub social preview)

**File:** `docs/images/banner.png` (README header) and `docs/images/social-preview.png` (1280×640, under 1 MB) · **Size:** 2:1
**Use:** the README header, and Settings → General → Social preview on GitHub. GitHub rejects files over 1 MB, so upload the resized `social-preview.png`, not the full-size banner.

```text
A wide hero banner for a developer tools project. On the left, a friendly open toolbox with
small floating modular tiles (skills) drifting out of it toward the right. On the right,
a clean code-editor window with a short status checklist made of colored dots
(mint, amber, coral, grey), with no readable code. Soft off-white background with a faint
dotted grid. Leave a clear empty area at the top-left for a title.
Optional title text in that area: "dev-skills" in a bold geometric sans-serif, slate color,
with the subtitle "Reusable skills for Claude Code" smaller beneath it.
16:8 aspect ratio, 1280×640.
```

---

## 2. Workflow: six steps

**File:** `docs/images/workflow.png` · **Size:** 1600×900 (16:9)
**README:** under "### Workflow", with the Mermaid diagram kept as the accessible, editable version

```text
A horizontal step-by-step process illustration with six evenly spaced stations connected by
a single flowing teal path with small arrowheads, read left to right:
1) a speech bubble with a question mark (a user asks a question),
2) a split signpost with two arms (choosing scope: one topic or everything),
3) a magnifying glass sweeping over a stack of file and folder icons (scanning the repository),
4) an open document with an eye icon and a small checkmark (verifying the real files),
5) a report card with four status dots: mint, amber, coral, grey (the report),
6) a hand offering a wrench, held back politely (offering fixes without applying them).
Each station sits on a soft rounded off-white card with a small teal circle containing
only the number 1–6. A thin dashed side-branch from station 3 leads to a small plain
magnifier icon (fallback search). No other text. Flat vector, airy, balanced spacing.
```

---

## 3. Status legend

**File:** `docs/images/status-legend.png` · **Size:** 1200×400
**README:** next to "Status legend" in Outputs

```text
Four large rounded badges in a row, each a soft card with one bold icon:
a mint circle with a white checkmark (verified and in use),
an amber circle filled halfway (partial),
a coral circle with a white X (missing),
a cool-grey circle with a white question mark (can't be verified from code).
A tiny stethoscope wraps around the left edge of the first card, hinting at a "health check".
Flat vector, equal spacing, transparent background, no text.
```

---

## 4. With the skill vs without

**File:** `docs/images/comparison.png` · **Size:** 1600×800
**README:** under "### With the skill vs without"

```text
A split-scene illustration with a thin vertical divider. Both halves show the same small
friendly robot explorer reaching the same goal: a flag on top of a repository-shaped
building of stacked folders.
Left half ("without"): the robot wanders a winding path with many footprints and
several small magnifying-glass stops, and arrives a little tired.
Right half ("with skill"): the robot holds a simple map (a checklist scroll) and takes
a short, direct path with few footprints, arriving relaxed.
Both flags are the same size and color, to show that both are correct; only the journey
differs. Flat vector, gentle humor, no text.
```

---

## 5. Architecture: marketplace → plugin → skill

**File:** `docs/images/architecture.png` · **Size:** 1400×700
**README:** under "What's inside"

```text
A nested-boxes diagram drawn as friendly objects: a wide market stall or shelf (the
marketplace) holding several labelled-looking boxes with blank labels (plugins). One box
is open and shows a few tools inside it, a magnifying glass, a wrench and a checklist
card (skills). Thin teal leader lines connect the three levels from top to bottom.
Flat vector, isometric-lite perspective, soft shadows, transparent background, no text.
```

---

## Light and dark versions in the README

```html
<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/images/workflow-dark.png">
  <img src="docs/images/workflow.png" alt="Six-step workflow: ask, scope, scan, verify, report, offer fixes" width="100%">
</picture>
```

For the dark version, add this to the shared style: `Dark mode: background #0F172A, lines #E2E8F0, keep accent colors.`
