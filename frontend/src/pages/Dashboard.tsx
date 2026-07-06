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
    { label: 'Net Worth', value: data.net_worth, color: 'green' as const },
    { label: 'Total Balance', value: data.total_balance, color: 'white' as const },
    { label: 'Monthly Income', value: data.monthly_income, color: 'green' as const },
    { label: 'Monthly Expenses', value: data.monthly_expenses, color: 'red' as const },
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
