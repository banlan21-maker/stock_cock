"use client";

import type { MarketIndex } from "@/types";

interface MarketOverviewProps {
  marketSummary: Record<string, MarketIndex>;
}

export default function MarketOverview({ marketSummary }: MarketOverviewProps) {
  return (
    <div className="grid grid-cols-2 gap-4">
      {Object.entries(marketSummary).map(([key, idx]) => (
        <div key={key} className="bg-white/5 border border-white/10 rounded-xl p-4">
          <p className="text-sm text-gray-400 uppercase">{key}</p>
          <p className="text-2xl font-bold">{idx.value.toLocaleString()}</p>
          <p
            className={`text-sm font-medium ${
              idx.change_rate > 0
                ? "text-green-400"
                : idx.change_rate < 0
                  ? "text-red-400"
                  : "text-gray-400"
            }`}
          >
            {idx.change_rate > 0 ? "+" : ""}
            {idx.change_rate}%
          </p>
        </div>
      ))}
    </div>
  );
}
