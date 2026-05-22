import clsx from "clsx";

interface Props {
  score: number;
  size?: "sm" | "md" | "lg";
}

const RINGS = [
  { min: 0, color: "#ef4444", label: "差", bg: "bg-red-50", text: "text-red-600" },
  { min: 40, color: "#f59e0b", label: "一般", bg: "bg-amber-50", text: "text-amber-600" },
  { min: 60, color: "#3b82f6", label: "良好", bg: "bg-blue-50", text: "text-blue-600" },
  { min: 80, color: "#22c55e", label: "优秀", bg: "bg-green-50", text: "text-green-600" },
];

export default function ScoreBadge({ score, size = "md" }: Props) {
  const ring = [...RINGS].reverse().find((r) => score >= r.min) || RINGS[0];
  const sizes = { sm: "w-10 h-10 text-xs", md: "w-14 h-14 text-sm", lg: "w-20 h-20 text-lg" };

  return (
    <div
      className={clsx(
        "rounded-full flex items-center justify-center font-bold border-2",
        sizes[size]
      )}
      style={{
        borderColor: ring.color,
        color: ring.color,
        background: `${ring.color}10`,
        boxShadow: `0 0 12px ${ring.color}20`,
      }}
    >
      {score}
    </div>
  );
}
