"use client";

import { useState, useEffect } from "react";
import { fetchNewsList } from "@/lib/api";
import { getCustomKeywordsQuery } from "@/lib/customKeywords";
import type { NewsListResponse } from "@/types";
import LoadingSpinner from "@/components/ui/LoadingSpinner";
import ErrorMessage from "@/components/ui/ErrorMessage";
import NewsCard from "@/components/news/NewsCard";
import Link from "next/link";
import { X, Globe, Settings } from "lucide-react";

const categories = [
  { value: "all", label: "전체" },
  { value: "global", label: "글로벌" },
  { value: "domestic", label: "국내" },
];

export default function IssuesPage() {
  const [category, setCategory] = useState("all");
  const [data, setData] = useState<NewsListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [activeKeywords, setActiveKeywords] = useState("");
  const [showAll, setShowAll] = useState(false);

  const load = (forceAll = false) => {
    setLoading(true);
    setError("");
    const kws = forceAll ? "" : getCustomKeywordsQuery();
    setActiveKeywords(kws);
    fetchNewsList(category, 1, 10, kws || undefined)
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  };

  // 페이지 진입/카테고리 변경/showAll 변경 시 재조회
  useEffect(() => {
    load(showAll);
  }, [category, showAll]);

  const handleClearKeywords = () => {
    setShowAll(true);
  };

  const handleRestoreKeywords = () => {
    setShowAll(false);
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <Globe className="w-6 h-6 text-amber-400" />
          이슈 콕
        </h1>
        <p className="text-gray-400 mt-1 text-sm">AI가 분석한 국내외 핵심 이슈, 단순 요약을 넘어 시장 파급력까지!</p>
      </div>

      {/* 활성 키워드 배지 */}
      {activeKeywords && !showAll ? (
        <div className="flex items-center gap-2 px-3 py-2 bg-skyblue/10 border border-skyblue/30 rounded-lg">
          <span className="text-xs text-skyblue font-medium">
            🔍 '{activeKeywords.split(",").join(", ")}' 기준 필터링 중
          </span>
          <div className="ml-auto flex items-center gap-3">
            <Link
              href="/dashboard"
              className="flex items-center gap-1 text-xs text-gray-400 hover:text-white transition-colors"
            >
              <Settings className="w-3 h-3" /> 키워드 변경
            </Link>
            <button
              type="button"
              onClick={handleClearKeywords}
              className="flex items-center gap-1 text-xs text-gray-400 hover:text-white transition-colors"
            >
              <X className="w-3.5 h-3.5" /> 전체 보기
            </button>
          </div>
        </div>
      ) : showAll && getCustomKeywordsQuery() ? (
        <div className="flex items-center gap-2 px-3 py-2 bg-white/5 border border-white/10 rounded-lg">
          <span className="text-xs text-gray-400">전체 뉴스 표시 중</span>
          <button
            type="button"
            onClick={handleRestoreKeywords}
            className="ml-auto text-xs text-skyblue hover:underline"
          >
            '{getCustomKeywordsQuery().split(",").join(", ")}' 필터 다시 적용
          </button>
        </div>
      ) : null}

      {/* 카테고리 필터 */}
      <div className="flex gap-2">
        {categories.map((c) => (
          <button
            key={c.value}
            onClick={() => setCategory(c.value)}
            className={`px-4 py-1.5 rounded-full text-sm font-medium transition-colors ${
              category === c.value
                ? "bg-skyblue text-white"
                : "bg-white/5 text-gray-400 hover:text-white hover:bg-white/10"
            }`}
          >
            {c.label}
          </button>
        ))}
      </div>

      {loading && <LoadingSpinner />}
      {error && <ErrorMessage message={error} onRetry={() => load(showAll)} />}

      {data && (
        <div className="space-y-3">
          {data.items.length === 0 ? (
            <p className="text-gray-400 text-sm text-center py-8">해당 키워드의 뉴스가 없습니다.</p>
          ) : (
            data.items.map((n) => (
              <NewsCard key={n.id} news={n} />
            ))
          )}
        </div>
      )}
    </div>
  );
}
