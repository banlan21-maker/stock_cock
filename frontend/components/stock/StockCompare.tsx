"use client";

import { useState } from "react";
import { Search, ArrowLeftRight, Trophy, Star, AlertTriangle, Loader2, PlayCircle } from "lucide-react";
import { searchStocks, fetchStockCompare } from "@/lib/api";
import { useReward } from "@/context/RewardProvider";
import AiDisclaimer from "@/components/ui/AiDisclaimer";
import type { StockSearchResult, StockCompareResult } from "@/types";

// ── 종목 선택 입력창 ─────────────────────────────────────────────
function StockPicker({
  label,
  selected,
  onSelect,
}: {
  label: string;
  selected: StockSearchResult | null;
  onSelect: (s: StockSearchResult) => void;
}) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<StockSearchResult[]>([]);
  const [searching, setSearching] = useState(false);
  const [open, setOpen] = useState(false);

  const handleInput = async (val: string) => {
    setQuery(val);
    if (!val.trim()) { setResults([]); setOpen(false); return; }
    setSearching(true);
    try {
      const data = await searchStocks(val);
      setResults(data.results.slice(0, 6));
      setOpen(true);
    } catch {
      setResults([]);
    } finally {
      setSearching(false);
    }
  };

  const choose = (s: StockSearchResult) => {
    onSelect(s);
    setQuery(s.name);
    setResults([]);
    setOpen(false);
  };

  return (
    <div className="flex-1 relative">
      <p className="text-xs text-gray-400 mb-1 font-semibold">{label}</p>
      <div className="relative">
        <Search className="absolute left-3 top-3 w-4 h-4 text-gray-400" />
        <input
          type="text"
          value={selected && query === selected.name ? `${selected.name} (${selected.code})` : query}
          onChange={(e) => {
            if (selected && e.target.value !== `${selected.name} (${selected.code})`) {
              // 수정 시작 → 선택 초기화
              setQuery(e.target.value);
              onSelect(null as any);
              handleInput(e.target.value);
            } else {
              handleInput(e.target.value);
            }
          }}
          onFocus={() => { if (results.length > 0) setOpen(true); }}
          placeholder="종목명 또는 코드 (예: 삼성전자)"
          className="w-full pl-9 pr-3 py-2.5 bg-white/5 border border-white/10 rounded-xl focus:outline-none focus:ring-2 focus:ring-skyblue text-white placeholder-gray-500 text-sm"
        />
        {searching && <Loader2 className="absolute right-3 top-3 w-4 h-4 text-gray-400 animate-spin" />}
      </div>
      {open && results.length > 0 && (
        <div className="absolute z-20 mt-1 w-full bg-[#1a1f2e] border border-white/10 rounded-xl overflow-hidden shadow-xl">
          {results.map((s) => (
            <button
              key={s.code}
              type="button"
              onClick={() => choose(s)}
              className="w-full text-left px-4 py-2.5 hover:bg-white/10 transition-colors flex justify-between items-center"
            >
              <span className="text-sm font-medium">{s.name}</span>
              <span className="text-xs text-gray-400">{s.code}</span>
            </button>
          ))}
        </div>
      )}
      {selected && (
        <div className="mt-2 px-3 py-1.5 bg-skyblue/10 border border-skyblue/30 rounded-lg flex justify-between items-center">
          <span className="text-sm font-bold text-skyblue">{selected.name}</span>
          <span className="text-xs text-gray-400">{selected.code}</span>
        </div>
      )}
    </div>
  );
}

// ── 비교 결과 렌더링 ─────────────────────────────────────────────
function CompareResult({ result }: { result: StockCompareResult }) {
  const { stock_a, stock_b, items, overall_winner, a_score, b_score, verdict, caution } = result;

  const winnerName =
    overall_winner === "A" ? stock_a.name :
    overall_winner === "B" ? stock_b.name : null;

  const winnerColor = (side: "A" | "B" | "같음" | "동점") => {
    if (side === "A") return "text-amber-400";
    if (side === "B") return "text-skyblue";
    return "text-gray-400";
  };

  const scoreDots = (score: number, color: string) =>
    [1, 2, 3, 4, 5].map((n) => (
      <Star
        key={n}
        className={`w-4 h-4 ${n <= score ? `${color} fill-current` : "text-gray-600"}`}
      />
    ));

  return (
    <div className="space-y-4">
      {/* 최종 결론 */}
      <div className={`rounded-xl p-5 border ${
        overall_winner === "동점"
          ? "bg-white/5 border-white/10"
          : "bg-skyblue/10 border-skyblue/30"
      }`}>
        <div className="flex items-center gap-2 mb-3">
          <Trophy className={`w-5 h-5 ${overall_winner === "동점" ? "text-gray-400" : "text-amber-400"}`} />
          <h3 className="font-bold text-white">
            {winnerName ? `${winnerName}이(가) 더 유리해요!` : "두 종목이 비슷해요"}
          </h3>
        </div>

        {/* 점수 비교 */}
        <div className="grid grid-cols-2 gap-3 mb-4">
          <div className={`rounded-lg p-3 text-center ${overall_winner === "A" ? "bg-amber-500/10 border border-amber-500/30" : "bg-white/5 border border-white/10"}`}>
            <p className="text-xs text-gray-400 mb-1">{stock_a.name}</p>
            <div className="flex justify-center gap-0.5">{scoreDots(a_score, "text-amber-400")}</div>
            <p className="text-lg font-bold mt-1 text-amber-400">{a_score}점</p>
          </div>
          <div className={`rounded-lg p-3 text-center ${overall_winner === "B" ? "bg-skyblue/10 border border-skyblue/30" : "bg-white/5 border border-white/10"}`}>
            <p className="text-xs text-gray-400 mb-1">{stock_b.name}</p>
            <div className="flex justify-center gap-0.5">{scoreDots(b_score, "text-skyblue")}</div>
            <p className="text-lg font-bold mt-1 text-skyblue">{b_score}점</p>
          </div>
        </div>

        <p className="text-sm text-gray-200 leading-relaxed">{verdict}</p>
      </div>

      {/* 주의사항 */}
      {caution && (
        <div className="flex items-start gap-3 bg-amber-500/10 border border-amber-500/20 rounded-xl px-4 py-3">
          <AlertTriangle className="w-4 h-4 text-amber-400 mt-0.5 shrink-0" />
          <p className="text-sm text-amber-200">{caution}</p>
        </div>
      )}

      {/* 항목별 비교 */}
      <div className="space-y-2">
        <p className="text-xs text-gray-400 font-semibold px-1">항목별 비교</p>
        {/* 헤더 */}
        <div className="grid grid-cols-[1fr_60px_1fr] gap-2 px-3 py-1.5 text-[10px] text-gray-500 font-semibold">
          <span className="text-amber-400 truncate">{stock_a.name}</span>
          <span className="text-center">항목</span>
          <span className="text-skyblue text-right truncate">{stock_b.name}</span>
        </div>

        {items.map((item, i) => (
          <div
            key={i}
            className="bg-white/5 border border-white/10 rounded-xl p-3 grid grid-cols-[1fr_60px_1fr] gap-2 items-start"
          >
            {/* A 결과 */}
            <div className={`text-sm ${item.winner === "A" ? "font-bold text-amber-400" : "text-gray-300"}`}>
              {item.a_result}
            </div>

            {/* 항목명 + 승자 */}
            <div className="text-center">
              <p className="text-[10px] text-gray-500 mb-1">{item.label}</p>
              <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded-full ${
                item.winner === "A"
                  ? "bg-amber-500/20 text-amber-400"
                  : item.winner === "B"
                    ? "bg-skyblue/20 text-skyblue"
                    : "bg-white/10 text-gray-400"
              }`}>
                {item.winner === "A" ? "A승" : item.winner === "B" ? "B승" : "동점"}
              </span>
            </div>

            {/* B 결과 */}
            <div className={`text-sm text-right ${item.winner === "B" ? "font-bold text-skyblue" : "text-gray-300"}`}>
              {item.b_result}
            </div>
          </div>
        ))}
      </div>

      {/* 근거 상세 */}
      <div className="space-y-2">
        <p className="text-xs text-gray-400 font-semibold px-1">AI 분석 근거</p>
        {items.map((item, i) => (
          <div key={i} className="bg-white/5 border border-white/10 rounded-xl px-4 py-3 flex gap-3">
            <span className={`text-xs font-bold shrink-0 mt-0.5 ${winnerColor(item.winner)}`}>{item.label}</span>
            <p className="text-sm text-gray-300">{item.reason}</p>
          </div>
        ))}
      </div>
      <AiDisclaimer />
    </div>
  );
}

// ── 메인 컴포넌트 ────────────────────────────────────────────────
export default function StockCompare() {
  const [stockA, setStockA] = useState<StockSearchResult | null>(null);
  const [stockB, setStockB] = useState<StockSearchResult | null>(null);
  const [result, setResult] = useState<StockCompareResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const { requestReward } = useReward();

  const handleCompare = () => {
    if (!stockA || !stockB) {
      setError("두 종목을 모두 선택해주세요.");
      return;
    }
    if (stockA.code === stockB.code) {
      setError("서로 다른 종목을 선택해주세요.");
      return;
    }
    setError("");
    setResult(null);

    requestReward(async () => {
      setLoading(true);
      try {
        const data = await fetchStockCompare(stockA.code, stockB.code);
        setResult(data);
      } catch (e: any) {
        setError(e?.message || "비교 분석 중 오류가 발생했습니다.");
      } finally {
        setLoading(false);
      }
    });
  };

  return (
    <div className="space-y-5">
      {/* 종목 선택 */}
      <div className="bg-white/5 border border-white/10 rounded-xl p-4 space-y-4">
        <div className="flex gap-3 items-end">
          <StockPicker label="A 종목" selected={stockA} onSelect={setStockA} />
          <div className="pb-2">
            <ArrowLeftRight className="w-5 h-5 text-gray-500" />
          </div>
          <StockPicker label="B 종목" selected={stockB} onSelect={setStockB} />
        </div>

        <button
          type="button"
          onClick={handleCompare}
          disabled={!stockA || !stockB || loading}
          className="w-full py-3 rounded-xl bg-skyblue text-white font-bold text-sm hover:bg-skyblue/80 transition-colors disabled:opacity-40 disabled:cursor-not-allowed flex items-center justify-center gap-2"
        >
          {loading ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              AI가 비교 분석 중... (30초~1분 소요)
            </>
          ) : (
            <>
              <PlayCircle className="w-4 h-4" />
              광고 보고 투자가치 비교하기
            </>
          )}
        </button>

        {!loading && (
          <p className="text-center text-xs text-gray-500">
            짧은 광고 시청 후 AI 비교 분석 결과를 무료로 확인하세요
          </p>
        )}
      </div>

      {error && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-4 text-sm text-red-300">
          {error}
        </div>
      )}

      {result && <CompareResult result={result} />}
    </div>
  );
}
