"use client";

import { useState, useEffect, useCallback } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from "recharts";
import { fetchPortfolioPerformance } from "@/lib/portfolio";
import type { PortfolioPerformanceResponse } from "@/types";

type Period = { label: string; days: number };

const PERIODS: Period[] = [
  { label: "1M", days: 30 },
  { label: "3M", days: 90 },
  { label: "6M", days: 180 },
  { label: "1Y", days: 365 },
];

interface ChartPoint {
  date: string;
  portfolio: number;
}

function formatDate(dateStr: string): string {
  const d = new Date(dateStr);
  return `${d.getMonth() + 1}/${d.getDate()}`;
}

function formatReturn(value: number): string {
  const sign = value >= 0 ? "+" : "";
  return `${sign}${value.toFixed(2)}%`;
}

interface CustomTooltipProps {
  active?: boolean;
  payload?: Array<{ name: string; value: number; color: string }>;
  label?: string;
}

function CustomTooltip({ active, payload, label }: CustomTooltipProps) {
  if (!active || !payload || payload.length === 0) return null;
  return (
    <div className="bg-[#1a1a2e] border border-white/10 rounded-lg p-3 text-xs shadow-lg">
      <p className="text-gray-400 mb-2">{label}</p>
      {payload.map((entry) => (
        <p key={entry.name} style={{ color: entry.color }} className="font-medium">
          {entry.name}: {formatReturn(entry.value)}
        </p>
      ))}
    </div>
  );
}

export default function PortfolioReturnChart() {
  const [days, setDays] = useState(90);
  const [data, setData] = useState<ChartPoint[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [latestPortfolio, setLatestPortfolio] = useState<number | null>(null);

  const load = useCallback(async (d: number) => {
    setLoading(true);
    setError(null);
    try {
      const res: PortfolioPerformanceResponse = await fetchPortfolioPerformance(d);
      if (res.dates.length === 0) {
        setData([]);
        return;
      }
      const points: ChartPoint[] = res.dates.map((date, i) => ({
        date: formatDate(date),
        portfolio: res.portfolio[i],
      }));
      setData(points);
      setLatestPortfolio(res.portfolio[res.portfolio.length - 1] ?? null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "데이터 불러오기 실패");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load(days);
  }, [days, load]);

  function handlePeriod(d: number) {
    setDays(d);
  }

  return (
    <div className="bg-white/5 border border-white/10 rounded-xl p-5">
      {/* 헤더 */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-4">
          <h3 className="text-sm text-gray-400">수익률 추이</h3>
          {!loading && !error && latestPortfolio !== null && (
            <div className="flex items-center gap-3 text-xs">
              <span
                className={
                  latestPortfolio >= 0
                    ? "text-red-400 font-semibold"
                    : "text-blue-400 font-semibold"
                }
              >
                내 포트폴리오 {formatReturn(latestPortfolio)}
              </span>
            </div>
          )}
        </div>
        {/* 기간 탭 */}
        <div className="flex gap-1">
          {PERIODS.map((p) => (
            <button
              key={p.days}
              onClick={() => handlePeriod(p.days)}
              className={`px-2.5 py-1 rounded text-xs font-medium transition-colors ${
                days === p.days
                  ? "bg-white/15 text-white"
                  : "text-gray-400 hover:text-white hover:bg-white/8"
              }`}
            >
              {p.label}
            </button>
          ))}
        </div>
      </div>

      {/* 차트 영역 */}
      {loading ? (
        <div className="h-[200px] flex items-center justify-center text-gray-500 text-sm">
          불러오는 중...
        </div>
      ) : error ? (
        <div className="h-[200px] flex items-center justify-center text-red-400 text-sm">
          {error}
        </div>
      ) : data.length === 0 ? (
        <div className="h-[200px] flex items-center justify-center text-gray-500 text-sm">
          차트 데이터가 없습니다.
        </div>
      ) : (
        <ResponsiveContainer width="100%" height={200}>
          <LineChart data={data} margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
            <XAxis
              dataKey="date"
              tick={{ fontSize: 10, fill: "#6b7280" }}
              tickLine={false}
              axisLine={false}
              interval="preserveStartEnd"
            />
            <YAxis
              tick={{ fontSize: 10, fill: "#6b7280" }}
              tickLine={false}
              axisLine={false}
              tickFormatter={(v: number) => `${v >= 0 ? "+" : ""}${v.toFixed(1)}%`}
              width={52}
            />
            <ReferenceLine y={0} stroke="rgba(255,255,255,0.15)" strokeDasharray="4 4" />
            <Tooltip content={<CustomTooltip />} />
            <Line
              type="monotone"
              dataKey="portfolio"
              name="내 포트폴리오"
              stroke="#38bdf8"
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4, fill: "#38bdf8" }}
            />
          </LineChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}
