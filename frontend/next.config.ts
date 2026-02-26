import type { NextConfig } from "next";
import path from "path";

const nextConfig: NextConfig = {
  // Turbopack이 루트(lockfile) 대신 frontend를 프로젝트 루트로 쓰도록 고정
  turbopack: {
    root: path.resolve(__dirname),
  },
};

export default nextConfig;
