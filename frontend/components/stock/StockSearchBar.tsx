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
      <input
        type="text"
        value={query}
        onChange={(e) => onQueryChange(e.target.value)}
        placeholder="종목명 또는 코드를 입력하세요 (예: 삼성전자, 005930)"
        className="w-full pl-4 pr-12 py-3 bg-white/5 border border-white/10 rounded-xl focus:outline-none focus:ring-2 focus:ring-skyblue text-white placeholder-gray-500"
      />
      <button
        type="submit"
        className="absolute right-3 top-2.5 p-1 text-gray-400 hover:text-skyblue transition-colors"
        aria-label="검색"
      >
        <Search className="w-5 h-5" />
      </button>
    </form>
  );
}
