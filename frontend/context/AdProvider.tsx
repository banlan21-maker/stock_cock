"use client";

import React, { createContext, useContext, useState, useEffect, useCallback } from "react";
import { usePathname } from "next/navigation";

interface AdContextType {
    adCounter: number;
    incrementCounter: () => void;
    resetCounter: () => void;
    showInterstitial: boolean;
    requestInterstitial: (onClose?: () => void) => void;
    closeInterstitial: () => void;
}

const AdContext = createContext<AdContextType | undefined>(undefined);

export function AdProvider({ children }: { children: React.ReactNode }) {
    const [adCounter, setAdCounter] = useState(0);
    const [showInterstitial, setShowInterstitial] = useState(false);
    const [onCloseCallback, setOnCloseCallback] = useState<(() => void) | null>(null);
    const pathname = usePathname();
    const [lastPathname, setLastPathname] = useState(pathname);

    const incrementCounter = useCallback(() => {
        setAdCounter((prev) => {
            const next = prev + 1;
            if (next >= 5) {
                setShowInterstitial(true);
                setOnCloseCallback(null);
                return 0; // Reset after triggering
            }
            return next;
        });
    }, []);

    const requestInterstitial = useCallback((onClose?: () => void) => {
        setShowInterstitial(true);
        if (onClose) setOnCloseCallback(() => onClose);
        else setOnCloseCallback(null);
    }, []);

    const resetCounter = useCallback(() => setAdCounter(0), []);
    const closeInterstitial = useCallback(() => {
        setShowInterstitial(false);
        if (onCloseCallback) {
            onCloseCallback();
            setOnCloseCallback(null);
        }
    }, [onCloseCallback]);

    // Watch for navigation
    useEffect(() => {
        if (pathname !== lastPathname) {
            setLastPathname(pathname);
            incrementCounter();
        }
    }, [pathname, lastPathname, incrementCounter]);

    return (
        <AdContext.Provider
            value={{
                adCounter,
                incrementCounter,
                resetCounter,
                showInterstitial,
                requestInterstitial,
                closeInterstitial,
            }}
        >
            {children}
            {showInterstitial && <InterstitialAd onClose={closeInterstitial} />}
        </AdContext.Provider>
    );
}

export function useAd() {
    const context = useContext(AdContext);
    if (context === undefined) {
        throw new Error("useAd must be used within an AdProvider");
    }
    return context;
}

/** 
 * 테스트 전면 광고 (Interstitial) 모달 컴포넌트
 */
function InterstitialAd({ onClose }: { onClose: () => void }) {
    const [seconds, setSeconds] = useState(3);

    useEffect(() => {
        if (seconds <= 0) return;
        const timer = setInterval(() => {
            setSeconds((s) => s - 1);
        }, 1000);
        return () => clearInterval(timer);
    }, [seconds]);

    return (
        <div className="fixed inset-0 z-[100] flex flex-col items-center justify-center bg-black/90 backdrop-blur-sm animate-in fade-in duration-300">
            <div className="relative w-full max-w-sm aspect-[9/16] bg-navy-light rounded-2xl overflow-hidden border border-white/20 shadow-2xl flex flex-col items-center justify-center p-8 text-center">
                {/* 상단 닫기 알림 */}
                <div className="absolute top-4 right-4">
                    <button
                        onClick={seconds <= 0 ? onClose : undefined}
                        className={`px-3 py-1 rounded-full text-sm font-medium transition-colors ${seconds > 0
                            ? "bg-white/10 text-gray-400 cursor-not-allowed"
                            : "bg-blue-600 text-white hover:bg-blue-700 cursor-pointer"
                            }`}
                    >
                        {seconds > 0 ? `${seconds}초 후 닫기` : "닫기 ✕"}
                    </button>
                </div>

                {/* 광고 내용 시뮬레이션 */}
                <div className="flex-1 flex flex-col items-center justify-center gap-6">
                    <div className="w-20 h-20 bg-blue-500/20 rounded-3xl flex items-center justify-center">
                        <span className="text-4xl">🚀</span>
                    </div>
                    <div>
                        <h2 className="text-2xl font-bold text-white mb-2">프리미엄 주식 분석</h2>
                        <p className="text-gray-400 text-sm leading-relaxed">
                            지금 멤버십에 가입하고<br />
                            실시간 AI 급등주 알림을 받아보세요!
                        </p>
                    </div>
                    <div className="w-full h-40 bg-white/5 rounded-xl border border-white/10 flex items-center justify-center text-xs text-gray-500 italic">
                        [ Google 테스트 전면 광고 영역 ]
                    </div>
                    <button className="w-full py-3 bg-blue-600 rounded-xl font-bold text-white hover:bg-blue-700 transition-all active:scale-95">
                        자세히 보기
                    </button>
                </div>

                <p className="mt-6 text-[10px] text-gray-600 uppercase tracking-widest">Advertisement</p>
            </div>
        </div>
    );
}
