# Personal Financial Dashboard Plan

## Overview
We will build a modern, interactive dashboard to visualize the financial data collected by `plaid-local`. This dashboard will replace the static CLI reports with a dynamic web interface.

**Framework Choice:** [Streamlit](https://streamlit.io/)
*   **Reason:** Native Python support, excellent for data visualization, rapid development, and direct integration with our existing Pandas/SQLModel stack.

## Architecture

```text
A:\projects\plaid-local
├── dashboard.py           <-- Main Entry Point
├── components/            <-- UI Components
│   ├── __init__.py
│   ├── overview.py        <-- Net Worth, Burn Rate
│   ├── spending.py        <-- Categorization, Merchant Analysis
│   ├── investments.py     <-- Portfolio Performance
│   └── data_grid.py       <-- Raw Data Inspector
└── .streamlit/
    └── config.toml        <-- Theme & Server Settings
```

## Features

### 1. Overview (Home)
*   **Key Metrics:** Total Liquid Cash, Credit Card Debt, Net Worth (Assets - Liabilities).
*   **Health Check:** "Burn Rate" vs "Income" gauge.
*   **Recent Activity:** Table of last 10 transactions.

### 2. Spending Analysis
*   **Time Series:** Monthly spending trends.
*   **Category Breakdown:** Interactive Pie/Donut chart of spending by `enriched_category`.
*   **Merchant Inspector:** Bar chart of top merchants.
*   **Drill-down:** Click a category to see associated transactions.

### 3. Investment Portfolio
*   **Holdings Table:** Current positions with live prices (from Plaid snapshot).
*   **Allocation:** Asset allocation by `type` (Equity, Mutual Fund, etc.).
*   **Performance:** YTD Gain/Loss summary.

### 4. Data Management (Admin)
*   **Manual Trigger:** Button to run `run_sync()` and `run_categorization()` directly from UI.
*   **Rule Editor:** Simple table editor to modify `CategoryRule` entries manually.

## Implementation Steps

1.  **Dependencies:** Add `streamlit` and `plotly` to `pyproject.toml`.
2.  **Layout:** Create `dashboard.py` with a sidebar for navigation and filters (Date Range, Account Picker).
3.  **Components:** Port logic from `reports/` into visual components.
    *   `reports/financial_health.py` -> `components/overview.py`
    *   `reports/portfolio_summary.py` -> `components/spending.py` & `components/investments.py`
4.  **Visualization:** Use `plotly.express` for interactive charts.

## Usage
```bash
uv run streamlit run dashboard.py
```
