import { useState, useEffect } from 'react';
import api from '../lib/api';

interface Provider {
  label: string;
  default_model: string;
  docs_url: string;
  env_var: string;
}

interface Presets {
  [key: string]: Provider;
}

export default function AISettings() {
  const [presets, setPresets] = useState<Presets>({});
  const [config, setConfig] = useState<{ configured: boolean; provider: string; model: string }>({
    configured: false, provider: '', model: '',
  });
  const [selectedProvider, setSelectedProvider] = useState('openai');
  const [apiKey, setApiKey] = useState('');
  const [model, setModel] = useState('');
  const [customUrl, setCustomUrl] = useState('');
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState('');

  useEffect(() => {
    api.get('/ai/presets').then(r => setPresets(r.data));
    api.get('/ai/config').then(r => setConfig(r.data));
  }, []);

  const provider = presets[selectedProvider];

  useEffect(() => {
    if (provider) setModel(provider.default_model);
  }, [selectedProvider, provider]);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setMessage('');
    try {
      await api.put('/ai/config', {
        provider: selectedProvider,
        api_key: apiKey,
        model: model || undefined,
        base_url: selectedProvider === 'custom' ? customUrl : undefined,
      });
      setConfig({ configured: true, provider: selectedProvider, model: model || provider?.default_model || '' });
      setApiKey('');
      setMessage('AI configuration saved successfully.');
    } catch {
      setMessage('Failed to save configuration.');
    }
    setSaving(false);
  };

  const handleDelete = async () => {
    await api.delete('/ai/config');
    setConfig({ configured: false, provider: '', model: '' });
    setMessage('AI configuration removed.');
  };

  return (
    <div className="max-w-2xl mx-auto">
      <h1 className="font-display text-2xl font-semibold mb-1.5" style={{ letterSpacing: '-0.02em', color: 'var(--color-ink)' }}>
        AI Settings
      </h1>
      <p className="text-sm mb-8" style={{ color: 'var(--color-ink-2)' }}>
        Connect your own AI provider to enable LLM-powered PR reviews. Your API key is encrypted at rest.
      </p>

      {message && (
        <div className="rounded-card p-3 mb-6 text-sm"
          style={{
            backgroundColor: 'var(--color-paper-2)',
            border: `1px solid ${message.includes('Failed') ? 'var(--color-severity-critical)' : 'var(--color-cat-testing)'}`,
            color: 'var(--color-ink)',
          }}>
          {message}
        </div>
      )}

      {config.configured && (
        <div className="rounded-card p-5 mb-6"
          style={{ backgroundColor: 'var(--color-paper-2)', border: '1px solid var(--color-rule-subtle)' }}>
          <div className="flex items-center justify-between mb-3">
            <span className="text-sm font-medium" style={{ color: 'var(--color-ink)' }}>Current Configuration</span>
            <button onClick={handleDelete} className="text-xs rounded-pill px-3 py-1 transition-colors"
              style={{
                color: 'var(--color-severity-critical)',
                border: '1px solid var(--color-severity-critical)',
                transitionDuration: 'var(--dur-short)',
              }}>
              Remove
            </button>
          </div>
          <div className="grid grid-cols-2 gap-3 text-sm">
            <div>
              <span className="text-xs" style={{ color: 'var(--color-muted)' }}>Provider</span>
              <p style={{ color: 'var(--color-ink-2)' }}>{presets[config.provider]?.label || config.provider}</p>
            </div>
            <div>
              <span className="text-xs" style={{ color: 'var(--color-muted)' }}>Model</span>
              <p style={{ color: 'var(--color-ink-2)' }}>{config.model}</p>
            </div>
          </div>
        </div>
      )}

      <form onSubmit={handleSave}>
        <div className="rounded-card p-5 mb-6"
          style={{ backgroundColor: 'var(--color-paper-2)', border: '1px solid var(--color-rule-subtle)' }}>
          <label className="block text-xs mb-3 font-medium" style={{ color: 'var(--color-muted)' }}>
            AI Provider
          </label>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 mb-5">
            {Object.entries(presets).map(([key, p]) => (
              <button
                key={key}
                type="button"
                onClick={() => setSelectedProvider(key)}
                className="rounded-input px-3 py-2.5 text-xs font-medium text-left transition-colors"
                style={{
                  backgroundColor: selectedProvider === key ? 'var(--color-paper-3)' : 'transparent',
                  border: `2px solid ${selectedProvider === key ? 'var(--color-accent)' : 'var(--color-rule-subtle)'}`,
                  color: 'var(--color-ink)',
                  transitionDuration: 'var(--dur-short)',
                }}
              >
                {p.label}
              </button>
            ))}
          </div>

          {provider?.docs_url && (
            <p className="text-xs mb-4" style={{ color: 'var(--color-ink-2)' }}>
              Get your key:{' '}
              <a href={provider.docs_url} target="_blank" rel="noopener noreferrer"
                className="underline" style={{ color: 'var(--color-accent)' }}>
                {provider.docs_url}
              </a>
            </p>
          )}

          <div className="mb-4">
            <label className="block text-xs mb-1.5" style={{ color: 'var(--color-muted)' }}>API Key</label>
            <input
              type="password"
              value={apiKey}
              onChange={e => setApiKey(e.target.value)}
              placeholder={provider?.env_var ? `Your ${provider.env_var}` : 'sk-...'}
              className="w-full rounded-input px-3 py-2 text-sm font-outlier"
              style={{
                backgroundColor: 'var(--color-paper-1)',
                border: '1px solid var(--color-rule-subtle)',
                color: 'var(--color-ink)',
              }}
            />
            <p className="text-xs mt-1" style={{ color: 'var(--color-muted)' }}>
              Stored with AES-256-GCM encryption. Never logged or sent anywhere but your chosen provider.
            </p>
          </div>

          <div className="mb-4">
            <label className="block text-xs mb-1.5" style={{ color: 'var(--color-muted)' }}>Model</label>
            <input
              type="text"
              value={model}
              onChange={e => setModel(e.target.value)}
              placeholder="gpt-4o"
              className="w-full rounded-input px-3 py-2 text-sm font-outlier"
              style={{
                backgroundColor: 'var(--color-paper-1)',
                border: '1px solid var(--color-rule-subtle)',
                color: 'var(--color-ink)',
              }}
            />
          </div>

          {selectedProvider === 'custom' && (
            <div className="mb-4">
              <label className="block text-xs mb-1.5" style={{ color: 'var(--color-muted)' }}>Base URL (OpenAI-compatible)</label>
              <input
                type="url"
                value={customUrl}
                onChange={e => setCustomUrl(e.target.value)}
                placeholder="https://your-endpoint/v1"
                className="w-full rounded-input px-3 py-2 text-sm font-outlier"
                style={{
                  backgroundColor: 'var(--color-paper-1)',
                  border: '1px solid var(--color-rule-subtle)',
                  color: 'var(--color-ink)',
                }}
              />
            </div>
          )}
        </div>

        <button
          type="submit"
          disabled={saving || !apiKey}
          className="rounded-pill px-6 py-2.5 text-sm font-medium transition-colors disabled:opacity-50"
          style={{
            backgroundColor: saving ? 'var(--color-paper-3)' : 'var(--color-accent)',
            color: 'var(--color-paper)',
            border: 'none',
            transitionDuration: 'var(--dur-short)',
            transitionTimingFunction: 'var(--ease-out)',
          }}
        >
          {saving ? 'Saving…' : 'Save AI Configuration'}
        </button>
      </form>
    </div>
  );
}
