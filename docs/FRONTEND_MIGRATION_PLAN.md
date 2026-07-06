# Frontend Migration Plan: DaisyUI + Pivot Table

## Context
The current frontend has broken WebDataRocks pivot table (React HMR/StrictMode incompatible), manual CSS styling (569 lines of variables), and no component library. This plan migrates to DaisyUI for consistent theming and replaces WebDataRocks with a React-compatible pivot table for financial analysis.

---

## Phase 1: Install Dependencies

### 1.1 Tailwind CSS + DaisyUI
```bash
cd frontend
npm install -D tailwindcss @tailwindcss/vite daisyui@latest
```

### 1.2 WebDataRocks (free, with React wrapper)
```bash
npm install @webdatarocks/webdatarocks @webdatarocks/react-webdatarocks
```
- Free for non-commercial use, MIT license for the React wrapper
- True pivot table with drag-and-drop field placement
- Toolbar with filtering, sorting, grouping, export (PDF/Excel/CSV)
- Official React wrapper (`WebDataRocksReact.Pivot`)

**Note:** WebDataRocks is not compatible with React `<StrictMode>`. We will remove `<StrictMode>` from `main.tsx`. This is development-only — no effect in production.

### 1.3 Remove StrictMode (required for WebDataRocks)
Edit `src/main.tsx` — remove `<StrictMode>` wrapper:
```tsx
// Before
createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <BrowserRouter><App /></BrowserRouter>
  </StrictMode>,
)

// After
createRoot(document.getElementById('root')!).render(
  <BrowserRouter><App /></BrowserRouter>,
)
```

### 1.4 Remove unused
```bash
npm uninstall @tanstack/react-table
```

---

## Phase 2: Configuration Files

### 2.1 `vite.config.ts`
```ts
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    proxy: {
      '/api': { target: 'http://127.0.0.1:8000', changeOrigin: true },
      '/health': { target: 'http://127.0.0.1:8000', changeOrigin: true },
      '/plaid': { target: 'http://127.0.0.1:8000', changeOrigin: true },
    },
  },
  build: { outDir: 'dist', sourcemap: false },
})
```

### 2.2 `tailwind.config.js` (new file)
```js
/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: { extend: {} },
  plugins: [require('daisyui')],
  daisyui: {
    themes: ['light', 'dark', 'dracula'],
    darkTheme: 'dark',
  },
}
```

### 2.3 `src/styles/globals.css` → replace with:
```css
@import "tailwindcss";
```
(DaisyUI handles all component styles via Tailwind utilities)

### 2.4 `index.html`
Add `data-theme="dark"` to `<html>` tag for default dark theme.

---

## Phase 3: Theme System Migration

### 3.1 `src/context/ThemeContext.tsx`
- Keep the same structure
- DaisyUI uses `data-theme` attribute (already in place)
- Map our theme names to DaisyUI themes: `'dark' → 'dark'`, `'light' → 'light'`
- Add `'dracula'` as third option

```tsx
type Theme = 'dark' | 'light' | 'dracula'
```

### 3.2 Theme toggle in Layout
- Use DaisyUI `swap` component for sun/moon icons
- Add theme dropdown with all 3 options

---

## Phase 4: Layout Migration (`components/Layout.tsx`)

### Current → DaisyUI Components

| Current | DaisyUI | Notes |
|---------|---------|-------|
| `.layout` (flex) | `drawer lg:drawer-open` | Responsive sidebar |
| `.sidebar` | `drawer-side` | |
| `.sidebar-header` | Part of `drawer-side` | Use `prose` or custom |
| `.nav-item` | `menu-item` / `<li><a>` | Use `menu` component |
| `.nav-item.active` | `menu-active` | |
| `.main-content` | `drawer-content` | |
| `.navbar` | `navbar` | DaisyUI navbar |
| `.icon-btn` | `btn btn-ghost btn-circle` | Theme toggle |

### New Layout Structure:
```tsx
<div className="drawer lg:drawer-open">
  <input type="checkbox" className="drawer-toggle" />
  <div className="drawer-content">
    {/* Navbar */}
    <div className="navbar bg-base-200 sticky top-0 z-50">
      <div className="flex-1">
        <span className="text-lg font-semibold">{pageTitle}</span>
      </div>
      <div className="flex-none">
        {/* Theme toggle */}
      </div>
    </div>
    {/* Page content */}
    <div className="p-6">
      <Outlet />
    </div>
  </div>
  <div className="drawer-side">
    <label className="drawer-overlay" />
    <aside className="menu bg-base-200 text-base-content w-60 min-h-screen">
      {/* Logo */}
      {/* Nav items */}
    </aside>
  </div>
</div>
```

---

## Phase 5: Dashboard Page Migration (`pages/Dashboard.tsx`)

### Current → DaisyUI

| Current | DaisyUI |
|---------|---------|
| `.stat-grid` | `stats-grid lg:grid-cols-4` (or custom grid) |
| `.stat-card` | `stat bg-base-200 rounded-box` |
| `.stat-label` | `stat-title` |
| `.stat-value` | `stat-value` |
| `.stat-positive` | `text-success` |
| `.stat-negative` | `text-error` |
| `.chart-card` | `card bg-base-200` |
| `.card-title` | `card-title` |

### Chart (Recharts)
- Keep Recharts (already working)
- Just update CSS variable references to DaisyUI equivalents
- `var(--accent-primary)` → `var(--p)` (DaisyUI primary)
- `var(--border-color)` → `var(--b3)` (DaisyUI base-300)

---

## Phase 6: Transactions Page Migration (`pages/Transactions.tsx`)

### WebDataRocks Integration

```tsx
import * as WebDataRocksReact from '@webdatarocks/react-webdatarocks'
import '@webdatarocks/webdatarocks/webdatarocks.css'

// Transform API data for WebDataRocks
const wdrData = transactions.map(tx => ({
  'Date': tx.date,
  'Name': tx.name,
  'Amount': tx.amount,
  'Flow Type': tx.flow_type,
  'Category': flattenCategory(tx.category),
  'Merchant': tx.merchant_name || '',
  'Channel': tx.payment_channel,
  'Pending': tx.pending ? 'Yes' : 'No',
}))

// Component
<WebDataRocksReact.Pivot
  toolbar={true}
  width="100%"
  height={600}
  report={{
    dataSource: { data: wdrData },
    slice: {
      rows: [{ uniqueName: 'Category' }],
      columns: [{ uniqueName: 'Flow Type' }],
      measures: [{ uniqueName: 'Amount', aggregation: 'sum' }],
    },
  }}
  shareReportConnection={{ url: 'https://olap.webdatarocks.com/reportapi' }}
/>
```

Features available:
- **Pivot**: Drag fields between rows, columns, and values
- **Filtering**: Built-in per-field filtering
- **Sorting**: Click to sort any column/row
- **Grouping**: Group by date, category, merchant, etc.
- **Export**: PDF, Excel, CSV from toolbar
- **Aggregation**: Sum, count, avg, min, max

### Layout
- Use DaisyUI `card` for the container
- Add date range filter with DaisyUI `input` + `select`
- Summary footer with DaisyUI `stat` or custom flex

---

## Phase 7: Accounts Page Migration (`pages/Accounts.tsx`)

### DaisyUI Components

| Current | DaisyUI |
|---------|---------|
| `.table-container table` | `table table-zebra` |
| `.badge` | `badge badge-success` / `badge badge-warning` |
| `.card` | `card bg-base-200` |
| Inline styles | Tailwind utilities |

### Structure:
```tsx
<div className="card bg-base-200 shadow-md">
  <div className="card-body">
    <h2 className="card-title">Accounts</h2>
    <div className="overflow-x-auto">
      <table className="table table-zebra">
        <thead>...</thead>
        <tbody>...</tbody>
      </table>
    </div>
  </div>
</div>
```

---

## Phase 8: Sync Status Page Migration (`pages/SyncStatus.tsx`)

### DaisyUI Components

| Current | DaisyUI |
|---------|---------|
| `.btn.btn-primary` | `btn btn-primary` |
| `.btn.btn-secondary` | `btn btn-secondary` |
| Loading spinner | `loading loading-spinner` |
| `.empty-state` | `flex flex-col items-center justify-center p-12` |
| Table | `table table-zebra` |

### Sync Button
```tsx
<button className={`btn btn-primary ${syncing ? 'loading' : ''}`} onClick={handleSync} disabled={syncing}>
  {!syncing && <Icon icon="mdi:sync" />}
  {syncing ? 'Syncing...' : 'Sync Now'}
</button>
```

---

## Phase 9: Remove Old CSS

Delete entire `globals.css` content, replace with:
```css
@import "tailwindcss";
```

Remove all CSS variable definitions, manual component styles, WebDataRocks overrides.

---

## File Change Summary

| File | Action |
|------|--------|
| `package.json` | Add tailwindcss, daisyui, @webdatarocks/webdatarocks, @webdatarocks/react-webdatarocks. Remove @tanstack/react-table |
| `vite.config.ts` | Add tailwindcss plugin |
| `tailwind.config.js` | **New file** - DaisyUI config |
| `index.html` | Add `data-theme="dark"` |
| `src/styles/globals.css` | Replace with `@import "tailwindcss"` |
| `src/main.tsx` | Remove `<StrictMode>` wrapper (required for WebDataRocks) |
| `src/App.tsx` | No change |
| `src/api/client.ts` | No change |
| `src/api/types.ts` | No change |
| `src/context/ThemeContext.tsx` | Update theme names for DaisyUI |
| `src/components/Layout.tsx` | Full rewrite with DaisyUI drawer/navbar/menu |
| `src/pages/Dashboard.tsx` | Rewrite with DaisyUI stats + cards |
| `src/pages/Transactions.tsx` | Full rewrite with pivot table library |
| `src/pages/Accounts.tsx` | Rewrite with DaisyUI table/cards |
| `src/pages/SyncStatus.tsx` | Rewrite with DaisyUI components |

---

## Testing Approach
1. After Phase 1-2: verify `npm run dev` starts without errors
2. After each page migration: visually verify in browser via Playwright
3. After Phase 9: verify `npm run build` succeeds, check bundle size
4. Full smoke test: navigate all pages, toggle theme, test sync button, verify pivot table loads

---

## Open Questions
1. **DaisyUI themes**: light/dark/dracula, or different set?
2. **Sidebar behavior**: Always open on desktop, drawer on mobile? (current behavior)
