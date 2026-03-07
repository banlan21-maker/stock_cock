"use client";

import { useState, useEffect } from "react";
import { X, TrendingUp, Search, BarChart2 } from "lucide-react";

const STORAGE_KEY = "stockcock_onboarding_seen";

const STEPS = [
  {
    icon: TrendingUp,
    color: "text-amber-400",
    bg: "bg-amber-400/10 border-amber-400/20",
    step: "1단계",
    title: "오늘 이슈 파악",
    desc: "대시보드에서 오늘의 테마 트렌드와 시장 흐름을 한눈에 확인하세요.",
  },
  {
    icon: Search,
    color: "text-sky-400",
    bg: "bg-sky-400/10 border-sky-400/20",
    step: "2단계",
    title: "종목 AI 분석",
    desc: "관심 종목을 검색해 AI가 주가·재무·수급을 콕 집어 분석해드려요.",
  },
  {
    icon: BarChart2,
    color: "text-emerald-400",
    bg: "bg-emerald-400/10 border-emerald-400/20",
    step: "3단계",
    title: "포트폴리오 진단",
    desc: "보유 종목을 등록하면 AI가 내 포트폴리오 전체를 진단해드려요.",
  },
];

export default function OnboardingGuide() {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    if (!localStorage.getItem(STORAGE_KEY)) {
      setVisible(true);
    }
  }, []);

  const dismiss = () => {
    localStorage.setItem(STORAGE_KEY, "1");
    setVisible(false);
  };

  if (!visible) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 px-4">
      <div className="relative w-full max-w-md bg-[#1a1f2e] border border-white/10 rounded-2xl p-6 shadow-2xl">
        <button
          onClick={dismiss}
          className="absolute top-4 right-4 text-gray-500 hover:text-white"
          aria-label="닫기"
        >
          <X className="w-5 h-5" />
        </button>

        <div className="mb-5">
          <p className="text-xs text-amber-400 font-semibold mb-1">주식콕 사용법</p>
          <h2 className="text-xl font-bold text-white">3단계로 투자 결정하기</h2>
          <p className="text-sm text-gray-400 mt-1">복잡한 주식 정보, 콕 집어 알려드려요.</p>
        </div>

        <div className="space-y-3 mb-6">
          {STEPS.map(({ icon: Icon, color, bg, step, title, desc }) => (
            <div key={step} className={`flex gap-4 p-4 rounded-xl border ${bg}`}>
              <div className={`mt-0.5 shrink-0 ${color}`}>
                <Icon className="w-5 h-5" />
              </div>
              <div>
                <p className={`text-xs font-semibold mb-0.5 ${color}`}>{step}</p>
                <p className="text-sm font-bold text-white">{title}</p>
                <p className="text-xs text-gray-400 mt-0.5">{desc}</p>
              </div>
            </div>
          ))}
        </div>

        <button
          onClick={dismiss}
          className="w-full py-3 rounded-xl bg-amber-400 hover:bg-amber-300 text-black font-bold text-sm transition-colors"
        >
          시작하기
        </button>
      </div>
    </div>
  );
}
