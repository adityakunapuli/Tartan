# DaisyUI → Mantine Full UI Migration Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace DaisyUI + Tailwind CSS with Mantine 8.x component library across the entire frontend.

**Architecture:** Remove Tailwind CSS + DaisyUI entirely. Install Mantine 8.x (compatible with React 18). Rewrite all 6 component/page files to use Mantine components. Replace WebDataRocks pivot with Mantine React Table for individual transaction rows + built-in filtering/sorting.

**Tech Stack:** Mantine 8.x (@mantine/core, @mantine/hooks, @mantine/dates), Mantine React Table (latest for Mantine 8), @tabler/icons-react (replaces @iconify/react), Emotion (Mantine's CSS engine), Recharts (keep), React 18 (keep), react-router-dom (keep)

---

## File Structure

### Files to DELETE:
- `frontend/tailwind.config.js`

### Files to CREATE:
- `frontend/src/theme.ts` — Mantine theme configuration (colors, dark mode)

### Files to MODIFY:
- `frontend/package.json` — swap dependencies
- `frontend/vite.config.ts` — remove tailwindcss plugin
- `frontend/index.html` — remove data-theme attribute
- `frontend/src/styles/globals.css` — replace Tailwind+DaisyUI with Mantine CSS imports
- `frontend/src/main.tsx` — wrap in MantineProvider
- `frontend/src/context/ThemeContext.tsx` — use Mantine color scheme instead of data-theme
- `frontend/src/components/Layout.tsx` — Mantine AppShell + Navbar + Menu
- `frontend/src/pages/Dashboard.tsx` — Mantine Paper/Stack/Group/Text/Loader
- `frontend/src/pages/Accounts.tsx` — Mantine Table/Badge/Paper/Loader
- `frontend/src/pages/Transactions.tsx` — Mantine React Table (replaces WebDataRocks)
- `frontend/src/pages/SyncStatus.tsx` — Mantine Button/Badge/Table/Paper/Loader

### Files UNCHANGED:
- `frontend/src/api/client.ts`
- `frontend/src/api/types.ts`
- `frontend/src/vite-env.d.ts`

---

### Task 1: Install Mantine, remove DaisyUI + Tailwind

**Files:**
- Modify: `frontend/package.json`

- [ ] **Step 1: Remove old dependencies**

```bash
cd frontend
npm uninstall daisyui tailwindcss @tailwindcss/vite @webdatarocks/react-webdatarocks @webdatarocks/webdatarocks @iconify/react
```

- [ ] **Step 2: Install Mantine + dependencies**

```bash
npm install @mantine/core@8.3.5 @mantine/hooks@8.3.5 @mantine/dates@8.3.5 @mantine/nprogress @emotion/react @tabler/icons-react dayjs mantine-react-table
```

- [ ] **Step 3: Verify package.json has React 18**

React 18.3.1 should already be in dependencies. If not, add it.

- [ ] **Step 4: Run npm install to verify no conflicts**

```bash
npm install
```

Expected: No errors.

---

### Task 2: Configure Vite + Mantine theme

**Files:**
- Modify: `frontend/vite.config.ts`
- Modify: `frontend/index.html`
- Create: `frontend/src/theme.ts`
- Modify: `frontend/src/styles/globals.css`

- [ ] **Step 1: Remove tailwindcss from vite.config.ts**

```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
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

- [ ] **Step 2: Remove data-theme from index.html**

Change `<html lang="en" data-theme="dark">` to `<html lang="en">`.

- [ ] **Step 3: Create Mantine theme file**

```typescript
// frontend/src/theme.ts
import { createTheme, type MantineColorsTuple } from '@mantine/core'

const brandColor: MantineColorsTuple = [
  '#eef3ff', '#dce4fd', '#b9c9fc', '#8ba8fa',
  '#5b82f5', '#3a66f2', '#244ee8', '#1d3ed0',
  '#1a34ab', '#172e89',
]

export const theme = createTheme({
  primaryColor: 'brand',
  colors: {
    brand: brandColor,
  },
  fontFamily: 'system-ui, -apple-system, sans-serif',
  components: {
    AppShell: {
      defaultProps: {
        header: { height: 56 },
        navbar: { width: 240, breakpoint: 'lg' },
      },
    },
  },
})
```

- [ ] **Step 4: Replace globals.css content**

```css
@import '@mantine/core/styles.css';
@import '@mantine/dates/styles.css';
@import '@mantine/nprogress/styles.css';
```

- [ ] **Step 5: Delete tailwind.config.js**

```bash
rm frontend/tailwind.config.js
```

- [ ] **Step 6: Verify build compiles**

```bash
cd frontend && npx vite build
```

Expected: Build succeeds (pages will have import errors until rewritten, but theme/CSS setup should compile).

---

### Task 3: Rewrite ThemeContext + main.tsx

**Files:**
- Modify: `frontend/src/main.tsx`
- Modify: `frontend/src/context/ThemeContext.tsx`

- [ ] **Step 1: Rewrite main.tsx to wrap with MantineProvider**

```tsx
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { MantineProvider } from '@mantine/core'
import { theme } from './theme'
import App from './App'
import './styles/globals.css'

createRoot(document.getElementById('root')!).render(
  <MantineProvider theme={theme} defaultColorScheme="dark">
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </MantineProvider>,
)
```

- [ ] **Step 2: Rewrite ThemeContext.tsx to use Mantine's color scheme**

```tsx
import { createContext, useContext, useState, useEffect, type ReactNode } from 'react'
import { useComputedColorScheme, useMantineColorScheme } from '@mantine/core'

type Theme = 'dark' | 'light'

interface ThemeContextValue {
  theme: Theme
  toggleTheme: () => void
}

const ThemeContext = createContext<ThemeContextValue>({
  theme: 'dark',
  toggleTheme: () => {},
})

export function useTheme() {
  return useContext(ThemeContext)
}

export function ThemeProvider({ children }: { children: ReactNode }) {
  const { setColorScheme } = useMantineColorScheme()
  const computed = useComputedColorScheme('dark')
  const [theme, setTheme] = useState<Theme>((computed as Theme) || 'dark')

  useEffect(() => {
    setTheme(computed as Theme)
  }, [computed])

  const toggleTheme = () => {
    const next = theme === 'dark' ? 'light' : 'dark'
    setTheme(next)
    setColorScheme(next)
  }

  return (
    <ThemeContext.Provider value={{ theme, toggleTheme }}>
      {children}
    </ThemeContext.Provider>
  )
}
```

- [ ] **Step 3: Update App.tsx to wrap routes in ThemeProvider**

```tsx
import { Routes, Route, Navigate } from 'react-router-dom'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import Transactions from './pages/Transactions'
import Accounts from './pages/Accounts'
import SyncStatus from './pages/SyncStatus'
import { ThemeProvider } from './context/ThemeContext'

export default function App() {
  return (
    <ThemeProvider>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<Dashboard />} />
          <Route path="/transactions" element={<Transactions />} />
          <Route path="/accounts" element={<Accounts />} />
          <Route path="/sync" element={<SyncStatus />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </ThemeProvider>
  )
}
```

- [ ] **Step 4: Verify app boots without errors**

```bash
cd frontend && npx vite build
```

Expected: Build succeeds. No runtime errors on load (pages will be blank/broken until rewritten).

---

### Task 4: Rewrite Layout.tsx (sidebar + navbar)

**Files:**
- Modify: `frontend/src/components/Layout.tsx`

- [ ] **Step 1: Rewrite Layout.tsx with Mantine AppShell**

```tsx
import { useState } from 'react'
import { Outlet, NavLink, useLocation } from 'react-router-dom'
import {
  AppShell,
  Group,
  Text,
  ActionIcon,
  Menu,
  Burger,
  Stack,
  useMantineColorScheme,
  useComputedColorScheme,
} from '@mantine/core'
import {
  IconDashboard,
  IconArrowsExchange,
  IconBuildingBank,
  IconRefresh,
  IconSun,
  IconMoon,
  IconMenu2,
} from '@tabler/icons-react'
import { useTheme } from '../context/ThemeContext'

const navItems = [
  { to: '/', label: 'Dashboard', icon: IconDashboard },
  { to: '/transactions', label: 'Transactions', icon: IconArrowsExchange },
  { to: '/accounts', label: 'Accounts', icon: IconBuildingBank },
  { to: '/sync', label: 'Sync Status', icon: IconRefresh },
]

const pageTitles: Record<string, string> = {
  '/': 'Dashboard',
  '/transactions': 'Transactions',
  '/accounts': 'Accounts',
  '/sync': 'Sync Status',
}

export default function Layout() {
  const { theme, toggleTheme } = useTheme()
  const location = useLocation()
  const [opened, setOpened] = useState(false)

  return (
    <AppShell
      header={{ height: 56 }}
      navbar={{ width: 240, breakpoint: 'lg', collapsed: { mobile: !opened } }}
      padding="md"
    >
      <AppShell.Header>
        <Group h="100%" px="md" justify="space-between">
          <Group>
            <Burger
              opened={opened}
              onClick={() => setOpened(!opened)}
              hiddenFrom="lg"
              size="sm"
            />
            <Text fw={600} size="lg">
              {pageTitles[location.pathname] || 'Dashboard'}
            </Text>
          </Group>
          <Menu shadow="md" width={160}>
            <Menu.Target>
              <ActionIcon variant="subtle" color="gray" size="lg">
                {theme === 'dark' ? <IconSun size={20} /> : <IconMoon size={20} />}
              </ActionIcon>
            </Menu.Target>
            <Menu.Dropdown>
              <Menu.Item
                leftSection={<IconMoon size={16} />}
                onClick={() => theme !== 'dark' && toggleTheme()}
                variant={theme === 'dark' ? 'light' : 'subtle'}
              >
                Dark
              </Menu.Item>
              <Menu.Item
                leftSection={<IconSun size={16} />}
                onClick={() => theme !== 'light' && toggleTheme()}
                variant={theme === 'light' ? 'light' : 'subtle'}
              >
                Light
              </Menu.Item>
            </Menu.Dropdown>
          </Menu>
        </Group>
      </AppShell.Header>

      <AppShell.Navbar p="md">
        <Stack gap={4}>
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === '/'}
              onClick={() => setOpened(false)}
              style={({ isActive }) => ({
                display: 'flex',
                alignItems: 'center',
                gap: 10,
                padding: '8px 12px',
                borderRadius: 6,
                textDecoration: 'none',
                color: isActive ? 'var(--mantine-color-brand-6)' : undefined,
                backgroundColor: isActive ? 'var(--mantine-color-brand-0)' : undefined,
                fontWeight: isActive ? 600 : 400,
              })}
            >
              <item.icon size={20} />
              {item.label}
            </NavLink>
          ))}
        </Stack>
      </AppShell.Navbar>

      <AppShell.Main>
        <Outlet />
      </AppShell.Main>
    </AppShell>
  )
}
```

- [ ] **Step 2: Verify layout renders with sidebar + navbar**

```bash
cd frontend && npx vite build
```

Expected: Build succeeds. Sidebar visible with nav links, header with theme toggle.

---

### Task 5: Rewrite Dashboard.tsx

**Files:**
- Modify: `frontend/src/pages/Dashboard.tsx`

- [ ] **Step 1: Rewrite Dashboard.tsx with Mantine components**

```tsx
import { useEffect, useState } from 'react'
import {
  SimpleGrid,
  Paper,
  Text,
  Title,
  Stack,
  Group,
  Loader,
  Center,
} from '@mantine/core'
import { IconAlertCircle } from '@tabler/icons-react'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'
import { api } from '../api/client'
import type { DashboardSummary } from '../api/types'

export default function Dashboard() {
  const [data, setData] = useState<DashboardSummary | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.getDashboard()
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  if (error) {
    return (
      <Center p="xl">
        <Group c="dimmed">
          <IconAlertCircle size={48} />
          <Text>{error}</Text>
        </Group>
      </Center>
    )
  }

  if (loading) {
    return (
      <Center p="xl">
        <Stack align="center" gap="sm">
          <Loader size="lg" />
          <Text c="dimmed">Loading dashboard...</Text>
        </Stack>
      </Center>
    )
  }

  if (!data) return null

  const stats = [
    { label: 'Net Worth', value: data.net_worth, color: 'green' },
    { label: 'Total Balance', value: data.total_balance, color: 'white' },
    { label: 'Monthly Income', value: data.monthly_income, color: 'green' },
    { label: 'Monthly Expenses', value: data.monthly_expenses, color: 'red' },
  ]

  const chartData = [
    { name: 'Income', value: data.monthly_income },
    { name: 'Expenses', value: data.monthly_expenses },
  ]

  return (
    <Stack gap="md">
      <SimpleGrid cols={{ base: 1, sm: 2, lg: 4 }} spacing="md">
        {stats.map((s) => (
          <Paper key={s.label} p="md" radius="md" bg="dark.6">
            <Text size="sm" c="dimmed">{s.label}</Text>
            <Text
              fw={700}
              size="xl"
              c={s.color === 'green' ? 'green.4' : s.color === 'red' ? 'red.4' : 'white'}
            >
              ${Math.abs(s.value).toLocaleString('en-US', { minimumFractionDigits: 2 })}
            </Text>
          </Paper>
        ))}
      </SimpleGrid>

      <Paper p="md" radius="md" bg="dark.6">
        <Title order={5} mb="md">Monthly Overview</Title>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={chartData}>
            <XAxis dataKey="name" stroke="#888888" />
            <YAxis stroke="#888888" />
            <Tooltip
              contentStyle={{
                backgroundColor: '#1a1b1e',
                border: '1px solid #373a40',
                borderRadius: 6,
              }}
            />
            <Bar dataKey="value" fill="var(--mantine-color-brand-5)" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </Paper>
    </Stack>
  )
}
```

- [ ] **Step 2: Verify Dashboard renders**

```bash
cd frontend && npx vite build
```

Expected: Build succeeds. Dashboard shows stats cards + chart.

---

### Task 6: Rewrite Accounts.tsx

**Files:**
- Modify: `frontend/src/pages/Accounts.tsx`

- [ ] **Step 1: Rewrite Accounts.tsx with Mantine Table + Badge**

```tsx
import { useEffect, useState } from 'react'
import {
  Stack,
  Paper,
  Title,
  Text,
  Table,
  Badge,
  Loader,
  Center,
  Group,
} from '@mantine/core'
import { IconAlertCircle } from '@tabler/icons-react'
import { api } from '../api/client'
import type { Account, PlaidItem, Liability } from '../api/types'

export default function Accounts() {
  const [accounts, setAccounts] = useState<Account[]>([])
  const [items, setItems] = useState<PlaidItem[]>([])
  const [liabilities, setLiabilities] = useState<Liability[]>([])
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([
      api.getAccounts(),
      api.getSyncStatus(),
      api.getLiabilities().catch(() => [] as Liability[]),
    ])
      .then(([acc, sync, liab]) => {
        setAccounts(acc)
        setItems(sync.items)
        setLiabilities(liab)
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  if (error) {
    return (
      <Center p="xl">
        <Group c="dimmed">
          <IconAlertCircle size={48} />
          <Text>{error}</Text>
        </Group>
      </Center>
    )
  }

  if (loading) {
    return (
      <Center p="xl">
        <Stack align="center" gap="sm">
          <Loader size="lg" />
          <Text c="dimmed">Loading accounts...</Text>
        </Stack>
      </Center>
    )
  }

  return (
    <Stack gap="md">
      <Paper p="md" radius="md" bg="dark.6">
        <Title order={5} mb="md">Accounts ({accounts.length})</Title>
        <Table striped highlightOnHover>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Name</Table.Th>
              <Table.Th>Type</Table.Th>
              <Table.Th>Mask</Table.Th>
              <Table.Th ta="right">Balance</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {accounts.map((a) => (
              <Table.Tr key={a.account_id}>
                <Table.Td>{a.name}</Table.Td>
                <Table.Td>{a.type}</Table.Td>
                <Table.Td>****{a.mask}</Table.Td>
                <Table.Td ta="right">
                  ${a.current_balance.toLocaleString('en-US', { minimumFractionDigits: 2 })}
                </Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      </Paper>

      <Paper p="md" radius="md" bg="dark.6">
        <Title order={5} mb="md">Institutions ({items.length})</Title>
        <Table striped highlightOnHover>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Name</Table.Th>
              <Table.Th>Status</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {items.map((item) => (
              <Table.Tr key={item.item_id || item.institution_name}>
                <Table.Td>{item.institution_name || 'Unknown'}</Table.Td>
                <Table.Td>
                  <Badge
                    color={item.next_cursor ? 'green' : 'yellow'}
                    variant="light"
                    size="sm"
                  >
                    {item.next_cursor ? 'Synced' : 'Pending'}
                  </Badge>
                </Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      </Paper>

      {liabilities.length > 0 && (
        <Paper p="md" radius="md" bg="dark.6">
          <Title order={5} mb="md">Liabilities ({liabilities.length})</Title>
          <Table striped highlightOnHover>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Account</Table.Th>
                <Table.Th>Type</Table.Th>
                <Table.Th>Overdue</Table.Th>
                <Table.Th ta="right">Balance</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {liabilities.map((l) => (
                <Table.Tr key={l.account_id}>
                  <Table.Td>{l.account_id}</Table.Td>
                  <Table.Td>{l.type}</Table.Td>
                  <Table.Td>
                    <Text c={l.is_overdue ? 'red' : 'dimmed'}>
                      {l.is_overdue ? 'Yes' : 'No'}
                    </Text>
                  </Table.Td>
                  <Table.Td ta="right">
                    ${l.principal_amount?.toLocaleString('en-US', { minimumFractionDigits: 2 }) ?? '—'}
                  </Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        </Paper>
      )}
    </Stack>
  )
}
```

- [ ] **Step 2: Verify Accounts renders**

```bash
cd frontend && npx vite build
```

Expected: Build succeeds. Tables with accounts, institutions, liabilities.

---

### Task 7: Rewrite Transactions.tsx with Mantine React Table

**Files:**
- Modify: `frontend/src/pages/Transactions.tsx`

- [ ] **Step 1: Rewrite Transactions.tsx using MantineReactTable**

```tsx
import { useEffect, useMemo, useState } from 'react'
import { MantineReactTable, type MRT_ColumnDef } from 'mantine-react-table'
import { Text, Stack, Group, Loader, Center } from '@mantine/core'
import { IconAlertCircle } from '@tabler/icons-react'
import { api } from '../api/client'
import type { Transaction } from '../api/types'

function flattenCategory(category: Record<string, string> | null): string {
  if (!category) return ''
  return Object.values(category).filter(Boolean).join(' / ')
}

export default function Transactions() {
  const [transactions, setTransactions] = useState<Transaction[]>([])
  const [total, setTotal] = useState(0)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.getTransactions({ limit: 1000 })
      .then((res) => {
        setTransactions(res.transactions)
        setTotal(res.total)
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  const columns = useMemo<MRT_ColumnDef<Transaction>[]>(
    () => [
      {
        accessorKey: 'date',
        header: 'Date',
        size: 100,
        Cell: ({ cell }) => cell.getValue<string>(),
      },
      {
        accessorKey: 'name',
        header: 'Description',
        size: 250,
      },
      {
        id: 'category',
        header: 'Category',
        accessorFn: (row) => flattenCategory(row.category),
        size: 200,
      },
      {
        accessorKey: 'flow_type',
        header: 'Type',
        size: 100,
        Cell: ({ cell }) => {
          const val = cell.getValue<string>()
          const color = val === 'INCOME' ? 'green' : val === 'EXPENSE' ? 'red' : 'blue'
          return <Text c={`${color}.4`} size="sm">{val}</Text>
        },
      },
      {
        accessorKey: 'amount',
        header: 'Amount',
        size: 120,
        accessorFn: (row) => row.amount,
        Cell: ({ cell }) => {
          const val = cell.getValue<number>()
          const color = val > 0 ? 'red' : 'green'
          return (
            <Text c={`${color}.4`} ta="right" size="sm" fw={500}>
              ${Math.abs(val).toLocaleString('en-US', { minimumFractionDigits: 2 })}
            </Text>
          )
        },
      },
      {
        accessorKey: 'merchant_name',
        header: 'Merchant',
        size: 150,
        Cell: ({ cell }) => cell.getValue<string>() || '—',
      },
      {
        accessorKey: 'payment_channel',
        header: 'Channel',
        size: 100,
      },
      {
        accessorKey: 'pending',
        header: 'Pending',
        size: 80,
        Cell: ({ cell }) => cell.getValue<boolean>() ? 'Yes' : 'No',
      },
    ],
    [],
  )

  const income = transactions
    .filter((t) => t.flow_type === 'INCOME')
    .reduce((sum, t) => sum + t.amount, 0)

  const expenses = transactions
    .filter((t) => t.flow_type === 'EXPENSE')
    .reduce((sum, t) => sum + t.amount, 0)

  const net = income - expenses

  if (error) {
    return (
      <Center p="xl">
        <Group c="dimmed">
          <IconAlertCircle size={48} />
          <Text>{error}</Text>
        </Group>
      </Center>
    )
  }

  if (loading) {
    return (
      <Center p="xl">
        <Stack align="center" gap="sm">
          <Loader size="lg" />
          <Text c="dimmed">Loading transactions...</Text>
        </Stack>
      </Center>
    )
  }

  return (
    <Stack gap="md">
      <Text size="sm" c="dimmed">
        {transactions.length} of {total} transactions
      </Text>

      <MantineReactTable
        columns={columns}
        data={transactions}
        enablePagination
        enableSorting
        enableFilters
        enableGlobalFilter
        enableColumnFilters
        enableRowSelection={false}
        enableTopToolbar
        enableBottomToolbar
        initialState={{ pagination: { pageSize: 25, pageIndex: 0 } }}
        mantineTableProps={{
          striped: true,
          highlightOnHover: true,
        }}
      />

      <Group gap="lg" p="md" style={{ borderRadius: 8, backgroundColor: 'var(--mantine-color-dark-6)' }}>
        <Text size="sm">
          Income: <Text component="span" c="green.4" fw={700}>+${income.toFixed(2)}</Text>
        </Text>
        <Text size="sm">
          Expenses: <Text component="span" c="red.4" fw={700}>-${expenses.toFixed(2)}</Text>
        </Text>
        <Text size="sm">
          Net:{' '}
          <Text component="span" c={net >= 0 ? 'green.4' : 'red.4'} fw={700}>
            {net >= 0 ? '+' : '-'}${Math.abs(net).toFixed(2)}
          </Text>
        </Text>
      </Group>
    </Stack>
  )
}
```

- [ ] **Step 2: Verify Transactions renders with table + filtering/sorting**

```bash
cd frontend && npx vite build
```

Expected: Build succeeds. Table shows individual transactions with sortable columns, global search, column filters.

---

### Task 8: Rewrite SyncStatus.tsx

**Files:**
- Modify: `frontend/src/pages/SyncStatus.tsx`

- [ ] **Step 1: Rewrite SyncStatus.tsx with Mantine components**

```tsx
import { useEffect, useState, useRef } from 'react'
import {
  Stack,
  Paper,
  Title,
  Text,
  Button,
  Table,
  Badge,
  Loader,
  Center,
  Group,
  Box,
} from '@mantine/core'
import { IconRefresh, IconAlertCircle, IconCheck } from '@tabler/icons-react'
import { api } from '../api/client'
import type { PlaidItem } from '../api/types'

export default function SyncStatus() {
  const [items, setItems] = useState<PlaidItem[]>([])
  const [isSyncing, setIsSyncing] = useState(false)
  const [lastSync, setLastSync] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [syncLog, setSyncLog] = useState<string[]>([])
  const eventSourceRef = useRef<EventSource | null>(null)

  const fetchStatus = () => {
    api.getSyncStatus()
      .then((status) => {
        setItems(status.items)
        setLastSync(status.last_sync)
        setIsSyncing(status.is_running)
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    fetchStatus()
  }, [])

  const handleSync = async () => {
    setIsSyncing(true)
    setSyncLog([])
    try {
      await api.triggerSync()
      const sse = new EventSource('/api/sync/stream')
      eventSourceRef.current = sse
      sse.onmessage = (event) => {
        setSyncLog((prev) => [...prev, event.data])
      }
      sse.onerror = () => {
        sse.close()
        setIsSyncing(false)
        fetchStatus()
      }
    } catch (e: any) {
      setError(e.message)
      setIsSyncing(false)
    }
  }

  if (error) {
    return (
      <Center p="xl">
        <Stack align="center" gap="sm">
          <Group c="dimmed">
            <IconAlertCircle size={48} />
            <Text>{error}</Text>
          </Group>
          <Button variant="light" onClick={() => { setError(null); fetchStatus() }}>
            Retry
          </Button>
        </Stack>
      </Center>
    )
  }

  if (loading) {
    return (
      <Center p="xl">
        <Stack align="center" gap="sm">
          <Loader size="lg" />
          <Text c="dimmed">Loading sync status...</Text>
        </Stack>
      </Center>
    )
  }

  return (
    <Stack gap="md">
      <Paper p="md" radius="md" bg="dark.6">
        <Group justify="space-between" mb="md">
          <Title order={5}>Sync Status</Title>
          <Button
            leftSection={<IconRefresh size={16} />}
            onClick={handleSync}
            loading={isSyncing}
            disabled={isSyncing}
          >
            Sync Now
          </Button>
        </Group>

        {lastSync && (
          <Text size="sm" c="dimmed" mb="md">
            Last sync: {new Date(lastSync).toLocaleString()}
          </Text>
        )}

        {isSyncing && syncLog.length > 0 && (
          <Box
            p="sm"
            style={{
              backgroundColor: 'var(--mantine-color-dark-7)',
              borderRadius: 6,
              maxHeight: 200,
              overflow: 'auto',
              fontFamily: 'monospace',
              fontSize: 12,
            }}
          >
            {syncLog.map((line, i) => (
              <Text key={i} size="xs">{line}</Text>
            ))}
          </Box>
        )}
      </Paper>

      <Paper p="md" radius="md" bg="dark.6">
        <Title order={5} mb="md">Institutions ({items.length})</Title>
        <Table striped highlightOnHover>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Name</Table.Th>
              <Table.Th>Status</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {items.map((item) => (
              <Table.Tr key={item.item_id || item.institution_name}>
                <Table.Td>{item.institution_name || 'Unknown'}</Table.Td>
                <Table.Td>
                  <Badge
                    color={item.next_cursor ? 'green' : 'yellow'}
                    variant="light"
                    size="sm"
                  >
                    {item.next_cursor ? 'Synced' : 'Pending'}
                  </Badge>
                </Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      </Paper>
    </Stack>
  )
}
```

- [ ] **Step 2: Verify SyncStatus renders**

```bash
cd frontend && npx vite build
```

Expected: Build succeeds. Sync button, institution table, SSE log streaming.

---

### Task 9: Final verification + cleanup

**Files:**
- Modify: `frontend/src/styles/globals.css` (verify correct imports)
- Delete: `frontend/tailwind.config.js` (if not already deleted)

- [ ] **Step 1: Full production build**

```bash
cd frontend && npx vite build
```

Expected: Build succeeds with no errors.

- [ ] **Step 2: Start dev server and visually verify all 4 pages**

```bash
cd frontend && npx vite
```

Open http://localhost:5173 and check:
- Dashboard: stats cards render, chart renders, dark theme works
- Transactions: table renders with all columns, sorting works, filtering works
- Accounts: three tables render (accounts, institutions, liabilities)
- Sync Status: sync button works, institution table renders

- [ ] **Step 3: Verify theme switching works**

Click the sun/moon icon in the navbar. Should toggle between dark and light themes.

- [ ] **Step 4: Run final build to confirm no Tailwind remnants**

```bash
cd frontend && npx vite build 2>&1 | grep -i "tailwind\|daisy"
```

Expected: No output (no Tailwind/DaisyUI references remain).
