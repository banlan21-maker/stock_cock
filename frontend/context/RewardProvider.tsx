"use client";

import React, { createContext, useContext, useState, useCallback } from "react";

interface RewardContextType {
    requestReward: (onEarned: () => void) => void;
}

const RewardContext = createContext<RewardContextType | undefined>(undefined);

export function RewardProvider({ children }: { children: React.ReactNode }) {
    const [activeRequest, setActiveRequest] = useState<{ onEarned: () => void } | null>(null);

    const requestReward = useCallback((onEarned: () => void) => {
        setActiveRequest({ onEarned });
    }, []);

    const handleEarned = () => {
        if (activeRequest) {
            activeRequest.onEarned();
            setActiveRequest(null);
        }
    };

    const handleClose = () => {
        setActiveRequest(null);
    };

    return (
        <RewardContext.Provider value={{ requestReward }}>
            {children}
            {activeRequest && (
                <RewardAdModal
                    onEarned={handleEarned}
                    onClose={handleClose}
                />
            )}
        </RewardContext.Provider>
    );
}

export function useReward() {
    const context = useContext(RewardContext);
    if (context === undefined) {
        throw new Error("useReward must be used within a RewardProvider");
    }
    return context;
}

function RewardAdModal({ onEarned, onClose }: { onEarned: () => void, onClose: () => void }) {
    const [seconds, setSeconds] = useState(5); // 보상형 광고 시뮬레이션: 5초 (원래 30초지만 테스트용으로 5초)
    const [isAdEnded, setIsAdEnded] = useState(false);

    React.useEffect(() => {
        if (seconds <= 0) {
            setIsAdEnded(true);
            return;
        }
        const timer = setInterval(() => {
            setSeconds((s) => s - 1);
        }, 1000);
        return () => clearInterval(timer);
    }, [seconds]);

    return (
        <div className="fixed inset-0 z-[200] flex items-center justify-center bg-black/95 backdrop-blur-md">
            <div className="w-full max-w-md bg-navy-light border border-white/20 rounded-3xl overflow-hidden shadow-2xl flex flex-col p-8 text-center">
                <div className="mb-6">
                    <div className="inline-block px-3 py-1 bg-amber-500/20 text-amber-500 text-[10px] font-bold rounded-full mb-4">
                        REWARD AD
                    </div>
                    <h2 className="text-2xl font-bold text-white mb-2">무료 AI 분석 시청 중</h2>
                    <p className="text-gray-400 text-sm">광고를 시청하면 즉시 꼰대아저씨의 분석 결과를 확인하실 수 있습니다.</p>
                </div>

                {/* 광고 시뮬레이션 영역 */}
                <div className="flex-1 bg-black/40 rounded-2xl aspect-video flex flex-col items-center justify-center mb-8 border border-white/5 relative overflow-hidden">
                    <div className="absolute inset-x-0 bottom-0 h-1 bg-white/10">
                        <div
                            className="h-full bg-blue-500 transition-all duration-1000"
                            style={{ width: `${(1 - seconds / 5) * 100}%` }}
                        />
                    </div>

                    {!isAdEnded ? (
                        <div className="flex flex-col items-center gap-4">
                            <div className="w-12 h-12 rounded-full border-2 border-blue-500 border-t-transparent animate-spin"></div>
                            <span className="text-blue-500 font-mono text-xl">{seconds}s</span>
                        </div>
                    ) : (
                        <div className="flex flex-col items-center gap-3 animate-in zoom-in duration-300">
                            <div className="w-16 h-16 bg-green-500 rounded-full flex items-center justify-center text-3xl">✓</div>
                            <span className="text-green-500 font-bold">시청 완료!</span>
                        </div>
                    )}
                </div>

                <div className="flex gap-4">
                    <button
                        onClick={onClose}
                        className="flex-1 py-3 bg-white/5 text-gray-400 rounded-xl text-sm font-medium hover:bg-white/10 transition-colors"
                    >
                        건너뛰기 (분석 취소)
                    </button>

                    <button
                        onClick={isAdEnded ? onEarned : undefined}
                        disabled={!isAdEnded}
                        className={`flex-1 py-3 rounded-xl text-sm font-bold transition-all ${isAdEnded
                                ? "bg-blue-600 text-white hover:bg-blue-700 shadow-lg shadow-blue-500/20 active:scale-95"
                                : "bg-gray-700 text-gray-500 cursor-not-allowed"
                            }`}
                    >
                        {isAdEnded ? "분석 결과 보기" : "시청 중..."}
                    </button>
                </div>
            </div>
        </div>
    );
}
