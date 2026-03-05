import { AiDisclaimerFooter } from "@/components/ui/AiDisclaimer";

export default function Footer() {
  return (
    <footer className="py-4 text-center text-xs text-gray-500 space-y-1.5 px-4">
      <p>Stock Cock v0.1.0 &middot; 투자 판단은 본인의 책임입니다.</p>
      <AiDisclaimerFooter />
    </footer>
  );
}
