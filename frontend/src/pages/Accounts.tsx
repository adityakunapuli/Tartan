import { useEffect, useMemo, useState } from 'react'
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
import { MantineReactTable, type MRT_ColumnDef } from 'mantine-react-table'
import { IconAlertCircle } from '@tabler/icons-react'
import { api } from '../api/client'
import type { Account, PlaidItem, Liability } from '../api/types'

const accountTypeColors: Record<string, string> = {
  depository: 'blue',
  investment: 'teal',
  credit: 'red',
  loan: 'orange',
  brokerage: 'violet',
  cash: 'green',
  '401k': 'pink',
}

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
      api.getLiabilities().catch(() => ({ liabilities: [] as Liability[] })),
    ])
      .then(([acc, sync, liab]) => {
        setAccounts(acc.accounts)
        setItems(sync.items)
        setLiabilities('liabilities' in liab ? liab.liabilities : liab)
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  const acctColumns = useMemo<MRT_ColumnDef<Account>[]>(
    () => [
      {
        accessorKey: 'name',
        header: 'Name',
        filterVariant: 'text',
      },
      {
        accessorKey: 'type',
        header: 'Type',
        filterVariant: 'select',
        mantineFilterSelectProps: {
          data: [
            { value: 'depository', label: 'Depository' },
            { value: 'credit', label: 'Credit' },
            { value: 'loan', label: 'Loan' },
            { value: 'investment', label: 'Investment' },
            { value: 'brokerage', label: 'Brokerage' },
          ],
        },
        Cell: ({ cell }) => {
          const val = cell.getValue<string>()
          return (
            <Badge color={accountTypeColors[val] || 'gray'} variant="light" size="sm">
              {val}
            </Badge>
          )
        },
      },
      {
        accessorKey: 'mask',
        header: 'Mask',
        enableColumnFilter: false,
        Cell: ({ cell }) => {
          const val = cell.getValue<string>()
          return val ? `****${val}` : '—'
        },
      },
      {
        accessorKey: 'current_balance',
        header: 'Balance',
        enableColumnFilter: false,
        Cell: ({ cell }) => {
          const val = cell.getValue<number>()
          return (
            <Text
              c={val >= 0 ? 'green.4' : 'red.4'}
              fw={600}
              ta="right"
            >
              ${val.toLocaleString('en-US', { minimumFractionDigits: 2 })}
            </Text>
          )
        },
      },
      {
        accessorKey: 'available_balance',
        header: 'Available',
        enableColumnFilter: false,
        Cell: ({ cell }) => {
          const val = cell.getValue<number | null>()
          if (val === null) return <Text c="dimmed">—</Text>
          return (
            <Text ta="right">
              ${val.toLocaleString('en-US', { minimumFractionDigits: 2 })}
            </Text>
          )
        },
      },
    ],
    [],
  )

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
      <Paper p="md" radius="md">
        <Title order={5} mb="md">Accounts ({accounts.length})</Title>
        <MantineReactTable
          columns={acctColumns}
          data={accounts}
          enableColumnFilters
          enableGlobalFilter
          enableSorting
          columnFilterDisplayMode="subheader"
          enableDensityToggle={false}
          enableRowSelection={false}
          enableTopToolbar
          enablePagination={false}
          enableColumnOrdering={false}
          initialState={{
            showGlobalFilter: true,
            showColumnFilters: true,
            sorting: [{ id: 'type', desc: false }, { id: 'current_balance', desc: true }],
          }}
          state={{ columnFilters: [] }}
          mantineTableProps={{
            withColumnBorders: true,
          }}
          mantineSearchTextInputProps={{
            style: { width: '200px' },
            size: 'xs',
            placeholder: 'Search accounts…',
          }}
          renderBottomToolbarCustomActions={({ table }) => {
            const total = table
              .getFilteredRowModel()
              .rows.reduce((s, r) => s + r.original.current_balance, 0)
            return (
              <Text size="sm" fw={600}>
                Total:{' '}
                <Text component="span" c="green.4">
                  ${total.toLocaleString('en-US', { minimumFractionDigits: 2 })}
                </Text>
              </Text>
            )
          }}
        />
      </Paper>

      <Paper p="md" radius="md">
        <Title order={5} mb="md">Institutions ({items.length})</Title>
        <Table highlightOnHover>
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
        <Paper p="md" radius="md">
          <Title order={5} mb="md">Liabilities ({liabilities.length})</Title>
          <Table highlightOnHover>
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