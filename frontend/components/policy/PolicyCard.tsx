"use client";

import Link from "next/link";
import { ExternalLink } from "lucide-react";
import type { PolicyInfo } from "@/types";

interface PolicyCardProps {
  policy: PolicyInfo;
}

export default function PolicyCard({ policy }: PolicyCardProps) {
  return (
    <Link
      href={`/policy/${policy.id}`}
      className="group block bg-white/5 border border-white/10 rounded-xl overflow-hidden hover:bg-white/10 transition-colors"
    >
      {policy.image_url ? (
        <div className="relative h-40 overflow-hidden">
          <img
            src={policy.image_url}
            alt=""
            className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
          />
          <div className="absolute inset-0 bg-gradient-to-t from-black/70 to-transparent" />
          <p className="absolute bottom-3 left-4 right-4 font-bold text-lg text-white line-clamp-2">
            {policy.title}
          </p>
        </div>
      ) : (
        <div className="relative h-40 bg-gradient-to-br from-purple-900/40 to-blue-900/40 flex items-end p-4">
          <p className="font-bold text-lg text-white line-clamp-2">{policy.title}</p>
        </div>
      )}

      <div className="p-4 space-y-2">
        <p className="text-sm text-purple-400">{policy.department}</p>
        <p className="text-sm text-gray-300 line-clamp-2">{policy.description}</p>
        <div className="flex items-center justify-between pt-1">
          {policy.created_at && (
            <p className="text-xs text-gray-500">
              {new Date(policy.created_at).toLocaleDateString("ko-KR")}
            </p>
          )}
          {policy.link && (
            <span className="text-xs text-gray-500 flex items-center gap-1">
              <ExternalLink className="w-3 h-3" /> 원문
            </span>
          )}
        </div>
      </div>
    </Link>
  );
}
