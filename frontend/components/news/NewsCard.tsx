"use client";

import Link from "next/link";
import { Sparkles, TrendingUp } from "lucide-react";
import { sanitizeNewsTitle } from "@/lib/sanitizeTitle";
import type { NewsArticle } from "@/types";

interface NewsCardProps {
  news: NewsArticle;
}

const categoryStyles: Record<string, string> = {
  global: "bg-blue-500/20 text-blue-300",
  domestic: "bg-green-500/20 text-green-300",
  policy: "bg-purple-500/20 text-purple-300",
};

const categoryLabels: Record<string, string> = {
  global: "해외",
  domestic: "국내",
  policy: "정책",
};

export default function NewsCard({ news }: NewsCardProps) {
  const style = categoryStyles[news.category] ?? "bg-gray-500/20 text-gray-300";

  return (
    <Link
      href={`/issues/${encodeURIComponent(news.id)}`}
      className="block bg-white/5 border border-white/10 rounded-xl p-5 hover:bg-white/10 transition-colors"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <span
            className={`inline-block text-[10px] font-bold px-2 py-0.5 rounded-full mb-2 ${style}`}
          >
            {categoryLabels[news.category] ?? news.category}
          </span>
          <p className="font-medium text-lg">{sanitizeNewsTitle(news.title)}</p>
          <div className="flex items-center gap-3 mt-2 flex-wrap">
            <p className="text-xs text-gray-400">
              {news.source} &middot; {new Date(news.published_at).toLocaleDateString("ko-KR")}
            </p>
            <div className="flex items-center gap-2">
              <span className="flex items-center gap-1 text-[10px] text-skyblue/70">
                <Sparkles className="w-3 h-3" /> AI 분석
              </span>
              {news.related_stocks?.length > 0 && (
                <span className="flex items-center gap-1 text-[10px] text-amber-400/80">
                  <TrendingUp className="w-3 h-3" /> 관련 종목 {news.related_stocks.length}개
                </span>
              )}
            </div>
          </div>
        </div>
      </div>
    </Link>
  );
}
