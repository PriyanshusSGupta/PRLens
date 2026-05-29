import { useEffect, useRef, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import api from '../lib/api';

export default function AuthCallback() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [status, setStatus] = useState('Processing authentication…');
  const [error, setError] = useState('');
  const startedRef = useRef(false);

  useEffect(() => {
    if (startedRef.current) return;
    startedRef.current = true;

    const exchangeToken = searchParams.get('exchange_token');
    const githubConnectNeeded = searchParams.get('github_connect_needed') === 'true';

    if (exchangeToken) {
      api.post('/auth/exchange', { exchange_token: exchangeToken })
        .then(() => {
          setStatus('Authentication successful! Redirecting…');
          const dest = githubConnectNeeded ? '/repos?connect_github=true' : '/';
          setTimeout(() => navigate(dest), 800);
        })
        .catch(() => {
          api.get('/auth/me').then(() => {
            setStatus('Already authenticated! Redirecting…');
            setTimeout(() => navigate('/'), 800);
          }).catch(() => {
            setError('Session exchange failed. Please try again.');
            setTimeout(() => navigate('/login'), 2000);
          });
        });
    } else {
      api.get('/auth/me').then(() => {
        navigate('/');
      }).catch(() => {
        setError('No session token received.');
        setTimeout(() => navigate('/login'), 2000);
      });
    }
  }, [searchParams, navigate]);

  return (
    <div className="min-h-screen flex items-center justify-center px-4" style={{ backgroundColor: 'var(--color-paper)' }}>
      <div className="rounded-card p-10 text-center max-w-md"
        style={{ backgroundColor: 'var(--color-paper-2)', border: '1px solid var(--color-rule-subtle)' }}>
        {error ? (
          <>
            <h2 className="font-display text-xl font-semibold mb-2" style={{ color: 'var(--color-severity-critical)' }}>
              Authentication Failed
            </h2>
            <p className="text-sm" style={{ color: 'var(--color-ink-2)' }}>{error}</p>
          </>
        ) : (
          <>
            <h2 className="font-display text-xl font-semibold mb-2" style={{ color: 'var(--color-ink)', letterSpacing: '-0.02em' }}>
              Connecting
            </h2>
            <p className="text-sm" style={{ color: 'var(--color-ink-2)' }}>{status}</p>
            <div className="mt-6 w-8 h-8 mx-auto border-2 border-t-transparent rounded-full animate-spin"
              style={{ borderColor: 'var(--color-rule)', borderTopColor: 'var(--color-accent)' }} />
          </>
        )}
      </div>
    </div>
  );
}
