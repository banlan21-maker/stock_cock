"use client";

import { useState, useEffect } from "react";
import { Treemap, ResponsiveContainer } from "recharts";
import { fetchThemeTrend } from "@/lib/api";
import type { ThemeGroup, ThemeTrendResponse } from "@/types";

type SortMode = "change_rate" | "volume";
type PeriodMode = "daily" | "weekly";

function getColor(changeRate: number): string {
  if (changeRate > 0) {
    if (changeRate >= 3.0) return "#ef4444";
    if (changeRate >= 1.0) return "#f87171";
    return "#fca5a5";
  } else if (changeRate < 0) {
    if (changeRate <= -3.0) return "#3b82f6";
    if (changeRate <= -1.0) return "#60a5fa";
    return "#93c5fd";
  }
  return "#4b5563";
}

interface TreemapContentProps {
  x?: number;
  y?: number;
  width?: number;
  height?: number;
  name?: string;
  depth?: number;
  value?: number;
  avgChangeRate?: number;
  fillColor?: string;
}

function truncateText(text: string, maxLen: number): string {
  if (text.length <= maxLen) return text;
  return text.slice(0, maxLen - 1) + "…";
}

function ThemeTreemapContent(props: TreemapContentProps) {
  const {
    x = 0,
    y = 0,
    width = 0,
    height = 0,
    name = "",
    depth = 0,
    avgChangeRate = 0,
    fillColor = "#ef4444",
  } = props;
  if (depth === 0 || width < 15 || height < 12) return null;

  const fontSize = Math.min(14, Math.max(10, width / 6));
  const showText = width > 28 && height > 20;
  const maxNameLen = Math.max(2, Math.floor(width / (fontSize * 0.85)));
  const displayName = truncateText(name, maxNameLen);
  const showRate = height > 40;
  const rateStr = `${avgChangeRate > 0 ? "+" : ""}${Number(avgChangeRate).toFixed(2)}%`;

  return (
    <g>
      <rect
        x={x + 1}
        y={y + 1}
        width={Math.max(0, width - 2)}
        height={Math.max(0, height - 2)}
        fill={fillColor}
        rx={3}
        stroke="#000000"
        strokeWidth={2}
      />
      {showText && (
        <>
          <text
            x={x + width / 2}
            y={showRate ? y + height / 2 - 8 : y + height / 2 + 4}
            textAnchor="middle"
            fill="#fff"
            fontSize={fontSize}
            fontWeight="bold"
            style={{ pointerEvents: "none" }}
          >
            {displayName}
          </text>
          {showRate && (
            <text
              x={x + width / 2}
              y={y + height / 2 + 10}
              textAnchor="middle"
              fill="#ffffff"
              fontSize={Math.max(9, fontSize - 1)}
              style={{ pointerEvents: "none" }}
            >
              {rateStr}
            </text>
          )}
        </>
      )}
    </g>
  );
}

function ThemeSkeleton() {
  return (
    <div className="w-full h-80 bg-white/5 border border-white/10 rounded-xl animate-pulse flex items-center justify-center text-gray-500 text-sm">
      테마 트렌드 로딩 중...
    </div>
  );
}

export default function ThemeTrend() {
  const [sort, setSort] = useState<SortMode>("change_rate");
  const [period, setPeriod] = useState<PeriodMode>("daily");
  const [response, setResponse] = useState<ThemeTrendResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    setLoading(true);
    setError("");
    setResponse(null);
    fetchThemeTrend(sort, period)
      .then(setResponse)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [sort, period]);

  const groups: ThemeGroup[] = response?.groups ?? [];
  const subtitle = response?.trade_date
    ? `${response.trade_date} 기준 · 최근 거래일`
    : "최근 거래일 기준";

  const treemapData = groups.map((g) => ({
    name: g.theme,
    value: Math.max(g.total_volume, 1),
    avgChangeRate: Number(g.avg_change_rate),
    fillColor: getColor(Number(g.avg_change_rate)),
  }));

  return (
    <section>
      <div className="flex flex-wrap items-center justify-between gap-2 mb-2">
        <div>
          <h2 className="text-lg font-bold">오늘의 테마 트렌드</h2>
          <p className="text-xs text-gray-400">{loading ? "데이터 로딩 중..." : subtitle}</p>
        </div>
        <div className="flex gap-1">
          <button
            type="button"
            onClick={() => setSort("change_rate")}
            className={`text-xs px-3 py-1.5 rounded-lg transition-colors ${
              sort === "change_rate" ? "bg-skyblue/20 text-skyblue" : "text-gray-400 hover:text-white hover:bg-white/5"
            }`}
          >
            상승률 기준
          </button>
          <button
            type="button"
            onClick={() => setSort("volume")}
            className={`text-xs px-3 py-1.5 rounded-lg transition-colors ${
              sort === "volume" ? "bg-skyblue/20 text-skyblue" : "text-gray-400 hover:text-white hover:bg-white/5"
            }`}
          >
            거래대금 기준
          </button>
        </div>
      </div>

      <div className="flex gap-1 mb-3">
        <button
          type="button"
          onClick={() => setPeriod("daily")}
          className={`text-xs px-4 py-1.5 rounded-lg border transition-colors ${
            period === "daily"
              ? "bg-white/15 border-white/30 text-white font-medium"
              : "border-white/10 text-gray-400 hover:text-white hover:bg-white/5"
          }`}
        >
          오늘 기준
        </button>
        <button
          type="button"
          onClick={() => setPeriod("weekly")}
          className={`text-xs px-4 py-1.5 rounded-lg border transition-colors ${
            period === "weekly"
              ? "bg-white/15 border-white/30 text-white font-medium"
              : "border-white/10 text-gray-400 hover:text-white hover:bg-white/5"
          }`}
        >
          주간 기준
        </button>
      </div>

      {loading ? (
        <ThemeSkeleton />
      ) : error ? (
        <div className="w-full h-32 bg-white/5 border border-white/10 rounded-xl flex items-center justify-center text-gray-400 text-sm">
          {error}
        </div>
      ) : treemapData.length === 0 ? (
        <div className="w-full h-32 bg-white/5 border border-white/10 rounded-xl flex items-center justify-center text-gray-400 text-sm">
          거래 데이터를 불러올 수 없습니다
        </div>
      ) : (
        <div className="w-full h-[480px] bg-white/5 border border-white/10 rounded-xl overflow-hidden p-1">
          <ResponsiveContainer width="100%" height="100%">
            <Treemap
              data={treemapData}
              dataKey="value"
              aspectRatio={4 / 3}
              content={(props) => <ThemeTreemapContent {...props} />}
            />
          </ResponsiveContainer>
        </div>
      )}
    </section>
  );
}
