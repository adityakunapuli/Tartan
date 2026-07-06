import { useEffect, useMemo, useState } from 'react'
import {
  MantineReactTable,
  type MRT_ColumnDef,
  type MRT_ColumnFiltersState,
} from 'mantine-react-table'
import { Badge, Text, Group, Stack, Center, Loader } from '@mantine/core'
import { api } from '../api/client'
import type { Transaction, Account } from '../api/types'

export default function Transactions() {
  const [transactions, setTransactions] = useState<Transaction[]>([])
  const [accounts, setAccounts] = useState<Account[]>([])
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [columnFilters, setColumnFilters] = useState<MRT_ColumnFiltersState>(
    [],
  )

  useEffect(() => {
    Promise.all([
      api.getTransactions({ limit: 2000 }),
      api.getAccounts(),
    ])
      .then(([txRes, acctRes]) => {
        setTransactions(txRes.transactions)
        setAccounts(acctRes.accounts)
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  const accountMap = useMemo(() => {
    const map: Record<string, string> = {}
    for (const a of accounts) {
      map[a.account_id] = a.name
    }
    return map
  }, [accounts])

  const columns = useMemo<MRT_ColumnDef<Transaction>[]>(
    () => [
      {
        accessorKey: 'date',
        header: 'Date',
        enableColumnFilter: true,
        filterVariant: 'date',
      },
      {
        accessorKey: 'name',
        header: 'Description',
        filterVariant: 'text',
      },
      {
        id: 'account',
        header: 'Account',
        accessorFn: (row) => accountMap[row.account_id] || row.account_id,
        filterVariant: 'text',
      },
      {
        accessorKey: 'enriched_category',
        header: 'Category',
        filterVariant: 'text',
        Cell: ({ cell }) => {
          const val = cell.getValue<string | null>()
          return val || <Text c="dimmed">—</Text>
        },
      },
      {
        accessorKey: 'flow_type',
        header: 'Type',
        filterVariant: 'select',
        mantineFilterSelectProps: {
          data: [
            { value: 'INCOME', label: 'Income' },
            { value: 'EXPENSE', label: 'Expense' },
            { value: 'TRANSFER', label: 'Transfer' },
          ],
        },
        Cell: ({ cell }) => {
          const val = cell.getValue<string>()
          const color =
            val === 'INCOME' ? 'green' : val === 'EXPENSE' ? 'red' : 'blue'
          return (
            <Badge color={color} variant="light" size="sm">
              {val}
            </Badge>
          )
        },
      },
      {
        accessorKey: 'amount',
        header: 'Amount',
        Footer: ({ table }) => {
          const total = table
            .getFilteredRowModel()
            .rows.reduce((sum, r) => sum + r.original.amount, 0)
          return `$${Math.abs(total).toLocaleString('en-US', {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
          })}`
        },
        enableAggregation: true,
        aggregationFn: 'sum',
        Cell: ({ cell }) => {
          const val = cell.getValue<number>()
          return (
            <Text
              c={val > 0 ? 'red.4' : 'green.4'}
              size="sm"
              fw={500}
              ta="right"
            >
              ${Math.abs(val).toLocaleString('en-US', {
                minimumFractionDigits: 2,
              })}
            </Text>
          )
        },
      },
      {
        accessorKey: 'merchant_name',
        header: 'Merchant',
        Cell: ({ cell }) => cell.getValue<string>() || '—',
        filterVariant: 'text',
      },
      {
        accessorKey: 'payment_channel',
        header: 'Channel',
        filterVariant: 'select',
        mantineFilterSelectProps: {
          data: [
            { value: 'online', label: 'Online' },
            { value: 'store', label: 'Store' },
            { value: 'atm', label: 'ATM' },
            { value: 'bank', label: 'Bank' },
            { value: 'other', label: 'Other' },
          ],
        },
      },
      {
        accessorKey: 'pending',
        header: 'Status',
        filterVariant: 'select',
        mantineFilterSelectProps: {
          data: [
            { value: 'true', label: 'Pending' },
            { value: 'false', label: 'Posted' },
          ],
        },
        Cell: ({ cell }) => {
          const val = cell.getValue<boolean>()
          return val ? (
            <Badge color="yellow" variant="light" size="sm">
              Pending
            </Badge>
          ) : (
            <Badge color="green" variant="light" size="sm">
              Posted
            </Badge>
          )
        },
      },
      {
        accessorKey: 'is_recurring',
        header: 'Recurring',
        filterVariant: 'select',
        mantineFilterSelectProps: {
          data: [
            { value: 'true', label: 'Recurring' },
            { value: 'false', label: 'One-time' },
          ],
        },
        Cell: ({ cell }) => {
          const val = cell.getValue<boolean | null>()
          if (val === null) return <Text c="dimmed">—</Text>
          return val ? (
            <Badge color="violet" variant="light" size="sm">
              Recurring
            </Badge>
          ) : null
        },
      },
    ],
    [accountMap, columnFilters],
  )

  if (error) {
    return (
      <Center p="xl">
        <Text c="dimmed">{error}</Text>
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
    <MantineReactTable
      columns={columns}
      data={transactions}
      enableColumnFilters
      enableGlobalFilter
      enableSorting
      enablePagination
      columnFilterDisplayMode="subheader"
      enableDensityToggle={false}
      enableRowSelection={false}
      enableTopToolbar
      enableColumnOrdering
      initialState={{
        showGlobalFilter: true,
        showColumnFilters: true,
        pagination: { pageSize: 25, pageIndex: 0 },
        sorting: [{ id: 'flow_type', desc: false }, { id: 'amount', desc: true }],
        columnVisibility: {
          merchant_name: false,
        },
      }}
      columnFilterModeOptions={['popover', 'subheader']}
      onColumnFiltersChange={setColumnFilters}
      state={{ columnFilters }}
      mantineTableProps={{
        withColumnBorders: true,
      }}
      mantineTableContainerProps={{
        style: { overflowX: 'auto' },
      }}
      mantineSearchTextInputProps={{
        style: { width: '250px' },
        size: 'xs',
        placeholder: 'Search all columns…',
      }}
      renderBottomToolbarCustomActions={({ table }) => {
        const rows = table.getFilteredRowModel().rows
        const income = rows
          .filter((r) => r.original.flow_type === 'INCOME')
          .reduce((s, r) => s + r.original.amount, 0)
        const expenses = rows
          .filter((r) => r.original.flow_type === 'EXPENSE')
          .reduce((s, r) => s + r.original.amount, 0)
        const net = income - expenses
        return (
          <Group gap="lg">
            <Text size="sm">
              Income:{' '}
              <Text component="span" c="green.4" fw={700}>
                +${income.toFixed(2)}
              </Text>
            </Text>
            <Text size="sm">
              Expenses:{' '}
              <Text component="span" c="red.4" fw={700}>
                -${expenses.toFixed(2)}
              </Text>
            </Text>
            <Text size="sm">
              Net:{' '}
              <Text
                component="span"
                c={net >= 0 ? 'green.4' : 'red.4'}
                fw={700}
              >
                {net >= 0 ? '+' : '-'}${Math.abs(net).toFixed(2)}
              </Text>
            </Text>
          </Group>
        )
      }}
    />
  )
}