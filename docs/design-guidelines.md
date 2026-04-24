# Design Guidelines - Con Bo Cuoi

## Design Philosophy

Con Bo Cuoi uses a dark glass UI system with a stricter operations-facing tone.

- Clarity: every control should explain itself fast
- Hierarchy: first fold must surface what needs attention now
- Consistency: shared tokens and shared factories win over local styling
- Accessibility: contrast and touch targets are non-negotiable
- Responsiveness: desktop shell and mobile shell should feel like the same product

---

## Operations-Professional Direction

For `expert` and `admin` screens, the visual tone is intentionally stricter:

- quieter background treatment
- stronger contrast and denser hierarchy
- action blocks before decorative content
- glass surfaces used as structure, not ornament
- bottom sheets preferred over modal-heavy branching on mobile

Apply this tone to:

- expert dashboard, consulting, raw review, utilities, settings
- admin dashboard, accounts, models, training, analytics

Do not reintroduce playful hero cards or mascot-heavy emphasis into those screens.

---

## Color System

### Primary Palette

These values are the current runtime source of truth from `webapp_system/src/ui/theme_tokens.py`.

| Name | Hex | Usage | Constant |
|------|-----|-------|----------|
| Primary | `#4FC38A` | main CTA, active emphasis, positive state | `PRIMARY` |
| Secondary | `#6FB7FF` | informational state, secondary emphasis | `SECONDARY` |
| Warning | `#E7B754` | caution, pending, review needed | `WARNING` |
| Danger | `#FF8B8B` | critical status and destructive signaling | `DANGER` |
| Success | `#73D79A` | success-only messaging and confirmations | `SUCCESS` |
| Neutral | `#AAB7C4` | low-emphasis status, muted indicators | `NEUTRAL` |
| Text Dark | `#08141B` | dark text on light surfaces | `TEXT_DARK` |

### Button Palette

These are internal button tokens used by `button_style()`.

| Name | Hex | Usage |
|------|-----|-------|
| Near Black | `#1B2730` | secondary button background, dark surface text |
| Soft Green Hover | `#3FA877` | primary hover state |
| Deep Green Hover | `#2D875D` | pressed/deeper success emphasis |
| Surface Light | `#E8EDF1` | light utility button background |
| Error | `#C84833` | destructive button background |
| Error Dark | `#AC3623` | destructive hover state |

### Neutral Colors

| Value | Usage |
|-------|-------|
| `ft.Colors.WHITE` | text on dark surfaces |
| `ft.Colors.BLACK` | overlays, shadows, low-level borders |
| `ft.Colors.WHITE24/38/54/70` | low-emphasis text, hints, dividers |

---

## Surface Tokens

### Glass Surface

```python
GLASS_BG = ft.Colors.with_opacity(0.74, "#182833")
GLASS_BORDER = ft.Colors.with_opacity(0.14, "#F4F7FA")
GLASS_SHADOW = ft.BoxShadow(
    blur_radius=34,
    color=ft.Colors.with_opacity(0.30, ft.Colors.BLACK),
    offset=ft.Offset(0, 18),
)
```

This is no longer a white frosted card system. The current product ships with dark teal glass panels.

### Background Treatment

App shells and auth screens share the same layered background approach:

- base fill: `#0E171D`
- background image: `backround.png` with opacity around `0.22` to `0.24`
- primary diagonal gradient: `#112028D8 -> #18303CD2 -> #214A55CC`
- horizontal dark overlay: `#091117D8 -> #091117B8 -> #09111742`
- radial cyan accent: `#83D9FF24`
- radial green accent: `#6FD59D18`
- final vertical depth overlay: `#0A131740 -> #0A131714 -> #0A131788`

Design intent:

- dark-first shell
- controlled atmospheric depth
- enough texture to avoid flatness
- enough restraint to keep dashboards readable

### Auth/Input Surface

Auth fields and inline fields should stay consistent with the shell:

- field background: `ft.Colors.with_opacity(0.14, "#D9E5ED")`
- field border: `ft.Colors.with_opacity(0.26, "#D9E5ED")`
- focused border: `PRIMARY`
- auth/form card background: same dark glass token family as runtime shell

---

## Typography

### Font Families

- Primary: system sans stack
- Monospace: system monospace for code-like or dense data contexts

### Font Sizes and Weights

| Context | Size | Weight | Usage |
|---------|------|--------|-------|
| Page Title | `24-28` | `W_700` | screen headers and hero metrics |
| Section Title | `17` | `W_700` | card/section headers |
| Body | `13-14` | `W_400` | main content and field text |
| Caption | `10-12` | `W_400` | supporting text, timestamps, helper copy |
| Button | `14` | `W_500` | button labels |
| Badge | `11` | `W_600` | status badges and chips |

### Flet Weight Constants

```python
ft.FontWeight.W_400
ft.FontWeight.W_500
ft.FontWeight.W_600
ft.FontWeight.W_700
```

Do not use string weights or raw numeric literals.

---

## Spacing System

### Base Unit

The design system still follows a 4px rhythm.

| Multiplier | Pixels | Usage |
|-----------|--------|-------|
| 1x | `4px` | tight spacing inside compact controls |
| 2x | `8px` | standard control spacing |
| 3x | `12px` | compact section padding |
| 4x | `16px` | standard section spacing |
| 5x | `20px` | shell/card internal padding on dense views |
| 6x | `24px` | default glass container padding |
| 7x | `28px` | larger shell radii and screen spacing |

Use Flet padding helpers instead of scattered numeric values.

---

## Button Styles

All shared buttons should come from `button_style()`.

### Primary Button

```python
button_style("primary")
```

- background: `PRIMARY` (`#4FC38A`)
- text: white
- hover: `#3FA877`
- border: same as background
- role: main submit/save/confirm action

### Secondary Button

```python
button_style("secondary")
```

- background: `#1B2730`
- text: white
- hover: `#22323D`
- role: strong secondary action on dark shells

### Surface Button

```python
button_style("surface")
```

- background: `#E8EDF1`
- text: `#1B2730`
- hover: `12%` black overlay
- border: subtle dark border
- role: utility action, filters, inline tools

### Warning Button

```python
button_style("warning")
```

- background: `WARNING` (`#E7B754`)
- text: `TEXT_DARK`
- hover: same tone
- role: caution or irreversible-but-not-destructive action

### Danger Button

```python
button_style("danger")
```

- background: `#C84833`
- text: white
- hover: `#AC3623`
- role: destructive actions

### Size Guidance

| Size | Height | Usage |
|------|--------|-------|
| Large | `48px` | primary CTAs and form submits |
| Medium | `40px` | default action button |
| Small | `32px` | inline or toolbar action |
| Icon | `40px` square | icon-only utility actions |

---

## Component Patterns

### Glass Container

Use `glass_container()` for shared panel styling.

```python
glass_container(
    content=ft.Column(controls=[...]),
    padding=24,
    radius=28,
)
```

Runtime defaults:

- dark glass background
- subtle cool border
- black shadow with deeper blur than the original v1 doc
- rounded corners usually `26-28`

### Status Badge

Use `status_badge(label, kind)`.

Current badge treatment:

- padding: `10px horizontal`, `4px vertical`
- background opacity: `0.28`
- border opacity: `0.62`
- text color: white for most kinds
- warning text color: `#1A1A1A`

Kinds:

- `primary`
- `secondary`
- `warning`
- `danger`
- `success`
- `neutral`

### Metric Card

Use `metric_card()` for top-level KPI summaries.

Structure:

- small muted title
- compact icon accent on the right
- large numeric or headline value
- enclosed in a glass container

### Section Title and Page Header

Use:

- `section_title()` for local grouped content
- `page_header()` for screen-level headers with optional actions

### Empty State

Use `empty_state()` when no data exists.

Current pattern:

- centered inbox icon
- low-emphasis copy
- no decorative filler

### Inputs

Use:

- `inline_field()` inside runtime screens
- `auth_text_field()` and `auth_dropdown()` inside auth flows

Do not introduce separate field styling unless it becomes a shared token.

---

## Layout Patterns

### Main Shell

Use `build_role_shell()` for user, expert, and admin runtime screens.

#### Desktop

- top bar uses dark glass strip
- left sidebar width: `276px`
- sidebar and content both live inside glass containers
- shell/content card radius: `26`

#### Mobile

- top header uses dark glass strip
- content area gets `bottom=96` padding to clear bottom nav
- main mobile content container radius: `26`
- bottom nav floats above content

### Desktop Sidebar

Desktop sidebar characteristics:

- dark glass surface, not flat black
- selected item uses `PRIMARY` tint with transparent fill
- text remains white
- subtitles use `#D2DEE6`

### Bottom Navigation Bar

Use `build_glass_nav_bar()`.

Current runtime values:

- height: `78px`
- outer radius: `28`
- background: `ft.Colors.with_opacity(0.72, "#182833")`
- border: `1px` at `10% #F4F7FA`
- selected item background: `28% PRIMARY`
- selected item border: `48% PRIMARY`
- icon size: `18`
- label size: `9`
- label max lines: `2`

Do not hide labels on unselected tabs anymore. The current mobile nav keeps all labels visible for readability.

---

## Motion and Interaction

Use motion sparingly.

- button hover: around `200ms`
- nav hover/selection: around `200ms`
- shell transitions should support readability first

Do not add ornamental animation to operations-heavy screens.

---

## Accessibility

### Core Rules

- maintain WCAG AA contrast where practical
- keep body text at `>= 13px`
- keep mobile tap targets around `40px+`
- every icon action needs a text label or tooltip
- field labels must stay explicit

### Practical Checks

- white text on dark glass remains the default safe pairing
- warning badges/buttons use dark text for contrast
- focus state should remain visible through `PRIMARY` focused borders
- mobile nav labels stay visible to reduce icon-only ambiguity

---

## Error and Success States

### Error Blocks

Recommended treatment:

- background: danger tint using current `DANGER` family, not the old `#FF7A7A`
- border: stronger danger border than body surface
- action buttons: `surface` or `danger` depending on severity

### Success Blocks

Recommended treatment:

- background: success tint using `SUCCESS` or `PRIMARY`
- border: success tint border
- keep copy concise and next-step oriented

### Toasts

Toasts should stay:

- compact
- high-contrast
- short-lived
- free of verbose explanation

---

## Responsive Breakpoints

Current shell logic effectively treats:

- mobile/tablet shell: `<= 900px`
- desktop shell: `> 900px`

Recommended content behavior:

| Screen Size | Layout | Navigation |
|-------------|--------|------------|
| `< 600px` | single column | bottom nav |
| `600-900px` | compact two-column when content allows | bottom nav |
| `> 900px` | desktop shell | sidebar |

Test at minimum:

- `393x852`
- `600x800`
- `1024x768`
- `1920x1080`

---

## Microcopy

- button labels should be action-first
- placeholders should hint, not replace labels
- errors should name the problem and the next fix
- confirmations should describe the consequence

For admin/expert areas, prefer direct operational phrasing over marketing-style copy.

---

## Localization Notes

Current product language remains Vietnamese UI with some English technical terminology.

- database-linked field names should stay schema-accurate
- display dates in compact Vietnamese-friendly format
- keep operational labels short enough for mobile nav and cards

---

## Theme Architecture

Theme responsibilities are now split across multiple files.

```text
webapp_system/src/ui/
|- theme_tokens.py      # color, button, glass tokens
|- theme_primitives.py  # shared component factories
|- theme_shells.py      # runtime shell/background composition
|- theme_nav.py         # mobile nav and avatar button
|- theme_auth.py        # auth inputs and auth shell
|- theme_tables.py      # table helpers
`- theme.py             # public facade/re-export layer
```

Rule:

- import shared APIs from `ui.theme` in feature screens
- update underlying token/factory modules when changing design system behavior
- do not hardcode local colors in screens when a shared token exists

---

## Common Pitfalls

| Pitfall | Bad | Good |
|---------|-----|------|
| Hardcoded color | `bgcolor="#4CAF50"` | `bgcolor=PRIMARY` |
| Old palette values in docs/code | Airbnb red references | current `theme_tokens.py` values |
| Flat black sidebar | isolated custom panel | shared glass shell |
| Icon-only mobile nav | unlabeled tabs | icon plus visible label |
| Random spacing | mixed pixel values | 4px rhythm |
| Decorative admin cards | mascot-heavy hero blocks | concise operational summaries |

---

## Design Review Checklist

Before shipping a screen:

- [ ] shared tokens/factories used instead of hardcoded palette values
- [ ] spacing follows 4px rhythm
- [ ] mobile and desktop shells both render cleanly
- [ ] contrast remains readable on dark glass
- [ ] empty, loading, success, and error states exist
- [ ] button hierarchy is clear
- [ ] admin/expert screens keep the operations-professional tone
- [ ] bottom nav content still fits within two-line label constraints

---

## Design Resources

- runtime facade: `webapp_system/src/ui/theme.py`
- tokens: `webapp_system/src/ui/theme_tokens.py`
- shells: `webapp_system/src/ui/theme_shells.py`
- auth shell: `webapp_system/src/ui/theme_auth.py`
- nav: `webapp_system/src/ui/theme_nav.py`

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-04-15 | Initial design system draft |
| 1.1 | 2026-04-21 | Synced docs to current runtime palette, dark glass shell, auth surfaces, mobile nav, and split theme architecture |
| 2.0 | TBD | Future mobile redesign if the shell architecture changes materially |
