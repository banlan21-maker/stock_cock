"use client";

import Script from "next/script";
import { useEffect, useRef, useState } from "react";

const AD_HEIGHT_PX = 60;
/** 배너 최소 너비 - availableWidth=0 방지 */
const AD_MIN_WIDTH_PX = 50;

/** Google 공식 테스트 광고 단위 ID (개발 환경용) */
const TEST_AD_CLIENT = "ca-pub-3940256099942544";
const TEST_AD_SLOT = "6300978111";

/** 현재는 테스트 광고만 사용. 실제 광고 전환 시 .env.local의 NEXT_PUBLIC_ADMOB_BANNER_ID 사용하도록 복원 */
function getAdConfig() {
  return {
    client: TEST_AD_CLIENT,
    slot: TEST_AD_SLOT,
    isTest: true,
  };
}

export const AD_BANNER_HEIGHT = AD_HEIGHT_PX;

export default function AdBanner() {
  const pushed = useRef(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const insRef = useRef<HTMLModElement>(null);
  const [scriptReady, setScriptReady] = useState(false);
  const [adFilled, setAdFilled] = useState(false);
  const { client, slot, isTest } = getAdConfig();

  useEffect(() => {
    if (!scriptReady || pushed.current) return;
    const el = containerRef.current;
    if (!el) return;

    const tryPush = () => {
      const width = el.offsetWidth || el.getBoundingClientRect().width;
      if (width < 1) return false;
      try {
        (window as unknown as { adsbygoogle: unknown[] }).adsbygoogle =
          (window as unknown as { adsbygoogle?: unknown[] }).adsbygoogle || [];
        (window as unknown as { adsbygoogle: unknown[] }).adsbygoogle.push({});
        pushed.current = true;
        return true;
      } catch (e) {
        console.error("[AdBanner]", e);
        return false;
      }
    };

    let timeoutId: ReturnType<typeof setTimeout> | undefined;
    const rafId = requestAnimationFrame(() => {
      if (tryPush()) return;
      timeoutId = setTimeout(tryPush, 150);
    });
    return () => {
      cancelAnimationFrame(rafId);
      if (timeoutId != null) clearTimeout(timeoutId);
    };
  }, [scriptReady]);

  // data-ad-status="filled" 감지 → placeholder 숨김
  useEffect(() => {
    const ins = insRef.current;
    if (!ins) return;
    const observer = new MutationObserver(() => {
      if (ins.dataset.adStatus === "filled") {
        setAdFilled(true);
      }
    });
    observer.observe(ins, { attributes: true, attributeFilter: ["data-ad-status"] });
    return () => observer.disconnect();
  }, []);

  return (
    <>
      <Script
        src={`https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=${client}`}
        strategy="afterInteractive"
        crossOrigin="anonymous"
        onReady={() => setScriptReady(true)}
      />
      <div
        ref={containerRef}
        className="ad-banner-slot fixed bottom-0 left-0 right-0 z-40 flex justify-center items-center bg-navy/95 border-t border-white/10 w-full min-w-[320px] overflow-hidden"
        style={{ height: `${AD_HEIGHT_PX}px`, width: "100%" }}
        aria-label="광고"
      >
        <ins
          ref={insRef}
          className="adsbygoogle relative z-10 ad-banner-ins"
          style={{
            display: "block",
            width: "100%",
            minWidth: `${AD_MIN_WIDTH_PX}px`,
            height: `${AD_HEIGHT_PX}px`,
          }}
          data-ad-client={client}
          data-ad-slot={slot}
          data-ad-format="horizontal"
          data-full-width-responsive="false"
          {...(isTest ? { "data-ad-test": "on" } : {})}
        />
        {/* 광고 미로드 시 보이는 플레이스홀더 */}
        {isTest && !adFilled && (
          <div
            className="absolute inset-0 flex items-center justify-center text-gray-500 text-xs pointer-events-none z-0"
            aria-hidden
          >
            테스트 광고 로딩 중...
          </div>
        )}
      </div>
    </>
  );
}
