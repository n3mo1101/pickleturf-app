# Changelog

## 2026-10-09 — UI/UX refinement

### Added
- Availability page slot states (available / reserved / unavailable / past) with legend
- Dashboard KPI hero/stack grid and theme-aware charts: daily revenue, revenue by type, monthly revenue
- Profile page stats (bookings, total spent, courts played), appearance toggle, account & security rows
- Live password rules on auth forms (8+ chars, not only numbers, match) — shown only while failing
- Mobile POS sticky checkout bars; mobile card mode for data tables

### Changed
- Rebuilt CSS design system (base, components, pages, dark mode)
- De-cluttered tables: 3-dot row action menus, muted uppercase headers, hidden empty action cells
- Standardized CTAs: navy primary, yellow accent, green reserved for success
- Sentence-case titles and buttons; plain card headers without colored banners or icons
- Theme-aware dashboard charts driven by `pt:themechange`; sidebar/nav label cleanup

### Fixed
- Stray quote in announcements admin list; confirm-modal default title
- Dark-mode contrast issues (yellow-on-white text, sticky totals)
- Required-field `*` markers removed via crispy field override (`templates/bootstrap5/`)

### Removed
- Court utilization and bookings-by-weekday dashboard widgets
- Dead `static/css/main/main.css`; emoji/decorative icons in headings; em-dash separators in titles (now `·`)
