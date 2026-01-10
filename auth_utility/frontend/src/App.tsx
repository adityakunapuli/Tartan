import { useEffect, useState, useCallback } from 'react';
import { usePlaidLink, PlaidLinkOptions, PlaidLinkOnSuccess, PlaidLinkOnExit } from 'react-plaid-link';
import axios from 'axios';

axios.defaults.baseURL = 'http://localhost:8000';

function App() {
  const [linkToken, setLinkToken] = useState<string | null>(null);
  const [accessToken, setAccessToken] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function createLinkToken() {
      try {
        const response = await axios.post('/api/create_link_token');
        setLinkToken(response.data.link_token);
      } catch (err: any) {
        console.error("Error creating link token:", err);
        setError(err.message || "Failed to load Link Token");
      }
    }
    createLinkToken();
  }, []);

  const onSuccess = useCallback<PlaidLinkOnSuccess>(async (public_token, metadata) => {
    try {
      const response = await axios.post('/api/set_access_token', { public_token });
      setAccessToken(response.data.access_token);
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

  return (
    <div style={{ padding: '40px', fontFamily: 'Arial, sans-serif', maxWidth: '800px', margin: '0 auto', textAlign: 'center' }}>
      <h1>Plaid Setup Utility</h1>
      <p style={{ marginBottom: '30px', color: '#666' }}>
        Use this page to authenticate with your bank and generate an Access Token.
      </p>

      {error && (
        <div style={{ color: 'red', marginBottom: '20px', padding: '10px', border: '1px solid red', borderRadius: '4px' }}>
          <strong>Error:</strong> {error}
        </div>
      )}
      
      {!accessToken ? (
        <button 
          onClick={() => open()} 
          disabled={!ready || !linkToken}
          style={{ padding: '12px 24px', fontSize: '16px', cursor: 'pointer' }}
        >
          Connect a Bank Account
        </button>
      ) : (
        <div style={{ background: '#f8f9fa', padding: '20px', borderRadius: '8px', border: '1px solid #ddd', textAlign: 'left' }}>
          <h3 style={{ marginTop: 0, color: 'green' }}>Authentication Successful!</h3>
          <p>Please copy the Access Token below and add it to your <code>.env</code> file as <code>PLAID_ACCESS_TOKEN</code>.</p>
          <div style={{ 
            background: '#fff', 
            padding: '15px', 
            border: '1px solid #ccc', 
            borderRadius: '4px',
            fontFamily: 'monospace',
            wordBreak: 'break-all',
            margin: '15px 0'
          }}>
            {accessToken}
          </div>
          <p style={{ fontSize: '0.9em', color: '#666' }}>
            Once saved, you can close this window and run the scripts in the <code>analysis/</code> folder.
          </p>
        </div>
      )}
    </div>
  );
}

export default App;
