import Link from "next/link";
import { Rocket, Globe, Search, FileText, Lightbulb, PieChart } from "lucide-react";

const cardClass = "bg-white/10 py-3 px-4 rounded-xl border border-white/20 backdrop-blur-sm hover:bg-white/15 transition-colors text-left";

const menuItems = [
  { href: "/dashboard", label: "시작", icon: Rocket, desc: "대시보드에서 오늘의 시장을 한눈에", highlight: true },
  { href: "/issues", label: "이슈콕", icon: Globe, desc: "오늘의 핫한 국·내외 뉴스 확인하기", highlight: false },
  { href: "/policy", label: "정책콕", icon: Search, desc: "대한민국 정책 수혜주 찾기", highlight: false },
  { href: "/disclosure", label: "공시콕", icon: FileText, desc: "상장기업 공시 정보 한눈에 보기", highlight: false },
  { href: "/stock", label: "종목콕", icon: Lightbulb, desc: "AI가 분석하는 종목 리포트", highlight: false },
  { href: "/portfolio", label: "포트폴리오", icon: PieChart, desc: "보유 종목 관리 및 AI 진단", highlight: false },
];

export default function Home() {
  return (
    <div className="min-h-screen bg-navy text-white flex flex-col items-center justify-center p-4">
      <main className="flex flex-col gap-3 items-center text-center w-full max-w-sm">
        <h1 className="text-3xl font-bold tracking-tighter text-sky-400">
          주식콕 Stock Cock
        </h1>
        <p className="text-base text-gray-300 max-w-md">
          복잡한 주식 정보, <span className="text-skyblue font-bold">콕</span> 집어 알려드려요.
        </p>

        <div className="grid grid-cols-1 w-full gap-2 mt-2">
          {menuItems.map(({ href, label, icon: Icon, desc, highlight }) => (
            <Link key={href} href={href} className={`${cardClass} ${highlight ? "border-skyblue/40" : ""}`}>
              <h2 className="text-sm font-bold mb-0.5 flex items-center gap-2">
                <Icon className="w-4 h-4 text-skyblue" />
                {label}
              </h2>
              <p className="text-xs text-gray-400">{desc}</p>
            </Link>
          ))}
        </div>
      </main>
    </div>
  );
}
