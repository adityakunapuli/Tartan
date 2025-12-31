import { useEffect, useState, useCallback } from 'react';
import { usePlaidLink, PlaidLinkOptions, PlaidLinkOnSuccess, PlaidLinkOnExit } from 'react-plaid-link';
import axios from 'axios';

// Configure axios base URL - assuming proxy is set in vite.config.ts
// or we can use full URL http://localhost:8000
axios.defaults.baseURL = 'http://localhost:8000';

function App() {
  const [linkToken, setLinkToken] = useState<string | null>(null);
  const [accessToken, setAccessToken] = useState<string | null>(null);
  const [transactions, setTransactions] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);

  // 1. Create Link Token on mount
  useEffect(() => {
    async function createLinkToken() {
      try {
        const response = await axios.post('/api/create_link_token');
        setLinkToken(response.data.link_token);
      } catch (err) {
        console.error("Error creating link token:", err);
      }
    }
    createLinkToken();
  }, []);

  // 2. Handle Success: Exchange Public Token for Access Token
  const onSuccess = useCallback<PlaidLinkOnSuccess>(async (public_token, metadata) => {
    try {
      const response = await axios.post('/api/set_access_token', { public_token });
      setAccessToken(response.data.access_token);
      alert("Account linked successfully!");
    } catch (err) {
      console.error("Error exchanging public token:", err);
    }
  }, []);

  const onExit = useCallback<PlaidLinkOnExit>((error, metadata) => {
    if (error) {
      console.error("Link Exited with Error:", error);
      alert(`Link Error: ${error.display_message || error.error_message}`);
    } else {
      console.log("Link Exited:", metadata);
    }
  }, []);

  const config: PlaidLinkOptions = {
    token: linkToken,
    onSuccess,
    onExit,
  };

  const { open, ready } = usePlaidLink(config);

  // 3. Fetch Transactions
  const fetchTransactions = async () => {
    if (!accessToken) return;
    setLoading(true);
    try {
      const response = await axios.get('/api/transactions');
      setTransactions(response.data.transactions);
    } catch (err) {
      console.error("Error fetching transactions:", err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ padding: '20px', fontFamily: 'Arial, sans-serif' }}>
      <h1>Plaid Local Analysis</h1>
      
      {!accessToken ? (
        <div>
          <p>Link your bank account to get started.</p>
          <button onClick={() => open()} disabled={!ready || !linkToken}>
            Connect a Bank Account
          </button>
        </div>
      ) : (
        <div>
          <p>Account Connected!</p>
          <div style={{ background: '#f0f0f0', padding: '10px', margin: '10px 0', wordBreak: 'break-all' }}>
            <strong>Access Token:</strong> {accessToken}
          </div>
          <button onClick={fetchTransactions} disabled={loading}>
            {loading ? 'Fetching...' : 'Fetch Recent Transactions'}
          </button>
        </div>
      )}

      {transactions.length > 0 && (
        <div style={{ marginTop: '20px' }}>
          <h2>Transactions</h2>
          <table border={1} cellPadding={5} style={{ borderCollapse: 'collapse', width: '100%' }}>
            <thead>
              <tr>
                <th>Date</th>
                <th>Name</th>
                <th>Amount</th>
                <th>Category</th>
              </tr>
            </thead>
            <tbody>
              {transactions.map((t: any) => (
                <tr key={t.transaction_id}>
                  <td>{t.date}</td>
                  <td>{t.merchant_name || t.name}</td>
                  <td>${t.amount}</td>
                  <td>{t.category ? t.category[0] : 'N/A'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

export default App;
