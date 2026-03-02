"use client";

import { useState, useEffect, useRef } from "react";
import { useParams, useSearchParams, useRouter } from "next/navigation";
import {
  fetchStockPrice,
  fetchStockChart,
  fetchStockAnalysis,
  fetchStockAnalysisStream,
  fetchStockDisclosures,
  fetchDisclosureAnalysis,
} from "@/lib/api";
import { useReward } from "@/context/RewardProvider";
import { addWatchlist, removeWatchlist, isInWatchlist } from "@/lib/watchlist";
import { createClient } from "@/utils/supabase/client";
import type { StockPrice, ChartResponse, StockAnalysis, DisclosureItem, DisclosureAnalysis } from "@/types";
import LoadingSpinner from "@/components/ui/LoadingSpinner";
import ErrorMessage from "@/components/ui/ErrorMessage";
import StockChart from "@/components/stock/StockChart";
import StockInfo from "@/components/stock/StockInfo";
import Link from "next/link";
import {
  ArrowLeft,
  Sparkles,
  Star,
  CheckCircle,
  Circle,
  Loader2,
  FileText,
  ChevronDown,
  ChevronUp,
  ExternalLink,
} from "lucide-react";

const supabase = createClient();

type Tab = "chart" | "analysis" | "disclosure";

// ── AI 분석 진행 단계 ───────────────────────────────────────────
const STEPS = [
  { step: 1, label: "주가 데이터 수집" },
  { step: 2, label: "뉴스 분석" },
  { step: 3, label: "AI 분석" },
];

function StepProgress({ currentStep }: { currentStep: number }) {
  return (
    <div className="space-y-4 py-4">
      <p className="text-gray-400 text-sm text-center">쉬운 말로 정리하고 있어요...</p>
      <div className="space-y-3">
        {STEPS.map(({ step, label }) => {
          const isDone = step < currentStep;
          const isActive = step === currentStep;
          return (
            <div key={step} className="flex items-center gap-3">
              {isDone ? (
                <CheckCircle className="w-5 h-5 text-green-400 flex-shrink-0" />
              ) : isActive ? (
                <Loader2 className="w-5 h-5 text-skyblue flex-shrink-0 animate-spin" />
              ) : (
                <Circle className="w-5 h-5 text-gray-600 flex-shrink-0" />
              )}
              <span
                className={`text-sm ${isDone ? "text-green-400" : isActive ? "text-white font-medium" : "text-gray-600"
                  }`}
              >
                {label}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

const sentimentColors: Record<string, string> = {
  bullish: "bg-green-500/20 text-green-300 border-green-500/30",
  bearish: "bg-red-500/20 text-red-300 border-red-500/30",
  neutral: "bg-gray-500/20 text-gray-300 border-gray-500/30",
};
const sentimentLabels: Record<string, string> = {
  bullish: "긍정적",
  bearish: "부정적",
  neutral: "중립",
};

// ── AI 분석 탭 콘텐츠 ──────────────────────────────────────────
function AnalysisTab({ code }: { code: string }) {
  const [analysis, setAnalysis] = useState<StockAnalysis | null>(null);
  const [loading, setLoading] = useState(true);
  const [currentStep, setCurrentStep] = useState(0);
  const [error, setError] = useState("");
  const abortRef = useRef<AbortController | null>(null);

  const { requestReward } = useReward();
  const [hasStarted, setHasStarted] = useState(false);

  async function runStream() {
    setLoading(true);
    setError("");
    setCurrentStep(0);
    setAnalysis(null);

    abortRef.current = new AbortController();

    try {
      for await (const event of fetchStockAnalysisStream(code, abortRef.current.signal)) {
        if (event.type === "status") {
          setCurrentStep(event.step);
        } else if (event.type === "done") {
          setAnalysis(event.data);
          setLoading(false);
          return;
        } else if (event.type === "error") {
          const msg = event.message ?? "분석 중 오류가 발생했습니다.";
          setError(
            msg.includes("429") || msg.includes("요청이 많") || event.code === "RATE_LIMITED"
              ? "AI 분석 요청이 많습니다. 30초 후 다시 시도해 주세요."
              : msg
          );
          setLoading(false);
          return;
        }
      }
      setLoading(false);
    } catch (e: unknown) {
      if ((e as Error)?.name === "AbortError") return;
      try {
        const data = await fetchStockAnalysis(code);
        setAnalysis(data);
      } catch (fallbackErr: unknown) {
        const msg = (fallbackErr as Error)?.message || "분석 중 오류가 발생했습니다.";
        setError(
          msg.includes("시간이 초과")
            ? "AI 분석에 시간이 걸리고 있습니다. 다시 시도해 주세요."
            : msg.includes("429") || msg.includes("요청이 많")
              ? "AI 분석 요청이 많습니다. 30초 후 다시 시도해 주세요."
              : msg
        );
      }
      setLoading(false);
    }
  }

  const handleStartAnalysis = () => {
    requestReward(() => {
      // runStream()은 useEffect가 hasStarted 변화를 감지해 호출 — 직접 호출 시 abort 레이스 컨디션 발생
      setHasStarted(true);
    });
  };

  useEffect(() => {
    if (hasStarted) {
      runStream();
    }
    return () => { abortRef.current?.abort(); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [code, hasStarted]);

  if (!hasStarted && !analysis) {
    return (
      <div className="bg-white/5 border border-white/10 rounded-xl p-8 text-center space-y-4">
        <Sparkles className="w-8 h-8 mx-auto text-skyblue opacity-50" />
        <div className="space-y-1">
          <p className="text-lg font-bold text-white">AI 종목 분석</p>
          <p className="text-gray-400 text-sm">30초 광고 시청 후 꼰대아저씨의<br />종목 진단을 무료로 확인하세요!</p>
        </div>
        <button
          onClick={handleStartAnalysis}
          className="w-full py-3 bg-blue-600 hover:bg-blue-700 text-white font-bold rounded-xl transition-all shadow-lg shadow-blue-500/10 active:scale-[0.98]"
        >
          광고 보고 분석 시작
        </button>
      </div>
    );
  }

  if (loading) return <StepProgress currentStep={currentStep} />;

  if (error)
    return (
      <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-4 text-center space-y-2">
        <p className="text-red-300 text-sm">{error}</p>
        <button onClick={runStream} className="text-skyblue text-sm font-medium hover:underline">
          다시 시도
        </button>
      </div>
    );

  if (!analysis) return null;

  return (
    <div className="space-y-3">
      {/* 헤더 */}
      <div className="flex items-center gap-3">
        <Sparkles className="w-5 h-5 text-skyblue" />
        <p className="text-xs text-gray-400 flex-1">
          {new Date(analysis.analyzed_at).toLocaleString("ko-KR")} 기준
        </p>
        <span
          className={`text-xs font-bold px-3 py-1 rounded-full border ${sentimentColors[analysis.sentiment] ?? sentimentColors.neutral
            }`}
        >
          {sentimentLabels[analysis.sentiment] ?? "중립"}
        </span>
      </div>

      {/* 항목별 카드 */}
      {analysis.items.map((item, i) => (
        <div key={i} className="bg-white/5 border border-white/10 rounded-xl p-4 space-y-2">
          <div className="flex items-baseline justify-between gap-2">
            <span className="text-gray-400 text-sm font-medium">{item.label}</span>
            <span className="text-white font-bold text-sm text-right">{item.result}</span>
          </div>
          <p className="text-gray-200 text-sm">{item.reason}</p>
          <p className="text-gray-500 text-xs">{item.description}</p>
        </div>
      ))}

      {/* 종합 별점 */}
      <div className="bg-skyblue/10 border border-skyblue/30 rounded-xl p-5 text-center space-y-3">
        <h2 className="text-skyblue font-bold">종합 평가</h2>
        <div className="flex justify-center gap-1">
          {[1, 2, 3, 4, 5].map((n) => (
            <Star
              key={n}
              className={`w-7 h-7 ${n <= analysis.overall_score ? "text-amber-400 fill-amber-400" : "text-gray-600"
                }`}
            />
          ))}
        </div>
        <p className="text-sm text-gray-200">{analysis.overall_comment}</p>
      </div>
    </div>
  );
}

// ── 공시 탭 ─────────────────────────────────────────────────
const DISCLOSURE_SENTIMENT_STYLE: Record<string, string> = {
  호재: "bg-red-500/20 text-red-300 border-red-500/30",
  악재: "bg-blue-500/20 text-blue-300 border-blue-500/30",
  중립: "bg-gray-500/20 text-gray-300 border-gray-500/30",
};

function formatDisclosureDate(yyyymmdd: string) {
  if (!yyyymmdd || yyyymmdd.length < 8) return yyyymmdd;
  return `${yyyymmdd.slice(0, 4)}.${yyyymmdd.slice(4, 6)}.${yyyymmdd.slice(6, 8)}`;
}

function DisclosureCard({ item }: { item: DisclosureItem }) {
  const [expanded, setExpanded] = useState(false);
  const [analysis, setAnalysis] = useState<DisclosureAnalysis | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const { requestReward } = useReward();

  const loadAnalysis = async () => {
    if (analysis) { setExpanded((p) => !p); return; }

    requestReward(async () => {
      setExpanded(true);
      setLoading(true);
      setError("");
      try {
        const data = await fetchDisclosureAnalysis(item.rcp_no, item.report_nm, item.corp_name);
        setAnalysis(data);
      } catch (e) {
        setError(e instanceof Error ? e.message : "분석에 실패했습니다.");
        setExpanded(false);
      } finally {
        setLoading(false);
      }
    });
  };

  const dartUrl = `https://dart.fss.or.kr/dsaf001/main.do?rcpNo=${item.rcp_no}`;

  return (
    <div className="bg-white/5 border border-white/10 rounded-xl overflow-hidden">
      <button onClick={loadAnalysis} className="w-full p-3 flex items-start gap-3 text-left hover:bg-white/3 transition-colors">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            {analysis && (
              <span className={`text-[10px] px-1.5 py-0.5 rounded-full border font-bold shrink-0 ${DISCLOSURE_SENTIMENT_STYLE[analysis.sentiment] ?? DISCLOSURE_SENTIMENT_STYLE["중립"]}`}>
                {analysis.sentiment}
              </span>
            )}
            <p className="text-sm font-medium truncate">{item.report_nm}</p>
          </div>
          <p className="text-[10px] text-gray-500 mt-0.5">{formatDisclosureDate(item.rcept_dt)}</p>
        </div>
        <div className="flex items-center gap-1 shrink-0 mt-0.5">
          {loading && <Loader2 className="w-3.5 h-3.5 text-skyblue animate-spin" />}
          {expanded ? <ChevronUp className="w-4 h-4 text-gray-400" /> : <ChevronDown className="w-4 h-4 text-gray-400" />}
        </div>
      </button>

      {expanded && (
        <div className="border-t border-white/10 p-3 space-y-2.5">
          {loading && <p className="text-xs text-gray-400 text-center py-2">꼰대아저씨 분석 중...</p>}
          {error && <p className="text-red-400 text-xs">{error}</p>}
          {analysis && (
            <>
              <div className="bg-white/5 rounded-lg p-3">
                <p className="text-[10px] text-gray-400 font-semibold mb-1">📋 핵심 요약</p>
                <p className="text-xs text-gray-200 whitespace-pre-wrap leading-relaxed">{analysis.summary}</p>
              </div>
              <div className="bg-skyblue/10 border border-skyblue/30 rounded-lg p-3">
                <p className="text-[10px] text-skyblue font-semibold mb-1">💬 꼰대아저씨 한마디</p>
                <p className="text-xs text-gray-200 leading-relaxed">{analysis.insight}</p>
              </div>
              {analysis.caution && (
                <div className="bg-amber-500/10 border border-amber-500/30 rounded-lg p-2.5">
                  <p className="text-[10px] text-amber-400 font-semibold mb-1">⚠️ 주의사항</p>
                  <p className="text-xs text-gray-300">{analysis.caution}</p>
                </div>
              )}
              <a href={dartUrl} target="_blank" rel="noopener noreferrer"
                className="inline-flex items-center gap-1 text-[10px] text-gray-400 hover:text-white transition-colors">
                <ExternalLink className="w-3 h-3" />DART 원문 보기
              </a>
            </>
          )}
        </div>
      )}
    </div>
  );
}

function DisclosureTab({ code }: { code: string }) {
  const [items, setItems] = useState<DisclosureItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    setLoading(true);
    setError("");
    fetchStockDisclosures(code, 60)
      .then((data) => setItems(data.items))
      .catch((e) => setError(e instanceof Error ? e.message : "공시를 불러올 수 없습니다."))
      .finally(() => setLoading(false));
  }, [code]);

  if (loading) return <LoadingSpinner text="공시 불러오는 중..." />;

  if (error) return (
    <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-4 text-center">
      <p className="text-red-300 text-sm">{error}</p>
    </div>
  );

  if (items.length === 0) return (
    <div className="bg-white/5 border border-white/10 rounded-xl p-8 text-center text-gray-400">
      <FileText className="w-7 h-7 mx-auto mb-2 opacity-30" />
      <p className="text-sm">최근 60일 내 공시가 없습니다.</p>
    </div>
  );

  return (
    <div className="space-y-2">
      <p className="text-xs text-gray-500 px-1">최근 60일 · 총 {items.length}건</p>
      {items.map((item) => (
        <DisclosureCard key={item.rcp_no} item={item} />
      ))}
    </div>
  );
}

// ── 메인 페이지 ────────────────────────────────────────────────
export default function StockDetailPage() {
  const { code } = useParams<{ code: string }>();
  const searchParams = useSearchParams();
  const router = useRouter();

  const rawTab = searchParams.get("tab");
  const initialTab: Tab =
    rawTab === "analysis" ? "analysis" : rawTab === "disclosure" ? "disclosure" : "chart";
  const [tab, setTab] = useState<Tab>(initialTab);
  const analysisLoadedRef = useRef(false);
  const disclosureLoadedRef = useRef(false);

  // 주가·차트
  const [price, setPrice] = useState<StockPrice | null>(null);
  const [chart, setChart] = useState<ChartResponse | null>(null);
  const [period, setPeriod] = useState("3m");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  // 관심종목
  const [inWatchlist, setInWatchlist] = useState(false);
  const [watchlistLoading, setWatchlistLoading] = useState(false);
  const [userChecked, setUserChecked] = useState(false);
  const [isLoggedIn, setIsLoggedIn] = useState(false);

  // 주가·차트 로드
  useEffect(() => {
    setLoading(true);
    setError("");
    Promise.all([fetchStockPrice(code), fetchStockChart(code, period)])
      .then(([p, c]) => { setPrice(p); setChart(c); })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [code, period]);

  // 로그인 상태·관심종목
  useEffect(() => {
    supabase.auth.getUser().then(({ data: { user } }) => {
      setUserChecked(true);
      setIsLoggedIn(!!user);
      if (user) isInWatchlist(code).then(setInWatchlist);
    });
  }, [code]);

  const switchTab = (t: Tab) => {
    setTab(t);
    if (t === "analysis") analysisLoadedRef.current = true;
    if (t === "disclosure") disclosureLoadedRef.current = true;
    const params = new URLSearchParams(searchParams.toString());
    if (t === "chart") params.delete("tab");
    else params.set("tab", t);
    router.replace(`/stock/${code}${params.size ? `?${params}` : ""}`, { scroll: false });
  };

  const toggleWatchlist = () => {
    if (!price) return;
    setWatchlistLoading(true);
    (inWatchlist ? removeWatchlist(code) : addWatchlist(code, price.name))
      .then((res) => {
        if (res.ok) setInWatchlist(!inWatchlist);
        else if (res.error) setError(res.error);
      })
      .finally(() => setWatchlistLoading(false));
  };

  if (loading) return <LoadingSpinner />;
  if (error) return <ErrorMessage message={error} />;
  if (!price) return null;

  return (
    <div className="space-y-4 max-w-2xl mx-auto">
      <Link
        href="/stock"
        className="inline-flex items-center text-gray-400 hover:text-white text-sm transition-colors"
      >
        <ArrowLeft className="w-4 h-4 mr-1" /> 검색으로
      </Link>

      {/* 종목 기본 정보 (항상 표시) */}
      <StockInfo
        price={price}
        inWatchlist={inWatchlist}
        isLoggedIn={isLoggedIn}
        userChecked={userChecked}
        watchlistLoading={watchlistLoading}
        onToggleWatchlist={toggleWatchlist}
      />

      {/* 탭 헤더 */}
      <div className="flex gap-1 bg-white/5 p-1 rounded-xl">
        <button
          type="button"
          onClick={() => switchTab("chart")}
          className={`flex-1 py-2 rounded-lg text-sm font-medium transition-colors ${tab === "chart" ? "bg-skyblue/20 text-skyblue" : "text-gray-400 hover:text-white"
            }`}
        >
          차트
        </button>
        <button
          type="button"
          onClick={() => switchTab("analysis")}
          className={`flex-1 py-2 rounded-lg text-sm font-medium transition-colors flex items-center justify-center gap-1.5 ${tab === "analysis" ? "bg-skyblue/20 text-skyblue" : "text-gray-400 hover:text-white"
            }`}
        >
          <Sparkles className="w-3.5 h-3.5" />
          AI 분석
        </button>
        <button
          type="button"
          onClick={() => switchTab("disclosure")}
          className={`flex-1 py-2 rounded-lg text-sm font-medium transition-colors flex items-center justify-center gap-1.5 ${tab === "disclosure" ? "bg-skyblue/20 text-skyblue" : "text-gray-400 hover:text-white"
            }`}
        >
          <FileText className="w-3.5 h-3.5" />
          공시
        </button>
      </div>

      {/* 탭: 차트 */}
      {tab === "chart" && (
        <div>
          <div className="flex gap-2 mb-3">
            {["1m", "3m", "6m", "1y"].map((p) => (
              <button
                key={p}
                onClick={() => setPeriod(p)}
                className={`px-3 py-1 rounded-lg text-sm transition-colors ${period === p ? "bg-skyblue text-white" : "bg-white/5 text-gray-400 hover:text-white"
                  }`}
              >
                {p === "1m" ? "1개월" : p === "3m" ? "3개월" : p === "6m" ? "6개월" : "1년"}
              </button>
            ))}
          </div>

          {chart && chart.data.length > 0 && (
            <div className="bg-white/5 border border-white/10 rounded-xl p-4">
              <StockChart data={chart.data} className="w-full" />
              <div className="flex justify-between mt-2 text-[10px] text-gray-500">
                <span>{chart.data[0]?.date}</span>
                <span>{chart.data[chart.data.length - 1]?.date}</span>
              </div>
            </div>
          )}
        </div>
      )}

      {/* 탭: AI 분석 — 탭 클릭 시 마운트, 이후 언마운트 방지 */}
      {(tab === "analysis" || analysisLoadedRef.current) && (
        <div className={tab === "analysis" ? "" : "hidden"}>
          <AnalysisTab code={code} />
        </div>
      )}

      {/* 탭: 공시 */}
      {(tab === "disclosure" || disclosureLoadedRef.current) && (
        <div className={tab === "disclosure" ? "" : "hidden"}>
          <DisclosureTab code={code} />
        </div>
      )}
    </div>
  );
}
