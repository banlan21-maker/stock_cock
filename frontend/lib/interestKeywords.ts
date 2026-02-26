/** 관심 키워드: 로그인 전에는 localStorage, 로그인 후에는 사용자 설정 사용 예정 */

const STORAGE_KEY = "stockcock_interest_keywords";
const ONBOARDING_KEY = "stockcock_onboarding_done";

/** 기본 키워드 목록 (id: API/필터용, label: 표시용) */
export const INTEREST_KEYWORDS = [
  { id: "ai", label: "AI" },
  { id: "robot", label: "로봇" },
  { id: "quantum", label: "양자컴퓨터" },
  { id: "superconductor", label: "초전도체" },
  { id: "bio", label: "바이오" },
  { id: "space", label: "우주관련" },
  { id: "smr", label: "SMR (소형 모듈 원자로)" },
  { id: "power_infra", label: "전력 인프라 (변압기, 구리)" },
  { id: "k_defense", label: "K-방산 (방위산업)" },
  { id: "battery_recycle", label: "폐배터리 및 자원 재활용" },
  { id: "silver_tech", label: "실버 테크 (안티에이징/디지털 헬스케어)" },
] as const;

export type InterestKeywordId = (typeof INTEREST_KEYWORDS)[number]["id"];

const MAX_SELECTION = 2;

export function getInterestKeywords(): InterestKeywordId[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as unknown;
    if (!Array.isArray(parsed)) return [];
    return parsed.filter((k): k is InterestKeywordId =>
      typeof k === "string" && INTEREST_KEYWORDS.some((kw) => kw.id === k)
    ).slice(0, MAX_SELECTION);
  } catch {
    return [];
  }
}

export function setInterestKeywords(ids: InterestKeywordId[]): void {
  if (typeof window === "undefined") return;
  const trimmed = ids.slice(0, MAX_SELECTION);
  localStorage.setItem(STORAGE_KEY, JSON.stringify(trimmed));
}

export function hasCompletedOnboarding(): boolean {
  if (typeof window === "undefined") return false;
  try {
    return localStorage.getItem(ONBOARDING_KEY) === "1";
  } catch {
    return false;
  }
}

export function setOnboardingCompleted(): void {
  if (typeof window === "undefined") return;
  localStorage.setItem(ONBOARDING_KEY, "1");
}

export function setOnboardingNotCompleted(): void {
  if (typeof window === "undefined") return;
  localStorage.removeItem(ONBOARDING_KEY);
}

export function clearInterestKeywords(): void {
  if (typeof window === "undefined") return;
  localStorage.removeItem(STORAGE_KEY);
}

export function getInterestKeywordsQuery(): string {
  return getInterestKeywords().join(",");
}

export { MAX_SELECTION };
