"use client";

import { Search } from "lucide-react";

interface StockSearchBarProps {
  query: string;
  onQueryChange: (value: string) => void;
  onSubmit: (e: React.FormEvent) => void;
}

export default function StockSearchBar({
  query,
  onQueryChange,
  onSubmit,
}: StockSearchBarProps) {
  return (
    <form onSubmit={onSubmit} className="relative">
      <Search className="absolute left-4 top-3.5 w-5 h-5 text-gray-400" />
      <input
        type="text"
        value={query}
        onChange={(e) => onQueryChange(e.target.value)}
        placeholder="종목명 또는 코드를 입력하세요 (예: 삼성전자, 005930)"
        className="w-full pl-12 pr-4 py-3 bg-white/5 border border-white/10 rounded-xl focus:outline-none focus:ring-2 focus:ring-skyblue text-white placeholder-gray-500"
      />
    </form>
  );
}
