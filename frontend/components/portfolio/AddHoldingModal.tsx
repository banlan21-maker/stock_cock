"use client";

import { useState, useEffect } from "react";
import { X, Search } from "lucide-react";
import { searchStocks } from "@/lib/api";
import type { PortfolioHolding, PortfolioAddRequest, StockSearchResult, WatchlistItem } from "@/types";

interface Props {
  initial?: PortfolioHolding | null;
  onClose: () => void;
  onSubmit: (data: PortfolioAddRequest) => Promise<void>;
}

export default function AddHoldingModal({ initial, onClose, onSubmit }: Props) {
  const isEdit = !!initial;

  const [stockCode, setStockCode] = useState(initial?.stock_code ?? "");
  const [stockName, setStockName] = useState(initial?.stock_name ?? "");
  const [quantity, setQuantity] = useState(initial ? String(initial.quantity) : "");
  const [avgPrice, setAvgPrice] = useState(initial ? String(initial.avg_price) : "");
  const [boughtAt, setBoughtAt] = useState(initial?.bought_at ?? "");
  const [searchQuery, setSearchQuery] = useState(initial?.stock_name ?? "");
  const [searchResults, setSearchResults] = useState<StockSearchResult[]>([]);
  const [searching, setSearching] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [watchlist, setWatchlist] = useState<WatchlistItem[]>([]);

  // 관심종목 로드
  useEffect(() => {
    if (!isEdit) {
      import("@/lib/watchlist").then(({ getWatchlist }) => {
        getWatchlist().then(setWatchlist);
      });
    }
  }, [isEdit]);

  // 종목 검색 (편집 모드가 아닐 때만)
  useEffect(() => {
    if (isEdit || searchQuery.trim().length < 2) {
      setSearchResults([]);
      return;
    }
    const timer = setTimeout(async () => {
      setSearching(true);
      try {
        const { results } = await searchStocks(searchQuery);
        setSearchResults(results.slice(0, 6));
      } catch {
        setSearchResults([]);
      } finally {
        setSearching(false);
      }
    }, 400);
    return () => clearTimeout(timer);
  }, [searchQuery, isEdit]);

  function selectStock(stock: { code: string; name: string }) {
    setStockCode(stock.code);
    setStockName(stock.name);
    setSearchQuery(stock.name);
    setSearchResults([]);
  }

  // 예상 평가금액 미리보기
  const previewEval =
    quantity && avgPrice
      ? (Number(quantity) * Number(avgPrice)).toLocaleString("ko-KR")
      : null;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    if (!stockCode || !stockName) {
      setError("종목을 선택해 주세요.");
      return;
    }
    const qty = Number(quantity);
    const price = Number(avgPrice);
    if (!qty || qty <= 0 || !price || price <= 0) {
      setError("수량과 매입가를 올바르게 입력해 주세요.");
      return;
    }
    setSubmitting(true);
    try {
      await onSubmit({
        stock_code: stockCode,
        stock_name: stockName,
        quantity: qty,
        avg_price: price,
        bought_at: boughtAt || undefined,
      });
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "오류가 발생했습니다.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <div className="bg-[#1a1a2e] border border-white/10 rounded-2xl w-full max-w-md shadow-2xl">
        <div className="flex items-center justify-between px-5 py-4 border-b border-white/10">
          <h2 className="font-semibold">{isEdit ? "종목 수정" : "종목 추가"}</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-white">
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-5 space-y-4">
          {/* 종목 검색 */}
          {!isEdit ? (
            <div className="space-y-3">
              {/* 관심종목 선택 */}
              {watchlist.length > 0 && (
                <div>
                  <label className="block text-xs text-gray-400 mb-1">관심종목에서 선택</label>
                  <select
                    className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:border-skyblue/50 text-gray-300"
                    onChange={(e) => {
                      const code = e.target.value;
                      if (!code) return;
                      const item = watchlist.find(w => w.stock_code === code);
                      if (item) selectStock({ code: item.stock_code, name: item.stock_name });
                    }}
                    value=""
                  >
                    <option value="">관심종목을 선택하세요...</option>
                    {watchlist.map(w => (
                      <option key={w.id} value={w.stock_code}>
                        {w.stock_name} ({w.stock_code})
                      </option>
                    ))}
                  </select>
                </div>
              )}

              <div className="relative">
                <label className="block text-xs text-gray-400 mb-1">직접 검색</label>
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
                  <input
                    type="text"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder="종목명 또는 코드"
                    className="w-full bg-white/5 border border-white/10 rounded-lg pl-9 pr-3 py-2.5 text-sm focus:outline-none focus:border-skyblue/50"
                  />
                </div>
                {(searching || searchResults.length > 0) && (
                  <div className="absolute z-10 w-full mt-1 bg-[#1a1a2e] border border-white/10 rounded-lg shadow-xl overflow-hidden">
                    {searching ? (
                      <p className="text-xs text-gray-400 p-3">검색 중...</p>
                    ) : (
                      searchResults.map((s) => (
                        <button
                          key={s.code}
                          type="button"
                          onClick={() => selectStock(s)}
                          className="w-full text-left px-3 py-2.5 hover:bg-white/5 transition-colors flex items-center justify-between"
                        >
                          <span className="text-sm">{s.name}</span>
                          <span className="text-xs text-gray-500">{s.code}</span>
                        </button>
                      ))
                    )}
                  </div>
                )}
                {stockCode && (
                  <p className="text-xs text-skyblue mt-1">선택됨: {stockName} ({stockCode})</p>
                )}
              </div>
            </div>
          ) : (
            <div>
              <label className="block text-xs text-gray-400 mb-1">종목</label>
              <p className="text-sm font-medium">{stockName} ({stockCode})</p>
            </div>
          )}

          {/* 수량 */}
          <div>
            <label className="block text-xs text-gray-400 mb-1">수량 (주)</label>
            <input
              type="number"
              value={quantity}
              onChange={(e) => setQuantity(e.target.value)}
              placeholder="0"
              min="1"
              className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:border-skyblue/50"
              required
            />
          </div>

          {/* 평균 매입가 */}
          <div>
            <label className="block text-xs text-gray-400 mb-1">평균 매입가 (원)</label>
            <input
              type="number"
              value={avgPrice}
              onChange={(e) => setAvgPrice(e.target.value)}
              placeholder="0"
              min="1"
              className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:border-skyblue/50"
              required
            />
          </div>

          {/* 매입일 */}
          <div>
            <label className="block text-xs text-gray-400 mb-1">매입일 (선택)</label>
            <input
              type="date"
              value={boughtAt}
              onChange={(e) => setBoughtAt(e.target.value)}
              className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:border-skyblue/50"
            />
          </div>

          {/* 예상 평가금액 미리보기 */}
          {previewEval && (
            <div className="bg-white/3 rounded-lg px-3 py-2 text-sm text-gray-400">
              예상 평가금액 <span className="text-white font-medium">₩{previewEval}</span>
            </div>
          )}

          {error && <p className="text-red-400 text-xs">{error}</p>}

          <div className="flex gap-2 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 py-2.5 rounded-lg bg-white/5 hover:bg-white/10 text-sm transition-colors"
            >
              취소
            </button>
            <button
              type="submit"
              disabled={submitting}
              className="flex-1 py-2.5 rounded-lg bg-skyblue text-black font-semibold text-sm hover:bg-skyblue/90 transition-colors disabled:opacity-50"
            >
              {submitting ? "저장 중..." : isEdit ? "수정" : "추가"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
