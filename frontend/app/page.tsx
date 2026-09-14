"use client";

import React, { useState, useEffect, useRef, useMemo } from "react";
import bgImage from "./image.png";

interface ParameterData {
  durations?: string[];
  notice_periods?: string[];
  financial_terms?: string[];
}

interface Clause {
  id: string;
  clause_text: string;
  clause_type: string;
  raw_category?: string;
  confidence: number;
  risk_score: number;
  risk_level: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
  risk_factors: string[];
  parameters: ParameterData;
}

interface RiskGraphEdge {
  source: string;
  target: string;
  relation_type: string;
  risk_multiplier: number;
  description: string;
}

interface RiskGraphData {
  nodes: Array<{ id: string; label: string; risk_score: number; risk_level: string; summary: string }>;
  edges: RiskGraphEdge[];
  systemic_risk_score: number;
}

interface AnalysisResult {
  contract_id: string;
  contract_title: string;
  inferred_contract_type: string;
  overall_risk_score: number;
  overall_risk_level: string;
  executive_summary: string;
  clauses: Clause[];
  risk_graph: RiskGraphData;
  actionable_recommendations: string[];
}

interface BriefingData {
  executive_summary: string;
  top_deal_breakers: Array<{
    title: string;
    clause_reference: string;
    hazard_explanation: string;
    recommended_fix: string;
  }>;
  hidden_financial_liabilities: Array<{
    item: string;
    estimated_risk_level: string;
    explanation: string;
  }>;
  negotiation_action_plan: string[];
}

export default function PactGuardDashboard() {
  const [contractText, setContractText] = useState("");
  const [contractTitle, setContractTitle] = useState("");
  const [isLiveSync, setIsLiveSync] = useState(true);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [analysis, setAnalysis] = useState<AnalysisResult | null>(null);
  const [selectedNode, setSelectedNode] = useState<string | null>(null);
  const [hoveredEdge, setHoveredEdge] = useState<RiskGraphEdge | null>(null);
  const [activeTab, setActiveTab] = useState<"graph" | "clauses">("graph");
  const [isDragging, setIsDragging] = useState(false);

  // Main Page View Mode: "dashboard" | "copilot" | "briefing"
  const [pageView, setPageView] = useState<"dashboard" | "copilot" | "briefing">("dashboard");

  // Copilot Chat State
  const [chatMessages, setChatMessages] = useState<Array<{ role: "user" | "assistant"; content: string }>>([]);
  const [questionInput, setQuestionInput] = useState("");
  const [copilotLoading, setCopilotLoading] = useState(false);

  // Briefing State
  const [briefingData, setBriefingData] = useState<BriefingData | null>(null);
  const [briefingLoading, setBriefingLoading] = useState(false);

  const fileInputRef = useRef<HTMLInputElement>(null);

  // Dynamic Suggestion Questions based on Inferred Contract Domain
  const getDynamicSuggestions = (domain: string) => {
    const d = (domain || "").toLowerCase();
    if (d.includes("employment") || d.includes("labor")) {
      return [
        "What is the probation period and can I be terminated during it?",
        "What advance notice is required to terminate employment?",
        "Can the employer unilaterally change my job duties?",
        "What are my leave, working hours, and gratuity entitlements?"
      ];
    } else if (d.includes("real estate") || d.includes("lease") || d.includes("rental")) {
      return [
        "Can I terminate early and what notice is required?",
        "Are there any double penalties or holdover charges?",
        "Who is responsible for repairs and maintenance?",
        "Under what terms is my security deposit refunded?"
      ];
    } else if (d.includes("saas") || d.includes("software")) {
      return [
        "What is the limitation of liability cap?",
        "What happens during service downtime or outages?",
        "Who owns customer data and intellectual property?",
        "What are the renewal and price increase terms?"
      ];
    } else if (d.includes("nda") || d.includes("confidential")) {
      return [
        "How long does the confidentiality obligation last?",
        "What exceptions exist to non-disclosure?",
        "What are the remedies and liabilities for breach?"
      ];
    } else {
      return [
        "What are the top liabilities in this contract?",
        "How can this agreement be terminated?",
        "What dispute resolution or governing law applies?"
      ];
    }
  };

  useEffect(() => {
    if (!isLiveSync || !contractText.trim() || contractText.trim().length < 30) return;
    const timer = setTimeout(() => {
      runAnalysis();
    }, 850);
    return () => clearTimeout(timer);
  }, [contractText, isLiveSync]);

  const runAnalysis = async () => {
    if (!contractText.trim()) return;
    setLoading(true);
    try {
      const res = await fetch("http://localhost:8000/contracts/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          title: contractTitle || "Uploaded Agreement",
          raw_text: contractText,
        }),
      });
      if (res.ok) {
        const data: AnalysisResult = await res.json();
        setAnalysis(data);
      }
    } catch (err) {
      console.error("Analysis failed:", err);
    } finally {
      setLoading(false);
    }
  };

  const uploadFile = async (file: File) => {
    setUploading(true);
    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await fetch("http://localhost:8000/contracts/upload", {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || "Failed to extract text");
      }

      const data = await res.json();
      setContractTitle(data.title);
      setContractText(data.text);
    } catch (err: any) {
      alert("Upload failed: " + err.message);
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) uploadFile(file);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files?.[0];
    if (file) uploadFile(file);
  };

  const handleAskCopilot = async (customQ?: string) => {
    const query = customQ || questionInput;
    if (!query.trim() || !contractText.trim()) return;

    const newChat = [...chatMessages, { role: "user" as const, content: query }];
    setChatMessages(newChat);
    setQuestionInput("");
    setCopilotLoading(true);

    try {
      const res = await fetch("http://localhost:8000/ai/ask-contract", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          contract_text: contractText,
          inferred_type: analysis?.inferred_contract_type || "Legal Contract",
          question: query,
          chat_history: newChat,
        }),
      });

      if (!res.ok) throw new Error("AI request failed");
      const data = await res.json();
      setChatMessages([...newChat, { role: "assistant", content: data.answer }]);
    } catch (err: any) {
      setChatMessages([...newChat, { role: "assistant", content: "⚠️ Response error: " + err.message }]);
    } finally {
      setCopilotLoading(false);
    }
  };

  const handleGenerateBriefing = async () => {
    if (!contractText.trim()) return;
    setBriefingLoading(true);
    try {
      const res = await fetch("http://localhost:8000/ai/executive-briefing", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          contract_text: contractText,
          inferred_type: analysis?.inferred_contract_type || "Legal Contract",
          overall_risk_score: analysis?.overall_risk_score || 50.0,
        }),
      });

      if (!res.ok) throw new Error("Briefing generation failed");
      const data = await res.json();
      setBriefingData(data);
    } catch (err: any) {
      alert("Briefing Error: " + err.message);
    } finally {
      setBriefingLoading(false);
    }
  };

  const graphLayout = useMemo(() => {
    if (!analysis || !analysis.clauses.length) return { nodes: [], edges: [] };

    const nodes = analysis.clauses;
    const count = nodes.length;
    const radius = 160;
    const centerX = 250;
    const centerY = 210;

    const nodePositions = nodes.map((node, i) => {
      const angle = (i / count) * 2 * Math.PI - Math.PI / 2;
      return {
        ...node,
        x: centerX + radius * Math.cos(angle),
        y: centerY + radius * Math.sin(angle),
      };
    });

    const posMap = new Map(nodePositions.map((n) => [n.id, n]));

    const edges = (analysis.risk_graph?.edges || [])
      .map((edge) => {
        const sourceNode = posMap.get(edge.source);
        const targetNode = posMap.get(edge.target);
        if (!sourceNode || !targetNode) return null;
        return {
          ...edge,
          x1: sourceNode.x,
          y1: sourceNode.y,
          x2: targetNode.x,
          y2: targetNode.y,
        };
      })
      .filter(Boolean) as Array<RiskGraphEdge & { x1: number; y1: number; x2: number; y2: number }>;

    return { nodes: nodePositions, edges };
  }, [analysis]);

  const getRiskBadge = (level: string) => {
    switch (level) {
      case "CRITICAL":
        return { bg: "bg-red-50 text-red-700 border-red-200", hex: "#dc2626" };
      case "HIGH":
        return { bg: "bg-amber-50 text-amber-800 border-amber-200", hex: "#d97706" };
      case "MEDIUM":
        return { bg: "bg-yellow-50 text-yellow-800 border-yellow-200", hex: "#ca8a04" };
      default:
        return { bg: "bg-emerald-50 text-emerald-700 border-emerald-200", hex: "#059669" };
    }
  };

  return (
    <div 
      className="min-h-screen text-[#00002A] flex flex-col font-sans selection:bg-[#1A3F75] selection:text-white relative bg-cover bg-center bg-fixed bg-no-repeat"
      style={{
        backgroundImage: `linear-gradient(to bottom, rgba(237, 244, 250, 0.60), rgba(226, 238, 248, 0.70)), url(${bgImage.src})`
      }}
    >
      
      {/* Top Navigation Bar */}
      <header className="bg-white/95 backdrop-blur-md border-b border-[#D0DFEC] sticky top-0 z-50 px-6 py-3.5 shadow-sm">
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4">
          
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-[#1A3F75] flex items-center justify-center text-white font-black text-lg shadow-md shadow-[#1A3F75]/20">
              P
            </div>
            <div>
              <span className="font-extrabold text-xl tracking-tight text-[#00002A]">
                PactGuard
              </span>
              <span className="ml-2 text-xs font-semibold px-2 py-0.5 rounded-full bg-[#E2EEF8] text-[#1A3F75]">
                AI Legal Intelligence
              </span>
            </div>
          </div>

          {/* Navigation Views Switcher */}
          <div className="flex items-center gap-1.5 p-1 bg-[#E2EEF8] rounded-xl border border-[#D0DFEC]">
            <button
              onClick={() => setPageView("dashboard")}
              className={`px-3.5 py-1.5 rounded-lg text-xs font-bold transition-all cursor-pointer ${
                pageView === "dashboard"
                  ? "bg-white text-[#1A3F75] shadow-xs"
                  : "text-[#3B6998] hover:text-[#00002A]"
              }`}
            >
              🛡️ Risk Dashboard & Graph
            </button>
            <button
              onClick={() => setPageView("copilot")}
              className={`px-3.5 py-1.5 rounded-lg text-xs font-bold transition-all cursor-pointer ${
                pageView === "copilot"
                  ? "bg-white text-[#1A3F75] shadow-xs"
                  : "text-[#3B6998] hover:text-[#00002A]"
              }`}
            >
              💬 Ask PactPilot
            </button>
            <button
              onClick={() => {
                setPageView("briefing");
                if (!briefingData && contractText) handleGenerateBriefing();
              }}
              className={`px-3.5 py-1.5 rounded-lg text-xs font-bold transition-all cursor-pointer ${
                pageView === "briefing"
                  ? "bg-white text-[#1A3F75] shadow-xs"
                  : "text-[#3B6998] hover:text-[#00002A]"
              }`}
            >
              📑 Deal-Breaker Briefing
            </button>
          </div>

          {/* Upload & Analyze Actions */}
          <div className="flex items-center gap-2">
            <input
              type="file"
              ref={fileInputRef}
              onChange={handleFileUpload}
              accept=".pdf,.docx,.doc,.txt,.md"
              className="hidden"
            />
            <button
              onClick={() => fileInputRef.current?.click()}
              disabled={uploading}
              className="px-3.5 py-1.5 bg-white hover:bg-[#F2F7FC] border border-[#1A3F75] text-[#1A3F75] text-xs font-bold rounded-xl transition-all flex items-center gap-1.5 cursor-pointer shadow-2xs"
            >
              {uploading ? "Extracting..." : "Upload Document"}
            </button>
            <button
              onClick={runAnalysis}
              disabled={loading || !contractText.trim()}
              className="px-4 py-1.5 bg-[#1A3F75] hover:bg-[#00002A] disabled:opacity-40 text-white text-xs font-bold rounded-xl shadow-md shadow-[#1A3F75]/20 transition-all flex items-center gap-1.5 cursor-pointer"
            >
              {loading ? "Scanning..." : "Analyze Contract"}
            </button>
          </div>

        </div>
      </header>

      {/* Main Container */}
      <div className="max-w-7xl mx-auto w-full p-6 md:p-8 flex-1 flex flex-col gap-6">
        
        {/* VIEW 1: RISK DASHBOARD & INTERACTIVE GRAPH */}
        {pageView === "dashboard" && (
          <>
            {!contractText ? (
              <div
                onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
                onDragLeave={() => setIsDragging(false)}
                onDrop={handleDrop}
                className={`border-2 border-dashed rounded-3xl p-12 text-center transition-all bg-white/90 backdrop-blur-sm shadow-sm flex flex-col items-center justify-center gap-4 ${
                  isDragging ? "border-[#1A3F75] bg-[#EBF3FA]" : "border-[#B8D3EB] hover:border-[#1A3F75]"
                }`}
              >
                <div className="w-16 h-16 rounded-2xl bg-[#E2EEF8] flex items-center justify-center text-[#1A3F75] shadow-inner">
                  <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.8" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                </div>
                <div className="max-w-md">
                  <h2 className="text-xl font-bold text-[#00002A]">Upload any legal contract to begin</h2>
                  <p className="text-xs text-[#3B6998] mt-1.5 leading-relaxed">
                    Drop your PDF, Word (.docx), or text document here. PactGuard’s AI model will automatically segment clauses, detect domain types, and evaluate hidden risks.
                  </p>
                </div>
                <button
                  onClick={() => fileInputRef.current?.click()}
                  className="px-6 py-2.5 bg-[#1A3F75] hover:bg-[#00002A] text-white text-xs font-bold rounded-xl shadow-md transition-all cursor-pointer"
                >
                  Choose File
                </button>
              </div>
            ) : (
              <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
                
                {/* Editor Column */}
                <div className="lg:col-span-5 bg-white/95 backdrop-blur-sm border border-[#D0DFEC] rounded-2xl shadow-sm overflow-hidden flex flex-col h-190">
                  <div className="p-4 border-b border-[#E2EEF8] bg-[#F7FAFD]/90 flex items-center justify-between">
                    <input
                      type="text"
                      value={contractTitle}
                      onChange={(e) => setContractTitle(e.target.value)}
                      placeholder="Contract Title..."
                      className="w-full bg-transparent font-bold text-sm text-[#00002A] focus:outline-none"
                    />
                    {analysis && (
                      <span className="text-[11px] font-semibold px-3 py-1 rounded-full bg-[#E2EEF8] text-[#1A3F75] whitespace-nowrap">
                        {analysis.inferred_contract_type}
                      </span>
                    )}
                  </div>
                  <div className="flex-1 p-4 overflow-y-auto">
                    <textarea
                      value={contractText}
                      onChange={(e) => setContractText(e.target.value)}
                      placeholder="Paste or edit contract text here..."
                      className="w-full h-full bg-transparent resize-none text-[#1E293B] text-xs font-mono leading-relaxed focus:outline-none"
                    />
                  </div>
                  <div className="px-4 py-2 bg-[#F7FAFD] border-t border-[#E2EEF8] text-[11px] text-[#3B6998] flex justify-between items-center">
                    <span>{contractText.length} characters</span>
                    <button onClick={() => { setContractText(""); setAnalysis(null); }} className="text-red-500 hover:text-red-700 cursor-pointer">
                      Clear Document
                    </button>
                  </div>
                </div>

                {/* Graph & Clauses Column */}
                <div className="lg:col-span-7 bg-white/95 backdrop-blur-sm border border-[#D0DFEC] rounded-2xl shadow-sm flex flex-col h-190 overflow-hidden">
                  <div className="p-5 border-b border-[#E2EEF8] bg-[#F7FAFD]/90 grid grid-cols-1 sm:grid-cols-3 gap-4">
                    <div className="p-3.5 rounded-xl bg-white border border-[#D0DFEC] flex items-center justify-between">
                      <div>
                        <span className="text-[10px] font-bold uppercase tracking-wider text-[#3B6998]">Systemic Risk</span>
                        <div className="flex items-baseline gap-1 mt-0.5">
                          <span className="text-2xl font-black text-[#00002A]">{analysis?.overall_risk_score ?? "--"}</span>
                          <span className="text-xs text-[#8FB1D0]">/ 100</span>
                        </div>
                      </div>
                      {analysis && (
                        <span className={`text-[11px] font-bold px-2.5 py-1 rounded-full border ${getRiskBadge(analysis.overall_risk_level).bg}`}>
                          {analysis.overall_risk_level}
                        </span>
                      )}
                    </div>
                    <div className="p-3.5 rounded-xl bg-white border border-[#D0DFEC]">
                      <span className="text-[10px] font-bold uppercase tracking-wider text-[#3B6998]">Domain Detection</span>
                      <p className="text-xs font-bold text-[#00002A] mt-1 truncate">{analysis?.inferred_contract_type || "Detecting..."}</p>
                      <span className="text-[10px] font-semibold text-emerald-600">✓ AI Verified</span>
                    </div>
                    <div className="p-3.5 rounded-xl bg-white border border-[#D0DFEC]">
                      <span className="text-[10px] font-bold uppercase tracking-wider text-[#3B6998]">Compound Hazards</span>
                      <p className="text-xs font-bold text-[#00002A] mt-1">{analysis?.risk_graph.edges.length || 0} Risk Multipliers</p>
                      <span className="text-[10px] font-semibold text-[#1A3F75]">
                        {analysis?.risk_graph.edges.length ? "Cross-clause loops found" : "No systemic loops"}
                      </span>
                    </div>
                  </div>

                  {/* Tabs */}
                  <div className="px-6 pt-3 border-b border-[#E2EEF8] flex items-center gap-6 bg-white">
                    <button
                      onClick={() => setActiveTab("graph")}
                      className={`pb-3 text-xs font-bold border-b-2 transition-all cursor-pointer ${
                        activeTab === "graph" ? "border-[#1A3F75] text-[#1A3F75]" : "border-transparent text-[#8FB1D0]"
                      }`}
                    >
                      🕸️ Interactive Risk Graph
                    </button>
                    <button
                      onClick={() => setActiveTab("clauses")}
                      className={`pb-3 text-xs font-bold border-b-2 transition-all cursor-pointer ${
                        activeTab === "clauses" ? "border-[#1A3F75] text-[#1A3F75]" : "border-transparent text-[#8FB1D0]"
                      }`}
                    >
                      📋 Extracted Clause Intelligence ({analysis?.clauses.length || 0})
                    </button>
                  </div>

                  {/* Graph Render */}
                  {activeTab === "graph" && (
                    <div className="flex-1 p-6 flex flex-col items-center justify-center relative bg-[#F7FAFD]/80 overflow-y-auto">
                      {hoveredEdge && (
                        <div className="absolute top-4 left-6 right-6 p-3 rounded-xl bg-white border border-amber-300 shadow-lg text-xs z-10">
                          <div className="flex items-center justify-between text-amber-700 font-bold">
                            <span>⚠ {hoveredEdge.relation_type}</span>
                            <span>×{hoveredEdge.risk_multiplier} Multiplier</span>
                          </div>
                          <p className="text-[#3B6998] mt-0.5">{hoveredEdge.description}</p>
                        </div>
                      )}

                      <div className="w-full max-w-120 aspect-square relative bg-white border border-[#D0DFEC] rounded-2xl p-4 shadow-sm flex items-center justify-center">
                        <svg className="w-full h-full" viewBox="0 0 500 420">
                          {graphLayout.edges.map((edge, idx) => (
                            <g key={idx} onMouseEnter={() => setHoveredEdge(edge)} onMouseLeave={() => setHoveredEdge(null)}>
                              <line
                                x1={edge.x1} y1={edge.y1} x2={edge.x2} y2={edge.y2}
                                stroke="#f59e0b" strokeWidth={2.5} strokeDasharray="4 4"
                                className="cursor-pointer opacity-80 hover:opacity-100"
                              />
                              <circle cx={(edge.x1 + edge.x2) / 2} cy={(edge.y1 + edge.y2) / 2} r={11} fill="#1A3F75" stroke="#f59e0b" strokeWidth={1.5} />
                              <text x={(edge.x1 + edge.x2) / 2} y={(edge.y1 + edge.y2) / 2 + 3.5} fontSize="9" fill="#ffffff" textAnchor="middle" fontWeight="bold">
                                ×{edge.risk_multiplier}
                              </text>
                            </g>
                          ))}
                          <circle cx={250} cy={210} r={32} fill="#1A3F75" stroke="#D0DFEC" strokeWidth={3} />
                          <text x={250} y={205} fontSize="9" fill="#E2EEF8" textAnchor="middle" fontWeight="bold">SYSTEMIC</text>
                          <text x={250} y={222} fontSize="14" fill="#ffffff" textAnchor="middle" fontWeight="black">{analysis?.overall_risk_score || 0}</text>

                          {graphLayout.nodes.map((node) => {
                            const badge = getRiskBadge(node.risk_level);
                            const isSelected = selectedNode === node.id;
                            return (
                              <g key={node.id} onClick={() => setSelectedNode(node.id === selectedNode ? null : node.id)} className="cursor-pointer">
                                <line x1={node.x} y1={node.y} x2={250} y2={210} stroke="#D0DFEC" strokeWidth={1} strokeDasharray="2 2" />
                                <circle cx={node.x} cy={node.y} r={isSelected ? 24 : 20} fill="#ffffff" stroke={badge.hex} strokeWidth={isSelected ? 3.5 : 2.5} />
                                <text x={node.x} y={node.y + 4} fontSize="10" fill={badge.hex} textAnchor="middle" fontWeight="bold">{node.risk_score}</text>
                                <text x={node.x} y={node.y + (node.y > 210 ? 30 : -24)} fontSize="10" fill="#1A3F75" textAnchor="middle" fontWeight="bold">
                                  {node.clause_type.length > 17 ? node.clause_type.slice(0, 15) + "..." : node.clause_type}
                                </text>
                              </g>
                            );
                          })}
                        </svg>
                      </div>

                      {selectedNode && (
                        <div className="w-full max-w-120 mt-4 p-4 rounded-xl bg-white border border-[#1A3F75]/30 text-xs shadow-md space-y-2">
                          {(() => {
                            const c = analysis?.clauses.find((cl) => cl.id === selectedNode);
                            if (!c) return null;
                            return (
                              <>
                                <div className="flex justify-between items-center">
                                  <span className="font-extrabold text-[#1A3F75] text-sm">{c.clause_type}</span>
                                  <span className={`px-2 py-0.5 rounded-full font-bold text-[10px] border ${getRiskBadge(c.risk_level).bg}`}>
                                    {c.risk_level} • {c.risk_score}/100
                                  </span>
                                </div>
                                <p className="text-[#3B6998] font-mono text-[11px] bg-[#F7FAFD] p-2.5 rounded border border-[#E2EEF8]">"{c.clause_text}"</p>
                                <div className="flex flex-wrap gap-1">
                                  {c.risk_factors.map((rf, idx) => (
                                    <span key={idx} className="text-[10px] px-2 py-0.5 rounded bg-red-50 text-red-700 border border-red-200 font-semibold">⚠ {rf}</span>
                                  ))}
                                </div>
                              </>
                            );
                          })()}
                        </div>
                      )}
                    </div>
                  )}

                  {/* Clauses List Render */}
                  {activeTab === "clauses" && (
                    <div className="p-6 space-y-4 flex-1 overflow-y-auto bg-[#F7FAFD]/80">
                      {analysis?.clauses.map((clause) => {
                        const badge = getRiskBadge(clause.risk_level);
                        return (
                          <div key={clause.id} className="p-4 rounded-xl bg-white border border-[#D0DFEC] shadow-2xs space-y-2.5">
                            <div className="flex items-center justify-between">
                              <span className="font-bold text-sm text-[#00002A]">{clause.clause_type}</span>
                              <span className={`text-[11px] px-2.5 py-0.5 rounded-full font-bold border ${badge.bg}`}>
                                {clause.risk_level} • Risk {clause.risk_score}
                              </span>
                            </div>
                            <p className="text-xs text-[#334155] font-mono bg-[#F7FAFD] p-3 rounded-lg border border-[#E2EEF8]">"{clause.clause_text}"</p>
                            <div className="flex flex-wrap gap-1.5">
                              {clause.risk_factors.map((rf, idx) => (
                                <span key={idx} className="text-[10px] font-semibold px-2 py-0.5 rounded-md bg-red-50 text-red-700 border border-red-200">⚠ {rf}</span>
                              ))}
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>

              </div>
            )}
          </>
        )}

        {/* VIEW 2: INTERACTIVE LEGAL COPILOT ("ASK MY CONTRACT") */}
        {pageView === "copilot" && (
          <div className="bg-white/95 backdrop-blur-sm border border-[#D0DFEC] rounded-3xl shadow-sm p-6 md:p-8 flex flex-col h-190">
            
            <div className="pb-4 border-b border-[#E2EEF8] flex items-center justify-between">
              <div>
                <h2 className="text-lg font-bold text-[#00002A]">💬 Q&A with PactPilot</h2>
                <p className="text-xs text-[#3B6998]">Ask anything about your agreement in plain English. The AI cites exact clauses.</p>
              </div>
              <span className="text-xs font-semibold px-3 py-1 rounded-full bg-[#E2EEF8] text-[#1A3F75]">
                Active: {analysis?.inferred_contract_type || "Contract Loaded"}
              </span>
            </div>

            {/* Dynamic Domain-Aware Suggested Question Chips */}
            <div className="py-3 flex flex-wrap gap-2 border-b border-[#E2EEF8]">
              <span className="text-[11px] font-bold text-[#1A3F75] py-1">Try Asking:</span>
              {getDynamicSuggestions(analysis?.inferred_contract_type || "").map((suggestion, idx) => (
                <button
                  key={idx}
                  onClick={() => handleAskCopilot(suggestion)}
                  className="px-3 py-1 rounded-full bg-[#F2F7FC] hover:bg-[#E2EEF8] border border-[#B8D3EB] text-[#1A3F75] text-xs transition-all cursor-pointer"
                >
                  {suggestion}
                </button>
              ))}
            </div>

            {/* Chat History */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4 my-2">
              {chatMessages.length === 0 ? (
                <div className="h-full flex flex-col items-center justify-center text-center text-[#8FB1D0] space-y-2">
                  <div className="w-12 h-12 rounded-full bg-[#E2EEF8] flex items-center justify-center text-[#1A3F75]">💬</div>
                  <p className="text-sm font-semibold text-[#3B6998]">No questions asked yet.</p>
                  <p className="text-xs max-w-sm">Type any question below or click one of the suggestion chips above.</p>
                </div>
              ) : (
                chatMessages.map((msg, idx) => (
                  <div key={idx} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
                    <div
                      className={`max-w-[80%] rounded-2xl p-4 text-xs leading-relaxed ${
                        msg.role === "user"
                          ? "bg-[#1A3F75] text-white font-medium"
                          : "bg-[#F7FAFD] text-[#00002A] border border-[#D0DFEC] shadow-2xs whitespace-pre-wrap"
                      }`}
                    >
                      {msg.content}
                    </div>
                  </div>
                ))
              )}
              {copilotLoading && (
                <div className="flex justify-start">
                  <div className="bg-[#F7FAFD] border border-[#D0DFEC] rounded-2xl p-4 text-xs text-[#3B6998] flex items-center gap-2">
                    <span className="animate-spin h-3.5 w-3.5 border-2 border-[#1A3F75] border-t-transparent rounded-full" />
                    Analyzing contract clauses & legal precedent...
                  </div>
                </div>
              )}
            </div>

            {/* Query Input */}
            <div className="pt-2 flex gap-2">
              <input
                type="text"
                value={questionInput}
                onChange={(e) => setQuestionInput(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleAskCopilot()}
                placeholder="Ask a question (e.g., 'What are my probation or termination rights?')..."
                className="flex-1 bg-[#F7FAFD] border border-[#D0DFEC] rounded-xl px-4 py-2.5 text-xs text-[#00002A] focus:outline-none focus:border-[#1A3F75]"
              />
              <button
                onClick={() => handleAskCopilot()}
                disabled={copilotLoading || !questionInput.trim() || !contractText.trim()}
                className="px-5 py-2.5 bg-[#1A3F75] hover:bg-[#00002A] disabled:opacity-40 text-white text-xs font-bold rounded-xl transition-all cursor-pointer"
              >
                Ask Copilot
              </button>
            </div>

          </div>
        )}

        {/* VIEW 3: 1-CLICK EXECUTIVE SUMMARY & DEAL-BREAKER SHEET */}
        {pageView === "briefing" && (
          <div className="bg-white/95 backdrop-blur-sm border border-[#D0DFEC] rounded-3xl shadow-sm p-6 md:p-8 space-y-6">
            
            <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 border-b border-[#E2EEF8] gap-4">
              <div>
                <h2 className="text-xl font-bold text-[#00002A]">📑 Deal-Breaker & Executive Briefing</h2>
                <p className="text-xs text-[#3B6998]">1-Page high-stakes briefing highlighting critical hazards, hidden costs, and negotiation points.</p>
              </div>
              <button
                onClick={handleGenerateBriefing}
                disabled={briefingLoading || !contractText.trim()}
                className="px-4 py-2 bg-[#1A3F75] hover:bg-[#00002A] text-white text-xs font-bold rounded-xl transition-all shadow-md cursor-pointer"
              >
                {briefingLoading ? "Generating Briefing..." : "🔄 Refresh Briefing"}
              </button>
            </div>

            {briefingLoading ? (
              <div className="py-20 flex flex-col items-center justify-center gap-3 text-center">
                <span className="animate-spin h-8 w-8 border-3 border-[#1A3F75] border-t-transparent rounded-full" />
                <p className="text-sm font-bold text-[#00002A]">Generating 1-Page Deal-Breaker Sheet...</p>
                <p className="text-xs text-[#3B6998]">Evaluating compound liabilities and extracting negotiation counter-offers.</p>
              </div>
            ) : briefingData ? (
              <div className="space-y-6">
                
                {/* Executive Summary Card */}
                <div className="p-5 rounded-2xl bg-[#F2F7FC] border border-[#D0DFEC]">
                  <h3 className="text-xs font-bold uppercase tracking-wider text-[#1A3F75]">Executive Overview</h3>
                  <p className="text-sm text-[#00002A] font-medium mt-1 leading-relaxed">{briefingData.executive_summary}</p>
                </div>

                {/* Top 3 Deal Breakers */}
                <div>
                  <h3 className="text-sm font-bold text-[#00002A] mb-3 flex items-center gap-2">
                    <span>🚨 Top Deal-Breakers (Must Negotiate)</span>
                  </h3>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    {briefingData.top_deal_breakers?.map((db, idx) => (
                      <div key={idx} className="p-4 rounded-2xl bg-red-50/60 border border-red-200 space-y-2">
                        <div className="flex items-center justify-between">
                          <span className="text-xs font-extrabold text-red-900">{db.title}</span>
                          <span className="text-[10px] px-2 py-0.5 rounded-full bg-red-100 text-red-800 font-bold">{db.clause_reference}</span>
                        </div>
                        <p className="text-xs text-red-950/80 leading-relaxed">{db.hazard_explanation}</p>
                        <div className="pt-2 border-t border-red-200/60">
                          <span className="text-[10px] font-bold text-red-900 uppercase">Recommended Redline:</span>
                          <p className="text-[11px] font-mono text-red-900 mt-0.5 bg-white/80 p-2 rounded border border-red-200">
                            "{db.recommended_fix}"
                          </p>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Hidden Liabilities */}
                <div>
                  <h3 className="text-sm font-bold text-[#00002A] mb-3 flex items-center gap-2">
                    <span>💸 Hidden Financial Exposure</span>
                  </h3>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {briefingData.hidden_financial_liabilities?.map((liab, idx) => (
                      <div key={idx} className="p-4 rounded-2xl bg-amber-50/60 border border-amber-200 space-y-1">
                        <div className="flex items-center justify-between">
                          <span className="text-xs font-bold text-amber-900">{liab.item}</span>
                          <span className="text-[10px] px-2 py-0.5 rounded font-bold bg-amber-200 text-amber-900">{liab.estimated_risk_level}</span>
                        </div>
                        <p className="text-xs text-amber-950/80 leading-relaxed">{liab.explanation}</p>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Negotiation Action Plan */}
                <div className="p-5 rounded-2xl bg-white border border-[#D0DFEC] shadow-2xs space-y-3">
                  <div className="flex items-center justify-between">
                    <h3 className="text-xs font-bold uppercase tracking-wider text-[#1A3F75]">📋 Counter-Negotiation Checklist</h3>
                    <button
                      onClick={() => {
                        navigator.clipboard.writeText(briefingData.negotiation_action_plan.join("\n"));
                        alert("Checklist copied to clipboard!");
                      }}
                      className="text-xs text-[#1A3F75] font-bold underline cursor-pointer"
                    >
                      Copy Checklist
                    </button>
                  </div>
                  <ul className="space-y-2">
                    {briefingData.negotiation_action_plan?.map((item, idx) => (
                      <li key={idx} className="text-xs text-[#1E293B] flex items-start gap-2.5">
                        <span className="w-4 h-4 rounded-full bg-[#E2EEF8] text-[#1A3F75] font-bold flex items-center justify-center text-[10px] shrink-0 mt-0.5">
                          {idx + 1}
                        </span>
                        <span>{item}</span>
                      </li>
                    ))}
                  </ul>
                </div>

              </div>
            ) : (
              <div className="py-16 text-center text-[#8FB1D0]">
                <p className="text-sm font-semibold text-[#3B6998]">No briefing generated yet.</p>
                <p className="text-xs mt-1">Upload a contract and click "Refresh Briefing" above.</p>
              </div>
            )}

          </div>
        )}

      </div>
    </div>
  );
}