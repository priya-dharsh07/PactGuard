"use client";

import React, { useState, useEffect, useRef, useMemo } from "react";

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
  obligations?: string[];
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

  const fileInputRef = useRef<HTMLInputElement>(null);

  // Debounced Live Analysis on typing
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

  const applyQuickFix = (type: "notice" | "cap" | "indemnity") => {
    let updated = contractText;
    if (type === "notice") {
      updated = updated.replace(/(\b\d+\s*days?\s*notice|\bimmediate\b|\b24 hours\b)/gi, "thirty (30) days written notice");
    } else if (type === "cap") {
      updated = updated.replace(
        /(unlimited|no limitation|without cap)/gi,
        "capped at the total fees paid in the preceding twelve (12) months"
      );
    } else if (type === "indemnity") {
      updated = updated.replace(/solely defend, indemnify/gi, "mutually defend, indemnify");
      updated = updated.replace(/without limitation/gi, "excluding consequential damages");
    }
    setContractText(updated);
  };

  // Circular layout for Interactive Risk Graph
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
        return { bg: "bg-red-50 text-red-700 border-red-200", dot: "bg-red-600", hex: "#dc2626" };
      case "HIGH":
        return { bg: "bg-amber-50 text-amber-800 border-amber-200", dot: "bg-amber-500", hex: "#d97706" };
      case "MEDIUM":
        return { bg: "bg-yellow-50 text-yellow-800 border-yellow-200", dot: "bg-yellow-500", hex: "#ca8a04" };
      default:
        return { bg: "bg-emerald-50 text-emerald-700 border-emerald-200", dot: "bg-emerald-500", hex: "#059669" };
    }
  };

  return (
    <div className="min-h-screen bg-[#EDF4FA] text-[#00002A] flex flex-col font-sans selection:bg-[#1A3F75] selection:text-white">
      
      {/* Top Professional Navigation Bar */}
      <header className="bg-white/90 backdrop-blur-md border-b border-[#D0DFEC] sticky top-0 z-50 px-6 py-4 shadow-sm">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          
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

          <div className="flex items-center gap-3">
            <div className="hidden sm:flex items-center gap-2 bg-[#F2F7FC] border border-[#D0DFEC] px-3 py-1.5 rounded-lg text-xs">
              <span className="text-[#3B6998] font-medium">Real-Time Sync</span>
              <button
                onClick={() => setIsLiveSync(!isLiveSync)}
                className={`w-7 h-4 rounded-full transition-colors relative cursor-pointer ${
                  isLiveSync ? "bg-[#1A3F75]" : "bg-slate-300"
                }`}
              >
                <div
                  className={`w-3 h-3 rounded-full bg-white transition-transform absolute top-0.5 ${
                    isLiveSync ? "left-3.5" : "left-0.5"
                  }`}
                />
              </button>
            </div>

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
              className="px-4 py-2 bg-white hover:bg-[#F2F7FC] border border-[#1A3F75] text-[#1A3F75] text-xs font-bold rounded-xl transition-all flex items-center gap-2 cursor-pointer shadow-sm hover:shadow"
            >
              {uploading ? (
                <span className="animate-spin h-3.5 w-3.5 border-2 border-[#1A3F75] border-t-transparent rounded-full" />
              ) : (
                <svg className="w-4 h-4 text-[#1A3F75]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
                </svg>
              )}
              <span>{uploading ? "Extracting..." : "Upload Document"}</span>
            </button>

            <button
              onClick={runAnalysis}
              disabled={loading || !contractText.trim()}
              className="px-5 py-2 bg-[#1A3F75] hover:bg-[#00002A] disabled:opacity-40 text-white text-xs font-bold rounded-xl shadow-md shadow-[#1A3F75]/20 transition-all flex items-center gap-2 cursor-pointer"
            >
              {loading ? (
                <>
                  <span className="animate-spin h-3.5 w-3.5 border-2 border-white border-t-transparent rounded-full" />
                  <span>Scanning...</span>
                </>
              ) : (
                <>
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
                  </svg>
                  <span>Analyze Contract</span>
                </>
              )}
            </button>
          </div>

        </div>
      </header>

      {/* Main Container */}
      <div className="max-w-7xl mx-auto w-full p-6 md:p-8 flex-1 flex flex-col gap-6">
        
        {/* Welcome / Empty State Prompt (if no contract text is loaded yet) */}
        {!contractText && (
          <div
            onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
            onDragLeave={() => setIsDragging(false)}
            onDrop={handleDrop}
            className={`border-2 border-dashed rounded-3xl p-12 text-center transition-all bg-white shadow-sm flex flex-col items-center justify-center gap-4 ${
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
            <div className="flex gap-3">
              <button
                onClick={() => fileInputRef.current?.click()}
                className="px-6 py-2.5 bg-[#1A3F75] hover:bg-[#00002A] text-white text-xs font-bold rounded-xl shadow-md transition-all cursor-pointer"
              >
                Choose File from Computer
              </button>
            </div>
          </div>
        )}

        {/* Active Analysis Dashboard */}
        {contractText && (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
            
            {/* Left Column: Smart Contract Editor */}
            <div className="lg:col-span-5 bg-white border border-[#D0DFEC] rounded-2xl shadow-sm overflow-hidden flex flex-col h-[760px]">
              
              <div className="p-4 border-b border-[#E2EEF8] bg-[#F7FAFD] flex items-center justify-between">
                <div className="w-full">
                  <input
                    type="text"
                    value={contractTitle}
                    onChange={(e) => setContractTitle(e.target.value)}
                    placeholder="Enter document title..."
                    className="w-full bg-transparent font-bold text-sm text-[#00002A] focus:outline-none placeholder-[#8FB1D0]"
                  />
                  <div className="text-[11px] text-[#3B6998] mt-0.5">
                    Live editable text • AI re-evaluates automatically
                  </div>
                </div>
                {analysis && (
                  <span className="text-[11px] font-semibold px-3 py-1 rounded-full bg-[#E2EEF8] text-[#1A3F75] whitespace-nowrap">
                    {analysis.inferred_contract_type}
                  </span>
                )}
              </div>

              {/* Quick Negotiation Actions */}
              <div className="px-4 py-2.5 bg-[#EDF4FA] border-b border-[#D0DFEC] flex items-center gap-2 overflow-x-auto">
                <span className="text-[11px] font-bold text-[#1A3F75] shrink-0">⚡ Quick Redlines:</span>
                <button
                  onClick={() => applyQuickFix("notice")}
                  className="px-2.5 py-1 bg-white hover:bg-[#E2EEF8] border border-[#B8D3EB] text-[#1A3F75] rounded-lg text-[11px] font-medium transition-all shrink-0 cursor-pointer shadow-2xs"
                >
                  +30-Day Notice
                </button>
                <button
                  onClick={() => applyQuickFix("cap")}
                  className="px-2.5 py-1 bg-white hover:bg-[#E2EEF8] border border-[#B8D3EB] text-[#1A3F75] rounded-lg text-[11px] font-medium transition-all shrink-0 cursor-pointer shadow-2xs"
                >
                  Cap 12mo Fees
                </button>
                <button
                  onClick={() => applyQuickFix("indemnity")}
                  className="px-2.5 py-1 bg-white hover:bg-[#E2EEF8] border border-[#B8D3EB] text-[#1A3F75] rounded-lg text-[11px] font-medium transition-all shrink-0 cursor-pointer shadow-2xs"
                >
                  Mutualize Indemnity
                </button>
              </div>

              {/* Text Area */}
              <div className="flex-1 p-4 overflow-y-auto">
                <textarea
                  value={contractText}
                  onChange={(e) => setContractText(e.target.value)}
                  placeholder="Paste or edit contract text here..."
                  className="w-full h-full bg-transparent resize-none text-[#1E293B] text-xs font-mono leading-relaxed focus:outline-none placeholder-[#8FB1D0]"
                />
              </div>

              <div className="px-4 py-2.5 bg-[#F7FAFD] border-t border-[#E2EEF8] text-[11px] text-[#3B6998] flex justify-between items-center font-medium">
                <span>{contractText.length} characters</span>
                <button
                  onClick={() => { setContractText(""); setAnalysis(null); }}
                  className="text-red-500 hover:text-red-700 text-[11px] cursor-pointer"
                >
                  Clear Document
                </button>
              </div>

            </div>

            {/* Right Column: AI Risk & Interactive Graph */}
            <div className="lg:col-span-7 bg-white border border-[#D0DFEC] rounded-2xl shadow-sm flex flex-col h-[760px] overflow-hidden">
              
              {/* Executive Metrics Header */}
              <div className="p-5 border-b border-[#E2EEF8] bg-[#F7FAFD] grid grid-cols-1 sm:grid-cols-3 gap-4">
                
                <div className="p-3.5 rounded-xl bg-white border border-[#D0DFEC] shadow-2xs flex items-center justify-between">
                  <div>
                    <span className="text-[10px] font-bold uppercase tracking-wider text-[#3B6998]">Systemic Risk</span>
                    <div className="flex items-baseline gap-1 mt-0.5">
                      <span className="text-2xl font-black text-[#00002A]">
                        {analysis?.overall_risk_score ?? "--"}
                      </span>
                      <span className="text-xs text-[#8FB1D0]">/ 100</span>
                    </div>
                  </div>
                  {analysis && (
                    <span className={`text-[11px] font-bold px-2.5 py-1 rounded-full border ${getRiskBadge(analysis.overall_risk_level).bg}`}>
                      {analysis.overall_risk_level}
                    </span>
                  )}
                </div>

                <div className="p-3.5 rounded-xl bg-white border border-[#D0DFEC] shadow-2xs">
                  <span className="text-[10px] font-bold uppercase tracking-wider text-[#3B6998]">Document Domain</span>
                  <p className="text-xs font-bold text-[#00002A] mt-1 truncate">
                    {analysis?.inferred_contract_type || "Detecting..."}
                  </p>
                  <span className="text-[10px] font-semibold text-emerald-600">✓ AI Verified</span>
                </div>

                <div className="p-3.5 rounded-xl bg-white border border-[#D0DFEC] shadow-2xs">
                  <span className="text-[10px] font-bold uppercase tracking-wider text-[#3B6998]">Compound Hazards</span>
                  <p className="text-xs font-bold text-[#00002A] mt-1">
                    {analysis?.risk_graph.edges.length || 0} Risk Multipliers
                  </p>
                  <span className="text-[10px] font-semibold text-[#1A3F75]">
                    {analysis?.risk_graph.edges.length ? "Cross-clause loops found" : "No systemic loops"}
                  </span>
                </div>

              </div>

              {/* View Selector Tabs */}
              <div className="px-6 pt-3 border-b border-[#E2EEF8] flex items-center gap-6 bg-white">
                <button
                  onClick={() => setActiveTab("graph")}
                  className={`pb-3 text-xs font-bold border-b-2 transition-all cursor-pointer ${
                    activeTab === "graph"
                      ? "border-[#1A3F75] text-[#1A3F75]"
                      : "border-transparent text-[#8FB1D0] hover:text-[#3B6998]"
                  }`}
                >
                  🕸️ Interactive Risk Graph
                </button>
                <button
                  onClick={() => setActiveTab("clauses")}
                  className={`pb-3 text-xs font-bold border-b-2 transition-all cursor-pointer ${
                    activeTab === "clauses"
                      ? "border-[#1A3F75] text-[#1A3F75]"
                      : "border-transparent text-[#8FB1D0] hover:text-[#3B6998]"
                  }`}
                >
                  📋 Extracted Clause Intelligence ({analysis?.clauses.length || 0})
                </button>
              </div>

              {/* Tab 1: Interactive Visual Risk Graph */}
              {activeTab === "graph" && (
                <div className="flex-1 p-6 flex flex-col items-center justify-center relative bg-[#F7FAFD] overflow-y-auto">
                  
                  {hoveredEdge && (
                    <div className="absolute top-4 left-6 right-6 p-3 rounded-xl bg-white border border-amber-300 shadow-lg text-xs z-10 animate-fadeIn">
                      <div className="flex items-center justify-between text-amber-700 font-bold">
                        <span>⚠ {hoveredEdge.relation_type}</span>
                        <span>×{hoveredEdge.risk_multiplier} Multiplier</span>
                      </div>
                      <p className="text-[#3B6998] mt-0.5 leading-relaxed">{hoveredEdge.description}</p>
                    </div>
                  )}

                  <div className="w-full max-w-[480px] aspect-square relative bg-white border border-[#D0DFEC] rounded-2xl p-4 shadow-sm flex items-center justify-center">
                    <svg className="w-full h-full" viewBox="0 0 500 420">
                      
                      {/* Connection Lines */}
                      {graphLayout.edges.map((edge, idx) => (
                        <g key={idx} onMouseEnter={() => setHoveredEdge(edge)} onMouseLeave={() => setHoveredEdge(null)}>
                          <line
                            x1={edge.x1}
                            y1={edge.y1}
                            x2={edge.x2}
                            y2={edge.y2}
                            stroke="#f59e0b"
                            strokeWidth={2.5}
                            strokeDasharray="4 4"
                            className="cursor-pointer transition-opacity opacity-80 hover:opacity-100"
                          />
                          <circle
                            cx={(edge.x1 + edge.x2) / 2}
                            cy={(edge.y1 + edge.y2) / 2}
                            r={11}
                            fill="#1A3F75"
                            stroke="#f59e0b"
                            strokeWidth={1.5}
                          />
                          <text
                            x={(edge.x1 + edge.x2) / 2}
                            y={(edge.y1 + edge.y2) / 2 + 3.5}
                            fontSize="9"
                            fill="#ffffff"
                            textAnchor="middle"
                            fontWeight="bold"
                          >
                            ×{edge.risk_multiplier}
                          </text>
                        </g>
                      ))}

                      {/* Central Systemic Hub */}
                      <circle cx={250} cy={210} r={32} fill="#1A3F75" stroke="#D0DFEC" strokeWidth={3} />
                      <text x={250} y={205} fontSize="9" fill="#E2EEF8" textAnchor="middle" fontWeight="bold">
                        SYSTEMIC
                      </text>
                      <text x={250} y={222} fontSize="14" fill="#ffffff" textAnchor="middle" fontWeight="black">
                        {analysis?.overall_risk_score || 0}
                      </text>

                      {/* Nodes */}
                      {graphLayout.nodes.map((node) => {
                        const badge = getRiskBadge(node.risk_level);
                        const isSelected = selectedNode === node.id;

                        return (
                          <g
                            key={node.id}
                            onClick={() => setSelectedNode(node.id === selectedNode ? null : node.id)}
                            className="cursor-pointer transition-transform hover:scale-105"
                          >
                            <line
                              x1={node.x}
                              y1={node.y}
                              x2={250}
                              y2={210}
                              stroke="#D0DFEC"
                              strokeWidth={1}
                              strokeDasharray="2 2"
                            />

                            <circle
                              cx={node.x}
                              cy={node.y}
                              r={isSelected ? 24 : 20}
                              fill="#ffffff"
                              stroke={badge.hex}
                              strokeWidth={isSelected ? 3.5 : 2.5}
                              className="shadow-md"
                            />

                            <text
                              x={node.x}
                              y={node.y + 4}
                              fontSize="10"
                              fill={badge.hex}
                              textAnchor="middle"
                              fontWeight="bold"
                            >
                              {node.risk_score}
                            </text>

                            <text
                              x={node.x}
                              y={node.y + (node.y > 210 ? 30 : -24)}
                              fontSize="10"
                              fill="#1A3F75"
                              textAnchor="middle"
                              fontWeight="bold"
                            >
                              {node.clause_type.length > 17 ? node.clause_type.slice(0, 15) + "..." : node.clause_type}
                            </text>
                          </g>
                        );
                      })}
                    </svg>
                  </div>

                  {/* Selected Node Details Drawer */}
                  {selectedNode && (
                    <div className="w-full max-w-[480px] mt-4 p-4 rounded-xl bg-white border border-[#1A3F75]/30 text-xs shadow-md space-y-2">
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
                            <p className="text-[#3B6998] font-mono text-[11px] bg-[#F7FAFD] p-2.5 rounded border border-[#E2EEF8] leading-relaxed">
                              "{c.clause_text}"
                            </p>
                            <div className="flex flex-wrap gap-1 pt-1">
                              {c.risk_factors.map((rf, idx) => (
                                <span key={idx} className="text-[10px] px-2 py-0.5 rounded bg-red-50 text-red-700 border border-red-200 font-semibold">
                                  ⚠ {rf}
                                </span>
                              ))}
                            </div>
                          </>
                        );
                      })()}
                    </div>
                  )}

                </div>
              )}

              {/* Tab 2: Detailed Clauses List */}
              {activeTab === "clauses" && (
                <div className="p-6 space-y-4 flex-1 overflow-y-auto bg-[#F7FAFD]">
                  {analysis?.clauses.map((clause) => {
                    const badge = getRiskBadge(clause.risk_level);
                    return (
                      <div
                        key={clause.id}
                        className="p-4 rounded-xl bg-white border border-[#D0DFEC] shadow-2xs hover:shadow-md transition-all space-y-2.5"
                      >
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2">
                            <span className="font-bold text-sm text-[#00002A]">{clause.clause_type}</span>
                            <span className="text-[10px] px-2 py-0.5 rounded-full bg-[#E2EEF8] text-[#1A3F75] font-semibold">
                              {Math.round(clause.confidence * 100)}% AI Confidence
                            </span>
                          </div>
                          <span className={`text-[11px] px-2.5 py-0.5 rounded-full font-bold border ${badge.bg}`}>
                            {clause.risk_level} • Risk {clause.risk_score}
                          </span>
                        </div>

                        <p className="text-xs text-[#334155] font-mono bg-[#F7FAFD] p-3 rounded-lg border border-[#E2EEF8] leading-relaxed">
                          "{clause.clause_text}"
                        </p>

                        {/* Detected Hazards */}
                        {clause.risk_factors.length > 0 && (
                          <div className="flex flex-wrap gap-1.5 pt-1">
                            {clause.risk_factors.map((rf, idx) => (
                              <span key={idx} className="text-[10px] font-semibold px-2 py-0.5 rounded-md bg-red-50 text-red-700 border border-red-200">
                                ⚠ {rf}
                              </span>
                            ))}
                          </div>
                        )}

                        {/* Extracted Parameters */}
                        {(clause.parameters.durations?.length || clause.parameters.notice_periods?.length || clause.parameters.financial_terms?.length) ? (
                          <div className="flex flex-wrap gap-1.5 pt-1">
                            {clause.parameters.durations?.map((d, i) => (
                              <span key={i} className="text-[10px] font-semibold px-2 py-0.5 rounded-md bg-[#E2EEF8] text-[#1A3F75] border border-[#B8D3EB]">
                                ⏱ {d}
                              </span>
                            ))}
                            {clause.parameters.notice_periods?.map((n, i) => (
                              <span key={i} className="text-[10px] font-semibold px-2 py-0.5 rounded-md bg-[#EBF3FA] text-[#3B6998] border border-[#D0DFEC]">
                                📢 {n}
                              </span>
                            ))}
                            {clause.parameters.financial_terms?.map((f, i) => (
                              <span key={i} className="text-[10px] font-semibold px-2 py-0.5 rounded-md bg-emerald-50 text-emerald-800 border border-emerald-200">
                                💵 {f}
                              </span>
                            ))}
                          </div>
                        ) : null}
                      </div>
                    );
                  })}
                </div>
              )}

            </div>

          </div>
        )}

      </div>
    </div>
  );
}