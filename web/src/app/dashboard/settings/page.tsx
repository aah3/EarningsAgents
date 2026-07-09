"use client";

import React, { useState, useEffect } from "react";
import { useUser, useClerk, useAuth } from "@clerk/nextjs";
import { 
  User as UserIcon, 
  Cpu, 
  Database, 
  Save, 
  Loader2, 
  Key, 
  Shield, 
  ExternalLink,
  CheckCircle2,
  AlertCircle
} from "lucide-react";
import { api } from "@/lib/api";

type TabType = "profile" | "agent" | "sources";

export default function SettingsPage() {
  const { user } = useUser();
  const { openUserProfile } = useClerk();
  const { getToken } = useAuth();

  const [activeTab, setActiveTab] = useState<TabType>("profile");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  const [settings, setSettings] = useState({
    provider: "gemini",
    model_name: "gemini-flash-latest",
    temperature: 0.3,
    max_tokens: 8192,
    use_react: false,
    react_max_turns: 6,
    enable_rebuttals: false,
    gemini_api_key: "",
    openai_api_key: "",
    anthropic_api_key: "",
    newsapi_api_key: "",
    alphavantage_api_key: "",
    earningsapi_api_key: "",
  });

  useEffect(() => {
    async function loadSettings() {
      try {
        setLoading(true);
        const token = await getToken();
        if (token) {
          const data = await api.getSettings(token);
          setSettings((prev) => ({
            ...prev,
            ...data,
            // fallback for missing values
            provider: data.provider || "gemini",
            model_name: data.model_name || "gemini-flash-latest",
            temperature: data.temperature !== undefined ? data.temperature : 0.3,
            max_tokens: data.max_tokens !== undefined ? data.max_tokens : 8192,
            use_react: !!data.use_react,
            react_max_turns: data.react_max_turns !== undefined ? data.react_max_turns : 6,
            enable_rebuttals: !!data.enable_rebuttals,
            gemini_api_key: data.gemini_api_key || "",
            openai_api_key: data.openai_api_key || "",
            anthropic_api_key: data.anthropic_api_key || "",
            newsapi_api_key: data.newsapi_api_key || "",
            alphavantage_api_key: data.alphavantage_api_key || "",
            earningsapi_api_key: data.earningsapi_api_key || "",
          }));
        }
      } catch (err: any) {
        console.error("Failed to load settings:", err);
        setMessage({ type: "error", text: "Failed to load settings from server." });
      } finally {
        setLoading(false);
      }
    }
    loadSettings();
  }, [getToken]);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value, type } = e.target;
    const val = type === "checkbox" ? (e.target as HTMLInputElement).checked : value;
    
    setSettings((prev) => ({
      ...prev,
      [name]: val,
    }));
  };

  const handleSliderChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setSettings((prev) => ({
      ...prev,
      [name]: parseFloat(value),
    }));
  };

  const handleNumberChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setSettings((prev) => ({
      ...prev,
      [name]: parseInt(value) || 0,
    }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setMessage(null);

    try {
      const token = await getToken();
      if (!token) throw new Error("Authentication token not found.");
      
      const res = await api.updateSettings(settings, token);
      setMessage({ type: "success", text: res.message || "Settings updated successfully!" });
      
      // Reload settings to refresh masked representations
      const data = await api.getSettings(token);
      setSettings((prev) => ({ ...prev, ...data }));
    } catch (err: any) {
      setMessage({ type: "error", text: err.message || "An error occurred while saving." });
    } finally {
      setSaving(false);
    }
  };

  // List of models per provider
  const modelsByProvider: Record<string, string[]> = {
    gemini: ["gemini-flash-latest", "gemini-1.5-flash", "gemini-1.5-pro", "gemini-2.5-flash", "gemini-2.5-pro"],
    openai: ["gpt-4o-mini", "gpt-4o", "gpt-4-turbo", "o1-mini"],
    anthropic: ["claude-3-5-sonnet-latest", "claude-3-5-haiku-latest", "claude-3-opus-latest"],
  };

  // Adjust model list when provider changes
  const handleProviderChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const newProvider = e.target.value;
    const defaultModel = modelsByProvider[newProvider]?.[0] || "";
    setSettings((prev) => ({
      ...prev,
      provider: newProvider,
      model_name: defaultModel,
    }));
  };

  const memberSince = user?.createdAt 
    ? new Date(user.createdAt).toLocaleDateString("en-US", { year: "numeric", month: "long" })
    : "N/A";

  if (loading) {
    return (
      <div className="h-[60vh] flex flex-col items-center justify-center gap-3">
        <Loader2 className="w-10 h-10 animate-spin text-teal" />
        <p className="text-ink-mute font-body text-[14.5px]">Loading settings configuration...</p>
      </div>
    );
  }

  return (
    <div className="space-y-8 pb-16">
      {/* Header */}
      <header className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-[32px] font-bold tracking-tight font-display text-white">Settings</h1>
          <p className="text-ink-mute font-body text-[15px] mt-1">Manage your account, model choices, and API integrations.</p>
        </div>
      </header>

      {/* Message Banner */}
      {message && (
        <div className={`p-4 rounded-xl border flex items-start gap-3 transition-all ${
          message.type === "success" 
            ? "bg-bull/8 border-bull/20 text-bull" 
            : "bg-bear/8 border-bear/20 text-bear"
        }`}>
          {message.type === "success" ? (
            <CheckCircle2 className="w-5 h-5 flex-shrink-0 mt-0.5" />
          ) : (
            <AlertCircle className="w-5 h-5 flex-shrink-0 mt-0.5" />
          )}
          <span className="text-[14.5px] font-semibold">{message.text}</span>
        </div>
      )}

      {/* Settings Grid */}
      <div className="flex flex-col lg:flex-row gap-8 items-start">
        {/* Navigation Sidebar */}
        <div className="w-full lg:w-[240px] flex flex-row lg:flex-col gap-1.5 border-b lg:border-b-0 lg:border-r border-panel-line pb-4 lg:pb-0 lg:pr-6 overflow-x-auto">
          <button
            onClick={() => { setActiveTab("profile"); setMessage(null); }}
            className={`flex items-center gap-3 px-4 py-3 rounded-xl font-body font-semibold text-[14.5px] transition-all cursor-pointer whitespace-nowrap outline-none
              ${activeTab === "profile" 
                ? "bg-teal/10 text-teal border-l-2 border-teal" 
                : "text-ink-mute border-l-2 border-transparent hover:bg-white/[0.02] hover:text-ink"}`}
          >
            <UserIcon className="w-4 h-4 flex-shrink-0" />
            <span>User Profile</span>
          </button>
          
          <button
            onClick={() => { setActiveTab("agent"); setMessage(null); }}
            className={`flex items-center gap-3 px-4 py-3 rounded-xl font-body font-semibold text-[14.5px] transition-all cursor-pointer whitespace-nowrap outline-none
              ${activeTab === "agent" 
                ? "bg-teal/10 text-teal border-l-2 border-teal" 
                : "text-ink-mute border-l-2 border-transparent hover:bg-white/[0.02] hover:text-ink"}`}
          >
            <Cpu className="w-4 h-4 flex-shrink-0" />
            <span>AI Agent Settings</span>
          </button>

          <button
            onClick={() => { setActiveTab("sources"); setMessage(null); }}
            className={`flex items-center gap-3 px-4 py-3 rounded-xl font-body font-semibold text-[14.5px] transition-all cursor-pointer whitespace-nowrap outline-none
              ${activeTab === "sources" 
                ? "bg-teal/10 text-teal border-l-2 border-teal" 
                : "text-ink-mute border-l-2 border-transparent hover:bg-white/[0.02] hover:text-ink"}`}
          >
            <Database className="w-4 h-4 flex-shrink-0" />
            <span>Data Sources</span>
          </button>
        </div>

        {/* Form Panel */}
        <form onSubmit={handleSubmit} className="flex-1 w-full bg-panel border border-panel-line rounded-2xl shadow-xl overflow-hidden p-6 md:p-8">
          
          {/* TAB 1: USER PROFILE */}
          {activeTab === "profile" && (
            <div className="space-y-6">
              <div>
                <h2 className="text-xl font-bold tracking-tight font-display text-white">User Profile</h2>
                <p className="text-ink-mute text-[14px] font-body mt-0.5">Details regarding your authenticated account.</p>
              </div>

              {/* Profile Card */}
              <div className="flex flex-col sm:flex-row items-center gap-5 p-5 rounded-xl border border-panel-line bg-white/[0.01]">
                <div className="w-16 h-16 rounded-full overflow-hidden border border-panel-line flex-shrink-0">
                  {user?.imageUrl ? (
                    /* eslint-disable-next-line @next/next/no-img-element */
                    <img src={user.imageUrl} alt={user.fullName || "User"} className="w-full h-full object-cover" />
                  ) : (
                    <div className="w-full h-full bg-teal/20 text-teal flex items-center justify-center font-display font-semibold text-xl">
                      U
                    </div>
                  )}
                </div>
                <div className="text-center sm:text-left space-y-1">
                  <h3 className="text-lg font-bold text-white leading-tight">{user?.fullName || "User Account"}</h3>
                  <p className="text-ink-mute text-[13.5px] font-medium">{user?.primaryEmailAddress?.emailAddress || ""}</p>
                  <p className="text-ink-dim text-[12px] font-mono">Member since: {memberSince}</p>
                </div>
              </div>

              {/* Security Actions */}
              <div className="border-t border-panel-line pt-6 space-y-4">
                <div className="flex items-start gap-3">
                  <Shield className="w-5 h-5 text-teal mt-0.5 flex-shrink-0" />
                  <div>
                    <h4 className="text-[14.5px] font-bold text-white">Account Security</h4>
                    <p className="text-ink-dim text-[13px] mt-0.5 leading-relaxed">
                      Update your password, manage linked accounts, or setup Two-Factor Authentication (2FA) via Clerk.
                    </p>
                  </div>
                </div>

                <button
                  type="button"
                  onClick={() => openUserProfile()}
                  className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-white/[0.04] hover:bg-white/[0.08] text-white border border-panel-line font-body font-semibold text-[13.5px] transition-all cursor-pointer outline-none focus-visible:ring-2 focus-visible:ring-teal"
                >
                  <span>Manage Security Settings</span>
                  <ExternalLink className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          )}

          {/* TAB 2: AI AGENT SETTINGS */}
          {activeTab === "agent" && (
            <div className="space-y-6">
              <div>
                <h2 className="text-xl font-bold tracking-tight font-display text-white">AI Agent Settings</h2>
                <p className="text-ink-mute text-[14px] font-body mt-0.5">Configure target LLMs and hyperparameters for the prediction debate.</p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                {/* LLM Provider */}
                <div className="space-y-2">
                  <label className="text-[11px] font-bold uppercase tracking-[0.12em] text-ink-mute">Active Provider</label>
                  <select
                    name="provider"
                    value={settings.provider}
                    onChange={handleProviderChange}
                    className="w-full bg-bg border border-panel-line rounded-xl px-4 py-3 text-[14px] text-white outline-none focus:border-teal/50 font-body"
                  >
                    <option value="gemini">Gemini (Google DeepMind)</option>
                    <option value="openai">OpenAI</option>
                    <option value="anthropic">Anthropic</option>
                  </select>
                </div>

                {/* Model Name */}
                <div className="space-y-2">
                  <label className="text-[11px] font-bold uppercase tracking-[0.12em] text-ink-mute">Model Name</label>
                  <select
                    name="model_name"
                    value={settings.model_name}
                    onChange={handleInputChange}
                    className="w-full bg-bg border border-panel-line rounded-xl px-4 py-3 text-[14px] text-white outline-none focus:border-teal/50 font-body"
                  >
                    {(modelsByProvider[settings.provider] || []).map((model) => (
                      <option key={model} value={model}>{model}</option>
                    ))}
                  </select>
                </div>

                {/* Temperature */}
                <div className="space-y-2">
                  <div className="flex justify-between items-center">
                    <label className="text-[11px] font-bold uppercase tracking-[0.12em] text-ink-mute">Temperature</label>
                    <span className="text-[12px] font-mono font-bold text-teal">{settings.temperature}</span>
                  </div>
                  <input
                    type="range"
                    name="temperature"
                    min="0"
                    max="1"
                    step="0.05"
                    value={settings.temperature}
                    onChange={handleSliderChange}
                    className="w-full h-1.5 bg-bg rounded-lg appearance-none cursor-pointer accent-teal border border-panel-line"
                  />
                  <div className="flex justify-between text-[10px] text-ink-dim font-mono">
                    <span>FACTUAL (0.0)</span>
                    <span>CREATIVE (1.0)</span>
                  </div>
                </div>

                {/* Max Tokens */}
                <div className="space-y-2">
                  <label className="text-[11px] font-bold uppercase tracking-[0.12em] text-ink-mute">Max Output Tokens</label>
                  <input
                    type="number"
                    name="max_tokens"
                    value={settings.max_tokens}
                    onChange={handleNumberChange}
                    className="w-full bg-bg border border-panel-line rounded-xl px-4 py-2.5 text-[14px] text-white outline-none focus:border-teal/50 font-mono"
                  />
                </div>
              </div>

              {/* Advanced Flags */}
              <div className="border-t border-panel-line pt-6 space-y-4">
                <h3 className="text-[13px] font-bold uppercase tracking-[0.1em] text-ink-dim">Debate Orchestration</h3>
                
                <div className="space-y-4">
                  {/* ReAct */}
                  <label className="flex items-start gap-3 cursor-pointer select-none">
                    <input
                      type="checkbox"
                      name="use_react"
                      checked={settings.use_react}
                      onChange={(e) => setSettings(prev => ({ ...prev, use_react: e.target.checked }))}
                      className="mt-1 w-4 h-4 rounded border-panel-line bg-bg text-teal focus:ring-teal/30 focus:ring-opacity-25"
                    />
                    <div>
                      <span className="text-[14px] font-semibold text-white">Enable ReAct Tool-Calling Loops</span>
                      <p className="text-ink-dim text-[12px] mt-0.5 leading-relaxed">
                        Allow agents to fetch real-time SEC reports, news, and filings dynamically during debate.
                      </p>
                    </div>
                  </label>

                  {/* ReAct Max Turns */}
                  {settings.use_react && (
                    <div className="pl-7 space-y-2 max-w-[200px]">
                      <label className="text-[11px] font-bold uppercase tracking-[0.12em] text-ink-mute">Max ReAct Turns</label>
                      <input
                        type="number"
                        name="react_max_turns"
                        value={settings.react_max_turns}
                        onChange={handleNumberChange}
                        min="1"
                        max="12"
                        className="w-full bg-bg border border-panel-line rounded-xl px-4 py-2 text-[13px] text-white outline-none focus:border-teal/50 font-mono"
                      />
                    </div>
                  )}

                  {/* Rebuttals */}
                  <label className="flex items-start gap-3 cursor-pointer select-none">
                    <input
                      type="checkbox"
                      name="enable_rebuttals"
                      checked={settings.enable_rebuttals}
                      onChange={(e) => setSettings(prev => ({ ...prev, enable_rebuttals: e.target.checked }))}
                      className="mt-1 w-4 h-4 rounded border-panel-line bg-bg text-teal focus:ring-teal/30 focus:ring-opacity-25"
                    />
                    <div>
                      <span className="text-[14px] font-semibold text-white">Enable Cross-Examination (Rebuttal Stage)</span>
                      <p className="text-ink-dim text-[12px] mt-0.5 leading-relaxed">
                        Add a formal rebuttal cycle where Bull and Bear agents cross-examine each other's points.
                      </p>
                    </div>
                  </label>
                </div>
              </div>

              {/* Provider Keys */}
              <div className="border-t border-panel-line pt-6 space-y-4">
                <div className="flex items-center gap-2">
                  <Key className="w-4 h-4 text-teal" />
                  <h3 className="text-[13px] font-bold uppercase tracking-[0.1em] text-ink-dim">LLM Provider API Keys</h3>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {/* Gemini Key */}
                  <div className="space-y-2">
                    <label className="text-[11px] font-bold uppercase tracking-[0.12em] text-ink-mute">Gemini API Key</label>
                    <input
                      type="password"
                      name="gemini_api_key"
                      value={settings.gemini_api_key}
                      onChange={handleInputChange}
                      placeholder={settings.gemini_api_key ? "••••••••••••••••" : "Leave blank to use environment default"}
                      className="w-full bg-bg border border-panel-line rounded-xl px-4 py-2.5 text-[13.5px] text-white outline-none focus:border-teal/50 font-mono"
                    />
                  </div>

                  {/* OpenAI Key */}
                  <div className="space-y-2">
                    <label className="text-[11px] font-bold uppercase tracking-[0.12em] text-ink-mute">OpenAI API Key</label>
                    <input
                      type="password"
                      name="openai_api_key"
                      value={settings.openai_api_key}
                      onChange={handleInputChange}
                      placeholder={settings.openai_api_key ? "••••••••••••••••" : "Leave blank to use environment default"}
                      className="w-full bg-bg border border-panel-line rounded-xl px-4 py-2.5 text-[13.5px] text-white outline-none focus:border-teal/50 font-mono"
                    />
                  </div>

                  {/* Anthropic Key */}
                  <div className="space-y-2">
                    <label className="text-[11px] font-bold uppercase tracking-[0.12em] text-ink-mute">Anthropic API Key</label>
                    <input
                      type="password"
                      name="anthropic_api_key"
                      value={settings.anthropic_api_key}
                      onChange={handleInputChange}
                      placeholder={settings.anthropic_api_key ? "••••••••••••••••" : "Leave blank to use environment default"}
                      className="w-full bg-bg border border-panel-line rounded-xl px-4 py-2.5 text-[13.5px] text-white outline-none focus:border-teal/50 font-mono"
                    />
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* TAB 3: DATA SOURCES */}
          {activeTab === "sources" && (
            <div className="space-y-6">
              <div>
                <h2 className="text-xl font-bold tracking-tight font-display text-white">Data Sources</h2>
                <p className="text-ink-mute text-[14px] font-body mt-0.5">Manage external market data provider credentials.</p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                {/* NewsAPI */}
                <div className="space-y-2">
                  <label className="text-[11px] font-bold uppercase tracking-[0.12em] text-ink-mute">NewsAPI Key</label>
                  <input
                    type="password"
                    name="newsapi_api_key"
                    value={settings.newsapi_api_key}
                    onChange={handleInputChange}
                    placeholder={settings.newsapi_api_key ? "••••••••••••••••" : "Leave blank to use environment default"}
                    className="w-full bg-bg border border-panel-line rounded-xl px-4 py-2.5 text-[13.5px] text-white outline-none focus:border-teal/50 font-mono"
                  />
                  <span className="text-[10px] text-ink-dim font-body block">Supplies macro sentiment news articles to agents.</span>
                </div>

                {/* AlphaVantage */}
                <div className="space-y-2">
                  <label className="text-[11px] font-bold uppercase tracking-[0.12em] text-ink-mute">Alpha Vantage API Key</label>
                  <input
                    type="password"
                    name="alphavantage_api_key"
                    value={settings.alphavantage_api_key}
                    onChange={handleInputChange}
                    placeholder={settings.alphavantage_api_key ? "••••••••••••••••" : "Leave blank to use environment default"}
                    className="w-full bg-bg border border-panel-line rounded-xl px-4 py-2.5 text-[13.5px] text-white outline-none focus:border-teal/50 font-mono"
                  />
                  <span className="text-[10px] text-ink-dim font-body block">Feeds consensus expectations and analyst estimate revisions.</span>
                </div>

                {/* EarningsAPI */}
                <div className="space-y-2">
                  <label className="text-[11px] font-bold uppercase tracking-[0.12em] text-ink-mute">EarningsAPI Key</label>
                  <input
                    type="password"
                    name="earningsapi_api_key"
                    value={settings.earningsapi_api_key}
                    onChange={handleInputChange}
                    placeholder={settings.earningsapi_api_key ? "••••••••••••••••" : "Leave blank to use environment default"}
                    className="w-full bg-bg border border-panel-line rounded-xl px-4 py-2.5 text-[13.5px] text-white outline-none focus:border-teal/50 font-mono"
                  />
                  <span className="text-[10px] text-ink-dim font-body block">Provides historical earnings beat rates and quarterly transcripts.</span>
                </div>
              </div>
            </div>
          )}

          {/* Action Footer */}
          {activeTab !== "profile" && (
            <div className="mt-8 pt-5 border-t border-panel-line flex justify-end">
              <button
                type="submit"
                disabled={saving}
                className="flex items-center gap-2 px-5 py-3 rounded-xl bg-teal hover:bg-teal-deep disabled:opacity-50 text-[#04231F] font-body font-bold text-[14px] cursor-pointer outline-none focus-visible:ring-2 focus-visible:ring-teal shadow-lg shadow-teal/10 transition-all"
              >
                {saving ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin text-[#04231F]" />
                    <span>Saving Changes...</span>
                  </>
                ) : (
                  <>
                    <Save className="w-4 h-4 text-[#04231F]" />
                    <span>Save Settings</span>
                  </>
                )}
              </button>
            </div>
          )}
        </form>
      </div>
    </div>
  );
}
