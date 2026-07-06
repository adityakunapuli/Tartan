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
  useComputedColorScheme,
} from '@mantine/core'
import {
  IconDashboard,
  IconArrowsExchange,
  IconBuildingBank,
  IconRefresh,
  IconSun,
  IconMoon,
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
  const computed = useComputedColorScheme()
  const location = useLocation()
  const [opened, setOpened] = useState(false)
  const isDark = computed === 'dark'

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
                color: isActive
                  ? 'var(--mantine-color-brand-4)'
                  : isDark
                    ? 'var(--mantine-color-dark-0)'
                    : undefined,
                backgroundColor: isActive
                  ? isDark
                    ? 'var(--mantine-color-dark-6)'
                    : 'var(--mantine-color-brand-0)'
                  : 'transparent',
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