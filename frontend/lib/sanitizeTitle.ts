/** 뉴스 제목 정제: HTML 엔티티 디코딩, 불필요한 [태그] 제거 (프론트 방어) */
export function sanitizeNewsTitle(raw: string | undefined): string {
  if (!raw || typeof raw !== "string") return "";
  let s = raw.trim();
  s = s.replace(/&quot;/g, '"').replace(/&amp;/g, "&").replace(/&lt;/g, "<").replace(/&gt;/g, ">").replace(/&#39;/g, "'");
  s = s.replace(/^[\s\u3000]*\[[^\]]*\]\s*/, "");
  s = s.replace(/\s+/g, " ");
  return s.trim();
}
