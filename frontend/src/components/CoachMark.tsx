"use client";
import { useState } from "react";
import Image from "next/image";

interface Props {
  steps: {
    target: string;
    title: string;
    content: string;
    position: "top" | "bottom" | "left" | "right";
  }[];
  onComplete: () => void;
}

export default function CoachMark({ steps, onComplete }: Props) {
  const [idx, setIdx] = useState(0);
  if (idx >= steps.length) return null;

  const step = steps[idx];

  const positionStyles: Record<string, React.CSSProperties> = {
    top: { bottom: "calc(100% + 12px)", left: "50%", transform: "translateX(-50%)" },
    bottom: { top: "calc(100% + 12px)", left: "50%", transform: "translateX(-50%)" },
    left: { right: "calc(100% + 12px)", top: "50%", transform: "translateY(-50%)" },
    right: { left: "calc(100% + 12px)", top: "50%", transform: "translateY(-50%)" },
  };

  return (
    <>
      <div className="fixed inset-0 bg-black/30 z-[9998]" />
      <div
        className="coach-mark"
        style={{
          position: "fixed",
          zIndex: 9999,
          ...positionStyles[step.position],
        }}
      >
        <div className="text-xs text-slate-300 mb-1">
          {idx + 1} / {steps.length}
        </div>
        <div className="font-semibold mb-1">{step.title}</div>
        <div className="text-xs text-slate-300 leading-relaxed">{step.content}</div>
        <div className="flex gap-2 mt-3">
          {idx > 0 && (
            <button
              className="text-xs text-slate-400 hover:text-white"
              onClick={() => setIdx(idx - 1)}
            >
              上一步
            </button>
          )}
          <button
            className="text-xs bg-brand-500 text-white px-3 py-1 rounded"
            onClick={() => {
              if (idx + 1 >= steps.length) onComplete();
              else setIdx(idx + 1);
            }}
          >
            {idx + 1 >= steps.length ? "知道了" : "下一步"}
          </button>
        </div>
      </div>
    </>
  );
}
