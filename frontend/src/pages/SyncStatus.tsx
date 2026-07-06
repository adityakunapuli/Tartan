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
import { IconRefresh, IconAlertCircle } from '@tabler/icons-react'
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
