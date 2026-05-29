import { useState, FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../lib/api';

type Tab = 'login' | 'register';

export default function LoginPage() {
  const [tab, setTab] = useState<Tab>('login');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [otp, setOtp] = useState('');
  const [showOtp, setShowOtp] = useState(false);
  const [pendingEmail, setPendingEmail] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleRegister = async (e: FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await api.post('/auth/register', { email, password });
      setPendingEmail(email);
      setShowOtp(true);
      setError('');
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || 'Registration failed';
      setError(msg);
    }
    setLoading(false);
  };

  const handleVerifyOtp = async (e: FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await api.post('/auth/verify-otp', { email: pendingEmail, code: otp });
      navigate('/');
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || 'Invalid code';
      setError(msg);
    }
    setLoading(false);
  };

  const handleLogin = async (e: FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await api.post('/auth/login', { email, password });
      navigate('/');
    } catch (err: unknown) {
      const errData = (err as { response?: { data?: { detail?: string }; status?: number } })?.response;
      const msg = errData?.data?.detail || 'Login failed';
      if (errData?.status === 403 && msg.includes('not verified')) {
        setPendingEmail(email);
        setShowOtp(true);
        setError('');
      } else {
        setError(msg);
      }
    }
    setLoading(false);
  };

  const handleOAuth = async (provider: string) => {
    setError('');
    try {
      const res = await api.get(`/auth/${provider}/login`);
      window.location.href = res.data.redirect_url;
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || 'OAuth not configured';
      setError(msg);
    }
  };

  if (showOtp) {
    return (
      <div className="min-h-screen flex items-center justify-center px-4" style={{ backgroundColor: 'var(--color-paper)' }}>
        <div className="w-full max-w-sm">
          <div className="rounded-card p-8" style={{ backgroundColor: 'var(--color-paper-2)', border: '1px solid var(--color-rule-subtle)' }}>
            <h1 className="font-display text-2xl font-semibold mb-1 text-center" style={{ color: 'var(--color-ink)', letterSpacing: '-0.02em' }}>
              Check your email
            </h1>
            <p className="text-sm text-center mb-6" style={{ color: 'var(--color-ink-2)' }}>
              We sent a 6-digit code to <strong>{pendingEmail}</strong>
            </p>
            <form onSubmit={handleVerifyOtp}>
              <input
                type="text"
                value={otp}
                onChange={e => setOtp(e.target.value.replace(/\D/g, '').slice(0, 6))}
                placeholder="000000"
                maxLength={6}
                autoFocus
                className="w-full rounded-input px-4 py-3 text-center text-xl font-outlier tracking-widest mb-4"
                style={{ backgroundColor: 'var(--color-paper-1)', border: '1px solid var(--color-rule-subtle)', color: 'var(--color-ink)' }}
              />
              {error && (
                <p className="text-xs mb-3 text-center" style={{ color: 'var(--color-severity-critical)' }}>{error}</p>
              )}
              <button
                type="submit"
                disabled={loading || otp.length !== 6}
                className="w-full rounded-pill py-2.5 text-sm font-medium transition-colors disabled:opacity-50 mb-3"
                style={{ backgroundColor: 'var(--color-accent)', color: 'var(--color-paper)', border: 'none', transitionDuration: 'var(--dur-short)' }}
              >
                {loading ? 'Verifying…' : 'Verify Code'}
              </button>
              <button
                type="button"
                onClick={() => { setShowOtp(false); setOtp(''); }}
                className="w-full text-xs transition-colors"
                style={{ color: 'var(--color-ink-2)', transitionDuration: 'var(--dur-short)' }}
              >
                ← Back
              </button>
            </form>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center px-4" style={{ backgroundColor: 'var(--color-paper)' }}>
      <div className="w-full max-w-sm">
        <div className="text-center mb-8">
          <h1 className="font-display text-3xl font-semibold mb-1" style={{ color: 'var(--color-ink)', letterSpacing: '-0.02em' }}>
            PRLens
          </h1>
          <p className="text-sm" style={{ color: 'var(--color-ink-2)' }}>
            AI-powered PR review
          </p>
        </div>

        <div className="rounded-card p-6"
          style={{ backgroundColor: 'var(--color-paper-2)', border: '1px solid var(--color-rule-subtle)' }}>
          <div className="flex mb-5 rounded-pill p-0.5" style={{ backgroundColor: 'var(--color-paper-3)' }}>
            {(['login', 'register'] as Tab[]).map(t => (
              <button
                key={t}
                onClick={() => { setTab(t); setError(''); }}
                className="flex-1 py-1.5 text-sm font-medium rounded-pill transition-colors capitalize"
                style={{
                  backgroundColor: tab === t ? 'var(--color-paper-2)' : 'transparent',
                  color: tab === t ? 'var(--color-ink)' : 'var(--color-ink-2)',
                  transitionDuration: 'var(--dur-short)',
                }}
              >
                {t}
              </button>
            ))}
          </div>

          <form onSubmit={tab === 'login' ? handleLogin : handleRegister}>
            <input
              type="email"
              value={email}
              onChange={e => setEmail(e.target.value)}
              placeholder="Email"
              required
              autoComplete="email"
              className="w-full rounded-input px-3 py-2.5 text-sm mb-3"
              style={{ backgroundColor: 'var(--color-paper-1)', border: '1px solid var(--color-rule-subtle)', color: 'var(--color-ink)' }}
            />
            <input
              type="password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              placeholder="Password"
              required
              minLength={8}
              autoComplete={tab === 'login' ? 'current-password' : 'new-password'}
              className="w-full rounded-input px-3 py-2.5 text-sm mb-4"
              style={{ backgroundColor: 'var(--color-paper-1)', border: '1px solid var(--color-rule-subtle)', color: 'var(--color-ink)' }}
            />

            {error && (
              <p className="text-xs mb-3" style={{ color: 'var(--color-severity-critical)' }}>{error}</p>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full rounded-pill py-2.5 text-sm font-medium transition-colors disabled:opacity-50 mb-4"
              style={{
                backgroundColor: 'var(--color-accent)',
                color: 'var(--color-paper)',
                border: 'none',
                transitionDuration: 'var(--dur-short)',
                transitionTimingFunction: 'var(--ease-out)',
              }}
            >
              {loading ? 'Please wait…' : tab === 'login' ? 'Sign In' : 'Create Account'}
            </button>
          </form>

          <div className="flex items-center gap-3 mb-4">
            <div className="flex-1" style={{ height: 1, backgroundColor: 'var(--color-rule-subtle)' }} />
            <span className="text-xs" style={{ color: 'var(--color-muted)' }}>or</span>
            <div className="flex-1" style={{ height: 1, backgroundColor: 'var(--color-rule-subtle)' }} />
          </div>

          <div className="space-y-2">
            <button
              onClick={() => handleOAuth('google')}
              className="w-full rounded-pill py-2.5 text-sm font-medium transition-colors flex items-center justify-center gap-2"
              style={{
                backgroundColor: 'var(--color-paper-1)',
                color: 'var(--color-ink)',
                border: '1px solid var(--color-rule-subtle)',
                transitionDuration: 'var(--dur-short)',
                transitionTimingFunction: 'var(--ease-out)',
              }}
            >
              <svg width="18" height="18" viewBox="0 0 24 24"><path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z"/><path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/><path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/><path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/></svg>
              Continue with Google
            </button>
            <button
              onClick={() => handleOAuth('github')}
              className="w-full rounded-pill py-2.5 text-sm font-medium transition-colors flex items-center justify-center gap-2"
              style={{
                backgroundColor: '#24292e',
                color: '#fff',
                border: 'none',
                transitionDuration: 'var(--dur-short)',
                transitionTimingFunction: 'var(--ease-out)',
              }}
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor"><path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"/></svg>
              Continue with GitHub
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
