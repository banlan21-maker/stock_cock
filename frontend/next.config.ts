import type { NextConfig } from "next";
import path from "path";

const BACKEND_URL = "http://152.67.193.198:8000";

const nextConfig: NextConfig = {
  // Turbopack이 루트(lockfile) 대신 frontend를 프로젝트 루트로 쓰도록 고정
  turbopack: {
    root: path.resolve(__dirname),
  },
  // HTTPS → HTTP mixed content 차단 우회:
  // 브라우저가 /api/... 로 요청하면 Next.js 서버가 Oracle Cloud로 프록시
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${BACKEND_URL}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;