"use client";

import { Sparkles, Rocket } from "lucide-react";
import { sanitizeNewsTitle } from "@/lib/sanitizeTitle";

interface AiSummaryProps {
  title: string;
  aiSummary: string;
  url?: string | null;
}

/** AI 분석 텍스트를 섹션별로 파싱 */
function parseSections(text: string): {
  summary: string;
  sections: { title: string; content: string }[];
  aiComment: string;
} {
  if (!text?.trim()) return { summary: "", sections: [], aiComment: "" };

  // AI의 한마디 추출
  const commentMatch = text.match(/AI의 한마디:\s*["']?([^"'\n]+)["']?/);
  const aiComment = commentMatch ? commentMatch[1].trim() : "";

  // 구버전 캐시에 포함된 프롬프트 아티팩트 제거 및 AI의 한마디 문구 제거
  const cleaned = text
    .replace(/\[뉴스 심층 분석 양식\]/g, "")
    .replace(/^---+$/gm, "")
    .replace(/AI의 한마디:.*$/gm, "")
    .replace(/\n{3,}/g, "\n\n")
    .trim();

  const parts = cleaned.split(/(?=^[📌🔍⚡💡])/m).filter(Boolean);

  let summary = "";
  const sections: { title: string; content: string }[] = [];

  for (const part of parts) {
    const lines = part.trim().split("\n");
    const firstLine = lines[0]?.trim() ?? "";
    const content = lines.slice(1).join("\n").trim();

    if (firstLine.includes("핵심 팩트") || firstLine.startsWith("📌")) {
      summary = content;
    } else if (firstLine) {
      sections.push({ title: firstLine, content });
    }
  }

  // 섹션으로 파싱이 안 되면 전체를 요약으로
  if (!summary && sections.length === 0) {
    summary = cleaned;
  }

  return { summary, sections, aiComment };
}

export default function AiSummary({ title, aiSummary, url }: AiSummaryProps) {
  const { summary, sections, aiComment } = parseSections(aiSummary);

  // 투자 인사이트(종목 추천) 섹션 찾기
  const recommendSection = sections.find(s => s.title.includes("그래서 어떤 종목") || s.title.includes("💡"));
  const displaySections = sections.filter(s => s !== recommendSection);

  return (
    <div className="flex flex-col space-y-5 pb-10">
      <h1 className="text-2xl font-bold px-0.5">{sanitizeNewsTitle(title)}</h1>

      {/* 1. 핵심 팩트 */}
      {summary && (
        <div className="bg-white/5 border border-white/10 rounded-xl p-5">
          <div className="flex items-center gap-2 mb-3">
            <Sparkles className="w-5 h-5 text-amber-400" />
            <h2 className="font-bold text-gray-100 text-sm italic">📌 한눈에 보는 핵심 팩트</h2>
          </div>
          <div className="text-gray-300 leading-relaxed whitespace-pre-wrap text-sm mb-5">
            {summary}
          </div>

          {url && (
            <div className="pt-2 border-t border-white/5">
              <a
                href={url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1.5 text-xs text-skyblue hover:text-skyblue/80 transition-colors font-medium"
              >
                <span>원문 보기</span>
                <Rocket className="w-3 h-3 rotate-45" />
              </a>
            </div>
          )}
        </div>
      )}

      {/* 2 & 3. 연관 분야, 파급력 등 (자동 파싱된 섹션) */}
      {displaySections.map((sec, i) => (
        <div
          key={i}
          className="bg-white/5 border border-white/10 rounded-xl p-5"
        >
          <h3 className="font-bold text-skyblue mb-3 text-sm">{sec.title}</h3>
          <div className="text-gray-200 text-sm leading-relaxed whitespace-pre-wrap">
            {sec.content}
          </div>
        </div>
      ))}

      {/* 4. AI의 한마디 */}
      {aiComment && (
        <div className="bg-skyblue/10 border border-skyblue/30 rounded-xl p-5">
          <div className="flex items-center gap-2 mb-3">
            <Rocket className="w-4 h-4 text-skyblue" />
            <span className="text-xs font-bold text-skyblue uppercase tracking-wider">AI의 한마디</span>
          </div>
          <p className="text-white font-medium leading-relaxed italic text-sm">
            "{aiComment}"
          </p>
        </div>
      )}

      {/* 5. 추천 종목 */}
      {recommendSection && (
        <div className="bg-white/5 border border-white/10 rounded-xl p-5">
          <h3 className="font-bold text-skyblue mb-4 text-sm">
            💡 그래서 어떤 종목? (투자 인사이트 - 5개 이상 추천)
          </h3>
          <div className="text-gray-200 text-sm leading-relaxed whitespace-pre-wrap">
            {recommendSection.content}
          </div>
        </div>
      )}
    </div>
  );
}
