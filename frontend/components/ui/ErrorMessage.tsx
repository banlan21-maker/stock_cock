"use client";

export default function ErrorMessage({
  message,
  onRetry,
}: {
  message: string;
  onRetry?: () => void;
}) {
  return (
    <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-4 text-center">
      <p className="text-red-300 text-sm mb-2">{message}</p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="text-xs text-skyblue hover:text-blue-400 underline"
        >
          다시 시도
        </button>
      )}
    </div>
  );
}
