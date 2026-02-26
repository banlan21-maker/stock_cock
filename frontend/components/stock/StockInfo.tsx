"use client";

import Link from "next/link";
import { TrendingUp, TrendingDown, Minus, Star } from "lucide-react";
import type { StockPrice } from "@/types";

interface StockInfoProps {
  price: StockPrice;
  inWatchlist?: boolean;
  isLoggedIn?: boolean;
  userChecked?: boolean;
  watchlistLoading?: boolean;
  onToggleWatchlist?: () => void;
}

export default function StockInfo({
  price,
  inWatchlist = false,
  isLoggedIn = false,
  userChecked = false,
  watchlistLoading = false,
  onToggleWatchlist,
}: StockInfoProps) {
  const changeColor =
    price.change_rate > 0
      ? "text-green-400"
      : price.change_rate < 0
        ? "text-red-400"
        : "text-gray-400";
  const ChangeIcon =
    price.change_rate > 0 ? TrendingUp : price.change_rate < 0 ? TrendingDown : Minus;

  return (
    <div className="bg-white/5 border border-white/10 rounded-xl p-6">
      <div className="flex justify-between items-start">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold">{price.name}</h1>
            {userChecked &&
              (isLoggedIn ? (
                <button
                  type="button"
                  onClick={onToggleWatchlist}
                  disabled={watchlistLoading}
                  className={`p-1.5 rounded-lg transition-colors ${
                    inWatchlist ? "bg-amber-500/20 text-amber-400" : "bg-white/10 text-gray-400 hover:text-amber-400"
                  }`}
                  title={inWatchlist ? "관심 종목 해제" : "관심 종목 추가"}
                >
                  <Star className={`w-5 h-5 ${inWatchlist ? "fill-current" : ""}`} />
                </button>
              ) : (
                <Link
                  href="/login"
                  className="p-1.5 rounded-lg bg-white/10 text-gray-400 hover:text-amber-400 transition-colors"
                  title="로그인하면 관심 종목에 추가할 수 있어요"
                >
                  <Star className="w-5 h-5" />
                </Link>
              ))}
          </div>
          <p className="text-sm text-gray-400">{price.code}</p>
        </div>
        <div className="text-right">
          <p className="text-3xl font-bold">
            {price.current_price.toLocaleString()}
            <span className="text-sm text-gray-400">원</span>
          </p>
          <div className={`flex items-center justify-end gap-1 ${changeColor}`}>
            <ChangeIcon className="w-4 h-4" />
            <span className="font-medium">
              {price.change > 0 ? "+" : ""}
              {price.change.toLocaleString()} (
              {price.change_rate > 0 ? "+" : ""}
              {price.change_rate}%)
            </span>
          </div>
        </div>
      </div>
      <div className="grid grid-cols-3 gap-4 mt-4 pt-4 border-t border-white/10 text-sm">
        <div>
          <p className="text-gray-400">고가</p>
          <p className="font-medium">{price.high.toLocaleString()}</p>
        </div>
        <div>
          <p className="text-gray-400">저가</p>
          <p className="font-medium">{price.low.toLocaleString()}</p>
        </div>
        <div>
          <p className="text-gray-400">거래량</p>
          <p className="font-medium">{price.volume.toLocaleString()}</p>
        </div>
      </div>

      {/* 재무 지표 */}
      <div className="grid grid-cols-3 gap-4 mt-3 pt-3 border-t border-white/10 text-sm">
        <div>
          <p className="text-gray-400">PBR</p>
          <p className="font-medium">{price.pbr != null ? `${price.pbr}배` : "-"}</p>
        </div>
        <div>
          <p className="text-gray-400">ROE</p>
          <p className="font-medium">{price.roe != null ? `${price.roe}%` : "-"}</p>
        </div>
        <div>
          <p className="text-gray-400">부채비율</p>
          <p className="font-medium">{price.debt_ratio != null ? `${price.debt_ratio}%` : "-"}</p>
        </div>
        <div>
          <p className="text-gray-400">매출성장률</p>
          <p className="font-medium">{price.revenue_growth != null ? `${price.revenue_growth}%` : "-"}</p>
        </div>
        <div>
          <p className="text-gray-400">영업이익률</p>
          <p className="font-medium">{price.operating_margin != null ? `${price.operating_margin}%` : "-"}</p>
        </div>
        <div>
          <p className="text-gray-400">영업현금흐름</p>
          <p className="font-medium">
            {price.operating_cashflow != null
              ? `${(price.operating_cashflow / 1e8).toFixed(0)}억`
              : "-"}
          </p>
        </div>
      </div>
    </div>
  );
}
