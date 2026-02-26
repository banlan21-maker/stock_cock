"use client";

import { useState, useEffect } from "react";
import { fetchDashboard } from "@/lib/api";
import type { DashboardResponse } from "@/types";
import MarketOverview from "@/components/dashboard/MarketOverview";
import ThemeTrend from "@/components/dashboard/ThemeTrend";
import KeywordFeed from "@/components/dashboard/KeywordFeed";
import DashboardSummary from "@/components/dashboard/DashboardSummary";
import LoadingSpinner from "@/components/ui/LoadingSpinner";
import ErrorMessage from "@/components/ui/ErrorMessage";

export default function DashboardPage() {
  const [data, setData] = useState<DashboardResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = () => {
    setLoading(true);
    setError("");
    fetchDashboard()
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    load();
  }, []);

  if (loading) return <LoadingSpinner text="대시보드 로딩 중..." />;
  if (error) return <ErrorMessage message={error} onRetry={load} />;
  if (!data) return null;

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">대시보드</h1>

      {/* 테마 트렌드 (최상단) */}
      <ThemeTrend />

      {/* 시장 현황 */}
      <MarketOverview marketSummary={data.market_summary} />

      {/* 내 관심 키워드 */}
      <KeywordFeed />

      <DashboardSummary topNews={data.top_news} hotPolicies={data.hot_policies} />
    </div>
  );
}
