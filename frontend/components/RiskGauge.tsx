"use client";

type Props = {
  probability: number; // 0..1
  riskLevel: "Low" | "Medium" | "High";
};

const RISK_COLOR: Record<Props["riskLevel"], string> = {
  Low: "var(--safe)",
  Medium: "var(--warn)",
  High: "var(--risk)",
};

// semicircle gauge, 180deg sweep from -90deg (left) to +90deg (right)
export default function RiskGauge({ probability, riskLevel }: Props) {
  const clamped = Math.min(Math.max(probability, 0), 1);
  const angle = -90 + clamped * 180;
  const color = RISK_COLOR[riskLevel];

  const cx = 110;
  const cy = 110;
  const r = 90;
  const needleLen = 78;
  const rad = (angle * Math.PI) / 180;
  const nx = cx + needleLen * Math.cos(rad);
  const ny = cy + needleLen * Math.sin(rad);

  // arc path helper
  const polar = (deg: number, radius: number) => {
    const a = (deg * Math.PI) / 180;
    return [cx + radius * Math.cos(a), cy + radius * Math.sin(a)];
  };
  const arcPath = (fromDeg: number, toDeg: number, radius: number) => {
    const [x1, y1] = polar(fromDeg, radius);
    const [x2, y2] = polar(toDeg, radius);
    const largeArc = toDeg - fromDeg > 180 ? 1 : 0;
    return `M ${x1} ${y1} A ${radius} ${radius} 0 ${largeArc} 1 ${x2} ${y2}`;
  };

  return (
    <div className="flex flex-col items-center">
      <svg viewBox="0 0 220 130" className="w-full max-w-[280px]">
        {/* track segments */}
        <path d={arcPath(-90, -30, r)} stroke="var(--safe)" strokeWidth="14" fill="none" strokeLinecap="round" opacity={0.35} />
        <path d={arcPath(-30, 30, r)} stroke="var(--warn)" strokeWidth="14" fill="none" opacity={0.35} />
        <path d={arcPath(30, 90, r)} stroke="var(--risk)" strokeWidth="14" fill="none" strokeLinecap="round" opacity={0.35} />

        {/* active arc up to current probability */}
        <path d={arcPath(-90, angle, r)} stroke={color} strokeWidth="14" fill="none" strokeLinecap="round" />

        {/* needle */}
        <line x1={cx} y1={cy} x2={nx} y2={ny} stroke={color} strokeWidth="3" strokeLinecap="round" />
        <circle cx={cx} cy={cy} r="6" fill={color} />

        {/* tick labels */}
        <text x="14" y="122" fontSize="10" fill="var(--text-faint)" fontFamily="var(--font-data)">0%</text>
        <text x="192" y="122" fontSize="10" fill="var(--text-faint)" fontFamily="var(--font-data)">100%</text>
      </svg>

      <div className="-mt-4 text-center">
        <div className="font-data text-4xl font-semibold" style={{ color }}>
          {(clamped * 100).toFixed(1)}%
        </div>
        <div
          className="mt-1 inline-block rounded-full px-3 py-1 text-xs font-medium tracking-wide uppercase"
          style={{ color, backgroundColor: `${color}1a`, border: `1px solid ${color}44` }}
        >
          {riskLevel} risk
        </div>
      </div>
    </div>
  );
}
