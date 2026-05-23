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
    } else {
      // 如果找不到元素，设置一个默认位置（右上角）
      setRect(null);
    }
    setVisible(true);
  }, [idx, steps]);

  useEffect(() => {
    // 检查是否已展示过
    if (localStorage.getItem(storageKey)) return;
    // 延迟显示，让用户先看到页面内容
    const timer = setTimeout(updateRect, 800);
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

  // 点击遮罩跳过
  const handleMaskClick = (e: React.MouseEvent) => {
    // 只在点击遮罩层（非气泡）时跳过
    if (e.target === e.currentTarget || (e.target as SVGElement).tagName === 'rect') {
      handleSkip();
    }
  };

  if (localStorage.getItem(storageKey)) return null;

  return (
    <div className="fixed inset-0 z-[9998]" onClick={handleMaskClick}>
      {/* 半透明遮罩，目标元素镂空高亮 */}
      <svg className="absolute inset-0 w-full h-full pointer-events-none" viewBox={`0 0 ${window.innerWidth} ${window.innerHeight}`}>
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
        <rect width="100%" height="100%" fill="rgba(0,0,0,0.35)" mask="url(#tour-hole)" className="cursor-pointer" />
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
            className="pointer-events-none"
          />
        )}
      </svg>

      {/* 提示气泡 */}
      {visible && (
        <div
          className="absolute bg-white dark:bg-navy-800 rounded-xl shadow-2xl p-5 w-72 transition-opacity duration-200 border border-gray-100 dark:border-navy-600"
          style={{
            left: rect ? _bubbleLeft(rect) : window.innerWidth - 320,
            top: rect ? _bubbleTop(rect) : 80,
            opacity: visible ? 1 : 0,
          }}
          onClick={(e) => e.stopPropagation()}
        >
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs text-slate-400 font-mono">{idx + 1}/{steps.length}</span>
            <div className="flex gap-1">
              {steps.map((_, i) => (
                <div
                  key={i}
                  className={`w-1.5 h-1.5 rounded-full ${i <= idx ? "bg-brand-500" : "bg-slate-200 dark:bg-navy-600"}`}
                />
              ))}
            </div>
          </div>
          <h3 className="font-bold text-slate-900 dark:text-white text-base mb-1">{steps[idx].title}</h3>
          <p className="text-sm text-slate-600 dark:text-slate-300 leading-relaxed mb-1">{steps[idx].content}</p>
          {steps[idx].action && (
            <p className="text-xs text-brand-600 font-medium mb-3">👉 {steps[idx].action}</p>
          )}
          <div className="flex items-center justify-between">
            <button onClick={handleSkip} className="text-xs text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 transition">
              跳过引导
            </button>
            <div className="flex gap-2">
              {idx > 0 && (
                <button
                  onClick={() => { setVisible(false); setTimeout(() => setIdx(idx - 1), 150); }}
                  className="text-xs text-slate-600 dark:text-slate-300 px-3 py-1.5 rounded-lg hover:bg-slate-100 dark:hover:bg-navy-700 transition"
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
// 气泡位置计算: 优先放在目标元素右下方，避免遮挡主要内容
// ------------------------------------------------------------------

function _bubbleLeft(rect: DOMRect): number {
  const gap = 16;
  const bubbleWidth = 288; // w-72 = 288px

  // 优先放在右侧
  const right = rect.right + gap;
  if (right + bubbleWidth <= window.innerWidth) {
    return right;
  }

  // 右侧空间不足，放在左侧
  const left = rect.left - bubbleWidth - gap;
  if (left >= 16) {
    return left;
  }

  // 左右都不够，放在底部中央
  return Math.max(16, Math.min(window.innerWidth - bubbleWidth - 16, rect.left + rect.width / 2 - bubbleWidth / 2));
}

function _bubbleTop(rect: DOMRect): number {
  const gap = 12;
  const bubbleHeight = 200; // estimated

  // 优先放在同高度
  const top = rect.top;
  if (top + bubbleHeight <= window.innerHeight) {
    return Math.max(16, top);
  }

  // 上方空间不足，放在元素下方
  const below = rect.bottom + gap;
  if (below + bubbleHeight <= window.innerHeight) {
    return below;
  }

  // 都不够，放在视口顶部
  return 16;
}
