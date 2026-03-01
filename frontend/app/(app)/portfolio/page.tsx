"use client";

import { useState, useEffect, useCallback, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { Plus, Brain, Star, Briefcase, Search, BookOpen, PieChart } from "lucide-react";
import Link from "next/link";
import { fetchPortfolioWithPrice, addHolding, updateHolding, deleteHolding } from "@/lib/portfolio";
import { getWatchlist, removeWatchlist } from "@/lib/watchlist";
import { fetchStockPrice } from "@/lib/api";
import type { PortfolioHolding, PortfolioSummary, PortfolioAddRequest, WatchlistItem, StockPrice } from "@/types";
import PortfolioSummaryCard from "@/components/portfolio/PortfolioSummaryCard";
import HoldingsTable from "@/components/portfolio/HoldingsTable";
import PortfolioPieChart from "@/components/portfolio/PortfolioPieChart";
import PortfolioReturnChart from "@/components/portfolio/PortfolioReturnChart";
import AddHoldingModal from "@/components/portfolio/AddHoldingModal";
import JournalTab from "@/components/portfolio/JournalTab";
import LoadingSpinner from "@/components/ui/LoadingSpinner";

type Tab = "holdings" | "watchlist" | "journal";

// ── 관심종목 탭 ───────────────────────────────────────────────────────────────

function WatchlistTab() {
  const [watchlist, setWatchlist] = useState<WatchlistItem[]>([]);
  const [prices, setPrices] = useState<Record<string, StockPrice>>({});
  const [loading, setLoading] = useState(true);
  const [priceLoading, setPriceLoading] = useState(false);

  const loadPrices = useCallback(async (items: WatchlistItem[]) => {
    if (items.length === 0) return;
    setPriceLoading(true);
    const results = await Promise.allSettled(
      items.map((w) => fetchStockPrice(w.stock_code))
    );
    const map: Record<string, StockPrice> = {};
    results.forEach((r, i) => {
      if (r.status === "fulfilled" && r.value) {
        map[items[i].stock_code] = r.value;
      }
    });
    setPrices(map);
    setPriceLoading(false);
  }, []);

  const load = useCallback(async () => {
    setLoading(true);
    const data = await getWatchlist();
    setWatchlist(data);
    setLoading(false);
    loadPrices(data);
  }, [loadPrices]);

  useEffect(() => { load(); }, [load]);

  async function handleRemove(code: string, name: string) {
    if (!confirm(`${name}을(를) 관심종목에서 제거할까요?`)) return;
    await removeWatchlist(code);
    await load();
  }

  if (loading) return <LoadingSpinner text="관심종목 불러오는 중..." />;

  if (watchlist.length === 0) {
    return (
      <div className="bg-white/5 border border-white/10 rounded-xl p-12 text-center text-gray-400">
        <Star className="w-8 h-8 text-amber-400 mx-auto mb-3 opacity-50" />
        <p className="text-lg mb-2">관심종목이 없어요.</p>
        <p className="text-sm mb-6">종목 상세 페이지에서 별 아이콘을 눌러 추가해 보세요.</p>
        <Link
          href="/stock"
          className="inline-flex items-center gap-2 px-5 py-2.5 bg-skyblue/20 text-skyblue rounded-lg text-sm hover:bg-skyblue/30 transition-colors"
        >
          <Search className="w-4 h-4" />
          종목 검색하러 가기
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {/* 상단: 종목 수 + 새로고침 */}
      <div className="flex items-center justify-between px-1 pb-1">
        <p className="text-sm text-gray-400">총 {watchlist.length}개 종목</p>
        <button
          onClick={load}
          disabled={priceLoading}
          className="text-xs text-skyblue hover:text-skyblue/70 transition-colors disabled:opacity-40"
        >
          {priceLoading ? "시세 불러오는 중..." : "시세 새로고침"}
        </button>
      </div>

      {watchlist.map((w) => {
        const p = prices[w.stock_code];
        const rate = p?.change_rate ?? null;
        const isBig = rate !== null && Math.abs(rate) >= 5;
        const isUp = rate !== null && rate > 0;
        const isDown = rate !== null && rate < 0;

        return (
          <div
            key={w.id}
            className={`bg-white/5 border rounded-xl p-4 flex items-center justify-between group transition-colors hover:bg-white/8 ${
              isBig && isUp
                ? "border-red-500/30"
                : isBig && isDown
                  ? "border-blue-500/30"
                  : "border-white/10"
            }`}
          >
            {/* 왼쪽: 종목명·코드·배지 */}
            <Link href={`/stock/${w.stock_code}`} className="flex-1 min-w-0">
              <div className="flex items-center gap-2 flex-wrap">
                <p className="font-medium truncate">{w.stock_name}</p>
                {isBig && (
                  <span
                    className={`text-[10px] px-2 py-0.5 rounded-full font-bold ${
                      isUp
                        ? "bg-red-500/20 text-red-400 border border-red-500/30"
                        : "bg-blue-500/20 text-blue-400 border border-blue-500/30"
                    }`}
                  >
                    {isUp ? "급등" : "급락"}
                  </span>
                )}
              </div>
              <p className="text-xs text-gray-400 mt-0.5">{w.stock_code}</p>
            </Link>

            {/* 오른쪽: 현재가·등락률·제거 */}
            <div className="flex items-center gap-3 ml-3 shrink-0">
              {p ? (
                <div className="text-right">
                  <p className="text-sm font-bold">
                    {p.current_price.toLocaleString()}원
                  </p>
                  <p
                    className={`text-xs font-medium ${
                      isUp ? "text-red-400" : isDown ? "text-blue-400" : "text-gray-400"
                    }`}
                  >
                    {isUp ? "▲" : isDown ? "▼" : ""}
                    {rate !== null ? `${Math.abs(rate).toFixed(2)}%` : "-"}
                  </p>
                </div>
              ) : (
                <div className="text-right">
                  <p className="text-sm text-gray-600">-</p>
                  <p className="text-xs text-gray-600">-</p>
                </div>
              )}

              <button
                onClick={() => handleRemove(w.stock_code, w.stock_name)}
                className="opacity-0 group-hover:opacity-100 transition-opacity text-gray-500 hover:text-red-400"
                title="관심종목 제거"
              >
                <Star className="w-4 h-4 fill-amber-400 text-amber-400 hover:fill-none hover:text-gray-500 transition-all" />
              </button>
            </div>
          </div>
        );
      })}
    </div>
  );
}

// ── 보유종목 탭 ───────────────────────────────────────────────────────────────

function HoldingsTab() {
  const [holdings, setHoldings] = useState<PortfolioHolding[]>([]);
  const [summary, setSummary] = useState<PortfolioSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showModal, setShowModal] = useState(false);
  const [editTarget, setEditTarget] = useState<PortfolioHolding | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchPortfolioWithPrice();
      setHoldings(data.holdings);
      setSummary(data.summary);
    } catch (err) {
      setError(err instanceof Error ? err.message : "불러오기 실패");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  async function handleAdd(data: PortfolioAddRequest) {
    const result = await addHolding(data);
    if (!result.ok) throw new Error(result.error);
    await load();
  }

  async function handleUpdate(data: PortfolioAddRequest) {
    if (!editTarget) return;
    const result = await updateHolding(editTarget.id, data);
    if (!result.ok) throw new Error(result.error);
    await load();
  }

  async function handleDelete(id: string, name: string) {
    if (!confirm(`${name}을(를) 포트폴리오에서 제거할까요?`)) return;
    const result = await deleteHolding(id);
    if (!result.ok) throw new Error(result.error);
    await load();
  }

  if (loading) return <LoadingSpinner text="보유종목 불러오는 중..." />;

  return (
    <div className="space-y-4">
      {/* 추가 버튼 + AI 진단 */}
      <div className="flex justify-end gap-2">
        {holdings.length > 0 && (
          <Link
            href="/portfolio/analysis"
            className="flex items-center gap-1.5 px-4 py-2 bg-purple-500/20 text-purple-300 border border-purple-500/30 rounded-lg text-sm hover:bg-purple-500/30 transition-colors"
          >
            <Brain className="w-4 h-4" />
            AI 진단
          </Link>
        )}
        <button
          onClick={() => { setEditTarget(null); setShowModal(true); }}
          className="flex items-center gap-1.5 px-4 py-2 bg-skyblue text-black font-semibold rounded-lg text-sm hover:bg-skyblue/90 transition-colors"
        >
          <Plus className="w-4 h-4" />
          종목 추가
        </button>
      </div>

      {error && (
        <div className="bg-red-400/10 border border-red-400/20 rounded-xl p-4 text-red-400 text-sm">
          {error}
        </div>
      )}

      {summary && holdings.length > 0 && (
        <PortfolioSummaryCard summary={summary} />
      )}

      {holdings.length > 0 ? (
        <>
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            <div className="lg:col-span-2">
              <HoldingsTable
                holdings={holdings}
                totalEval={summary?.total_eval ?? 0}
                onEdit={(h) => { setEditTarget(h); setShowModal(true); }}
                onDelete={handleDelete}
              />
            </div>
            <div>
              <PortfolioPieChart holdings={holdings} />
            </div>
          </div>
          <PortfolioReturnChart />
        </>
      ) : (
        <div className="bg-white/5 border border-white/10 rounded-xl p-12 text-center text-gray-400">
          <Briefcase className="w-8 h-8 mx-auto mb-3 opacity-30" />
          <p className="text-lg mb-2">보유 종목이 없어요.</p>
          <p className="text-sm mb-6">종목 추가 버튼으로 포트폴리오를 시작해 보세요.</p>
          <button
            onClick={() => { setEditTarget(null); setShowModal(true); }}
            className="inline-flex items-center gap-2 px-5 py-2.5 bg-skyblue text-black font-semibold rounded-lg text-sm"
          >
            <Plus className="w-4 h-4" />
            첫 종목 추가하기
          </button>
        </div>
      )}

      {showModal && (
        <AddHoldingModal
          initial={editTarget}
          onClose={() => { setShowModal(false); setEditTarget(null); }}
          onSubmit={editTarget ? handleUpdate : handleAdd}
        />
      )}
    </div>
  );
}

// ── 메인 페이지 ───────────────────────────────────────────────────────────────

function PortfolioPageInner() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const tabParam = searchParams.get("tab");
  const activeTab: Tab =
    tabParam === "watchlist" ? "watchlist" :
    tabParam === "journal" ? "journal" :
    "holdings";

  function setTab(tab: Tab) {
    const params = new URLSearchParams(searchParams.toString());
    if (tab === "holdings") {
      params.delete("tab");
    } else {
      params.set("tab", tab);
    }
    router.replace(`/portfolio${params.size > 0 ? `?${params}` : ""}`);
  }

  const tabs: { id: Tab; label: string; icon: React.ReactNode }[] = [
    {
      id: "holdings",
      label: "보유종목",
      icon: <Briefcase className="w-4 h-4" />,
    },
    {
      id: "watchlist",
      label: "관심종목",
      icon: <Star className="w-4 h-4" />,
    },
    {
      id: "journal",
      label: "투자일지",
      icon: <BookOpen className="w-4 h-4" />,
    },
  ];

  return (
    <div className="space-y-6">
      {/* 헤더 */}
      <div>
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <PieChart className="w-6 h-6 text-amber-400" />
          내 포트폴리오
        </h1>
        <p className="text-gray-400 mt-1 text-sm">AI 매매일지 피드백과 종목 진단으로 더 단단한 투자 포트폴리오를 완성하세요.</p>
      </div>

      {/* 탭 */}
      <div className="flex gap-1 bg-white/5 rounded-xl p-1 w-fit">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setTab(tab.id)}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              activeTab === tab.id
                ? "bg-white/10 text-white"
                : "text-gray-400 hover:text-white"
            }`}
          >
            {tab.icon}
            {tab.label}
          </button>
        ))}
      </div>

      {/* 탭 콘텐츠 */}
      {activeTab === "holdings" && <HoldingsTab />}
      {activeTab === "watchlist" && <WatchlistTab />}
      {activeTab === "journal" && <JournalTab />}
    </div>
  );
}

export default function PortfolioPage() {
  return (
    <Suspense fallback={<LoadingSpinner text="불러오는 중..." />}>
      <PortfolioPageInner />
    </Suspense>
  );
}
