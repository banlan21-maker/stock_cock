import type { PortfolioSummary } from "@/types";

interface Props {
  summary: PortfolioSummary;
}

function fmt(n: number) {
  return n.toLocaleString("ko-KR");
}

export default function PortfolioSummaryCard({ summary }: Props) {
  const isPositive = summary.total_profit_loss >= 0;
  const colorClass = isPositive ? "text-red-400" : "text-blue-400";
  const sign = isPositive ? "+" : "";

  return (
    <div className="bg-white/5 border border-white/10 rounded-xl p-5">
      <h2 className="text-sm text-gray-400 mb-4">포트폴리오 요약</h2>
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <div>
          <p className="text-xs text-gray-500 mb-1">총 매입금액</p>
          <p className="text-lg font-semibold">₩{fmt(summary.total_invest)}</p>
        </div>
        <div>
          <p className="text-xs text-gray-500 mb-1">총 평가금액</p>
          <p className="text-lg font-semibold">₩{fmt(summary.total_eval)}</p>
        </div>
        <div>
          <p className="text-xs text-gray-500 mb-1">총 손익</p>
          <p className={`text-lg font-semibold ${colorClass}`}>
            {sign}₩{fmt(Math.abs(summary.total_profit_loss))}
          </p>
        </div>
        <div>
          <p className="text-xs text-gray-500 mb-1">수익률</p>
          <p className={`text-lg font-bold ${colorClass}`}>
            {sign}{summary.total_profit_rate.toFixed(2)}%
          </p>
        </div>
      </div>
    </div>
  );
}
