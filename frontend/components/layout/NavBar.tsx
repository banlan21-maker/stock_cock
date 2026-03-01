"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Globe, Search, Rocket, PieChart, FileText, Lightbulb } from "lucide-react";

const navItems = [
  { href: "/dashboard", label: "시작", icon: Rocket },
  { href: "/issues", label: "이슈콕", icon: Globe },
  { href: "/policy", label: "정책콕", icon: Search },
  { href: "/disclosure", label: "공시콕", icon: FileText },
  { href: "/stock", label: "종목콕", icon: Lightbulb },
  { href: "/portfolio", label: "포트폴리오", icon: PieChart },
];

export default function NavBar() {
  const pathname = usePathname();

  return (
    <nav className="sticky top-0 z-50 bg-navy/90 backdrop-blur-md border-b border-white/10">
      <div className="max-w-5xl mx-auto px-4 h-14 flex items-center justify-evenly">
        {navItems.map(({ href, label, icon: Icon }) => {
          const active = pathname.startsWith(href);
          return (
            <Link
              key={href}
              href={href}
              className={`flex flex-col items-center gap-0.5 px-3 py-1.5 rounded-lg text-xs transition-colors ${
                active
                  ? "text-skyblue"
                  : "text-gray-400 hover:text-white"
              }`}
            >
              <Icon className="w-5 h-5" />
              <span>{label}</span>
            </Link>
          );
        })}
      </div>
    </nav>
  );
}
