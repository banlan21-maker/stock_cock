"use client";

import { useState, useEffect } from "react";
import { fetchKeywordFeed, fetchThemeTrend } from "@/lib/api";
import { getCustomKeywords, setCustomKeywords, getCustomKeywordsQuery } from "@/lib/customKeywords";
import type { KeywordFeedResponse, KeywordStock } from "@/types";
import Link from "next/link";
import { Search, Sparkles } from "lucide-react";

export default function KeywordFeed() {
  const [kw1, setKw1] = useState("");
  const [kw2, setKw2] = useState("");
  const [feed, setFeed] = useState<KeywordFeedResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [autoSource, setAutoSource] = useState(""); // 자동 적용 시 출처 표시

  const applyKeywords = (k1: string, k2: string, source = "") => {
    const kws = [k1, k2].filter((k) => k.trim()).join(",");
    if (!kws) return;
    setCustomKeywords(k1, k2);
    setAutoSource(source);
    setLoading(true);
    setError("");
    fetchKeywordFeed(kws)
      .then(setFeed)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  };

  // 마운트: 저장된 키워드 복원 or 테마 top2 자동 적용
  useEffect(() => {
    const saved = getCustomKeywords();
    if (saved.kw1 || saved.kw2) {
      // 저장된 키워드 복원
      setKw1(saved.kw1);
      setKw2(saved.kw2);
      applyKeywords(saved.kw1, saved.kw2);
    } else {
      // 저장된 키워드 없음 → 테마 트렌드 상위 2개 자동 적용
      setLoading(true);
      fetchThemeTrend("change_rate", "daily")
        .then((res) => {
          const top2 = res.groups.slice(0, 2).map((g) => g.theme);
          const k1 = top2[0] ?? "";
          const k2 = top2[1] ?? "";
          if (k1) {
            setKw1(k1);
            setKw2(k2);
            applyKeywords(k1, k2, "오늘의 테마 트렌드 상위 2개 자동 적용");
          } else {
            setLoading(false);
          }
        })
        .catch(() => setLoading(false));
    }
  }, []);

  const handleApply = () => {
    applyKeywords(kw1, kw2);
  };

  const currentQuery = getCustomKeywordsQuery();

  return (
    <section>
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-lg font-bold">내 관심 키워드</h2>
        {autoSource && (
          <span className="text-xs text-gray-500 flex items-center gap-1">
            <Sparkles className="w-3 h-3" /> {autoSource}
          </span>
        )}
      </div>

      {/* 입력 영역 */}
      <div className="bg-white/5 border border-white/10 rounded-xl p-4">
        <div className="flex flex-col sm:flex-row gap-2">
          <input
            type="text"
            value={kw1}
            onChange={(e) => setKw1(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleApply()}
            placeholder="키워드 예: AI"
            className="flex-1 min-w-0 bg-white/10 border border-white/10 rounded-lg px-3 py-2 text-sm placeholder:text-gray-500 focus:outline-none focus:border-skyblue/50"
          />
          <input
            type="text"
            value={kw2}
            onChange={(e) => setKw2(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleApply()}
            placeholder="키워드 예: 반도체"
            className="flex-1 min-w-0 bg-white/10 border border-white/10 rounded-lg px-3 py-2 text-sm placeholder:text-gray-500 focus:outline-none focus:border-skyblue/50"
          />
          <button
            type="button"
            onClick={handleApply}
            disabled={loading || (!kw1.trim() && !kw2.trim())}
            className="w-full sm:w-auto px-4 py-2 bg-skyblue/20 text-skyblue rounded-lg text-sm hover:bg-skyblue/30 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-1.5 whitespace-nowrap flex-shrink-0"
          >
            <Search className="w-4 h-4" />
            적용
          </button>
        </div>
        {currentQuery && (
          <p className="text-xs text-gray-500 mt-2">
            뉴스·정책 페이지에도 <span className="text-skyblue">'{currentQuery.split(",").join(", ")}'</span> 필터가 적용됩니다
          </p>
        )}
      </div>

      {/* 결과 로딩 skeleton */}
      {loading && (
        <div className="mt-4 space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-16 bg-white/5 border border-white/10 rounded-xl animate-pulse" />
          ))}
        </div>
      )}

      {error && (
        <div className="mt-4 text-sm text-red-400 bg-red-400/10 border border-red-400/20 rounded-xl p-3">
          {error}
        </div>
      )}

      {!loading && feed && (
        <div className="mt-4 space-y-5">
          {/* 관련 종목 */}
          {feed.stocks.length > 0 && (
            <div>
              <h3 className="text-sm font-semibold text-gray-300 mb-2">
                관련 종목
                <span className="text-xs text-gray-500 font-normal ml-1">AI 추천 · 실제 상장 검증</span>
              </h3>
              <div className="space-y-2">
                {(feed.stocks as KeywordStock[]).map((s) => (
                  <Link
                    key={s.code}
                    href={`/stock/${s.code}`}
                    className="block bg-white/5 border border-white/10 rounded-xl p-3 hover:bg-white/10 transition-colors"
                  >
                    <div className="flex items-center justify-between gap-3">
                      <div className="min-w-0">
                        <div className="flex items-center gap-2">
                          <p className="text-sm font-medium truncate">{s.name}</p>
                          <p className="text-xs text-gray-400">{s.code}</p>
                          {s.current_price != null && (
                            <span className={`text-xs font-medium ${(s.change_rate ?? 0) >= 0 ? "text-green-400" : "text-red-400"}`}>
                              {(s.change_rate ?? 0) >= 0 ? "+" : ""}{(s.change_rate ?? 0).toFixed(1)}%
                            </span>
                          )}
                        </div>
                        <p className="text-xs text-gray-400 mt-0.5 line-clamp-1">{s.reason}</p>
                      </div>
                      {s.current_price != null && (
                        <p className="text-sm font-medium text-right whitespace-nowrap">{s.current_price.toLocaleString()}원</p>
                      )}
                    </div>
                  </Link>
                ))}
              </div>
            </div>
          )}

          {/* 관련 뉴스 */}
          {feed.news.length > 0 && (
            <div>
              <h3 className="text-sm font-semibold text-gray-300 mb-2">관련 뉴스</h3>
              <div className="space-y-2">
                {feed.news.map((n) => (
                  <Link
                    key={n.id}
                    href={`/issues/${encodeURIComponent(n.id)}`}
                    className="block bg-white/5 border border-white/10 rounded-xl p-3 hover:bg-white/10 transition-colors"
                  >
                    <p className="text-sm font-medium line-clamp-2">{n.title}</p>
                    <p className="text-xs text-gray-400 mt-1">
                      {n.source} &middot; {new Date(n.published_at).toLocaleDateString("ko-KR")}
                    </p>
                  </Link>
                ))}
              </div>
            </div>
          )}

          {/* 관련 정책 */}
          {feed.policies.length > 0 && (
            <div>
              <h3 className="text-sm font-semibold text-gray-300 mb-2">관련 정책</h3>
              <div className="space-y-2">
                {feed.policies.map((p) => (
                  <Link
                    key={p.id}
                    href={`/policy/${p.id}`}
                    className="block bg-white/5 border border-white/10 rounded-xl p-3 hover:bg-white/10 transition-colors"
                  >
                    <p className="text-sm font-medium line-clamp-2">{p.title}</p>
                    <p className="text-xs text-gray-400 mt-1">{p.department}</p>
                  </Link>
                ))}
              </div>
            </div>
          )}

          {feed.stocks.length === 0 && feed.news.length === 0 && feed.policies.length === 0 && (
            <p className="text-sm text-gray-400 text-center py-4">해당 키워드의 결과가 없습니다.</p>
          )}
        </div>
      )}
    </section>
  );
}
