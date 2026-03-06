"use client";

import { useState, useEffect } from "react";
import { fetchPolicyList } from "@/lib/api";
import { getCustomKeywordsQuery } from "@/lib/customKeywords";
import type { PolicyListResponse } from "@/types";
import LoadingSpinner from "@/components/ui/LoadingSpinner";
import ErrorMessage from "@/components/ui/ErrorMessage";
import PolicyCard from "@/components/policy/PolicyCard";
import Link from "next/link";
import { Search, X, Settings } from "lucide-react";

export default function PolicyPage() {
  const [data, setData] = useState<PolicyListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [activeKeywords, setActiveKeywords] = useState("");
  const [showAll, setShowAll] = useState(false);

  const load = (forceAll = false) => {
    setLoading(true);
    setError("");
    const kws = forceAll ? "" : getCustomKeywordsQuery();
    setActiveKeywords(kws);
    fetchPolicyList(1, 20, kws || undefined)
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    load(showAll);
  }, [showAll]);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <Search className="w-6 h-6 text-amber-400" />
          정책 콕
        </h1>
        <p className="text-gray-400 mt-1 text-sm">방대한 정책 보도자료, AI가 3줄 핵심 요약부터 연관 수혜주까지 한 번에 정리!</p>
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
              onClick={() => setShowAll(true)}
              className="flex items-center gap-1 text-xs text-gray-400 hover:text-white transition-colors"
            >
              <X className="w-3.5 h-3.5" /> 전체 보기
            </button>
          </div>
        </div>
      ) : showAll && getCustomKeywordsQuery() ? (
        <div className="flex items-center gap-2 px-3 py-2 bg-white/5 border border-white/10 rounded-lg">
          <span className="text-xs text-gray-400">전체 정책 표시 중</span>
          <button
            type="button"
            onClick={() => setShowAll(false)}
            className="ml-auto text-xs text-skyblue hover:underline"
          >
            '{getCustomKeywordsQuery().split(",").join(", ")}' 필터 다시 적용
          </button>
        </div>
      ) : null}

      {loading && <LoadingSpinner />}
      {error && <ErrorMessage message={error} onRetry={() => load(showAll)} />}

      {data && (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {data.items.length === 0 ? (
            <p className="col-span-2 text-gray-400 text-sm text-center py-8">해당 키워드의 정책이 없습니다.</p>
          ) : (
            data.items.map((p) => (
              <PolicyCard key={p.id} policy={p} />
            ))
          )}
        </div>
      )}
    </div>
  );
}
