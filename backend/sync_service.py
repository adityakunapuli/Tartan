import os
import datetime
import pandas as pd
from dotenv import load_dotenv
import plaid
from plaid.api import plaid_api
from plaid.model.transactions_get_request import TransactionsGetRequest
from plaid.model.transactions_get_request_options import TransactionsGetRequestOptions

# Load environment
load_dotenv()

CSV_FILE = "transactions.csv"
DAYS_TO_FETCH = 30  # Fetch overlap to catch status changes (Pending -> Posted)


class TransactionSyncer:
    def __init__(self):
        self.access_token = os.getenv('PLAID_ACCESS_TOKEN')
        if not self.access_token:
            raise ValueError("PLAID_ACCESS_TOKEN not found in .env. Run setup_server.py first.")

        # Setup Client
        env_map = {
            'production': plaid.Environment.Production,
            'development': plaid.Environment.Development,
            'sandbox': plaid.Environment.Sandbox
        }
        host = env_map.get(os.getenv('PLAID_ENV', 'sandbox'), plaid.Environment.Sandbox)

        configuration = plaid.Configuration(
            host=host,
            api_key={
                'clientId': os.getenv('PLAID_CLIENT_ID'),
                'secret': os.getenv('PLAID_SECRET'),
            }
        )
        api_client = plaid.ApiClient(configuration)
        self.client = plaid_api.PlaidApi(api_client)

    def fetch_recent(self):
        end_date = datetime.date.today()
        start_date = end_date - datetime.timedelta(days=DAYS_TO_FETCH)

        print(f"Fetching Plaid data from {start_date} to {end_date}...")

        all_transactions = []
        offset = 0

        while True:
            request = TransactionsGetRequest(
                access_token=self.access_token,
                start_date=start_date,
                end_date=end_date,
                options=TransactionsGetRequestOptions(count=500, offset=offset)
            )

            try:
                response = self.client.transactions_get(request)
                txs = response['transactions']
                all_transactions.extend(txs)

                if len(all_transactions) >= response['total_transactions']:
                    break
                offset += len(txs)
            except plaid.ApiException as e:
                print(f"API Error: {e}")
                break

        return self._parse_transactions(all_transactions)

    def _parse_transactions(self, pl_transactions):
        data = []
        for t in pl_transactions:
            data.append({
                'transaction_id': t.transaction_id,
                'date': t.date,
                'amount': t.amount,
                'merchant': t.merchant_name or t.name,
                'category': t.category[0] if t.category else "Uncategorized",
                'pending': t.pending,
                'account_id': t.account_id
            })
        return pd.DataFrame(data)

    def sync(self):
        # 1. Get new data
        new_df = self.fetch_recent()
        if new_df.empty:
            print("No new data found.")
            return

        # 2. Load old data (if exists)
        if os.path.exists(CSV_FILE):
            try:
                old_df = pd.read_csv(CSV_FILE)
                # Ensure date column is datetime for sorting
                old_df['date'] = pd.to_datetime(old_df['date']).dt.date
                print(f"Loaded {len(old_df)} existing transactions.")
            except Exception:
                old_df = pd.DataFrame()
        else:
            old_df = pd.DataFrame()

        # 3. Merge: Combine old and new
        # We prioritize NEW data for the same transaction_id (to capture Pending -> Posted updates)
        combined_df = pd.concat([new_df, old_df])

        # Drop duplicates, keeping the first occurrence (which is from new_df due to concat order)
        # We rely on transaction_id being unique
        deduped_df = combined_df.drop_duplicates(subset=['transaction_id'], keep='first')

        # 4. Sort and Save
        deduped_df['date'] = pd.to_datetime(deduped_df['date'])  # Ensure datetime for sorting
        deduped_df = deduped_df.sort_values(by='date', ascending=False)

        deduped_df.to_csv(CSV_FILE, index=False)
        print(f"Sync Complete. Total transactions: {len(deduped_df)}. Saved to {CSV_FILE}")


if __name__ == "__main__":
    try:
        syncer = TransactionSyncer()
        syncer.sync()
    except Exception as e:
        print(f"Sync Failed: {e}")