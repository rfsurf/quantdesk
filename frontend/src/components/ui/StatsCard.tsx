import clsx from "clsx";
import { ReactNode } from "react";
import { Card } from "./Card";

interface StatsCardProps {
  label: string;
  value: string | number;
  icon?: ReactNode;
  trend?: "up" | "down" | "neutral";
  trendValue?: string;
  color?: "brand" | "profit" | "loss" | "gray" | "amber" | "blue" | "purple";
  className?: string;
  subtitle?: string;
}

export function StatsCard({
  label,
  value,
  icon,
  trend,
  trendValue,
  color = "brand",
  className,
  subtitle,
}: StatsCardProps) {
  const colors = {
    brand: "text-brand-500 dark:text-brand-400",
    profit: "text-profit",
    loss: "text-loss",
    gray: "text-gray-600 dark:text-gray-400",
    amber: "text-amber-500 dark:text-amber-400",
    blue: "text-blue-500 dark:text-blue-400",
    purple: "text-purple-500 dark:text-purple-400",
  };

  const trendColors = {
    up: "text-profit",
    down: "text-loss",
    neutral: "text-gray-400",
  };

  const iconBgColors = {
    brand: "bg-brand-50 dark:bg-brand-900/20",
    profit: "bg-green-50 dark:bg-green-900/20",
    loss: "bg-red-50 dark:bg-red-900/20",
    gray: "bg-gray-50 dark:bg-navy-700",
    amber: "bg-amber-50 dark:bg-amber-900/20",
    blue: "bg-blue-50 dark:bg-blue-900/20",
    purple: "bg-purple-50 dark:bg-purple-900/20",
  };

  const iconColors = {
    brand: "text-brand-500",
    profit: "text-profit",
    loss: "text-loss",
    gray: "text-gray-400",
    amber: "text-amber-500",
    blue: "text-blue-500",
    purple: "text-purple-500",
  };

  return (
    <Card
      className={clsx(
        "p-5",
        "hover:-translate-y-0.5 transition-all duration-350",
        className
      )}
      hover
    >
      <div className="flex items-start justify-between mb-3">
        {icon && (
          <div
            className={clsx(
              "w-10 h-10 rounded-[12px] flex items-center justify-center",
              iconBgColors[color],
              iconColors[color]
            )}
          >
            {icon}
          </div>
        )}
        {trend && (
          <div className={clsx("flex items-center gap-1 text-xs font-medium", trendColors[trend])}>
            <span>
              {trend === "up" ? "↑" : trend === "down" ? "↓" : "→"}
            </span>
            {trendValue && <span>{trendValue}</span>}
          </div>
        )}
      </div>

      <div className={clsx("stat-value", colors[color])}>
        {value}
      </div>

      <div className="mt-1 flex items-center justify-between">
        <span className="text-xs text-gray-400 dark:text-gray-500 font-medium">{label}</span>
        {subtitle && (
          <span className="text-xs text-gray-400 dark:text-gray-500">{subtitle}</span>
        )}
      </div>
    </Card>
  );
}
