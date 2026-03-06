"use client";

import { useEffect, useRef, useState } from "react";
import {
  TrendingUp,
  TrendingDown,
  Minus,
  AlertTriangle,
  CheckCircle,
  RefreshCw,
} from "lucide-react";
import AiDisclaimer from "@/components/ui/AiDisclaimer";
import { fetchPortfolioAnalysisStream } from "@/lib/portfolio";
import type { PortfolioAIAnalysis } from "@/types";

const RISK_LABEL: Record<string, string> = {
  low: "낮음",
  medium: "보통",
  high: "높음",
};

const RISK_COLOR: Record<string, string> = {
  low: "text-green-400 bg-green-400/10 border-green-400/20",
  medium: "text-amber-400 bg-amber-400/10 border-amber-400/20",
  high: "text-red-400 bg-red-400/10 border-red-400/20",
};

const ACTION_ICON: Record<string, React.ReactNode> = {
  reduce: <TrendingDown className="w-4 h-4 text-blue-400" />,
  increase: <TrendingUp className="w-4 h-4 text-red-400" />,
  hold: <Minus className="w-4 h-4 text-gray-400" />,
};

const ACTION_LABEL: Record<string, string> = {
  reduce: "비중 축소",
  increase: "비중 확대",
  hold: "유지",
};

function ScoreDots({ score }: { score: number }) {
  return (
    <div className="flex gap-1">
      {[1, 2, 3, 4, 5].map((i) => (
        <div
          key={i}
          className={`w-2.5 h-2.5 rounded-full ${
            i <= score ? "bg-skyblue" : "bg-white/10"
          }`}
        />
      ))}
    </div>
  );
}

const MAX_AUTO_RETRIES = 2;

export default function AIAnalysisReport() {
  const [status, setStatus] = useState<{ step: number; message: string } | null>(null);
  const [result, setResult] = useState<PortfolioAIAnalysis | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const abortRef = useRef<AbortController | null>(null);
  const autoRetryRef = useRef(0);

  async function run(isAutoRetry = false) {
    if (!isAutoRetry) {
      autoRetryRef.current = 0;
      setResult(null);
      setError(null);
    }
    setLoading(true);
    setStatus(null);

    abortRef.current?.abort();
    const ctrl = new AbortController();
    abortRef.current = ctrl;

    let gotResult = false;
    try {
      for await (const event of fetchPortfolioAnalysisStream(ctrl.signal)) {
        if (event.type === "status") {
          setStatus({ step: event.step, message: event.message });
        } else if (event.type === "done") {
          gotResult = true;
          setResult(event.data);
          setLoading(false);
        } else if (event.type === "error") {
          gotResult = true;
          setError(event.message);
          setLoading(false);
        }
      }
    } catch (err) {
      if ((err as Error).name !== "AbortError") {
        setError("분석 중 오류가 발생했습니다.");
      }
      setLoading(false);
      return;
    }

    // SSE 루프가 done/error 없이 종료된 경우 → 자동 재시도
    if (!gotResult) {
      if (autoRetryRef.current < MAX_AUTO_RETRIES) {
        autoRetryRef.current++;
        run(true);
      } else {
        setError("분석 결과를 받지 못했습니다. 다시 시도해 주세요.");
        setLoading(false);
      }
    }
  }

  useEffect(() => {
    run();
    return () => abortRef.current?.abort();
  }, []);

  if (loading) {
    return (
      <div className="bg-white/5 border border-white/10 rounded-xl p-8">
        <div className="flex flex-col items-center gap-4">
          <div className="w-8 h-8 border-2 border-skyblue border-t-transparent rounded-full animate-spin" />
          <p className="text-gray-400 text-sm">
            {status ? status.message : "AI 진단 준비 중..."}
          </p>
          {status && (
            <div className="w-full max-w-xs bg-white/5 rounded-full h-1.5">
              <div
                className="bg-skyblue h-1.5 rounded-full transition-all duration-500"
                style={{ width: `${(status.step / 2) * 100}%` }}
              />
            </div>
          )}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-white/5 border border-red-400/20 rounded-xl p-6 text-center">
        <AlertTriangle className="w-8 h-8 text-red-400 mx-auto mb-2" />
        <p className="text-red-400 text-sm mb-4">{error}</p>
        <button
          onClick={run}
          className="text-xs text-gray-400 hover:text-white flex items-center gap-1 mx-auto"
        >
          <RefreshCw className="w-3 h-3" /> 다시 시도
        </button>
      </div>
    );
  }

  if (!result) return null;

  const riskClass = RISK_COLOR[result.risk_level] ?? RISK_COLOR.medium;

  return (
    <div className="space-y-4">
      {/* 헤더 */}
      <div className="bg-white/5 border border-white/10 rounded-xl p-5">
        <div className="flex items-center justify-between mb-3">
          <h3 className="font-semibold">AI 포트폴리오 진단</h3>
          <button
            onClick={run}
            className="text-xs text-gray-400 hover:text-white flex items-center gap-1"
          >
            <RefreshCw className="w-3 h-3" /> 재분석
          </button>
        </div>
        <div className="flex items-center gap-4 flex-wrap">
          <div>
            <p className="text-xs text-gray-500 mb-1">종합 점수</p>
            <ScoreDots score={result.overall_score} />
          </div>
          <div>
            <p className="text-xs text-gray-500 mb-1">리스크</p>
            <span
              className={`text-xs px-2 py-0.5 rounded-full border ${riskClass}`}
            >
              {RISK_LABEL[result.risk_level] ?? result.risk_level}
            </span>
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-xs text-gray-500 mb-1">종합 평가</p>
            <p className="text-sm text-gray-300 leading-relaxed">{result.overall_comment}</p>
          </div>
        </div>
      </div>

      {/* 섹터 분석 */}
      {result.sector_analysis.length > 0 && (
        <div className="bg-white/5 border border-white/10 rounded-xl p-5">
          <h4 className="text-sm font-medium mb-3">섹터 분석</h4>
          <div className="space-y-2">
            {result.sector_analysis.map((s, i) => (
              <div key={i} className="flex items-start gap-3">
                <div className="w-20 shrink-0">
                  <p className="text-xs text-gray-300 truncate">{s.sector}</p>
                  <p className="text-xs text-skyblue">{s.ratio.toFixed(1)}%</p>
                </div>
                <div className="flex-1">
                  <div className="bg-white/5 rounded-full h-1.5 mb-1">
                    <div
                      className="bg-skyblue h-1.5 rounded-full"
                      style={{ width: `${Math.min(s.ratio, 100)}%` }}
                    />
                  </div>
                  <p className="text-xs text-gray-500">{s.comment}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 리밸런싱 추천 */}
      {result.rebalancing.length > 0 && (
        <div className="bg-white/5 border border-white/10 rounded-xl p-5">
          <h4 className="text-sm font-medium mb-3">리밸런싱 추천</h4>
          <div className="space-y-2">
            {result.rebalancing.map((r, i) => (
              <div key={i} className="flex items-start gap-3 py-2 border-b border-white/5 last:border-0">
                <div className="flex items-center gap-1.5 shrink-0 w-24">
                  {ACTION_ICON[r.action]}
                  <span className="text-xs text-gray-300">{ACTION_LABEL[r.action]}</span>
                </div>
                <div className="flex-1">
                  <p className="text-xs font-medium">{r.stock_code}</p>
                  <p className="text-xs text-gray-500">{r.reason}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      <p className="text-xs text-gray-600 text-right">
        분석 시각: {new Date(result.analyzed_at).toLocaleString("ko-KR")}
        {" · "}24시간 캐시됨
      </p>
      <AiDisclaimer />
    </div>
  );
}
