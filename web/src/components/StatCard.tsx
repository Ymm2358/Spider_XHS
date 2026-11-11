type Props = {
  label: string;
  value: string;
  hint?: string;
  tone?: "default" | "accent" | "muted";
};

const TONE = {
  default: "text-ink",
  accent: "text-accent",
  muted: "text-muted"
};

export default function StatCard({ label, value, hint, tone = "default" }: Props) {
  return (
    <div className="rounded-xl border border-line bg-panel px-4 py-4">
      <div className="text-[11px] text-muted">{label}</div>
      <div className={`mt-2 text-[24px] font-semibold leading-none ${TONE[tone]}`}>{value}</div>
      {hint && <div className="mt-2 text-[11px] text-muted">{hint}</div>}
    </div>
  );
}
