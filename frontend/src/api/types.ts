export interface Account {
  account_id: string
  name: string
  mask: string
  type: string
  current_balance: number
  available_balance: number | null
  last_updated: string
}

export interface PlaidItem {
  access_token: string
  item_id: string | null
  institution_id: string | null
  institution_name: string | null
  next_cursor: string | null
}

export interface Transaction {
  transaction_id: string
  account_id: string
  date: string
  name: string
  amount: number
  currency: string
  flow_type: 'INCOME' | 'EXPENSE' | 'TRANSFER'
  category: Record<string, string>
  category_id: string | null
  enriched_category: string | null
  pending: boolean
  merchant_name: string | null
  payment_channel: string
  is_recurring: boolean | null
}

export interface Liability {
  account_id: string
  type: string
  is_overdue: boolean
  last_payment_amount: number | null
  last_payment_date: string | null
  next_payment_due_date: string | null
  minimum_payment_amount: number | null
  principal_amount: number | null
  interest_rate_percentage: number | null
  expected_payoff_date: string | null
}

export interface DashboardSummary {
  total_balance: number
  total_assets: number
  total_liabilities: number
  monthly_income: number
  monthly_expenses: number
  net_worth: number
}

export interface SyncStatus {
  is_running: boolean
  last_sync: string | null
  items: PlaidItem[]
}
