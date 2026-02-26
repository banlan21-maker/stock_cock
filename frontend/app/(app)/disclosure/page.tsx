"use client";

import { useState, useEffect, useCallback } from "react";
import { FileText, ChevronDown, ChevronUp, ExternalLink, Loader2 } from "lucide-react";
import Link from "next/link";
import { fetchTodayDisclosures, fetchDisclosureAnalysis } from "@/lib/api";
import { useReward } from "@/context/RewardProvider";
import type { DisclosureItem, DisclosureAnalysis } from "@/types";
import LoadingSpinner from "@/components/ui/LoadingSpinner";
import ErrorMessage from "@/components/ui/ErrorMessage";

// ── 감성 스타일 ───────────────────────────────────────────────
const SENTIMENT_STYLE: Record<string, string> = {
  호재: "bg-red-500/20 text-red-300 border-red-500/30",
  악재: "bg-blue-500/20 text-blue-300 border-blue-500/30",
  중립: "bg-gray-500/20 text-gray-300 border-gray-500/30",
};

function formatDate(yyyymmdd: string) {
  if (!yyyymmdd || yyyymmdd.length < 8) return yyyymmdd;
  return `${yyyymmdd.slice(0, 4)}.${yyyymmdd.slice(4, 6)}.${yyyymmdd.slice(6, 8)}`;
}

// ── 개별 공시 카드 ─────────────────────────────────────────────
function DisclosureCard({ item }: { item: DisclosureItem }) {
  const [expanded, setExpanded] = useState(false);
  const [analysis, setAnalysis] = useState<DisclosureAnalysis | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const { requestReward } = useReward();

  const loadAnalysis = async () => {
    if (analysis) {
      setExpanded((prev) => !prev);
      return;
    }

    // 보상형 광고 요청
    requestReward(async () => {
      setExpanded(true);
      setLoading(true);
      setError("");
      try {
        const data = await fetchDisclosureAnalysis(item.rcp_no, item.report_nm, item.corp_name);
        setAnalysis(data);
      } catch (e) {
        setError(e instanceof Error ? e.message : "분석에 실패했습니다.");
        setExpanded(false); // 실패 시 닫기
      } finally {
        setLoading(false);
      }
    });
  };

  const dartUrl = `https://dart.fss.or.kr/dsaf001/main.do?rcpNo=${item.rcp_no}`;
  const sentimentStyle = analysis ? (SENTIMENT_STYLE[analysis.sentiment] ?? SENTIMENT_STYLE["중립"]) : "";

  return (
    <div className="bg-white/5 border border-white/10 rounded-xl overflow-hidden transition-colors hover:border-white/20">
      {/* 헤더 (클릭 → AI 분석 펼치기) */}
      <button
        onClick={loadAnalysis}
        className="w-full p-4 flex items-start gap-3 text-left"
      >
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-semibold text-sm">{item.corp_name}</span>
            {item.stock_code && (
              <span className="text-[10px] text-gray-500">{item.stock_code}</span>
            )}
            {analysis && (
              <span
                className={`text-[10px] px-2 py-0.5 rounded-full border font-bold ${sentimentStyle}`}
              >
                {analysis.sentiment}
              </span>
            )}
          </div>
          <p className="text-xs text-gray-300 mt-0.5 line-clamp-1">{item.report_nm}</p>
          <p className="text-[10px] text-gray-500 mt-0.5">{formatDate(item.rcept_dt)}</p>
        </div>
        <div className="flex items-center gap-1.5 shrink-0 mt-0.5">
          {loading && <Loader2 className="w-3.5 h-3.5 text-skyblue animate-spin" />}
          {expanded ? (
            <ChevronUp className="w-4 h-4 text-gray-400" />
          ) : (
            <ChevronDown className="w-4 h-4 text-gray-400" />
          )}
        </div>
      </button>

      {/* AI 분석 패널 */}
      {expanded && (
        <div className="border-t border-white/10 p-4 space-y-3">
          {loading && <LoadingSpinner text="꼰대아저씨 분석 중..." />}

          {error && (
            <div className="flex items-center gap-2">
              <p className="text-red-400 text-sm flex-1">{error}</p>
              <button
                onClick={() => { setError(""); loadAnalysis(); }}
                className="text-skyblue text-xs hover:underline shrink-0"
              >
                다시 시도
              </button>
            </div>
          )}

          {analysis && (
            <>
              {/* 핵심 요약 */}
              <div className="bg-white/5 rounded-lg p-3 space-y-1.5">
                <p className="text-[11px] text-gray-400 font-semibold">📋 핵심 요약</p>
                <p className="text-sm text-gray-200 whitespace-pre-wrap leading-relaxed">
                  {analysis.summary}
                </p>
              </div>

              {/* 꼰대아저씨 한마디 */}
              <div className="bg-skyblue/10 border border-skyblue/30 rounded-lg p-3">
                <p className="text-[11px] text-skyblue font-semibold mb-1.5">
                  💬 꼰대아저씨 한마디
                </p>
                <p className="text-sm text-gray-200 leading-relaxed">{analysis.insight}</p>
              </div>

              {/* 주의사항 (있을 때만) */}
              {analysis.caution && (
                <div className="bg-amber-500/10 border border-amber-500/30 rounded-lg p-3">
                  <p className="text-[11px] text-amber-400 font-semibold mb-1">⚠️ 주의사항</p>
                  <p className="text-sm text-gray-300">{analysis.caution}</p>
                </div>
              )}

              {/* 관련 링크 */}
              <div className="flex items-center gap-3 pt-1">
                <a
                  href={dartUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 text-xs text-gray-400 hover:text-white transition-colors"
                >
                  <ExternalLink className="w-3 h-3" />
                  DART 원문 보기
                </a>
                {item.stock_code && (
                  <Link
                    href={`/stock/${item.stock_code}`}
                    className="text-xs text-skyblue hover:text-skyblue/70 transition-colors"
                  >
                    종목 상세 보기 →
                  </Link>
                )}
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}

// ── 메인 페이지 ──────────────────────────────────────────────
export default function DisclosurePage() {
  const [items, setItems] = useState<DisclosureItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const data = await fetchTodayDisclosures(40);
      setItems(data.items);
    } catch (e) {
      setError(e instanceof Error ? e.message : "공시 목록을 불러올 수 없습니다.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  return (
    <div className="space-y-6">
      {/* 헤더 */}
      <div>
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <FileText className="w-6 h-6 text-amber-400" />
          공시 콕
        </h1>
        <p className="text-gray-400 mt-1 text-sm">
          오늘 발표된 주요 공시를 꼰대아저씨가 쉽게 풀어드립니다
        </p>
      </div>

      {loading && <LoadingSpinner text="오늘의 공시 불러오는 중..." />}
      {error && <ErrorMessage message={error} onRetry={load} />}

      {!loading && !error && items.length === 0 && (
        <div className="bg-white/5 border border-white/10 rounded-xl p-12 text-center text-gray-400">
          <FileText className="w-8 h-8 mx-auto mb-3 opacity-30" />
          <p className="text-lg mb-1">오늘 공시된 주요 항목이 없습니다.</p>
          <p className="text-sm text-gray-600">
            정기공시·주요사항보고 기준으로 수집합니다.
          </p>
        </div>
      )}

      {items.length > 0 && (
        <div className="space-y-2">
          <p className="text-xs text-gray-500 px-1">총 {items.length}건 · 카드를 누르면 AI 분석을 볼 수 있어요</p>
          {items.map((item) => (
            <DisclosureCard key={item.rcp_no} item={item} />
          ))}
        </div>
      )}
    </div>
  );
}
