/**
 * 대시보드 '내 관심 키워드' 공유 유틸
 * 저장 키: "stockcock_custom_keywords"
 * 포맷 : { kw1: string, kw2: string }
 */

const STORAGE_KEY = "stockcock_custom_keywords";

export interface CustomKeywords {
  kw1: string;
  kw2: string;
}

export function getCustomKeywords(): CustomKeywords {
  if (typeof window === "undefined") return { kw1: "", kw2: "" };
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved) {
      const parsed = JSON.parse(saved) as Partial<CustomKeywords>;
      return { kw1: parsed.kw1 ?? "", kw2: parsed.kw2 ?? "" };
    }
  } catch {
    // ignore
  }
  return { kw1: "", kw2: "" };
}

/** 쉼표 구분 키워드 문자열 반환. 없으면 "" */
export function getCustomKeywordsQuery(): string {
  const { kw1, kw2 } = getCustomKeywords();
  return [kw1, kw2].filter((k) => k.trim()).join(",");
}

export function setCustomKeywords(kw1: string, kw2: string): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({ kw1: kw1.trim(), kw2: kw2.trim() }));
  } catch {
    // ignore
  }
}

export function clearCustomKeywords(): void {
  try {
    localStorage.removeItem(STORAGE_KEY);
  } catch {
    // ignore
  }
}
