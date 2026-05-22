import clsx from "clsx";

interface CardProps {
  children: React.ReactNode;
  className?: string;
  hover?: boolean;
  glass?: boolean;
  gradient?: boolean;
  glow?: boolean;
  onClick?: () => void;
}

export function Card({
  children,
  className,
  hover = false,
  glass = false,
  gradient = false,
  glow = false,
  onClick,
}: CardProps) {
  return (
    <div
      onClick={onClick}
      className={clsx(
        "rounded-[20px] border overflow-hidden",
        // Base
        !glass && !gradient && "bg-white dark:bg-navy-700 border-gray-100 dark:border-navy-600/60",
        // Glass
        glass && "bg-white/70 dark:bg-navy-700/60 backdrop-blur-card border-white/20 dark:border-white/10",
        // Gradient
        gradient && "bg-gradient-to-br from-white to-gray-50 dark:from-navy-700 dark:to-navy-800 border-gray-100 dark:border-navy-600/40",
        // Shadow
        "shadow-card dark:shadow-dark-card",
        hover && "hover:shadow-card-hover dark:hover:shadow-dark-hover transition-all duration-350 hover:-translate-y-0.5",
        glow && "shadow-brand-glow-sm",
        // Cursor
        onClick && "cursor-pointer",
        className
      )}
    >
      {children}
    </div>
  );
}
