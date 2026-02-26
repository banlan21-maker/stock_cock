"use client";

import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend } from "recharts";
import type { PortfolioHolding } from "@/types";

interface Props {
  holdings: PortfolioHolding[];
}

const COLORS = [
  "#38bdf8", "#818cf8", "#34d399", "#fb923c", "#f472b6", "#a3e635",
];

export default function PortfolioPieChart({ holdings }: Props) {
  const holdingsWithEval = holdings.filter((h) => h.eval_amount !== null && h.eval_amount > 0);
  if (holdingsWithEval.length === 0) return null;

  const totalEval = holdingsWithEval.reduce((sum, h) => sum + (h.eval_amount ?? 0), 0);

  // 상위 4개 + 기타
  const sorted = [...holdingsWithEval].sort(
    (a, b) => (b.eval_amount ?? 0) - (a.eval_amount ?? 0)
  );

  let chartData: { name: string; value: number }[] = [];
  if (sorted.length <= 5) {
    chartData = sorted.map((h) => ({
      name: h.stock_name,
      value: Math.round(((h.eval_amount ?? 0) / totalEval) * 100 * 10) / 10,
    }));
  } else {
    const top4 = sorted.slice(0, 4);
    const rest = sorted.slice(4);
    const restValue = rest.reduce((sum, h) => sum + (h.eval_amount ?? 0), 0);
    chartData = [
      ...top4.map((h) => ({
        name: h.stock_name,
        value: Math.round(((h.eval_amount ?? 0) / totalEval) * 100 * 10) / 10,
      })),
      {
        name: "기타",
        value: Math.round((restValue / totalEval) * 100 * 10) / 10,
      },
    ];
  }

  return (
    <div className="bg-white/5 border border-white/10 rounded-xl p-5">
      <h3 className="text-sm text-gray-400 mb-4">종목 비중</h3>
      <ResponsiveContainer width="100%" height={220}>
        <PieChart>
          <Pie
            data={chartData}
            cx="50%"
            cy="50%"
            innerRadius={55}
            outerRadius={85}
            paddingAngle={2}
            dataKey="value"
          >
            {chartData.map((_, i) => (
              <Cell key={i} fill={COLORS[i % COLORS.length]} />
            ))}
          </Pie>
          <Tooltip
            formatter={(value: any) => [`${value}%`, "비중"]}
            contentStyle={{
              backgroundColor: "#1a1a2e",
              border: "1px solid rgba(255,255,255,0.1)",
              borderRadius: "8px",
              fontSize: "12px",
              color: "#ffffff",
            }}
            labelStyle={{ color: "#ffffff" }}
            itemStyle={{ color: "#d1d5db" }}
          />
          <Legend
            iconType="circle"
            iconSize={8}
            formatter={(value) => (
              <span style={{ fontSize: "12px", color: "#9ca3af" }}>{value}</span>
            )}
          />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
}
