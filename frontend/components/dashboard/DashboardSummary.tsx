import type { NewsArticle, PolicyInfo } from "@/types";
import Link from "next/link";
import NewsList from "@/components/news/NewsList";

interface Props {
  topNews: NewsArticle[];
  hotPolicies: PolicyInfo[];
}

export default function DashboardSummary({ topNews, hotPolicies }: Props) {
  return (
    <>
      {/* 최신 뉴스 */}
      <section>
        <div className="flex justify-between items-center mb-3">
          <div>
            <h2 className="text-lg font-bold">최신 뉴스</h2>
            <p className="text-xs text-gray-400">쉽게 요약해 드려요</p>
          </div>
          <Link href="/issues" className="text-sm text-skyblue hover:underline">
            전체 보기
          </Link>
        </div>
        <NewsList items={topNews} />
      </section>

      {/* 주요 정책 */}
      <section>
        <div className="flex justify-between items-center mb-3">
          <div>
            <h2 className="text-lg font-bold">주요 정책</h2>
            <p className="text-xs text-gray-400">쉽게 풀어서 설명해 드려요</p>
          </div>
          <Link href="/policy" className="text-sm text-skyblue hover:underline">
            전체 보기
          </Link>
        </div>
        <div className="space-y-3">
          {hotPolicies.length === 0 ? (
            <p className="text-gray-400 text-sm text-center py-8">
              정책 정보가 없습니다.
            </p>
          ) : (
            hotPolicies.map((p) => (
              <Link
                key={p.id}
                href={`/policy/${p.id}`}
                className="block bg-white/5 border border-white/10 rounded-xl p-4 hover:bg-white/10 transition-colors"
              >
                <p className="font-medium">{p.title}</p>
                <p className="text-xs text-gray-400 mt-1">{p.department}</p>
              </Link>
            ))
          )}
        </div>
      </section>
    </>
  );
}
