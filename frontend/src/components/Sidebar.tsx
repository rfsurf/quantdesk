"use client";
import { Suspense } from "react";
import Link from "next/link";
import { usePathname, useSearchParams } from "next/navigation";
import {
  LayoutDashboard,
  BarChart3,
  Bot,
  Settings,
  Plus,
  Key,
} from "lucide-react";
import clsx from "clsx";

const navItems = [
  { href: "/dashboard", label: "策略列表", icon: LayoutDashboard, tab: "" },
  { href: "/dashboard?tab=backtests", label: "回测记录", icon: BarChart3, tab: "backtests" },
  { href: "/dashboard?tab=ai", label: "AI 助手", icon: Bot, tab: "ai" },
  { href: "/dashboard?tab=settings", label: "设置", icon: Settings, tab: "settings" },
];

function SidebarContent() {
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const currentTab = searchParams.get("tab") || "";

  return (
    <aside
      className="w-60 border-r border-gray-100/80 dark:border-navy-700/60
        bg-white/60 dark:bg-navy-800/60
        backdrop-blur-sm
        min-h-[calc(100vh-57px)] p-4 flex flex-col
        transition-colors duration-300"
    >
      {/* New Strategy Button */}
      <Link
        href="/strategy/new/edit"
        className="flex items-center justify-center gap-2 px-4 py-2.5 mb-6
          bg-brand-gradient text-white
          rounded-[16px] font-semibold text-sm
          shadow-brand-glow-sm hover:shadow-brand-glow
          hover:-translate-y-px active:translate-y-0
          transition-all duration-300"
      >
        <Plus size={16} />
        新建策略
      </Link>

      {/* Nav Items */}
      <nav className="flex flex-col gap-1">
        {navItems.map((item) => {
          const isActive = pathname === "/dashboard" && currentTab === item.tab;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={clsx(
                "flex items-center gap-3 px-3.5 py-2.5 rounded-[14px] text-sm font-medium transition-all duration-300",
                isActive
                  ? "bg-brand-gradient text-white shadow-brand-glow-sm"
                  : "text-gray-600 dark:text-gray-400 hover:bg-gray-100/80 dark:hover:bg-navy-700/50 hover:text-gray-800 dark:hover:text-gray-200"
              )}
            >
              <item.icon size={17} className={isActive ? "text-white" : ""} />
              <span>{item.label}</span>
            </Link>
          );
        })}

        {/* Agent Tokens Quick Link */}
        <Link
          href="/settings/agent-tokens"
          className={clsx(
            "flex items-center gap-3 px-3.5 py-2.5 rounded-[14px] text-sm font-medium transition-all duration-300 mt-1",
            pathname === "/settings/agent-tokens"
              ? "bg-brand-gradient text-white shadow-brand-glow-sm"
              : "text-gray-600 dark:text-gray-400 hover:bg-gray-100/80 dark:hover:bg-navy-700/50 hover:text-gray-800 dark:hover:text-gray-200"
          )}
        >
          <Key size={17} />
          <span>Agent Tokens</span>
        </Link>
      </nav>

      {/* Footer */}
      <div className="mt-auto pt-4 border-t border-gray-100/80 dark:border-navy-700/60">
        <div className="text-xs text-gray-400 dark:text-gray-500 px-3 flex items-center gap-1.5">
          <div className="w-1.5 h-1.5 rounded-full bg-green-500" />
          QuantDesk v2.0
        </div>
      </div>
    </aside>
  );
}

function SidebarSkeleton() {
  return (
    <aside
      className="w-60 border-r border-gray-100/80 dark:border-navy-700/60
        bg-white/60 dark:bg-navy-800/60 min-h-[calc(100vh-57px)] p-4 flex flex-col"
    >
      <div className="h-10 bg-gray-100/80 dark:bg-navy-700/60 rounded-[16px] mb-6 animate-pulse" />
      <div className="space-y-1.5">
        {[1, 2, 3, 4, 5].map((i) => (
          <div key={i} className="h-10 bg-gray-50 dark:bg-navy-700/40 rounded-[14px] animate-pulse" />
        ))}
      </div>
    </aside>
  );
}

export default function Sidebar() {
  return (
    <Suspense fallback={<SidebarSkeleton />}>
      <SidebarContent />
    </Suspense>
  );
}
