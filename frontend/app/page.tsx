import Link from "next/link";

const cardClass = "bg-white/10 p-6 rounded-2xl border border-white/20 backdrop-blur-sm hover:bg-white/15 transition-colors text-left";

export default function Home() {
  return (
    <div className="min-h-screen bg-navy text-white flex flex-col items-center justify-center p-4">
      <main className="flex flex-col gap-6 items-center text-center w-full max-w-sm">
        <h1 className="text-4xl font-bold tracking-tighter text-sky-400">
          주식콕 Stock Cock
        </h1>
        <p className="text-xl text-gray-300 max-w-md">
          복잡한 주식 정보, <span className="text-skyblue font-bold">콕</span> 집어 알려드려요.
        </p>

        <div className="grid grid-cols-1 w-full gap-4 mt-4">
          <Link href="/dashboard" className={`${cardClass} border-skyblue/40`}>
            <h2 className="text-lg font-bold mb-2">시작하기</h2>
            <p className="text-sm text-gray-400">대시보드에서 오늘의 시장을 한눈에</p>
          </Link>

          <Link href="/issues" className={cardClass}>
            <h2 className="text-lg font-bold mb-2">국내외 이슈</h2>
            <p className="text-sm text-gray-400">오늘의 핫한 국·내외 뉴스 확인하기</p>
          </Link>

          <Link href="/policy" className={cardClass}>
            <h2 className="text-lg font-bold mb-2">정책 돋보기</h2>
            <p className="text-sm text-gray-400">대한민국 정책 수혜주 찾기</p>
          </Link>

          <Link href="/stock" className={cardClass}>
            <h2 className="text-lg font-bold mb-2">종목 분석</h2>
            <p className="text-sm text-gray-400">AI가 분석하는 종목 리포트</p>
          </Link>

          <Link href="/portfolio" className={cardClass}>
            <h2 className="text-lg font-bold mb-2">내 포트폴리오</h2>
            <p className="text-sm text-gray-400">보유 종목 관리 및 AI 진단</p>
          </Link>
        </div>
      </main>

      <footer className="absolute bottom-4 text-xs text-gray-500">
        Stock Cock v0.1.0
      </footer>
    </div>
  );
}
