# Design Guidelines — Con Bò Cưới

## Design Philosophy

Con Bò Cưới follows a **modern, approachable design system** inspired by Airbnb and Apple:

- **Clarity:** Every element has a purpose; no clutter
- **Hierarchy:** Important actions are prominent; secondary actions are subtle
- **Consistency:** Same patterns used throughout the app
- **Accessibility:** WCAG AA compliant (work in progress)
- **Responsiveness:** Desktop (sidebar) ↔ Mobile (bottom nav) seamlessly

---

## Color System

### Primary Palette

| Name | Hex | Usage | Flet Constant |
|------|-----|-------|---------------|
| **Primary** | #4CAF50 | Success, CTA buttons, positive states | `PRIMARY` |
| **Secondary** | #56CCF2 | Information, secondary actions | `SECONDARY` |
| **Warning** | #F2C94C | Alerts, caution, pending states | `WARNING` |
| **Danger** | #FF7A7A | Errors, critical alerts, delete actions | `DANGER` |
| **Text Dark** | #06131B | Primary text on light backgrounds | `TEXT_DARK` |

### Extended Palette (Airbnb-Inspired Buttons)

| Name | Hex | Usage |
|------|-----|-------|
| **Near Black** | #222222 | Primary button background |
| **Rausch Red** | #ff385c | Secondary button, hover state |
| **Deep Rausch** | #e00b41 | Secondary button pressed state |
| **Surface Light** | #f2f2f2 | Light backgrounds, surface buttons |
| **Error** | #c13515 | Danger button background |

### Neutral Palette

| Name | Flet Constant | Usage |
|------|---------------|-------|
| **White** | `ft.Colors.WHITE` | Backgrounds, text on dark |
| **Black** | `ft.Colors.BLACK` | Text on light |
| **Gray** | `ft.Colors.WHITE24/38/54/70` | Borders, disabled states, hints |

### Glass Effect (Frosted Glass)

```python
GLASS_BG = ft.Colors.with_opacity(0.16, ft.Colors.WHITE)
GLASS_BORDER = ft.Colors.with_opacity(0.18, ft.Colors.WHITE)
GLASS_SHADOW = ft.BoxShadow(
    blur_radius=28,
    color=ft.Colors.BLACK45,
    offset=ft.Offset(0, 14),
)
```

All content panels use `glass_container()` for visual consistency.

---

## Typography

### Font Families
- **Primary:** System default (Segoe UI on Windows, San Francisco on macOS, Roboto on Linux)
- **Monospace:** For data display, code snippets (Courier New, Consolas)

### Font Sizes & Weights

| Context | Size (sp) | Weight | Usage |
|---------|----------|--------|-------|
| **Page Title** | 28 | W_700 | Screen headers |
| **Section Title** | 17 | W_700 | Section headers, card titles |
| **Body** | 14 | W_400 | Main content, descriptions |
| **Caption** | 11 | W_400 | Hints, helper text, timestamps |
| **Button** | 14 | W_500 | Button labels |
| **Badge** | 11 | W_600 | Status badges, tags |

### Flet Weight Constants

```python
ft.FontWeight.W_400  # Regular
ft.FontWeight.W_500  # Medium
ft.FontWeight.W_600  # Semibold
ft.FontWeight.W_700  # Bold
```

**Never use strings** like `weight="bold"` or integers like `weight=700`.

---

## Spacing System

### Base Unit: 4px

All spacing uses multiples of 4px for consistency:

| Multiplier | Pixels | Usage |
|-----------|--------|-------|
| 0.5x | 2px | Micro spacing (between icon + text) |
| 1x | 4px | Small gaps (inside tight components) |
| 2x | 8px | Standard padding inside components |
| 3x | 12px | Padding inside cards, buttons |
| 4x | 16px | Vertical spacing between sections |
| 6x | 24px | Padding inside glass containers |
| 7x | 28px | Spacing between screens |

### Flet Spacing Helpers

```python
# Instead of hardcoding:
ft.padding.symmetric(horizontal=8, vertical=3)    # 2x h, 0.75x v
ft.padding.symmetric(horizontal=16, vertical=12)  # 4x h, 3x v
ft.margin.only(bottom=16)                         # 4x bottom margin
```

---

## Button Styles

### Primary Button

```python
button_style(kind="primary")
```

**Visual:**
- Background: Near Black (#222222)
- Text: White
- Hover: Rausch Red (#ff385c)
- Pressed: Deep Rausch (#e00b41)
- Border radius: 8px
- Font weight: W_500

**Usage:**
- Main call-to-action (submit, save, confirm)
- Should be the most prominent action on screen
- Only 1 primary button per screen

**Example:**
```python
ft.ElevatedButton(
    text="Save Changes",
    style=button_style("primary"),
    on_click=on_save,
)
```

### Secondary Button

```python
button_style(kind="secondary")
```

**Visual:**
- Background: Rausch Red (#ff385c)
- Text: White
- Hover: Deep Rausch (#e00b41)
- Border radius: 8px

**Usage:**
- Important secondary actions (cancel, delete, reset)
- Less prominent than primary

### Surface Button

```python
button_style(kind="surface")
```

**Visual:**
- Background: Light (#f2f2f2)
- Text: Near Black (#222222)
- Border: 1px light gray
- Hover: Slight darkening

**Usage:**
- Utility buttons (add, edit, view details)
- Icon buttons, circular buttons
- Low-emphasis actions

### Warning Button

```python
button_style(kind="warning")
```

**Visual:**
- Background: Amber (#F2C94C)
- Text: Dark (#06131B)
- Hover: Darkened amber

**Usage:**
- Caution actions (overwrite, force delete)

### Danger Button

```python
button_style(kind="danger")
```

**Visual:**
- Background: Error red (#c13515)
- Text: White
- Hover: Dark error (#b32505)

**Usage:**
- Destructive actions (delete permanently, clear data)

### Button Size Guidelines

| Size | Width | Height | Font | Usage |
|------|-------|--------|------|-------|
| **Large** | 100% (full) | 48px | 14px | Main CTAs, form submit |
| **Medium** | 120px–200px | 40px | 14px | Standard buttons, modals |
| **Small** | 80px–120px | 32px | 12px | Toolbar, inline actions |
| **Icon** | 40px | 40px | 20px | Icon-only buttons |

---

## Component Patterns

### Glass Container

Every data panel/card uses frosted glass styling:

```python
glass_container(
    content=ft.Column(controls=[...]),
    width=400,
    height=300,
    padding=24,
    radius=28,
)
```

**Features:**
- Frosted glass background (16% white opacity)
- Subtle border (18% white opacity)
- Drop shadow (blur_radius=28, offset=(0, 14))
- Rounded corners (28px radius)
- Interior padding (24px default)

### Status Badge

Color-coded pill badge for status indicators:

```python
status_badge(label="Active", kind="primary")
status_badge(label="Pending", kind="warning")
status_badge(label="Error", kind="danger")
```

**Sizes:**
- Height: 20px (fixed)
- Padding: 8px horizontal, 3px vertical
- Font: 11px, W_600

**Colors:**
- Background: Semi-transparent color (22% opacity)
- Border: Semi-transparent color (45% opacity)
- Text: Solid color (matching kind)

### Metric Card

Display a key metric with large number + label:

```python
metric_card(
    title="Total Cattle",
    value="247",
    icon=ft.Icons.PETS,
    icon_color=PRIMARY,
)
```

**Structure:**
```
┌──────────────────┐
│ [ICON] Total ... │
│      247         │
└──────────────────┘
```

### Data Table

Display structured data in a scrollable table:

```python
data_table(
    columns=["ID", "Name", "Status", "Actions"],
    rows=[
        ["1", "Herd A", "Active", "[Edit] [Delete]"],
        ["2", "Herd B", "Offline", "[Edit] [Delete]"],
    ],
)
```

**Features:**
- Header row: bold, background color
- Data rows: alternating background (zebra striping)
- Scrollable horizontally for overflow
- Action buttons right-aligned

### Section Title

Header for a group of related content:

```python
section_title(
    icon_name="DASHBOARD",  # ft.Icons.DASHBOARD
    text="Overview",
    subtitle="Real-time metrics",
)
```

**Structure:**
```
📊 Overview
  Real-time metrics
```

### Empty State

Placeholder when no data exists:

```python
empty_state(text="No cameras assigned yet")
```

**Visual:**
- Centered icon (36px, 24% opacity)
- Help text below (13px, 38% opacity)
- Suggests user what to do next

### Inline Field

Compact text input (form-style):

```python
inline_field(
    label="Username",
    value="john_doe",
    icon=ft.Icons.PERSON,
    hint="Enter your username",
    expand=True,
)
```

---

## Layout Patterns

### Main Shell (Responsive)

All main screens use `build_role_shell()` to adapt layout:

**Desktop Layout** (width > 900px):
```
┌─────────┬──────────────────┐
│ NAV     │  CONTENT         │
│ SIDEBAR │  (dynamic)       │
│         │                  │
│         │                  │
│         │                  │
└─────────┴──────────────────┘
```

**Mobile Layout** (width ≤ 900px):
```
┌──────────────────────────┐
│  CONTENT (full width)    │
│  (scrollable)            │
├──────────────────────────┤
│ NAV BOTTOM BAR (5 items) │
└──────────────────────────┘
```

### Navigation Sidebar (Desktop)

```
┌─────────────┐
│  Logo/App   │
├─────────────┤
│ ► Dashboard │  ← selected (highlighted)
│   Users     │
│   Reports   │
│   Settings  │
│   Profile   │
├─────────────┤
│   Logout    │  ← bottom-aligned
└─────────────┘
```

**Styling:**
- Width: 240px
- Background: Dark (near black #222222)
- Text: White
- Selected item: Accent color background
- Icons: 20px, left-aligned with text

### Bottom Navigation Bar (Mobile)

```
┌──────┬──────┬──────┬──────┬──────┐
│ [D]  │ [U]  │ [R]  │ [S]  │ [P]  │
│ Dash │ Users│ Rpts │ Sett │ Prof │
└──────┴──────┴──────┴──────┴──────┘
```

**Styling:**
- Height: 56px (icon 24px + label 10px + padding)
- Background: Glass effect (matches theme)
- Selected icon: Accent color
- Label: 10px font, only show for selected tab

### Screen Grid

Main content area uses a 12-column grid system:

```
┌─────┬─────┬─────┬─────┐
│  6  │  6  │  -  │  -  │  2 cards, 50% width each
└─────┴─────┴─────┴─────┘

┌──────────────────────────┐
│         12               │  1 full-width card
└──────────────────────────┘

┌───┬────┬────┬────┬───┐
│ 3 │ 3  │ 3  │ 3  │ - │  4 cards, 25% width each
└───┴────┴────┴────┴───┘
```

### Form Layout

```
┌──────────────────────────┐
│  [Title]                 │
│  [Description]           │
├──────────────────────────┤
│  [Label 1]               │
│  [Input 1]               │
│                          │
│  [Label 2]               │
│  [Input 2]               │
│                          │
│  [Label 3]               │
│  [Dropdown 3]            │
├──────────────────────────┤
│  [Cancel]  [Submit]      │
└──────────────────────────┘
```

**Vertical spacing:** 16px between fields, 24px before buttons

---

## Animation & Motion

### Transitions (When Applicable)

Flet has limited animation support. Use transitions sparingly:

- **Page transitions:** 300ms fade-in
- **Button feedback:** 100ms opacity change on hover
- **Modal appear:** 250ms slide-up
- **Notification toast:** 200ms fade-in, 300ms fade-out

**Principle:** Animations should feel natural and not distract from content.

### Disabled States

When a control is disabled:
- Opacity: 50%
- Cursor: not-allowed (when possible)
- Text color: Gray (WHITE38 or WHITE54)

```python
ft.ElevatedButton(
    text="Save",
    disabled=True,  # Flet handles styling
)
```

---

## Accessibility (A11y)

### WCAG AA Compliance Checklist

- [ ] **Color Contrast:** All text ≥4.5:1 contrast ratio
  - Primary text on white: #06131B (15.3:1 ✓)
  - Primary text on glass: White on glass (>7:1 ✓)
  - Danger red on white: #FF7A7A (5.2:1 ✓)

- [ ] **Text Alternatives:** Icons have tooltips or nearby labels
  - ✓ Navigation icons have labels in sidebar
  - ✓ Button icons have text in button

- [ ] **Keyboard Navigation:**
  - [ ] Tab order is logical (top-to-bottom, left-to-right)
  - [ ] All actions accessible via keyboard (not mouse-only)
  - [ ] Focus indicators visible (Flet default)

- [ ] **Readable Text:**
  - ✓ Font size ≥12px for body text
  - ✓ Line height ≥1.5x font size
  - ✓ Max line length 80 characters

- [ ] **Form Labels:**
  - ✓ Every input has explicit label
  - ✓ Error messages clear and actionable

- [ ] **Motion & Animations:**
  - [ ] No auto-playing animations > 5 seconds
  - [ ] Animations have reduced-motion option

---

## Dark Mode (Future Enhancement)

Reserved for Phase 4. When implementing:

| Element | Light | Dark |
|---------|-------|------|
| **Background** | White | #1a1a1a |
| **Card** | #f5f5f5 | #2a2a2a |
| **Text** | #06131B | #f0f0f0 |
| **Primary** | #4CAF50 | #66bb6a |
| **Accent** | #ff385c | #ff6b7a |

---

## Responsive Design Breakpoints

```
Mobile    Tablet    Desktop   Ultra-Wide
┌────┐   ┌─────┐   ┌──────┐   ┌────────┐
│ 1x │   │ 2x  │   │ 3x   │   │ 4x     │
└────┘   └─────┘   └──────┘   └────────┘
 320px    600px    900px      1440px
```

### Breakpoint Behavior

| Screen Size | Layout | Nav | Cards |
|-------------|--------|-----|-------|
| **<600px** | Single column | Bottom bar | 1 per row |
| **600–900px** | 2 columns | Bottom bar | 2 per row |
| **>900px** | 3+ columns | Sidebar | 3 per row |

### Testing Breakpoints

- [ ] 393x852 (mobile default in main.py)
- [ ] 600x800 (small tablet)
- [ ] 1024x768 (tablet landscape)
- [ ] 1920x1080 (desktop)

---

## Error & Success States

### Error Message Styling

```
┌─────────────────────────────────┐
│ ⚠️  [Error Title]                │
│ [Detailed explanation of error] │
│ [Suggested action or hint]       │
│ [Dismiss] [Retry]               │
└─────────────────────────────────┘
```

**Styling:**
- Background: Semi-transparent danger color (22% #FF7A7A)
- Border: 1px danger red
- Icon: Error icon (18px, #FF7A7A)
- Text: Dark text (#06131B) on light, white on dark

### Success Message Styling

```
┌─────────────────────────────────┐
│ ✓ [Success Title]                │
│ [What was accomplished]         │
│ [Next action, if any]           │
│ [Close]                         │
└─────────────────────────────────┘
```

**Styling:**
- Background: Semi-transparent primary color (22% #4CAF50)
- Border: 1px primary green
- Icon: Checkmark (18px, #4CAF50)
- Duration: Auto-dismiss after 5 seconds

### Toast Notifications

Short, temporary messages in corner:

```
┌─────────────────────┐
│ ✓ Saved!            │
└─────────────────────┘
```

**Styling:**
- Small (200px width)
- Top-right corner
- 3s auto-dismiss
- No action buttons

---

## Microcopy (Text Guidelines)

### Button Labels

- ✓ Action verb + object: "Save changes", "Delete user", "Export report"
- ✗ Vague: "OK", "Yes", "Proceed"

### Form Placeholders

- ✓ Hints, not labels: "enter@email.com", "john_doe"
- ✗ Full instructions: "This is a required field for..."

### Error Messages

- ✓ Specific: "Password must be ≥8 characters"
- ✗ Generic: "Invalid input"

### Confirmation Dialogs

- ✓ Clear consequence: "This will permanently delete 5 alerts. Continue?"
- ✗ Ambiguous: "Are you sure?"

### Help Text

- ✓ Concise, actionable: "Separate multiple emails with commas"
- ✗ Verbose: "If you have more than one email address, please use the comma character (,) to separate them..."

---

## Localization Considerations

Current: **Vietnamese UI + English technical terminology**

### Field Name Casing

Use exact database field names in Vietnamese:
- ✓ `ten_dang_nhap` (UI label: "Username" or "Tên đăng nhập")
- ✓ `mat_khau` (UI label: "Password" or "Mật khẩu")
- ✗ `username` (incorrect, not in schema)

### Numbers & Dates

- **Numbers:** 1000 → "1,000" (US format)
- **Dates:** ISO format in DB (2026-04-15); UI display "15/04 14:30" (Vietnamese format)
- **Currency:** USD (if applicable) → "$500", not "500 USD"

---

## Design System Files

All design tokens are centralized in:

```
ui/theme.py
├── Color constants
├── Glass effect (GLASS_BG, GLASS_BORDER, GLASS_SHADOW)
├── Component factories
│   ├── glass_container()
│   ├── button_style()
│   ├── status_badge()
│   ├── section_title()
│   ├── empty_state()
│   ├── inline_field()
│   ├── metric_card()
│   ├── data_table()
│   ├── build_role_shell()
│   └── build_auth_shell()
└── Utilities
    ├── fmt_dt() — format datetime
    └── responsive helpers
```

**Never hardcode colors/spacing in screens.** Always import from `theme.py`.

---

## Common Design Pitfalls to Avoid

| Pitfall | ✗ Bad | ✓ Good |
|---------|-------|--------|
| **Hardcoded colors** | `bgcolor="#4CAF50"` | `bgcolor=PRIMARY` |
| **Inconsistent spacing** | Random px values | Use 4px multiples |
| **Too many fonts** | 5+ different sizes | Use defined sizes |
| **Poor button hierarchy** | Multiple red buttons | One primary, rest secondary |
| **No whitespace** | Content edge-to-edge | Padding around all content |
| **Disabled state unclear** | Looks active but broken | 50% opacity when disabled |
| **No feedback on click** | Button doesn't respond | Color change + animation |
| **Inaccessible icons** | Icon-only button | Icon + text label |
| **Text on images** | No contrast | Overlay with semi-transparent bg |
| **Tiny touch targets** | <32px buttons | 40px+ for mobile |

---

## Design Review Checklist

Before shipping any UI screen:

- [ ] Uses components from theme.py (no hardcoded colors)
- [ ] Spacing is consistent (multiples of 4px)
- [ ] Responsive on mobile (<600px) and desktop (>900px)
- [ ] Color contrast ≥4.5:1 for all text
- [ ] All buttons have clear labels (not icon-only)
- [ ] Disabled states visually distinct
- [ ] Empty states handled (not blank screens)
- [ ] Error/success messages clear and actionable
- [ ] Load times <2 seconds
- [ ] No layout shifts or jank during interactions
- [ ] Consistent with admin/expert/farmer design language

---

## Design Resources

- **Colors:** See Primary Palette section
- **Icons:** Flet built-in icons (`ft.Icons.*`)
- **Fonts:** System defaults (no custom fonts needed)
- **Component examples:** See ui/theme.py
- **Screen layouts:** See ui/components/{admin,user}/*.py

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-04-15 | Initial design system (Phase 1) |
| 1.1 | TBD | Dark mode (Phase 4) |
| 2.0 | TBD | Redesign for mobile app (Phase 5) |
