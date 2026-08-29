"use client";

import { useState } from "react";

interface Clause {
  id: string;
  clause_type: string;
  text: string;
  base_risk_score: number;
  parameters: Record<string, number>;
}

interface AnalysisResult {
  contract_id: string;
  contract_value: number | null;
  clauses: Clause[];
  edges: unknown[];
  compounded_risk_score: number;
  risk_level: string;
  estimated_exposure: number | null;
}

function formatCategory(category: string) {
  return category
    .replaceAll("_", " ")
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

function getRiskColor(score: number) {
  if (score >= 0.7) return "text-red-400";
  if (score >= 0.4) return "text-yellow-400";
  return "text-emerald-400";
}

function getRiskBadge(level: string) {
  const normalized = level.toLowerCase();

  if (normalized === "high") {
    return "border-red-500/30 bg-red-500/10 text-red-400";
  }

  if (normalized === "medium") {
    return "border-yellow-500/30 bg-yellow-500/10 text-yellow-400";
  }

  return "border-emerald-500/30 bg-emerald-500/10 text-emerald-400";
}

export default function Home() {
  const [file, setFile] = useState<File | null>(null);
  const [contractValue, setContractValue] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [error, setError] = useState("");

  async function analyzeContract() {
    if (!file) {
      setError("Please select a PDF or TXT contract.");
      return;
    }

    setLoading(true);
    setError("");
    setResult(null);

    const formData = new FormData();
    formData.append("file", file);

    if (contractValue.trim()) {
      formData.append("contract_value", contractValue);
    }

    try {
      const response = await fetch(
        "http://127.0.0.1:8000/api/contracts/upload",
        {
          method: "POST",
          body: formData,
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Contract analysis failed.");
      }

      setResult(data);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Something went wrong while analyzing the contract."
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="min-h-screen bg-[#061426] text-white">
      {/* Background */}
      <div className="pointer-events-none fixed inset-0 overflow-hidden">
        <div className="absolute left-[-150px] top-[-150px] h-[450px] w-[450px] rounded-full bg-blue-600/10 blur-3xl" />
        <div className="absolute right-[-150px] top-[200px] h-[500px] w-[500px] rounded-full bg-cyan-500/10 blur-3xl" />
        <div className="absolute bottom-[-200px] left-[30%] h-[500px] w-[500px] rounded-full bg-indigo-600/10 blur-3xl" />
      </div>

      {/* Navigation */}
      <nav className="relative z-10 border-b border-blue-900/40 bg-[#07182d]/80 backdrop-blur-xl">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-5 lg:px-10">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-blue-400/30 bg-blue-500/10">
              <span className="text-xl">⚖</span>
            </div>

            <div>
              <div className="text-xl font-bold tracking-tight">
                Pact<span className="text-blue-400">Guard</span>
              </div>

              <div className="text-[10px] uppercase tracking-[0.25em] text-slate-500">
                Contract Intelligence
              </div>
            </div>
          </div>

          <div className="hidden items-center gap-8 text-sm text-slate-400 md:flex">
            <span className="cursor-pointer transition hover:text-white">
              Dashboard
            </span>

            <span className="cursor-pointer transition hover:text-white">
              How It Works
            </span>

            <div className="rounded-full border border-blue-400/20 bg-blue-500/10 px-4 py-2 text-blue-300">
              Legal AI
            </div>
          </div>
        </div>
      </nav>

      {/* Hero */}
      <section className="relative z-10 mx-auto max-w-7xl px-6 pb-16 pt-20 lg:px-10 lg:pt-28">
        <div className="max-w-4xl">
          <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-blue-400/20 bg-blue-500/10 px-4 py-2 text-xs font-medium uppercase tracking-[0.2em] text-blue-300">
            <span className="h-2 w-2 rounded-full bg-blue-400 shadow-[0_0_12px_rgba(96,165,250,0.8)]" />
            AI-Powered Contract Analysis
          </div>

          <h1 className="text-5xl font-bold leading-[1.05] tracking-tight sm:text-6xl lg:text-7xl">
            Read the fine print.
            <br />

            <span className="bg-gradient-to-r from-blue-300 via-cyan-300 to-indigo-400 bg-clip-text text-transparent">
              See the risk.
            </span>
          </h1>

          <p className="mt-7 max-w-2xl text-lg leading-8 text-slate-400">
            PactGuard analyzes legal contracts, identifies important clauses,
            evaluates contractual risk, and estimates potential exposure.
          </p>
        </div>

        {/* Upload Card */}
        <div className="mt-14 grid gap-8 lg:grid-cols-[1.3fr_0.7fr]">
          <div className="rounded-3xl border border-blue-900/50 bg-[#0a1d35]/90 p-8 shadow-2xl shadow-blue-950/30 backdrop-blur-xl">
            <div className="mb-7">
              <h2 className="text-xl font-semibold">
                Analyze a contract
              </h2>

              <p className="mt-2 text-sm text-slate-500">
                Upload a PDF or text contract for AI-powered analysis.
              </p>
            </div>

            <label className="mb-3 block text-sm font-medium text-slate-300">
              Contract File
            </label>

            <div className="group rounded-2xl border-2 border-dashed border-blue-900/60 bg-[#07172a] p-10 text-center transition hover:border-blue-500/50 hover:bg-blue-950/20">
              <div className="mx-auto mb-5 flex h-16 w-16 items-center justify-center rounded-2xl border border-blue-400/20 bg-blue-500/10 text-3xl">
                📄
              </div>

              <p className="font-medium text-slate-200">
                Choose your contract
              </p>

              <p className="mt-2 text-sm text-slate-500">
                PDF or TXT files supported
              </p>

              <input
                type="file"
                accept=".pdf,.txt"
                onChange={(e) => {
                  setFile(e.target.files?.[0] || null);
                  setError("");
                }}
                className="mx-auto mt-6 block w-full max-w-xs text-sm text-slate-400 file:mr-4 file:rounded-lg file:border-0 file:bg-blue-500/15 file:px-4 file:py-2 file:text-sm file:font-medium file:text-blue-300 hover:file:bg-blue-500/25"
              />
            </div>

            {file && (
              <div className="mt-4 flex items-center justify-between rounded-xl border border-blue-900/50 bg-[#07172a] px-4 py-3">
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium text-slate-200">
                    {file.name}
                  </p>

                  <p className="mt-1 text-xs text-slate-500">
                    {(file.size / 1024).toFixed(1)} KB
                  </p>
                </div>

                <span className="ml-4 rounded-full bg-emerald-500/10 px-3 py-1 text-xs text-emerald-400">
                  Ready
                </span>
              </div>
            )}

            <label className="mt-7 mb-3 block text-sm font-medium text-slate-300">
              Contract Value
              <span className="ml-2 text-slate-600">(Optional)</span>
            </label>

            <div className="relative">
              <span className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-500">
                $
              </span>

              <input
                type="number"
                value={contractValue}
                onChange={(e) => setContractValue(e.target.value)}
                placeholder="250000"
                className="w-full rounded-xl border border-blue-900/50 bg-[#07172a] px-9 py-3.5 text-white outline-none transition placeholder:text-slate-700 focus:border-blue-400/60 focus:ring-2 focus:ring-blue-500/10"
              />
            </div>

            <button
              onClick={analyzeContract}
              disabled={loading}
              className="mt-7 w-full rounded-xl bg-gradient-to-r from-blue-500 to-indigo-500 px-6 py-4 font-semibold text-white shadow-lg shadow-blue-950/40 transition hover:from-blue-400 hover:to-indigo-400 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {loading ? (
                <span className="flex items-center justify-center gap-3">
                  <span className="h-5 w-5 animate-spin rounded-full border-2 border-white/30 border-t-white" />
                  Analyzing Contract...
                </span>
              ) : (
                "Analyze Contract →"
              )}
            </button>

            {error && (
              <div className="mt-5 rounded-xl border border-red-500/20 bg-red-500/10 px-4 py-3 text-sm text-red-300">
                {error}
              </div>
            )}
          </div>

          {/* Feature Panel */}
          <div className="rounded-3xl border border-blue-900/50 bg-gradient-to-b from-[#0c2340] to-[#08182d] p-8">
            <p className="text-xs font-semibold uppercase tracking-[0.25em] text-blue-400">
              What PactGuard checks
            </p>

            <div className="mt-8 space-y-6">
              <div className="flex gap-4">
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-blue-500/10 text-blue-300">
                  ⚖
                </div>

                <div>
                  <h3 className="font-semibold">Clause Detection</h3>
                  <p className="mt-1 text-sm leading-6 text-slate-500">
                    Identifies important contractual clauses and provisions.
                  </p>
                </div>
              </div>

              <div className="flex gap-4">
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-indigo-500/10 text-indigo-300">
                  ◈
                </div>

                <div>
                  <h3 className="font-semibold">Risk Scoring</h3>
                  <p className="mt-1 text-sm leading-6 text-slate-500">
                    Calculates risk based on detected contractual conditions.
                  </p>
                </div>
              </div>

              <div className="flex gap-4">
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-cyan-500/10 text-cyan-300">
                  $
                </div>

                <div>
                  <h3 className="font-semibold">Exposure Estimation</h3>
                  <p className="mt-1 text-sm leading-6 text-slate-500">
                    Estimates potential financial exposure from risky clauses.
                  </p>
                </div>
              </div>

              <div className="mt-8 rounded-2xl border border-blue-500/10 bg-blue-500/5 p-5">
                <p className="text-xs uppercase tracking-wider text-slate-600">
                  Powered by
                </p>

                <p className="mt-2 font-semibold text-blue-300">
                  Legal NLP + Risk Intelligence
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Results */}
      {result && (
        <section className="relative z-10 mx-auto max-w-7xl px-6 pb-24 lg:px-10">
          <div className="border-t border-blue-900/40 pt-16">
            <div className="flex flex-col justify-between gap-4 md:flex-row md:items-end">
              <div>
                <p className="text-xs uppercase tracking-[0.25em] text-blue-400">
                  Analysis Complete
                </p>

                <h2 className="mt-2 text-3xl font-bold">
                  Contract Results
                </h2>

                <p className="mt-2 text-sm text-slate-500">
                  Contract ID: {result.contract_id}
                </p>
              </div>

              <div
                className={`rounded-full border px-5 py-2 text-sm font-semibold uppercase tracking-wider ${getRiskBadge(
                  result.risk_level
                )}`}
              >
                {result.risk_level} Risk
              </div>
            </div>

            {/* Summary cards */}
            <div className="mt-8 grid gap-5 md:grid-cols-2 xl:grid-cols-4">
              <div className="rounded-2xl border border-blue-900/40 bg-[#0a1d35] p-6">
                <p className="text-sm text-slate-500">
                  Overall Risk Score
                </p>

                <div className="mt-3 flex items-end gap-2">
                  <span
                    className={`text-4xl font-bold ${getRiskColor(
                      result.compounded_risk_score / 100
                    )}`}
                  >
                    {result.compounded_risk_score.toFixed(1)}
                  </span>

                  <span className="mb-1 text-sm text-slate-600">
                    / 100
                  </span>
                </div>

                <div className="mt-4 h-2 overflow-hidden rounded-full bg-slate-800">
                  <div
                    className="h-full rounded-full bg-gradient-to-r from-blue-500 to-indigo-500"
                    style={{
                      width: `${Math.min(
                        100,
                        Math.max(0, result.compounded_risk_score)
                      )}%`,
                    }}
                  />
                </div>
              </div>

              <div className="rounded-2xl border border-blue-900/40 bg-[#0a1d35] p-6">
                <p className="text-sm text-slate-500">
                  Clauses Detected
                </p>

                <p className="mt-3 text-4xl font-bold text-white">
                  {result.clauses.length}
                </p>

                <p className="mt-2 text-xs text-slate-600">
                  Classified contractual provisions
                </p>
              </div>

              <div className="rounded-2xl border border-blue-900/40 bg-[#0a1d35] p-6">
                <p className="text-sm text-slate-500">
                  Contract Value
                </p>

                <p className="mt-3 text-3xl font-bold text-white">
                  {result.contract_value !== null
                    ? `$${result.contract_value.toLocaleString()}`
                    : "N/A"}
                </p>

                <p className="mt-2 text-xs text-slate-600">
                  Declared contract value
                </p>
              </div>

              <div className="rounded-2xl border border-blue-900/40 bg-[#0a1d35] p-6">
                <p className="text-sm text-slate-500">
                  Estimated Exposure
                </p>

                <p className="mt-3 text-3xl font-bold text-white">
                  {result.estimated_exposure !== null
                    ? `$${result.estimated_exposure.toLocaleString()}`
                    : "N/A"}
                </p>

                <p className="mt-2 text-xs text-slate-600">
                  Based on detected risks
                </p>
              </div>
            </div>

            {/* Clause Analysis */}
            <div className="mt-12">
              <div className="mb-6">
                <p className="text-xs uppercase tracking-[0.2em] text-blue-400">
                  Clause Intelligence
                </p>

                <h3 className="mt-2 text-2xl font-bold">
                  Detected Clauses
                </h3>

                <p className="mt-1 text-sm text-slate-500">
                  Individual classifications and risk scores
                </p>
              </div>

              <div className="space-y-5">
                {result.clauses.map((clause, index) => (
                  <div
                    key={clause.id}
                    className="group overflow-hidden rounded-2xl border border-blue-900/40 bg-[#0a1d35] transition hover:border-blue-500/30"
                  >
                    <div className="p-6">
                      <div className="flex flex-col justify-between gap-5 md:flex-row md:items-start">
                        <div className="flex gap-4">
                          <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl border border-blue-500/20 bg-blue-500/10 text-sm font-bold text-blue-300">
                            {String(index + 1).padStart(2, "0")}
                          </div>

                          <div>
                            <p className="text-xs uppercase tracking-wider text-slate-600">
                              Detected Category
                            </p>

                            <h4 className="mt-1 text-xl font-semibold text-white">
                              {formatCategory(clause.clause_type)}
                            </h4>
                          </div>
                        </div>

                        <div className="flex items-center gap-3">
                          <div className="rounded-full border border-blue-500/20 bg-blue-500/10 px-4 py-2 text-sm font-medium text-blue-300">
                            Risk{" "}
                            {(clause.base_risk_score * 100).toFixed(1)}%
                          </div>
                        </div>
                      </div>

                      <div className="mt-6 rounded-xl border border-slate-800 bg-[#07172a] p-5">
                        <p className="whitespace-pre-wrap text-sm leading-7 text-slate-400">
                          {clause.text}
                        </p>
                      </div>

                      {Object.keys(clause.parameters).length > 0 && (
                        <div className="mt-4 flex flex-wrap gap-2">
                          {Object.entries(clause.parameters).map(
                            ([key, value]) => (
                              <div
                                key={key}
                                className="rounded-lg border border-indigo-500/20 bg-indigo-500/5 px-3 py-2 text-xs text-indigo-300"
                              >
                                {formatCategory(key)}: {value}
                              </div>
                            )
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </section>
      )}

      {/* Footer */}
      <footer className="relative z-10 border-t border-blue-900/30 bg-[#051124]">
        <div className="mx-auto flex max-w-7xl flex-col justify-between gap-3 px-6 py-8 text-xs text-slate-600 md:flex-row lg:px-10">
          <p>
            © 2026 PactGuard. Contract intelligence platform.
          </p>

          <p>
            AI-generated analysis should not be considered legal advice.
          </p>
        </div>
      </footer>
    </main>
  );
}