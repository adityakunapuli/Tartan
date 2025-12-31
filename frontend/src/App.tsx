import { useEffect, useState, useCallback } from 'react';
import { usePlaidLink, PlaidLinkOptions, PlaidLinkOnSuccess, PlaidLinkOnExit } from 'react-plaid-link';
import axios from 'axios';

axios.defaults.baseURL = 'http://localhost:8000';

function App() {
  const [linkToken, setLinkToken] = useState<string | null>(null);
  const [accessToken, setAccessToken] = useState<string | null>(null);
  const [transactions, setTransactions] = useState<any[]>([]);
  const [investments, setInvestments] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [syncing, setSyncing] = useState(false);

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
    fetchData(); // Try fetching data on mount if already linked (token in backend)
  }, []);

  const onSuccess = useCallback<PlaidLinkOnSuccess>(async (public_token, metadata) => {
    try {
      const response = await axios.post('/api/set_access_token', { public_token });
      setAccessToken(response.data.access_token);
      alert("Account linked successfully!");
      handleSync();
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

  const fetchData = async () => {
    setLoading(true);
    try {
      const [txRes, invRes] = await Promise.all([
        axios.get('/api/transactions'),
        axios.get('/api/investments')
      ]);
      setTransactions(txRes.data);
      setInvestments(invRes.data);
    } catch (err) {
      console.error("Error fetching data:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleSync = async () => {
    setSyncing(true);
    try {
      await axios.post('/api/sync');
      alert("Sync Complete!");
      fetchData();
    } catch (err) {
      console.error("Error syncing data:", err);
      alert("Sync failed. Check console.");
    } finally {
      setSyncing(false);
    }
  };

  return (
    <div style={{ padding: '20px', fontFamily: 'Arial, sans-serif', maxWidth: '1200px', margin: '0 auto' }}>
      <h1>Plaid Local Analysis</h1>
      
      <div style={{ marginBottom: '20px', display: 'flex', gap: '10px' }}>
        <button onClick={() => open()} disabled={!ready || !linkToken}>
          Link New Account
        </button>
        <button onClick={handleSync} disabled={syncing}>
          {syncing ? 'Syncing...' : 'Sync Data from Plaid'}
        </button>
        <button onClick={fetchData} disabled={loading}>
          {loading ? 'Refreshing...' : 'Refresh View'}
        </button>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
        <div>
          <h2>Recent Transactions</h2>
          {transactions.length === 0 ? <p>No transactions found. Try syncing.</p> : (
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
                    <td>{t.name}</td>
                    <td style={{ textAlign: 'right' }}>${t.amount.toFixed(2)}</td>
                    <td>{t.category}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        <div>
          <h2>Investment Holdings</h2>
          {investments.length === 0 ? <p>No investments found. Try syncing.</p> : (
            <table border={1} cellPadding={5} style={{ borderCollapse: 'collapse', width: '100%' }}>
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Ticker</th>
                  <th>Quantity</th>
                  <th>Price</th>
                  <th>Value</th>
                </tr>
              </thead>
              <tbody>
                {investments.map((i: any) => (
                  <tr key={i.id}>
                    <td>{i.security_name}</td>
                    <td>{i.ticker}</td>
                    <td style={{ textAlign: 'right' }}>{i.quantity.toFixed(4)}</td>
                    <td style={{ textAlign: 'right' }}>${i.price.toFixed(2)}</td>
                    <td style={{ textAlign: 'right' }}>${i.value.toFixed(2)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}

export default App;
