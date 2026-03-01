"use client";

import { useState } from "react";
import { searchStocks } from "@/lib/api";
import StockSearchBar from "@/components/stock/StockSearchBar";
import StockSearchResultCard from "@/components/stock/StockSearchResultCard";
import StockCompare from "@/components/stock/StockCompare";
import { Lightbulb } from "lucide-react";

type Tab = "search" | "compare";

export default function StockSearchPage() {
  const [tab, setTab] = useState<Tab>("search");

  // 종목검색 상태
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<Awaited<ReturnType<typeof searchStocks>>["results"]>([]);
  const [loading, setLoading] = useState(false);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;
    setLoading(true);
    try {
      const data = await searchStocks(query);
      setResults(data.results);
    } catch {
      setResults([]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <Lightbulb className="w-6 h-6 text-amber-400" />
          종목 콕
        </h1>
        <p className="text-gray-400 mt-1 text-sm">AI가 종목을 분석하고 쉽게 설명해줍니다 AI와 함께 투자의 확신을 더하세요.</p>
      </div>

      {/* 탭 헤더 */}
      <div className="flex gap-1 bg-white/5 p-1 rounded-xl">
        <button
          type="button"
          onClick={() => setTab("search")}
          className={`flex-1 py-2 rounded-lg text-sm font-medium transition-colors ${
            tab === "search" ? "bg-skyblue/20 text-skyblue" : "text-gray-400 hover:text-white"
          }`}
        >
          종목검색
        </button>
        <button
          type="button"
          onClick={() => setTab("compare")}
          className={`flex-1 py-2 rounded-lg text-sm font-medium transition-colors ${
            tab === "compare" ? "bg-skyblue/20 text-skyblue" : "text-gray-400 hover:text-white"
          }`}
        >
          종목비교
        </button>
      </div>

      {/* 탭: 종목검색 */}
      {tab === "search" && (
        <div className="space-y-4">
          <StockSearchBar
            query={query}
            onQueryChange={setQuery}
            onSubmit={handleSearch}
          />

          {loading && <p className="text-center text-gray-400 text-sm">검색 중...</p>}

          {results.length > 0 && (
            <div className="space-y-2">
              {results.map((s) => (
                <StockSearchResultCard key={s.code} stock={s} />
              ))}
            </div>
          )}

          {!loading && query && results.length === 0 && (
            <p className="text-center text-gray-400 text-sm">검색 결과가 없습니다.</p>
          )}
        </div>
      )}

      {/* 탭: 종목비교 */}
      {tab === "compare" && <StockCompare />}
    </div>
  );
}
