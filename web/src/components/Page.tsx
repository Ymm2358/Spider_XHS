import type { ReactNode } from "react";

type Props = {
  title?: string;
  description?: string;
  actions?: ReactNode;
  children: ReactNode;
};

export default function Page({ title, description, actions, children }: Props) {
  return (
    <div className="mx-auto flex w-full max-w-[1180px] flex-col gap-5">
      {(title || description || actions) && (
        <div className="flex items-start justify-between gap-4">
          <div>
            {title && <h2 className="text-[18px] font-medium">{title}</h2>}
            {description && <p className="mt-1 text-[12px] leading-5 text-muted">{description}</p>}
          </div>
          {actions && <div className="flex shrink-0 items-center gap-2">{actions}</div>}
        </div>
      )}
      {children}
    </div>
  );
}
