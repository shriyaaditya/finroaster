"use client";

import React, { useState, useEffect, useRef, useCallback } from "react";
import { usePlaidLink } from "react-plaid-link";
import { 
  ResponsiveContainer, 
  AreaChart, 
  Area, 
  LineChart, 
  Line, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  Legend, 
  ComposedChart 
} from "recharts";
import { 
  Upload, 
  Flame, 
  Sparkles, 
  AlertCircle, 
  FileText, 
  CheckCircle2, 
  TrendingUp, 
  DollarSign,
  Bot,
  Zap,
  ExternalLink,
  ChevronDown,
  ChevronUp,
  Loader2,
  ShieldAlert,
  Landmark
} from "lucide-react";

interface HistoricalData {
  date: string;
  amount: number;
}

interface ForecastData {
  date: string;
  p10: number;
  p50: number;
  p90: number;
}

interface CopilotAction {
  target_vendor: string;
  action_mode: "playwright_auto" | "tavily_search";
  requires_auth: boolean;
  target_url?: string | null;
  instructions?: string | null;
}

interface APIResponse {
  historical: HistoricalData[];
  forecast: ForecastData[];
  roast: string;
  copilot_action?: CopilotAction | null;
}

export default function Home() {
  const [mounted, setMounted] = useState(false);
  const [dragActive, setDragActive] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [loadingStep, setLoadingStep] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<APIResponse | null>(null);
  const [showPaste, setShowPaste] = useState(false);
  const [pasteContent, setPasteContent] = useState("");

  // Plaid States
  const [linkToken, setLinkToken] = useState<string | null>(null);
  const [accessToken, setAccessToken] = useState<string | null>(null);

  // Copilot Action States
  const [killing, setKilling] = useState(false);
  const [killSuccess, setKillSuccess] = useState(false);
  const [killError, setKillError] = useState<string | null>(null);
  const [showSteps, setShowSteps] = useState(false);

  const fileInputRef = useRef<HTMLInputElement>(null);

  // Fetch Plaid Link Token on mount
  useEffect(() => {
    setMounted(true);
    const fetchLinkToken = async () => {
      try {
        const response = await fetch("http://localhost:8055/api/create_link_token", {
          method: "POST"
        });
        if (response.ok) {
          const resData = await response.json();
          setLinkToken(resData.link_token);
        }
      } catch (err) {
        console.error("Failed to fetch Plaid link token:", err);
      }
    };
    fetchLinkToken();
  }, []);

  const triggerPlaidForecast = async (token: string) => {
    setLoading(true);
    setLoadingStep(0);
    setError(null);
    setData(null);
    setKilling(false);
    setKillSuccess(false);
    setKillError(null);
    setShowSteps(false);

    try {
      const response = await fetch("http://localhost:8055/forecast/plaid", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ access_token: token })
      });

      if (!response.ok) {
        const errData = await response.json();
        throw new Error(errData.detail || "Failed to process Plaid transactions.");
      }

      const result = await response.json();
      setTimeout(() => {
        setData(result);
        setLoading(false);
      }, 3500);

    } catch (err: any) {
      setError(err.message || "Error connecting to backend for Plaid forecast.");
      setLoading(false);
    }
  };

  const onSuccessPlaid = useCallback(async (public_token: string | null) => {
    setLoading(true);
    setLoadingStep(0);
    setError(null);
    if (!public_token) {
      setError("Plaid returned no public token.");
      setLoading(false);
      return;
    }
    try {
      const res = await fetch("http://localhost:8055/api/set_access_token", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ public_token })
      });

      if (!res.ok) {
        throw new Error("Failed to exchange Plaid public token.");
      }

      const tokenData = await res.json();
      setAccessToken(tokenData.access_token);
      await triggerPlaidForecast(tokenData.access_token);

    } catch (err: any) {
      setError(err.message || "Error completing Plaid authentication.");
      setLoading(false);
    }
  }, []);

  const { open: openPlaid, ready: plaidReady } = usePlaidLink({
    token: linkToken,
    onSuccess: onSuccessPlaid,
  });

  // Loading micro-animation steps
  useEffect(() => {
    if (!loading) return;
    const intervals = [1200, 2200, 3500];
    const timer1 = setTimeout(() => setLoadingStep(1), intervals[0]);
    const timer2 = setTimeout(() => setLoadingStep(2), intervals[1]);
    
    return () => {
      clearTimeout(timer1);
      clearTimeout(timer2);
    };
  }, [loading]);

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const droppedFile = e.dataTransfer.files[0];
      if (droppedFile.name.endsWith(".csv")) {
        setFile(droppedFile);
        triggerUpload(droppedFile);
      } else {
        setError("Please upload a CSV file only.");
      }
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const selectedFile = e.target.files[0];
      setFile(selectedFile);
      triggerUpload(selectedFile);
    }
  };

  const triggerUpload = async (uploadFile: File) => {
    setLoading(true);
    setLoadingStep(0);
    setError(null);
    setData(null);
    setKilling(false);
    setKillSuccess(false);
    setKillError(null);
    setShowSteps(false);

    const formData = new FormData();
    formData.append("file", uploadFile);

    try {
      // Backend is configured on port 8055
      const response = await fetch("http://localhost:8055/forecast/upload", {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        const errData = await response.json();
        throw new Error(errData.detail || "Failed to process transactions file.");
      }

      const result = await response.json();
      setTimeout(() => {
        setData(result);
        setLoading(false);
      }, 4000);

    } catch (err: any) {
      setError(err.message || "An unexpected error occurred connecting to the backend.");
      setLoading(false);
    }
  };

  const selectNewFile = () => {
    fileInputRef.current?.click();
  };

  const handlePasteSubmit = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (!pasteContent.trim()) {
      setError("Please paste valid CSV data.");
      return;
    }
    const pastedFile = new File([pasteContent], "pasted_transactions.csv", { type: "text/csv" });
    triggerUpload(pastedFile);
  };

  const handleKillSubscription = async (copilotAction: CopilotAction) => {
    setKilling(true);
    setKillError(null);
    setKillSuccess(false);

    try {
      const response = await fetch("http://localhost:8055/cancel-subscription", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          vendor: copilotAction.target_vendor,
          url: copilotAction.target_url || "https://www.google.com",
          requires_auth: copilotAction.requires_auth
        })
      });

      if (!response.ok) {
        const errData = await response.json();
        throw new Error(errData.detail || "Failed to execute Playwright cancellation.");
      }

      const result = await response.json();
      setKilling(false);
      setKillSuccess(true);
    } catch (err: any) {
      setKilling(false);
      setKillError(err.message || "Error executing subscription cancellation.");
    }
  };

  // Process data for Recharts composed view (combines historical and forecast)
  const getChartData = () => {
    if (!data) return [];
    
    const chartList: any[] = [];
    
    // Add historical items
    data.historical.forEach((item) => {
      chartList.push({
        date: item.date,
        spend: item.amount,
        type: "Historical",
      });
    });

    // Add forecast items
    data.forecast.forEach((item) => {
      chartList.push({
        date: item.date,
        p50: item.p50,
        range: [item.p10, item.p90],
        type: "Forecast",
      });
    });

    return chartList;
  };

  const totalHistorical = data?.historical.reduce((sum, item) => sum + item.amount, 0) || 0;
  const avgHistorical = data?.historical.length ? (totalHistorical / data.historical.length) : 0;
  const maxProjected = data?.forecast ? Math.max(...data.forecast.map((f) => f.p90)) : 0;

  if (!mounted) return null;

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans selection:bg-rose-500 selection:text-white">
      {/* Premium Header */}
      <header className="border-b border-slate-800/80 bg-slate-900/40 backdrop-blur-md sticky top-0 z-50">
        <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-gradient-to-tr from-rose-500 to-amber-500 rounded-xl shadow-lg shadow-rose-500/20">
              <Flame className="w-6 h-6 text-white animate-pulse" />
            </div>
            <div>
              <h1 className="font-extrabold text-xl tracking-tight bg-gradient-to-r from-rose-400 via-amber-300 to-rose-400 bg-clip-text text-transparent">
                FinRoast
              </h1>
              <p className="text-[10px] text-slate-400 font-mono tracking-widest uppercase">
                Zero-Shot Financial Intervention & Subscription Copilot
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <span className="h-2 w-2 rounded-full bg-emerald-500 animate-ping"></span>
            <span className="text-xs font-mono text-slate-400">Chronos v0.1 + Playwright Copilot</span>
          </div>
        </div>
      </header>

      {/* Main Content Workspace */}
      <main className="flex-1 max-w-6xl w-full mx-auto px-6 py-10 flex flex-col gap-8">
        
        {/* Intro Hero Section */}
        {!data && !loading && (
          <div className="text-center max-w-2xl mx-auto my-12 flex flex-col gap-4">
            <h2 className="text-4xl font-extrabold tracking-tight sm:text-5xl bg-gradient-to-b from-white to-slate-400 bg-clip-text text-transparent">
              Upload transactions.<br />Get roasted. Kill parasitic subscriptions.
            </h2>
            <p className="text-slate-400 text-lg">
              FinRoast aggregates your bank statements, forecasts 14-day spending, delivers AI roasts, and deploys an automated Copilot to eliminate unwanted recurring charges.
            </p>
          </div>
        )}

        {/* Upload / Landing Area */}
        {!data && !loading && (
          <div className="max-w-3xl w-full mx-auto">
            {showPaste ? (
              <div 
                className="border-2 border-slate-800 bg-slate-900/30 rounded-3xl p-8 flex flex-col gap-4"
                onClick={(e) => e.stopPropagation()}
              >
                <div className="flex items-center justify-between">
                  <h3 className="text-lg font-bold text-slate-200">Paste CSV Content</h3>
                  <button 
                    onClick={() => setShowPaste(false)}
                    className="text-xs text-slate-450 hover:text-slate-200 transition-colors"
                  >
                    Back to Upload
                  </button>
                </div>
                <textarea
                  id="paste-csv-textarea"
                  rows={10}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl p-4 text-slate-200 font-mono text-xs focus:outline-none focus:border-rose-500/50 resize-y"
                  placeholder="Date,Amount,Category&#10;2026-08-01,15.50,Dining&#10;2026-08-02,45.00,Shopping..."
                  value={pasteContent}
                  onChange={(e) => setPasteContent(e.target.value)}
                />
                <div className="flex items-center gap-3 justify-end">
                  <button
                    onClick={() => setShowPaste(false)}
                    className="px-4 py-2 border border-slate-850 hover:border-slate-800 bg-slate-900/40 text-slate-400 hover:text-slate-250 text-xs font-semibold rounded-lg transition-all"
                  >
                    Cancel
                  </button>
                  <button
                    id="submit-paste-btn"
                    onClick={handlePasteSubmit}
                    className="px-5 py-2.5 bg-gradient-to-r from-rose-600 to-amber-600 hover:from-rose-500 hover:to-amber-500 text-white text-xs font-semibold rounded-lg shadow-lg shadow-rose-950/20 transition-all duration-200"
                  >
                    Analyze & Roast
                  </button>
                </div>
              </div>
            ) : (
              <div
                onDragEnter={handleDrag}
                onDragOver={handleDrag}
                onDragLeave={handleDrag}
                onDrop={handleDrop}
                onClick={selectNewFile}
                className={`border-2 border-dashed rounded-3xl p-12 text-center cursor-pointer transition-all duration-300 ${
                  dragActive 
                    ? "border-rose-500 bg-rose-500/5 shadow-2xl shadow-rose-500/10 scale-[1.01]" 
                    : "border-slate-800 bg-slate-900/30 hover:border-slate-700 hover:bg-slate-900/50"
                }`}
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  className="hidden"
                  accept=".csv"
                  onChange={handleFileChange}
                />
                <div className="flex flex-col items-center gap-4">
                  <div className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800 text-slate-400 shadow-inner group-hover:scale-110 transition-transform">
                    <Upload className="w-10 h-10 text-rose-500 animate-bounce" />
                  </div>
                  <div>
                    <p className="text-lg font-semibold text-slate-200">
                      Drag and drop your bank CSV here
                    </p>
                    <p className="text-sm text-slate-500 mt-1">
                      CSV should contain headers: <code className="text-slate-400 bg-slate-950 px-1.5 py-0.5 rounded font-mono">Date</code>, <code className="text-slate-400 bg-slate-950 px-1.5 py-0.5 rounded font-mono">Amount</code>, <code className="text-slate-400 bg-slate-950 px-1.5 py-0.5 rounded font-mono">Category</code>
                    </p>
                  </div>
                  <div className="flex flex-wrap items-center justify-center gap-3">
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        openPlaid();
                      }}
                      disabled={!plaidReady}
                      className="mt-2 px-6 py-2.5 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 disabled:opacity-50 text-white text-sm font-semibold rounded-full shadow-lg shadow-emerald-950/30 flex items-center gap-2 transition-all duration-200"
                    >
                      <Landmark className="w-4 h-4 text-white" />
                      <span>Connect Bank (Plaid)</span>
                    </button>
                    <button
                      type="button"
                      className="mt-2 px-6 py-2.5 bg-gradient-to-r from-rose-600 to-amber-600 hover:from-rose-500 hover:to-amber-500 text-white text-sm font-semibold rounded-full shadow-lg shadow-rose-950/20 transition-all duration-200"
                    >
                      Browse Files
                    </button>
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        setShowPaste(true);
                      }}
                      className="mt-2 px-6 py-2.5 border border-slate-700 hover:border-slate-650 hover:bg-slate-900 text-slate-300 text-sm font-semibold rounded-full transition-all duration-200"
                    >
                      Paste CSV Text
                    </button>
                  </div>

                </div>
              </div>
            )}

            {/* Error Message */}
            {error && (
              <div className="mt-6 p-4 bg-rose-500/10 border border-rose-500/30 rounded-2xl flex items-center gap-3 text-rose-400 text-sm">
                <AlertCircle className="w-5 h-5 flex-shrink-0" />
                <p>{error}</p>
              </div>
            )}
          </div>
        )}

        {/* Elegant Loading View */}
        {loading && (
          <div className="max-w-xl w-full mx-auto my-12 bg-slate-900/40 border border-slate-800/80 backdrop-blur-md p-10 rounded-3xl flex flex-col items-center gap-8 shadow-2xl">
            <div className="relative flex items-center justify-center">
              <div className="w-24 h-24 rounded-full border-4 border-slate-800 border-t-rose-500 animate-spin"></div>
              <div className="absolute p-4 bg-slate-950 border border-slate-850 rounded-full shadow-xl">
                <Flame className="w-8 h-8 text-rose-500 animate-pulse" />
              </div>
            </div>
            
            <div className="w-full flex flex-col gap-3">
              <div className="flex items-center gap-3">
                <div className={`w-5 h-5 rounded-full flex items-center justify-center text-xs ${loadingStep >= 0 ? "bg-rose-500 text-white" : "bg-slate-800 text-slate-400"}`}>
                  {loadingStep > 0 ? "✓" : "1"}
                </div>
                <p className={`text-sm ${loadingStep >= 0 ? "text-slate-200 font-medium" : "text-slate-500"}`}>
                  Ingesting transaction history CSV...
                </p>
              </div>
              <div className="flex items-center gap-3">
                <div className={`w-5 h-5 rounded-full flex items-center justify-center text-xs ${loadingStep >= 1 ? "bg-rose-500 text-white" : "bg-slate-800 text-slate-400"}`}>
                  {loadingStep > 1 ? "✓" : "2"}
                </div>
                <p className={`text-sm ${loadingStep >= 1 ? "text-slate-200 font-medium" : "text-slate-500"}`}>
                  Executing Amazon Chronos zero-shot forecast & Copilot scan...
                </p>
              </div>
              <div className="flex items-center gap-3">
                <div className={`w-5 h-5 rounded-full flex items-center justify-center text-xs ${loadingStep >= 2 ? "bg-rose-500 text-white" : "bg-slate-800 text-slate-400"}`}>
                  {loadingStep > 2 ? "✓" : "3"}
                </div>
                <p className={`text-sm ${loadingStep >= 2 ? "text-slate-200 font-medium" : "text-slate-500"}`}>
                  Generating roast via Gemini 3.5 Flash...
                </p>
              </div>
            </div>
            
            <p className="text-xs font-mono text-slate-500 animate-pulse">
              Please wait, processing analytics...
            </p>
          </div>
        )}

        {/* Dashboard, AI Roast, and Copilot Action Card */}
        {data && (
          <div className="flex flex-col gap-8">
            
            {/* The AI Roast Banner (Glassmorphic) */}
            <div className="relative overflow-hidden bg-gradient-to-br from-slate-900 via-rose-950/20 to-slate-900 border border-rose-500/20 shadow-xl shadow-rose-950/5 p-8 rounded-3xl">
              <div className="absolute top-0 right-0 p-8 text-rose-500/10 pointer-events-none">
                <Flame className="w-40 h-40" />
              </div>
              <div className="relative z-10 flex flex-col sm:flex-row gap-6 items-start">
                <div className="p-4 bg-gradient-to-tr from-rose-500 to-amber-500 rounded-2xl text-white shadow-xl shadow-rose-500/10">
                  <Flame className="w-8 h-8" />
                </div>
                <div className="flex flex-col gap-2">
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] font-mono tracking-widest text-rose-400 uppercase bg-rose-500/10 border border-rose-500/20 px-2 py-0.5 rounded-full">
                      The Verdict
                    </span>
                    <span className="text-xs text-slate-500">Gemini 3.5 Flash</span>
                  </div>
                  <h3 className="text-xl font-bold text-slate-100">
                    The Financial Roast
                  </h3>
                  <p className="text-slate-300 text-lg leading-relaxed font-serif italic mt-1">
                    "{data.roast}"
                  </p>
                </div>
              </div>
            </div>

            {/* STAGE 2: Copilot Action Card (Conditional Component) */}
            {data.copilot_action && (
              <div className="relative overflow-hidden bg-slate-900/60 border border-rose-500/30 rounded-3xl p-8 shadow-2xl backdrop-blur-md">
                <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
                  
                  {/* Left Column: Copilot Details */}
                  <div className="flex items-start gap-4">
                    <div className="p-3.5 bg-rose-500/10 border border-rose-500/30 rounded-2xl text-rose-400 flex-shrink-0 mt-1">
                      <Bot className="w-7 h-7 animate-bounce" />
                    </div>
                    <div className="flex flex-col gap-1">
                      <div className="flex items-center gap-2">
                        <span className="text-[10px] font-mono tracking-wider uppercase bg-rose-500/20 border border-rose-500/40 text-rose-300 px-2.5 py-0.5 rounded-full font-bold">
                          Subscription Killer Copilot
                        </span>
                        <span className="text-xs text-slate-400 font-mono flex items-center gap-1">
                          <Zap className="w-3.5 h-3.5 text-amber-400" />
                          {data.copilot_action.action_mode === "playwright_auto" ? "Playwright Attended Bot" : "Tavily Search Assist"}
                        </span>
                      </div>

                      <h4 className="text-xl font-extrabold text-slate-100 mt-1">
                        Flagged Recurring Charge: <span className="text-rose-400 underline decoration-rose-500/40">{data.copilot_action.target_vendor}</span>
                      </h4>

                      {data.copilot_action.action_mode === "playwright_auto" ? (
                        <p className="text-sm text-slate-400 mt-0.5">
                          Playwright execution engine is ready to intervene and eliminate this subscription automatically.
                          {data.copilot_action.requires_auth && (
                            <span className="block text-xs text-amber-300 font-mono mt-1 flex items-center gap-1">
                              <ShieldAlert className="w-3.5 h-3.5 text-amber-400 inline" />
                              A browser window will open for you to enter your password.
                            </span>
                          )}
                        </p>
                      ) : (
                        <p className="text-sm text-slate-400 mt-0.5">
                          Tavily search assist has located direct cancellation instructions and billing page link.
                        </p>
                      )}
                    </div>
                  </div>

                  {/* Right Column: Action Buttons */}
                  <div className="flex flex-col items-end gap-3 w-full md:w-auto">
                    {data.copilot_action.action_mode === "playwright_auto" ? (
                      <button
                        id="kill-subscription-btn"
                        disabled={killing || killSuccess}
                        onClick={() => data.copilot_action && handleKillSubscription(data.copilot_action)}
                        className={`w-full md:w-auto px-6 py-3.5 rounded-2xl font-bold text-sm shadow-xl flex items-center justify-center gap-2 transition-all duration-300 ${
                          killSuccess
                            ? "bg-emerald-600 text-white border border-emerald-500"
                            : killing
                            ? "bg-rose-950 border border-rose-500/50 text-rose-300 cursor-not-allowed"
                            : "bg-gradient-to-r from-rose-600 to-red-600 hover:from-rose-500 hover:to-red-500 text-white shadow-rose-950/40 hover:scale-[1.02]"
                        }`}
                      >
                        {killing ? (
                          <>
                            <Loader2 className="w-4 h-4 animate-spin text-rose-400" />
                            <span>Agent Deploying...</span>
                          </>
                        ) : killSuccess ? (
                          <>
                            <CheckCircle2 className="w-4 h-4 text-white" />
                            <span>Subscription Cancellation Executed!</span>
                          </>
                        ) : (
                          <>
                            <Zap className="w-4 h-4 text-white fill-white" />
                            <span>Kill {data.copilot_action.target_vendor} Subscription (Auto-Bot)</span>
                          </>
                        )}
                      </button>
                    ) : (
                      <button
                        onClick={() => setShowSteps(!showSteps)}
                        className="w-full md:w-auto px-6 py-3 border border-slate-700 hover:border-slate-600 bg-slate-800/80 hover:bg-slate-800 text-slate-200 font-semibold text-sm rounded-2xl flex items-center justify-center gap-2 transition-all"
                      >
                        <span>View Cancellation Steps</span>
                        {showSteps ? <ChevronUp className="w-4 h-4 text-slate-400" /> : <ChevronDown className="w-4 h-4 text-slate-400" />}
                      </button>
                    )}
                  </div>

                </div>

                {/* Kill Error Notice */}
                {killError && (
                  <div className="mt-4 p-3 bg-rose-500/10 border border-rose-500/30 rounded-xl text-xs text-rose-400 flex items-center gap-2">
                    <AlertCircle className="w-4 h-4 flex-shrink-0" />
                    <span>{killError}</span>
                  </div>
                )}

                {/* Tavily Steps Accordion Expansion */}
                {data.copilot_action.action_mode === "tavily_search" && showSteps && (
                  <div className="mt-6 pt-6 border-t border-slate-800 flex flex-col gap-4">
                    <div className="bg-slate-950/80 border border-slate-800 rounded-2xl p-5 text-sm text-slate-300 leading-relaxed font-sans">
                      <p className="font-semibold text-slate-200 mb-2">Cancellation Instructions:</p>
                      <p className="text-slate-400 text-xs">
                        {data.copilot_action.instructions || `Navigate to your ${data.copilot_action.target_vendor} account settings page to cancel your plan.`}
                      </p>
                    </div>
                    {data.copilot_action.target_url && (
                      <a
                        href={data.copilot_action.target_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="self-start px-5 py-2.5 bg-slate-800 hover:bg-slate-750 border border-slate-700 text-slate-200 text-xs font-semibold rounded-xl flex items-center gap-2 transition-all"
                      >
                        <span>Open Direct Cancellation Link</span>
                        <ExternalLink className="w-3.5 h-3.5 text-slate-400" />
                      </a>
                    )}
                  </div>
                )}
              </div>
            )}

            {/* Quick Metrics Cards */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div className="bg-slate-900/40 border border-slate-800/80 p-6 rounded-2xl flex items-center gap-4">
                <div className="p-3 bg-indigo-500/10 border border-indigo-500/20 rounded-xl text-indigo-400">
                  <DollarSign className="w-6 h-6" />
                </div>
                <div>
                  <p className="text-xs font-mono uppercase tracking-wider text-slate-500">Total Historical Spend</p>
                  <p className="text-2xl font-bold text-slate-200 mt-0.5">${totalHistorical.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}</p>
                </div>
              </div>
              <div className="bg-slate-900/40 border border-slate-800/80 p-6 rounded-2xl flex items-center gap-4">
                <div className="p-3 bg-amber-500/10 border border-amber-500/20 rounded-xl text-amber-400">
                  <TrendingUp className="w-6 h-6" />
                </div>
                <div>
                  <p className="text-xs font-mono uppercase tracking-wider text-slate-500">Daily Historical Avg</p>
                  <p className="text-2xl font-bold text-slate-200 mt-0.5">${avgHistorical.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}</p>
                </div>
              </div>
              <div className="bg-slate-900/40 border border-slate-800/80 p-6 rounded-2xl flex items-center gap-4">
                <div className="p-3 bg-rose-500/10 border border-rose-500/20 rounded-xl text-rose-400">
                  <Sparkles className="w-6 h-6" />
                </div>
                <div>
                  <p className="text-xs font-mono uppercase tracking-wider text-slate-500">Peak Projected Daily Spend</p>
                  <p className="text-2xl font-bold text-slate-200 mt-0.5">${maxProjected.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}</p>
                </div>
              </div>
            </div>

            {/* Time-Series Forecast Visualizer Chart */}
            <div className="bg-slate-900/40 border border-slate-800/80 p-6 rounded-3xl">
              <div className="flex items-center justify-between mb-6">
                <div>
                  <h4 className="text-lg font-bold text-slate-200">Spend Forecast Trend</h4>
                  <p className="text-xs text-slate-500">Zero-Shot 14-Day uncertainty bounds (p10 to p90)</p>
                </div>
                <button
                  onClick={selectNewFile}
                  className="px-4 py-2 border border-slate-800 hover:border-slate-700 bg-slate-950 text-slate-300 text-xs font-semibold rounded-lg transition-colors flex items-center gap-2"
                >
                  <FileText className="w-3.5 h-3.5" />
                  Upload Different Statement
                </button>
              </div>

              {/* Composed Chart Visualizing historical and uncertainty bands */}
              <div className="h-80 w-full font-mono text-[10px]">
                <ResponsiveContainer width="100%" height="100%">
                  <ComposedChart
                    data={getChartData()}
                    margin={{ top: 10, right: 10, left: -20, bottom: 0 }}
                  >
                    <defs>
                      <linearGradient id="riskGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#f43f5e" stopOpacity={0.15}/>
                        <stop offset="95%" stopColor="#f43f5e" stopOpacity={0.01}/>
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" opacity={0.3} />
                    <XAxis 
                      dataKey="date" 
                      stroke="#475569" 
                      tickLine={false} 
                      axisLine={false}
                    />
                    <YAxis 
                      stroke="#475569" 
                      tickLine={false} 
                      axisLine={false} 
                      tickFormatter={(v) => `$${v}`}
                    />
                    <Tooltip 
                      contentStyle={{ backgroundColor: "#020617", border: "1px solid #334155", borderRadius: "12px", color: "#e2e8f0" }} 
                      labelStyle={{ fontWeight: "bold", color: "#94a3b8" }}
                    />
                    <Legend wrapperStyle={{ paddingTop: "15px" }} />
                    
                    {/* Uncertainty Shaded Risk Area */}
                    <Area 
                      name="Projected Range (p10-p90)"
                      dataKey="range" 
                      stroke="none" 
                      fill="url(#riskGrad)" 
                      connectNulls 
                    />

                    {/* Historical daily spend line */}
                    <Line 
                      name="Historical Daily Spend"
                      type="monotone" 
                      dataKey="spend" 
                      stroke="#38bdf8" 
                      strokeWidth={2.5}
                      dot={false}
                      activeDot={{ r: 5 }}
                    />

                    {/* Forecasted median line */}
                    <Line 
                      name="Forecast Median Spend (p50)"
                      type="monotone" 
                      dataKey="p50" 
                      stroke="#f43f5e" 
                      strokeWidth={2}
                      strokeDasharray="4 4"
                      dot={false}
                    />
                  </ComposedChart>
                </ResponsiveContainer>
              </div>
            </div>
            
          </div>
        )}
      </main>

      {/* Hidden input for switching files */}
      <input
        ref={fileInputRef}
        type="file"
        className="hidden"
        accept=".csv"
        onChange={handleFileChange}
      />

      {/* Footer */}
      <footer className="border-t border-slate-900 bg-slate-950 mt-auto py-8">
        <div className="max-w-6xl mx-auto px-6 text-center text-xs text-slate-650 flex flex-col sm:flex-row items-center justify-between gap-4">
          <p>© 2026 FinRoast. Empowered by Antigravity 2.0.</p>
          <div className="flex items-center gap-6">
            <span className="hover:text-slate-450 transition-colors">Privacy</span>
            <span className="hover:text-slate-450 transition-colors">Terms of Service</span>
            <span className="hover:text-slate-450 transition-colors">Security Guardrails</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
