"use client";

import { useState, useEffect } from "react";
import { useParams } from "next/navigation";
import { fetchNewsSummary, fetchStockAnalysis } from "@/lib/api";
import type { StockMention, StockAnalysis } from "@/types";
import LoadingSpinner from "@/components/ui/LoadingSpinner";
import ErrorMessage from "@/components/ui/ErrorMessage";
import AiSummary from "@/components/news/AiSummary";
import Link from "next/link";
import { ArrowLeft, Sparkles, Star, Search } from "lucide-react";
import { useRouter } from "next/navigation";

// StockAnalysisPanel removed as research is now done via navigation

// ── 관련 종목 선택 목록 ───────────────────────────────────────────
function RelatedStockList({
  stocks,
  onSelect,
  impactStrength,
}: {
  stocks: StockMention[];
  onSelect: (code: string) => void;
  impactStrength?: string;
}) {
  const impactLabel: Record<string, string> = {
    "매우 높음": "시장 파급력이 매우 높은 뉴스입니다. 아래 종목들을 주목하세요.",
    "높음": "시장 파급력이 높은 뉴스입니다. 관련 종목 흐름을 체크하세요.",
    "보통": "보통 수준의 시장 영향이 예상됩니다.",
    "낮음": "시장 영향은 제한적이나 관련 종목을 참고하세요.",
  };

  return (
    <div className="space-y-3">
      {/* AI의 한마디 */}
      <div className="bg-skyblue/10 border border-skyblue/30 rounded-xl px-4 py-3 flex items-start gap-3">
        <Sparkles className="w-4 h-4 text-skyblue mt-0.5 shrink-0" />
        <div>
          <p className="text-xs text-skyblue font-semibold mb-0.5">AI의 한마디</p>
          <p className="text-sm text-gray-200">
            {impactStrength
              ? impactLabel[impactStrength] ?? `파급력 ${impactStrength} — 관련 종목을 참고하세요.`
              : "AI가 이 뉴스에서 관련 종목을 분석했습니다. 종목을 클릭하면 종목분석 상세로 이동합니다."}
          </p>
          {impactStrength && (
            <span className="inline-block mt-1 text-[10px] px-2 py-0.5 rounded-full bg-skyblue/20 text-skyblue font-bold">
              파급력 {impactStrength}
            </span>
          )}
        </div>
      </div>

      {/* 종목 목록 */}
      {stocks.map((s, i) => {
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
                  {s.type && (
                    <span className={`text-[10px] px-2 py-0.5 rounded-full font-bold ${s.type === "direct"
                      ? "bg-amber-500/20 text-amber-400 border border-amber-500/30"
                      : "bg-skyblue/20 text-skyblue border border-skyblue/30"
                      }`}>
                      {s.type === "direct" ? "직접수혜주" : "낙수효과주"}
                    </span>
                  )}
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
type Tab = "news" | "stocks";

export default function NewsDetailPage() {
  const { id: rawId } = useParams<{ id: string }>();
  const id = decodeURIComponent(rawId);
  const router = useRouter();
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [tab, setTab] = useState<Tab>("news");

  const load = () => {
    setLoading(true);
    setError("");
    fetchNewsSummary(id)
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, [id]);

  const relatedStocks: StockMention[] = data?.related_stocks ?? [];
  const hasStocks = relatedStocks.length > 0;

  const handleSelectStock = (code: string) => {
    router.push(`/stock/${code}?tab=analysis`);
  };

  return (
    <div className="space-y-4 max-w-2xl mx-auto">
      <Link href="/issues" className="inline-flex items-center text-gray-400 hover:text-white text-sm transition-colors">
        <ArrowLeft className="w-4 h-4 mr-1" /> 목록으로
      </Link>

      {loading && <LoadingSpinner text="AI가 뉴스를 분석하고 있어요..." />}
      {error && <ErrorMessage message={error} onRetry={load} />}

      {data && (
        <>
          {/* 탭 헤더 */}
          {hasStocks && (
            <div className="flex gap-1 bg-white/5 p-1 rounded-xl">
              <button
                type="button"
                onClick={() => setTab("news")}
                className={`flex-1 py-2 rounded-lg text-sm font-medium transition-colors ${tab === "news" ? "bg-skyblue/20 text-skyblue" : "text-gray-400 hover:text-white"
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
          {tab === "news" && (
            <AiSummary
              title={data.title}
              aiSummary={data.ai_summary}
              url={data.url || data.link}
            />
          )}

          {/* 탭: 관련 종목 보기 */}
          {tab === "stocks" && (
            <div className="space-y-4">
              <RelatedStockList
                stocks={relatedStocks}
                onSelect={handleSelectStock}
                impactStrength={data.impact_strength}
              />
            </div>
          )}
        </>
      )}
    </div>
  );
}
