"use client";

import Link from "next/link";
import type { StockSearchResult } from "@/types";

interface StockSearchResultCardProps {
  stock: StockSearchResult;
}

export default function StockSearchResultCard({ stock }: StockSearchResultCardProps) {
  return (
    <Link
      href={`/stock/${stock.code}`}
      className="block bg-white/5 border border-white/10 rounded-xl p-4 hover:bg-white/10 transition-colors"
    >
      <div className="flex justify-between items-center">
        <div>
          <p className="font-medium">{stock.name}</p>
          <p className="text-xs text-gray-400">{stock.code}</p>
        </div>
        <span className="text-xs px-2 py-1 rounded-full bg-white/10 text-gray-300">
          {stock.market}
        </span>
      </div>
    </Link>
  );
}
