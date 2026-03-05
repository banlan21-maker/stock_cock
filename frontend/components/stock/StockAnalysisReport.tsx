"use client";

import { Star, Sparkles } from "lucide-react";
import type { StockAnalysis } from "@/types";
import AiDisclaimer from "@/components/ui/AiDisclaimer";

interface StockAnalysisReportProps {
  analysis: StockAnalysis;
}

const sentimentLabels: Record<string, string> = {
  bullish: "긍정적",
  bearish: "부정적",
  neutral: "중립",
};

const sentimentStyles: Record<string, string> = {
  bullish: "bg-green-500/20 text-green-300",
  bearish: "bg-red-500/20 text-red-300",
  neutral: "bg-gray-500/20 text-gray-300",
};

export default function StockAnalysisReport({ analysis }: StockAnalysisReportProps) {
  const style = sentimentStyles[analysis.sentiment] ?? sentimentStyles.neutral;
  const label = sentimentLabels[analysis.sentiment] ?? "중립";

  return (
    <div className="space-y-3">
      {/* 헤더 */}
      <div className="flex items-center gap-2">
        <Sparkles className="w-5 h-5 text-skyblue" />
        <h2 className="font-bold text-skyblue">주식콕 분석</h2>
        <span className={`text-sm font-bold px-2 py-0.5 rounded-full ${style}`}>{label}</span>
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
      <div className="bg-skyblue/10 border border-skyblue/30 rounded-xl p-4 text-center space-y-2">
        <h3 className="text-skyblue font-bold">종합 평가</h3>
        <div className="flex justify-center gap-1">
          {[1, 2, 3, 4, 5].map((n) => (
            <Star
              key={n}
              className={`w-6 h-6 ${
                n <= analysis.overall_score
                  ? "text-amber-400 fill-amber-400"
                  : "text-gray-600"
              }`}
            />
          ))}
        </div>
        <p className="text-sm text-gray-200">{analysis.overall_comment}</p>
      </div>
      <AiDisclaimer />
    </div>
  );
}
