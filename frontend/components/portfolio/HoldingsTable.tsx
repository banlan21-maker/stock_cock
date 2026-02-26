"use client";

import { useState } from "react";
import { Pencil, Trash2 } from "lucide-react";
import type { PortfolioHolding } from "@/types";
import Link from "next/link";

interface Props {
  holdings: PortfolioHolding[];
  totalEval: number;
  onEdit: (holding: PortfolioHolding) => void;
  onDelete: (id: string, name: string) => void;
}

function fmtNum(n: number | null) {
  if (n === null) return "-";
  return n.toLocaleString("ko-KR");
}

function fmtRate(n: number | null) {
  if (n === null) return "-";
  const sign = n >= 0 ? "+" : "";
  return `${sign}${n.toFixed(2)}%`;
}

export default function HoldingsTable({ holdings, totalEval, onEdit, onDelete }: Props) {
  const [hovered, setHovered] = useState<string | null>(null);

  if (holdings.length === 0) {
    return (
      <div className="bg-white/5 border border-white/10 rounded-xl p-8 text-center text-gray-400">
        <p className="mb-2">보유 종목이 없습니다.</p>
        <p className="text-sm">상단 버튼으로 종목을 추가해 보세요.</p>
      </div>
    );
  }

  return (
    <div className="bg-white/5 border border-white/10 rounded-xl overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-white/10 text-gray-400 text-xs">
              <th className="text-left px-4 py-3">종목</th>
              <th className="text-right px-3 py-3">수량</th>
              <th className="text-right px-3 py-3">매입가</th>
              <th className="text-right px-3 py-3">현재가</th>
              <th className="text-right px-3 py-3">손익</th>
              <th className="text-right px-3 py-3">수익률</th>
              <th className="text-right px-3 py-3">비중</th>
              <th className="px-3 py-3" />
            </tr>
          </thead>
          <tbody>
            {holdings.map((h) => {
              const isPos = (h.profit_rate ?? 0) >= 0;
              const colorClass = isPos ? "text-red-400" : "text-blue-400";
              const weight =
                totalEval > 0 && h.eval_amount !== null
                  ? ((h.eval_amount / totalEval) * 100).toFixed(1)
                  : "-";

              return (
                <tr
                  key={h.id}
                  className="border-b border-white/5 hover:bg-white/5 transition-colors"
                  onMouseEnter={() => setHovered(h.id)}
                  onMouseLeave={() => setHovered(null)}
                >
                  <td className="px-4 py-3">
                    <Link
                      href={`/stock/${h.stock_code}`}
                      className="hover:text-skyblue transition-colors"
                    >
                      <p className="font-medium">{h.stock_name}</p>
                      <p className="text-xs text-gray-500">{h.stock_code}</p>
                    </Link>
                  </td>
                  <td className="text-right px-3 py-3">{fmtNum(h.quantity)}</td>
                  <td className="text-right px-3 py-3">{fmtNum(h.avg_price)}</td>
                  <td className="text-right px-3 py-3">
                    {h.current_price !== null ? fmtNum(h.current_price) : (
                      <span className="text-gray-500">-</span>
                    )}
                  </td>
                  <td className={`text-right px-3 py-3 ${colorClass}`}>
                    {fmtNum(h.profit_loss)}
                  </td>
                  <td className={`text-right px-3 py-3 font-medium ${colorClass}`}>
                    {fmtRate(h.profit_rate)}
                  </td>
                  <td className="text-right px-3 py-3 text-gray-400">
                    {weight !== "-" ? `${weight}%` : "-"}
                  </td>
                  <td className="px-3 py-3">
                    <div
                      className={`flex gap-1 justify-end transition-opacity ${
                        hovered === h.id ? "opacity-100" : "opacity-0"
                      }`}
                    >
                      <button
                        onClick={() => onEdit(h)}
                        className="p-1 hover:text-skyblue transition-colors"
                        title="수정"
                      >
                        <Pencil className="w-3.5 h-3.5" />
                      </button>
                      <button
                        onClick={() => onDelete(h.id, h.stock_name)}
                        className="p-1 hover:text-red-400 transition-colors"
                        title="삭제"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
