import type { NewsArticle } from "@/types";
import Link from "next/link";

interface Props {
  items: NewsArticle[];
}

export default function NewsList({ items }: Props) {
  if (items.length === 0) {
    return (
      <p className="text-gray-400 text-sm text-center py-8">뉴스가 없습니다.</p>
    );
  }

  return (
    <div className="space-y-3">
      {items.map((n) => (
        <Link
          key={n.id}
          href={`/issues/${encodeURIComponent(n.id)}`}
          className="block bg-white/5 border border-white/10 rounded-xl p-4 hover:bg-white/10 transition-colors"
        >
          <p className="font-medium line-clamp-2">{n.title}</p>
          <p className="text-xs text-gray-400 mt-1">
            {n.source} &middot;{" "}
            {new Date(n.published_at).toLocaleDateString("ko-KR")}
          </p>
        </Link>
      ))}
    </div>
  );
}
