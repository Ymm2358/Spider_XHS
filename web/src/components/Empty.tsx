import type { ReactNode } from "react";

type Props = {
  title: string;
  description?: string;
  action?: ReactNode;
};

export default function Empty({ title, description, action }: Props) {
  return (
    <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-line bg-panel/40 px-6 py-14 text-center">
      <div className="mb-3 flex h-9 w-9 items-center justify-center rounded-lg border border-line text-muted">
        <span className="text-[15px]">＋</span>
      </div>
      <div className="text-[13px] font-medium">{title}</div>
      {description && <p className="mt-1 max-w-[380px] text-[12px] leading-5 text-muted">{description}</p>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}
