"use client";
import { useState, useEffect, useCallback } from "react";

interface TourStep {
  selector: string;          // CSS 选择器，用于定位目标元素
  title: string;
  content: string;
  action?: string;           // 引导用户的操作
}

interface Props {
  steps: TourStep[];
  onComplete: () => void;
  storageKey: string;        // localStorage key，避免重复展示
}

export default function GuidedTour({ steps, onComplete, storageKey }: Props) {
  const [idx, setIdx] = useState(0);
  const [rect, setRect] = useState<DOMRect | null>(null);
  const [visible, setVisible] = useState(false);

  const updateRect = useCallback(() => {
    const step = steps[idx];
    const el = document.querySelector(step.selector);
    if (el) {
      const r = el.getBoundingClientRect();
      setRect(r);
      // 滚动到视口内
      if (r.bottom > window.innerHeight || r.top < 0) {
        el.scrollIntoView({ behavior: "smooth", block: "center" });
      }
    }
    setVisible(true);
  }, [idx, steps]);

  useEffect(() => {
    // 检查是否已展示过
    if (localStorage.getItem(storageKey)) return;
    const timer = setTimeout(updateRect, 400);
    return () => clearTimeout(timer);
  }, [idx, storageKey, updateRect]);

  const handleNext = () => {
    setVisible(false);
    setTimeout(() => {
      if (idx + 1 >= steps.length) {
        localStorage.setItem(storageKey, "1");
        onComplete();
      } else {
        setIdx(idx + 1);
      }
    }, 150);
  };

  const handleSkip = () => {
    localStorage.setItem(storageKey, "1");
    onComplete();
  };

  if (localStorage.getItem(storageKey)) return null;

  return (
    <div className="fixed inset-0 z-[9998]">
      {/* 暗色遮罩，目标元素镂空 */}
      <svg className="absolute inset-0 w-full h-full" viewBox={`0 0 ${window.innerWidth} ${window.innerHeight}`}>
        <defs>
          <mask id="tour-hole">
            <rect width="100%" height="100%" fill="white" />
            {rect && (
              <rect
                x={rect.x - 8}
                y={rect.y - 8}
                width={rect.width + 16}
                height={rect.height + 16}
                rx="8"
                fill="black"
              />
            )}
          </mask>
        </defs>
        <rect width="100%" height="100%" fill="rgba(0,0,0,0.55)" mask="url(#tour-hole)" />
        {rect && (
          <rect
            x={rect.x - 8}
            y={rect.y - 8}
            width={rect.width + 16}
            height={rect.height + 16}
            rx="8"
            fill="none"
            stroke="#6366f1"
            strokeWidth="2"
          />
        )}
      </svg>

      {/* 提示气泡 */}
      {rect && visible && (
        <div
          className="absolute bg-white rounded-xl shadow-2xl p-5 w-80 transition-opacity duration-200"
          style={{
            left: _bubbleLeft(rect),
            top: _bubbleTop(rect),
            opacity: visible ? 1 : 0,
          }}
        >
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs text-slate-400 font-mono">{idx + 1}/{steps.length}</span>
            <div className="flex gap-1">
              {steps.map((_, i) => (
                <div
                  key={i}
                  className={`w-1.5 h-1.5 rounded-full ${i <= idx ? "bg-brand-500" : "bg-slate-200"}`}
                />
              ))}
            </div>
          </div>
          <h3 className="font-bold text-slate-900 text-base mb-1">{steps[idx].title}</h3>
          <p className="text-sm text-slate-600 leading-relaxed mb-1">{steps[idx].content}</p>
          {steps[idx].action && (
            <p className="text-xs text-brand-600 font-medium mb-3">👉 {steps[idx].action}</p>
          )}
          <div className="flex items-center justify-between">
            <button onClick={handleSkip} className="text-xs text-slate-400 hover:text-slate-600 transition">
              跳过引导
            </button>
            <div className="flex gap-2">
              {idx > 0 && (
                <button
                  onClick={() => { setVisible(false); setTimeout(() => setIdx(idx - 1), 150); }}
                  className="text-xs text-slate-600 px-3 py-1.5 rounded-lg hover:bg-slate-100 transition"
                >
                  上一步
                </button>
              )}
              <button
                onClick={handleNext}
                className="text-xs bg-brand-600 text-white px-4 py-1.5 rounded-lg font-medium hover:bg-brand-700 transition"
              >
                {idx + 1 >= steps.length ? "开始使用" : "下一步"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ------------------------------------------------------------------
// 气泡位置计算: 默认放在目标元素右下方
// ------------------------------------------------------------------

function _bubbleLeft(rect: DOMRect): number {
  const right = rect.right + 16;
  if (right + 340 > window.innerWidth) {
    return Math.max(16, rect.left - 340);
  }
  return right;
}

function _bubbleTop(rect: DOMRect): number {
  const top = rect.top;
  if (top + 250 > window.innerHeight) {
    return Math.max(16, window.innerHeight - 260);
  }
  return Math.max(16, top);
}
