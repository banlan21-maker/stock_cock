"use client";

import { Sparkles, ExternalLink, Rocket } from "lucide-react";
import type { PolicyInfo } from "@/types";

interface PolicyAnalysisProps {
  policy: PolicyInfo;
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
    .replace(/\[정책 심층 분석 양식\]/g, "")
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

export default function PolicyAnalysis({ policy }: PolicyAnalysisProps) {
  const { summary, sections, aiComment } = parseSections(policy.ai_analysis ?? "");

  // 투자 인사이트(일반)와 종목 추천 섹션 분리
  const insightSection = sections.find(s => s.title.includes("투자 인사이트") && !s.title.includes("추천"));
  const recommendSection = sections.find(s => s.title.includes("투자 인사이트") && s.title.includes("추천"));

  // 메인 카드 목록에서는 제외 (나중에 하단에 통합 표시)
  const displaySections = sections.filter(s => !s.title.includes("투자 인사이트"));

  // AI의 한마디 결정: "AI의 한마디" 텍스트 우선, 없으면 일반 투자 인사이트 내용 사용
  const finalAiComment = aiComment || (insightSection?.content ? insightSection.content.split('\n')[0] : "");

  return (
    <div className="flex flex-col space-y-5 pb-10">
      {policy.image_url && (
        <div className="rounded-xl overflow-hidden">
          <img src={policy.image_url} alt="" className="w-full h-56 object-cover" />
        </div>
      )}

      <div className="px-0.5">
        <p className="text-sm text-purple-400 mb-1">{policy.department}</p>
        <h1 className="text-2xl font-bold">{policy.title}</h1>
        {policy.effective_date && (
          <p className="text-xs text-gray-500 mt-2">시행일: {policy.effective_date}</p>
        )}
      </div>

      {/* 1. 핵심 팩트 */}
      {summary && (
        <div className="bg-white/5 border border-white/10 rounded-xl p-5">
          <div className="flex items-center gap-2 mb-3">
            <Sparkles className="w-5 h-5 text-amber-400" />
            <h2 className="font-bold text-gray-100 italic text-sm">📌 한눈에 보는 핵심 팩트</h2>
          </div>
          <div className="text-gray-300 leading-relaxed whitespace-pre-wrap text-sm mb-5">{summary}</div>

          {policy.link && (
            <div className="pt-2 border-t border-white/5">
              <a
                href={policy.link}
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

      {/* 2 & 3. 연관 분야, 테마 등 (자동 파싱된 섹션) */}
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
      {finalAiComment && (
        <div className="bg-skyblue/10 border border-skyblue/30 rounded-xl p-5">
          <div className="flex items-center gap-2 mb-3">
            <Rocket className="w-4 h-4 text-skyblue" />
            <span className="text-xs font-bold text-skyblue uppercase tracking-wider">AI의 한마디</span>
          </div>
          <p className="text-white font-medium leading-relaxed italic text-sm">
            "{finalAiComment}"
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
