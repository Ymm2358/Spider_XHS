import type { ReactNode } from "react";

type Props = {
  open: boolean;
  title: string;
  onClose: () => void;
  children: ReactNode;
  width?: number;
};

export default function Modal({ open, title, onClose, children, width = 460 }: Props) {
  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 px-4" onMouseDown={onClose}>
      <div
        className="w-full rounded-xl border border-line bg-panel shadow-2xl"
        style={{ maxWidth: width }}
        onMouseDown={(event) => event.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b border-line px-4 py-3">
          <h3 className="text-[13px] font-medium">{title}</h3>
          <button
            type="button"
            onClick={onClose}
            className="rounded-md px-2 py-0.5 text-[16px] leading-none text-muted hover:bg-panel-2 hover:text-ink"
            aria-label="关闭"
          >
            ×
          </button>
        </div>
        <div className="px-4 py-4">{children}</div>
      </div>
    </div>
  );
}
