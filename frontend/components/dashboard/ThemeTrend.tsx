"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { Treemap, ResponsiveContainer } from "recharts";
import { X, ExternalLink } from "lucide-react";
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
  totalVolume?: number;
  sortMode?: SortMode;
  fillColor?: string;
}

function truncateText(text: string, maxLen: number): string {
  if (text.length <= maxLen) return text;
  return text.slice(0, maxLen - 1) + "…";
}

function formatVolume(volume: number): string {
  if (volume >= 1_000_000_000_000) return `${(volume / 1_000_000_000_000).toFixed(1)}조`;
  if (volume >= 100_000_000_000) return `${Math.round(volume / 100_000_000_000) * 1000}억`.replace(/(\d)(?=(\d{3})+(?!\d))/g, "$1,");
  if (volume >= 100_000_000) return `${Math.round(volume / 100_000_000)}억`;
  if (volume >= 10_000_000) return `${Math.round(volume / 10_000_000)}천만`;
  return `${Math.round(volume / 1_000_000)}백만`;
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
    totalVolume = 0,
    sortMode = "change_rate",
    fillColor = "#ef4444",
  } = props;
  if (depth === 0 || width < 15 || height < 12) return null;

  const fontSize = Math.min(14, Math.max(10, width / 6));
  const showText = width > 28 && height > 20;
  const maxNameLen = Math.max(2, Math.floor(width / (fontSize * 0.85)));
  const displayName = truncateText(name, maxNameLen);
  const showRate = height > 40;
  const subStr = sortMode === "volume"
    ? formatVolume(totalVolume)
    : `${avgChangeRate > 0 ? "+" : ""}${Number(avgChangeRate).toFixed(2)}%`;

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
              {subStr}
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
  const [selectedGroup, setSelectedGroup] = useState<ThemeGroup | null>(null);

  useEffect(() => {
    setLoading(true);
    setError("");
    setResponse(null);
    setSelectedGroup(null);
    fetchThemeTrend(sort, period)
      .then(setResponse)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [sort, period]);

  function handleTreemapClick(data: { name?: string }) {
    if (!data.name) return;
    const group = groups.find((g) => g.theme === data.name);
    setSelectedGroup((prev) =>
      prev?.theme === data.name ? null : (group ?? null)
    );
  }

  const groups: ThemeGroup[] = response?.groups ?? [];
  const subtitle = response?.trade_date
    ? `${response.trade_date} 기준 · 최근 거래일`
    : "최근 거래일 기준";

  const treemapData = groups.map((g) => ({
    name: g.theme,
    value: Math.max(g.total_volume, 1),
    avgChangeRate: Number(g.avg_change_rate),
    totalVolume: g.total_volume,
    sortMode: sort,
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
        <>
          <p className="text-xs text-gray-500 mb-2">테마를 클릭하면 관련 종목을 확인할 수 있어요</p>
          <div className="w-full h-[480px] bg-white/5 border border-white/10 rounded-xl overflow-hidden p-1 cursor-pointer">
            <ResponsiveContainer width="100%" height="100%">
              <Treemap
                data={treemapData}
                dataKey="value"
                aspectRatio={4 / 3}
                content={(props) => <ThemeTreemapContent {...props} />}
                onClick={handleTreemapClick}
              />
            </ResponsiveContainer>
          </div>

          {selectedGroup && (
            <div className="mt-3 bg-white/5 border border-skyblue/30 rounded-xl p-4">
              <div className="flex items-center justify-between mb-3">
                <div>
                  <h3 className="font-semibold text-sm">{selectedGroup.theme}</h3>
                  <p className="text-xs text-gray-400">
                    테마 평균{" "}
                    <span className={Number(selectedGroup.avg_change_rate) >= 0 ? "text-red-400" : "text-blue-400"}>
                      {Number(selectedGroup.avg_change_rate) > 0 ? "+" : ""}
                      {Number(selectedGroup.avg_change_rate).toFixed(2)}%
                    </span>
                  </p>
                </div>
                <div className="flex items-center gap-3">
                  <Link
                    href="/issues"
                    className="text-xs text-skyblue hover:underline flex items-center gap-1"
                  >
                    관련 뉴스 <ExternalLink className="w-3 h-3" />
                  </Link>
                  <button
                    onClick={() => setSelectedGroup(null)}
                    className="text-gray-500 hover:text-white transition-colors"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-2">
                {selectedGroup.stocks.map((stock) => (
                  <Link
                    key={stock.code}
                    href={`/stock/${stock.code}`}
                    className="flex items-center justify-between p-2.5 bg-white/5 hover:bg-white/10 rounded-lg transition-colors"
                  >
                    <div className="min-w-0">
                      <p className="text-xs font-medium truncate">{stock.name}</p>
                      <p className="text-xs text-gray-500">{stock.code}</p>
                    </div>
                    <p
                      className={`text-xs font-bold ml-2 shrink-0 ${
                        stock.change_rate > 0
                          ? "text-red-400"
                          : stock.change_rate < 0
                          ? "text-blue-400"
                          : "text-gray-400"
                      }`}
                    >
                      {stock.change_rate > 0 ? "+" : ""}
                      {Number(stock.change_rate).toFixed(2)}%
                    </p>
                  </Link>
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </section>
  );
}
