"use client";

import { useState, useEffect } from "react";
import { useParams } from "next/navigation";
import { fetchPolicyAnalysis, fetchStockAnalysis } from "@/lib/api";
import type { PolicyInfo, StockRecommendation, StockAnalysis } from "@/types";
import LoadingSpinner from "@/components/ui/LoadingSpinner";
import ErrorMessage from "@/components/ui/ErrorMessage";
import PolicyAnalysis from "@/components/policy/PolicyAnalysis";
import Link from "next/link";
import { ArrowLeft, Search } from "lucide-react";
import { useRouter } from "next/navigation";

// StockAnalysisPanel removed as research is now done via navigation

// ── 관련 종목 목록 ────────────────────────────────────────────────
function RelatedStockList({
  stocks,
  onSelect,
}: {
  stocks: StockRecommendation[];
  onSelect: (code: string) => void;
}) {
  const tagStyle = (impact: string) => {
    if (impact === "positive") return { cls: "bg-amber-500/20 text-amber-400 border border-amber-500/30", label: "직접수혜주" };
    if (impact === "negative") return { cls: "bg-red-500/20 text-red-400 border border-red-500/30", label: "피해주" };
    return { cls: "bg-skyblue/20 text-skyblue border border-skyblue/30", label: "관련주" };
  };

  return (
    <div className="space-y-3">
      {/* 종목 목록 */}
      {stocks.map((s, i) => {
        const tag = tagStyle(s.impact);
        return (
          <button
            key={i}
            type="button"
            onClick={() => onSelect(s.stock_code)}
            className="w-full text-left rounded-xl p-4 border bg-white/5 border-white/10 hover:bg-white/10 transition-colors"
          >
            <div className="flex justify-between items-center gap-3">
              <div className="flex-1">
                <div className="flex items-center gap-2 flex-wrap">
                  <p className="font-medium">{s.stock_name}</p>
                  <span className={`text-[10px] px-2 py-0.5 rounded-full font-bold ${tag.cls}`}>
                    {tag.label}
                  </span>
                </div>
                <div className="flex items-center gap-1.5 mt-0.5">
                  <p className="text-xs text-gray-400">{s.stock_code}</p>
                  <span className="text-gray-600">·</span>
                  <div className="flex items-center gap-0.5 text-skyblue">
                    <Search className="w-3 h-3" />
                    <span className="text-[10px] font-bold">종목분석</span>
                  </div>
                </div>
              </div>
              <p className="text-sm text-gray-300 text-right max-w-[50%] shrink-0">{s.reason}</p>
            </div>
          </button>
        );
      })}
    </div>
  );
}

// ── 메인 페이지 ───────────────────────────────────────────────────
type Tab = "analysis" | "stocks";

export default function PolicyDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [data, setData] = useState<PolicyInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [tab, setTab] = useState<Tab>("analysis");

  const load = () => {
    setLoading(true);
    setError("");
    fetchPolicyAnalysis(id)
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, [id]);

  const relatedStocks = data?.beneficiary_stocks ?? [];
  const hasStocks = relatedStocks.length > 0;

  const handleSelectStock = (code: string) => {
    router.push(`/stock/${code}?tab=analysis`);
  };

  return (
    <div className="space-y-4 max-w-2xl mx-auto">
      <Link href="/policy" className="inline-flex items-center text-gray-400 hover:text-white text-sm transition-colors">
        <ArrowLeft className="w-4 h-4 mr-1" /> 목록으로
      </Link>

      {loading && <LoadingSpinner text="AI가 정책을 분석하고 있어요..." />}
      {error && <ErrorMessage message={error} onRetry={load} />}

      {data && (
        <>
          {/* 탭 헤더 */}
          {hasStocks && (
            <div className="flex gap-1 bg-white/5 p-1 rounded-xl">
              <button
                type="button"
                onClick={() => setTab("analysis")}
                className={`flex-1 py-2 rounded-lg text-sm font-medium transition-colors ${tab === "analysis" ? "bg-skyblue/20 text-skyblue" : "text-gray-400 hover:text-white"
                  }`}
              >
                AI 분석
              </button>
              <button
                type="button"
                onClick={() => setTab("stocks")}
                className={`flex-1 py-2 rounded-lg text-sm font-medium transition-colors ${tab === "stocks" ? "bg-skyblue/20 text-skyblue" : "text-gray-400 hover:text-white"
                  }`}
              >
                관련 종목 보기 ({relatedStocks.length})
              </button>
            </div>
          )}

          {/* 탭: AI 분석 */}
          {tab === "analysis" && <PolicyAnalysis policy={data} />}

          {/* 탭: 관련 종목 보기 */}
          {tab === "stocks" && (
            <div className="space-y-4">
              <RelatedStockList
                stocks={relatedStocks}
                onSelect={handleSelectStock}
              />
            </div>
          )}
        </>
      )}
    </div>
  );
}
