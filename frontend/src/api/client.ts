import type { Account, Transaction, Liability, DashboardSummary, SyncStatus, PlaidItem } from './types'

const BASE = '/api'

async function fetchJSON<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, {
    headers: { 'Content-Type': 'application/json', ...init?.headers },
    ...init,
  })
  if (!res.ok) {
    const body = await res.text()
    throw new Error(`${res.status}: ${body}`)
  }
  return res.json()
}

export const api = {
  // Health
  health: () => fetchJSON<{ status: string }>('/health'),

  // Dashboard
  getDashboard: () => fetchJSON<DashboardSummary>(`${BASE}/dashboard/summary`),
  getTransactions: (params?: { account_id?: string; limit?: number; offset?: number; search?: string }) => {
    const qs = new URLSearchParams()
    if (params?.account_id) qs.set('account_id', params.account_id)
    if (params?.limit) qs.set('limit', String(params.limit))
    if (params?.offset) qs.set('offset', String(params.offset))
    if (params?.search) qs.set('search', params.search)
    return fetchJSON<{ transactions: Transaction[]; total: number }>(`${BASE}/transactions?${qs}`)
  },
  getAccounts: () => fetchJSON<{ accounts: Account[] }>(`${BASE}/accounts`),
  getLiabilities: () => fetchJSON<{ liabilities: Liability[] }>(`${BASE}/liabilities`),
  getSyncStatus: () => fetchJSON<SyncStatus>(`${BASE}/sync/status`),
  triggerSync: () => fetchJSON<{ status: string }>(`${BASE}/sync/trigger`, { method: 'POST' }),

  // Plaid Link
  createLinkToken: () => fetchJSON<{ link_token: string }>('/plaid/create_link_token'),
  exchangeToken: (public_token: string) =>
    fetchJSON<{ status: string }>('/plaid/exchange_token', {
      method: 'POST',
      body: JSON.stringify({ public_token }),
    }),
}
