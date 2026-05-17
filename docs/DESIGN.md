# ReviewPulse UI/UX Design

## Design Philosophy

ReviewPulse surfaces complex review analytics through a clean, scannable interface.
Authors should understand their review health at a glance, then drill down as needed.

## Page Layout

### Shell Structure
- **Sidebar** (240px, hidden on mobile): Navigation + branding
- **Header**: User info + global actions
- **Main Content**: Routed pages with max-width 1280px container

### Route Map
```
/login          → Auth card (centered)
/register       → Auth card (centered)
/               → Dashboard (catalog grid + activity)
/books/:id      → Book deep-dive (charts + review table)
/compare        → Side-by-side comparison
/search         → Semantic search interface
/digest         → Weekly email-style preview
```

## Color System

Built on CSS custom properties with HSL values for light/dark mode support:

- **Primary**: Indigo (222, 84%, 55%) — distinctive in publishing space
- **Sentiment Positive**: Green (142, 71%, 35%)
- **Sentiment Mixed**: Amber (38, 92%, 42%)
- **Sentiment Negative**: Red (0, 72%, 45%)

All sentiment colors have subtle background variants at 10% opacity for badges.

## Component Patterns

### Book Card
Compact card showing: title initial, title, review count, sentiment badge.
Links to deep-dive page. Grid layout: 1-col mobile, 2-col tablet, 3-col desktop.

### Sentiment Timeline
Stacked area chart (Recharts) showing positive/mixed/negative over weekly buckets.
Green/amber/red fills at 35-40% opacity with solid stroke lines.

### Theme Breakdown
Horizontal bar chart showing top 10 themes by frequency.
Indigo bars with rounded corners, sorted descending.

### Reviews Table
Full-width table with columns: snippet, rating (stars), sentiment badge, theme tags, date.
Actionable and AI-flagged reviews get inline badges.

### Semantic Search
Full-width input with search button. Results as cards showing:
book badge, snippet, match percentage, sentiment indicator.

## Chart Library

Recharts (pairs with shadcn/ui chart patterns). All charts are:
- Wrapped in `ResponsiveContainer` for fluid width
- Dark mode compatible via CSS variable colors
- Animated on initial load (disabled when >50 data points)

## Typography

- Headings: system font stack, semi-bold (600)
- Body: 14px, regular (400), 1.6 line height
- Labels: 12px, medium (500)

## Responsive Strategy

- **Mobile** (<768px): Single column, sidebar becomes drawer, charts stack
- **Tablet** (768-1024px): Two-column layouts, sidebar visible
- **Desktop** (1024px+): Full three-column grids, all features visible

## Accessibility

- All interactive elements have visible focus rings
- Sentiment never conveyed by color alone (always includes text label)
- Charts wrapped in `<figure>` with descriptive `<figcaption>`
- Minimum 44x44px touch targets
