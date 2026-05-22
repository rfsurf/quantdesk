"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/store";
import { LogOut, User, Shield, Sun, Moon, Sparkles } from "lucide-react";
import { useTheme } from "./ThemeProvider";

export default function Navbar() {
  const { user, logout } = useAuthStore();
  const { theme, toggleTheme } = useTheme();
  const router = useRouter();

  const handleLogout = () => {
    logout();
    router.push("/");
  };

  return (
    <nav
      className="flex items-center justify-between px-6 py-3
        bg-white/80 dark:bg-navy-800/80
        backdrop-blur-nav
        border-b border-gray-100/60 dark:border-navy-700/60
        sticky top-0 z-50
        transition-colors duration-300"
    >
      <Link href="/dashboard" className="flex items-center gap-2.5 group">
        <div
          className="w-9 h-9 bg-brand-gradient rounded-[12px]
            flex items-center justify-center text-white font-bold text-sm
            shadow-brand-glow-sm group-hover:shadow-brand-glow
            transition-all duration-300"
        >
          <Sparkles size={16} />
        </div>
        <span className="text-lg font-bold text-gray-800 dark:text-white transition-colors tracking-tight">
          QuantDesk
        </span>
      </Link>

      <div className="flex items-center gap-2">
        {/* Theme Toggle */}
        <button
          onClick={toggleTheme}
          className="p-2 rounded-[12px] text-gray-400 dark:text-gray-500
            hover:bg-gray-100/80 dark:hover:bg-navy-700/60
            hover:text-gray-600 dark:hover:text-gray-300
            transition-all duration-200"
          title={theme === "light" ? "切换到深色" : "切换到浅色"}
        >
          {theme === "light" ? <Moon size={16} /> : <Sun size={16} />}
        </button>

        {/* Admin */}
        <Link
          href="/admin"
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-[12px]
            text-sm text-gray-500 dark:text-gray-400
            hover:bg-gray-100/80 dark:hover:bg-navy-700/60
            hover:text-brand-500 dark:hover:text-brand-400
            transition-all duration-200"
        >
          <Shield size={14} />
          <span>管理</span>
        </Link>

        {/* User */}
        {user && (
          <div className="hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-[12px]
            bg-gray-50 dark:bg-navy-700/60">
            <div className="w-6 h-6 rounded-full bg-brand-gradient flex items-center justify-center">
              <User size={12} className="text-white" />
            </div>
            <span className="text-sm text-gray-600 dark:text-gray-300 font-medium">
              {user.email}
            </span>
          </div>
        )}

        {/* Logout */}
        <button
          onClick={handleLogout}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-[12px]
            text-sm text-gray-500 dark:text-gray-400
            hover:bg-red-50 dark:hover:bg-red-900/20
            hover:text-loss
            transition-all duration-200"
        >
          <LogOut size={14} />
          <span className="hidden sm:inline">退出</span>
        </button>
      </div>
    </nav>
  );
}
