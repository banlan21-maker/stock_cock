/**
 * Oracle Cloud 백엔드 프록시
 * - 브라우저 → HTTPS Firebase → 이 파일 → HTTP Oracle Cloud
 * - Mixed content 차단 우회
 */
import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL = "http://152.67.193.198:8000";

async function proxyRequest(
  req: NextRequest,
  context: { params: Promise<{ proxy: string[] }> }
) {
  const { proxy } = await context.params;
  const path = proxy.join("/");
  const search = req.nextUrl.search;
  const targetUrl = `${BACKEND_URL}/api/${path}${search}`;

  // 헤더 복사 (Authorization 포함, host 제외)
  const headers = new Headers();
  for (const [key, value] of req.headers.entries()) {
    if (!["host", "content-length", "transfer-encoding"].includes(key)) {
      headers.set(key, value);
    }
  }

  const isBodyMethod = req.method !== "GET" && req.method !== "HEAD";
  const upstream = await fetch(targetUrl, {
    method: req.method,
    headers,
    body: isBodyMethod ? req.body : undefined,
    // @ts-ignore - Node.js 스트리밍 바디 전달
    duplex: "half",
  });

  // SSE 스트리밍 (AI 분석 등)
  const contentType = upstream.headers.get("content-type") ?? "";
  if (contentType.includes("text/event-stream")) {
    return new Response(upstream.body, {
      status: upstream.status,
      headers: {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
        "X-Accel-Buffering": "no",
      },
    });
  }

  const data = await upstream.arrayBuffer();
  return new NextResponse(data, {
    status: upstream.status,
    headers: {
      "Content-Type": contentType || "application/json",
    },
  });
}

export const GET = proxyRequest;
export const POST = proxyRequest;
export const PUT = proxyRequest;
export const DELETE = proxyRequest;
export const PATCH = proxyRequest;