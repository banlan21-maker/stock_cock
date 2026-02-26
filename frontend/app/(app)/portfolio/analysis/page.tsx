import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import AIAnalysisReport from "@/components/portfolio/AIAnalysisReport";

export default function PortfolioAnalysisPage() {
  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Link
          href="/portfolio"
          className="text-gray-400 hover:text-white transition-colors"
        >
          <ArrowLeft className="w-5 h-5" />
        </Link>
        <h1 className="text-2xl font-bold">AI 포트폴리오 진단</h1>
      </div>
      <AIAnalysisReport />
    </div>
  );
}
