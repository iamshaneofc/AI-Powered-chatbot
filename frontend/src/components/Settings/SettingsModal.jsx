import { useState, useEffect } from 'react';
import { X, Settings, Key, Globe, Check, AlertCircle, Loader2, Eye, EyeOff } from 'lucide-react';
import { getProviders, getCurrentSettings, updateSettings, testProvider } from '../../services/api';

const PROVIDER_INFO = {
  openai: {
    name: 'OpenAI',
    description: 'GPT-4o, GPT-4o-mini, GPT-3.5-turbo',
    color: 'from-green-500 to-emerald-600',
    free: false,
  },
  openrouter: {
    name: 'OpenRouter',
    description: '500+ models, 50 free req/day',
    color: 'from-purple-500 to-violet-600',
    free: true,
  },
  nvidia: {
    name: 'NVIDIA NIM',
    description: 'Llama, Nemotron - 40 RPM free',
    color: 'from-green-600 to-teal-600',
    free: true,
  },
  groq: {
    name: 'Groq',
    description: 'Ultra-fast Llama, Mixtral - 30 RPM free',
    color: 'from-orange-500 to-red-500',
    free: true,
  },
  cerebras: {
    name: 'Cerebras',
    description: 'Fastest inference - 1M tokens/day free',
    color: 'from-blue-500 to-indigo-600',
    free: true,
  },
  gemini: {
    name: 'Google Gemini',
    description: 'Gemini Flash/Pro - 1500 req/day free',
    color: 'from-blue-400 to-cyan-500',
    free: true,
  },
  mimo: {
    name: 'MiMo Free',
    description: 'Xiaomi MiMo — free tier available',
    color: 'from-orange-400 to-amber-500',
    free: true,
  },
  opencode: {
    name: 'OpenCode',
    description: 'Self-hosted OpenCode-compatible endpoint',
    color: 'from-teal-500 to-cyan-600',
    free: false,
  },
  custom: {
    name: 'Custom Provider',
    description: 'Any OpenAI-compatible API',
    color: 'from-gray-500 to-gray-600',
    free: false,
  },
};

export default function SettingsModal({ isOpen, onClose }) {
  const [providers, setProviders] = useState([]);
  const [currentSettings, setCurrentSettings] = useState(null);
  const [selectedProvider, setSelectedProvider] = useState('');
  const [apiKey, setApiKey] = useState('');
  const [model, setModel] = useState('');
  const [baseUrl, setBaseUrl] = useState('');
  const [maxTokens, setMaxTokens] = useState(1024);
  const [temperature, setTemperature] = useState(0.2);
  const [loading, setLoading] = useState(false);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState(null);
  const [saveResult, setSaveResult] = useState(null);
  const [showApiKey, setShowApiKey] = useState(false);

  const loadData = async () => {
    try {
      setLoading(true);
      const [providersRes, settingsRes] = await Promise.all([
        getProviders(),
        getCurrentSettings(),
      ]);
      setProviders(providersRes.providers);
      setCurrentSettings(settingsRes);
      setSelectedProvider(settingsRes.provider);
      setModel(settingsRes.model);
      setMaxTokens(settingsRes.max_tokens);
      setTemperature(settingsRes.temperature);
      setApiKey(''); // Don't load actual API key for security
      setBaseUrl('');
      setTestResult(null);
      setSaveResult(null);
    } catch (error) {
      console.error('Failed to load settings:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      loadData();
    }
  }, [isOpen]);

  const handleProviderChange = (providerId) => {
    setSelectedProvider(providerId);
    const provider = providers.find(p => p.id === providerId);
    if (provider) {
      setModel(provider.default_model);
      if (providerId === 'custom' || providerId === 'opencode') {
        setBaseUrl('');
      }
    }
    setApiKey('');
    setTestResult(null);
  };

  const handleTest = async () => {
    if (!apiKey) {
      setTestResult({ success: false, message: 'Please enter an API key' });
      return;
    }

    try {
      setTesting(true);
      setTestResult(null);
      const result = await testProvider(selectedProvider, apiKey, baseUrl);
      setTestResult(result);
    } catch (error) {
      setTestResult({ 
        success: false, 
        message: error.message || 'Failed to test connection' 
      });
    } finally {
      setTesting(false);
    }
  };

  const handleSave = async () => {
    try {
      setLoading(true);
      setSaveResult(null);
      
      const result = await updateSettings({
        provider: selectedProvider,
        api_key: apiKey || undefined,
        model: model,
        base_url: baseUrl || undefined,
        max_tokens: maxTokens,
        temperature: temperature,
      });
      
      setSaveResult(result);
      
      // Close modal after successful save
      setTimeout(() => {
        onClose();
        window.location.reload(); // Reload to apply new settings
      }, 1500);
    } catch (error) {
      setSaveResult({ 
        success: false, 
        message: error.message || 'Failed to save settings' 
      });
    } finally {
      setLoading(false);
    }
  };

  const getAvailableModels = () => {
    const provider = providers.find(p => p.id === selectedProvider);
    return provider ? provider.models : [];
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div 
        className="absolute inset-0 bg-black/70 backdrop-blur-sm"
        onClick={onClose}
      />
      
      {/* Modal */}
      <div className="relative w-full max-w-2xl max-h-[90vh] bg-[#0f172a] rounded-3xl border border-white/10 shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-white/10">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center">
              <Settings className="text-white" size={20} />
            </div>
            <div>
              <h2 className="text-lg font-bold text-white">AI Provider Settings</h2>
              <p className="text-xs text-gray-400">Configure your AI provider and API key</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="w-8 h-8 rounded-lg bg-white/5 hover:bg-white/10 flex items-center justify-center text-gray-400 hover:text-white transition-colors"
          >
            <X size={18} />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto max-h-[calc(90vh-200px)]">
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="animate-spin text-indigo-500" size={32} />
            </div>
          ) : (
            <div className="space-y-6">
              {/* Provider Selection */}
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-3">
                  Select Provider
                </label>
                <div className="grid grid-cols-2 gap-3">
                  {providers.map((provider) => {
                    const info = PROVIDER_INFO[provider.id] || PROVIDER_INFO.custom;
                    return (
                      <button
                        key={provider.id}
                        onClick={() => handleProviderChange(provider.id)}
                        className={`relative p-4 rounded-xl border-2 transition-all text-left ${
                          selectedProvider === provider.id
                            ? 'border-indigo-500 bg-indigo-500/10'
                            : 'border-white/10 hover:border-white/20 bg-white/5'
                        }`}
                      >
                        <div className="flex items-start justify-between">
                          <div>
                            <div className="font-medium text-white">{info.name}</div>
                            <div className="text-xs text-gray-400 mt-1">{info.description}</div>
                          </div>
                          {info.free && (
                            <span className="px-2 py-0.5 text-[10px] font-bold bg-green-500/20 text-green-400 rounded-full">
                              FREE
                            </span>
                          )}
                        </div>
                        {selectedProvider === provider.id && (
                          <div className="absolute top-2 right-2">
                            <Check className="text-indigo-400" size={16} />
                          </div>
                        )}
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* API Key */}
              {PROVIDER_INFO[selectedProvider]?.requires_api_key !== false && (
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    API Key
                  </label>
                  <div className="relative">
                    <input
                      type={showApiKey ? 'text' : 'password'}
                      value={apiKey}
                      onChange={(e) => setApiKey(e.target.value)}
                      placeholder={`Enter your ${PROVIDER_INFO[selectedProvider]?.name || ''} API key`}
                      className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:border-indigo-500 transition-colors pr-12"
                    />
                    <button
                      type="button"
                      onClick={() => setShowApiKey(!showApiKey)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-white"
                    >
                      {showApiKey ? <EyeOff size={18} /> : <Eye size={18} />}
                    </button>
                  </div>
                  {currentSettings?.api_key_set && !apiKey && (
                    <p className="text-xs text-gray-500 mt-2">
                      ✓ API key is already configured. Leave blank to keep current key.
                    </p>
                  )}
                </div>
              )}

              {/* Model Selection */}
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Model
                </label>
                <select
                  value={model}
                  onChange={(e) => setModel(e.target.value)}
                  className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-xl text-white focus:outline-none focus:border-indigo-500 transition-colors"
                >
                  {getAvailableModels().map((m) => (
                    <option key={m} value={m} className="bg-[#0f172a]">
                      {m}
                    </option>
                  ))}
                </select>
              </div>

              {/* Base URL (custom & opencode providers) */}
              {(selectedProvider === 'custom' || selectedProvider === 'opencode') && (
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Base URL
                  </label>
                  <input
                    type="text"
                    value={baseUrl}
                    onChange={(e) => setBaseUrl(e.target.value)}
                    placeholder="https://your-api-endpoint.com/v1"
                    className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:border-indigo-500 transition-colors"
                  />
                </div>
              )}

              {/* Advanced Settings */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Max Tokens
                  </label>
                  <input
                    type="number"
                    value={maxTokens}
                    onChange={(e) => setMaxTokens(parseInt(e.target.value) || 1024)}
                    min={1}
                    max={8192}
                    className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-xl text-white focus:outline-none focus:border-indigo-500 transition-colors"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Temperature
                  </label>
                  <input
                    type="number"
                    value={temperature}
                    onChange={(e) => setTemperature(parseFloat(e.target.value) || 0.2)}
                    min={0}
                    max={2}
                    step={0.1}
                    className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-xl text-white focus:outline-none focus:border-indigo-500 transition-colors"
                  />
                </div>
              </div>

              {/* Test Connection */}
              <div className="flex items-center gap-3">
                <button
                  onClick={handleTest}
                  disabled={testing || !apiKey}
                  className="flex items-center gap-2 px-4 py-2 bg-white/5 hover:bg-white/10 border border-white/10 rounded-xl text-white text-sm font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {testing ? (
                    <Loader2 className="animate-spin" size={16} />
                  ) : (
                    <Globe size={16} />
                  )}
                  Test Connection
                </button>
                
                {testResult && (
                  <div className={`flex items-center gap-2 text-sm ${
                    testResult.success ? 'text-green-400' : 'text-red-400'
                  }`}>
                    {testResult.success ? (
                      <Check size={16} />
                    ) : (
                      <AlertCircle size={16} />
                    )}
                    {testResult.message}
                  </div>
                )}
              </div>

              {/* Save Result */}
              {saveResult && (
                <div className={`p-4 rounded-xl ${
                  saveResult.success 
                    ? 'bg-green-500/10 border border-green-500/20 text-green-400' 
                    : 'bg-red-500/10 border border-red-500/20 text-red-400'
                }`}>
                  <div className="flex items-center gap-2">
                    {saveResult.success ? <Check size={16} /> : <AlertCircle size={16} />}
                    {saveResult.message}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 p-6 border-t border-white/10 bg-[#0a0f1a]">
          <button
            onClick={onClose}
            className="px-4 py-2 text-gray-400 hover:text-white transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={loading}
            className="flex items-center gap-2 px-6 py-2 bg-gradient-to-r from-indigo-500 to-purple-600 hover:from-indigo-600 hover:to-purple-700 rounded-xl text-white font-medium transition-all disabled:opacity-50"
          >
            {loading ? (
              <Loader2 className="animate-spin" size={16} />
            ) : (
              <Key size={16} />
            )}
            Save Settings
          </button>
        </div>
      </div>
    </div>
  );
}
