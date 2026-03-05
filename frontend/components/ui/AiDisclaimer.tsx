import { AlertTriangle } from "lucide-react";

const TEXT =
  "주식콕 AI의 분석은 데이터에 기반한 예측일 뿐, 수익을 보장하지 않습니다. 투자는 반드시 본인의 책임하에 진행하세요.";

/** Footer용 - 아주 작은 회색 텍스트 */
export function AiDisclaimerFooter() {
  return (
    <p className="text-[10px] text-gray-600 leading-relaxed">{TEXT}</p>
  );
}

/** AI 분석 결과 하단용 - 빨간 경고 아이콘 + 텍스트 */
export default function AiDisclaimer() {
  return (
    <div className="flex items-start gap-2 mt-3 px-3 py-2.5 bg-red-500/5 border border-red-500/15 rounded-xl">
      <AlertTriangle className="w-3.5 h-3.5 text-red-400 shrink-0 mt-0.5" />
      <p className="text-[11px] text-red-300/70 leading-relaxed">{TEXT}</p>
    </div>
  );
}
