import { NavLink, Outlet, useLocation } from "react-router-dom";
import { useEffect, useState } from "react";

import { getHealth } from "../lib/api";

type NavItem = { to: string; label: string; hint: string; end?: boolean };

const NAV: NavItem[] = [
  { to: "/", label: "概览", hint: "今天的数字", end: true },
  { to: "/accounts", label: "账号", hint: "登录与健康" },
  { to: "/collect", label: "采集", hint: "搜索与监控" },
  { to: "/library", label: "内容库", hint: "存下来的笔记" },
  { to: "/drafts", label: "写稿", hint: "草稿与改写" },
  { to: "/publish", label: "发布", hint: "队列与记录" },
  { to: "/settings", label: "设置", hint: "模型与偏好" }
];

function usePageTitle() {
  const { pathname } = useLocation();
  const item = NAV.find((nav) => (nav.end ? pathname === nav.to : pathname.startsWith(nav.to)));
  return item?.label ?? "页面";
}

export default function Layout() {
  const title = usePageTitle();
  const [online, setOnline] = useState<boolean | null>(null);

  useEffect(() => {
    let alive = true;
    getHealth()
      .then(() => alive && setOnline(true))
      .catch(() => alive && setOnline(false));
    return () => {
      alive = false;
    };
  }, []);

  return (
    <div className="flex h-full min-h-screen bg-bg text-ink">
      <aside className="flex w-[228px] shrink-0 flex-col border-r border-line bg-panel">
        <div className="px-5 py-5">
          <div className="text-[15px] font-semibold tracking-wide">xhs-ops</div>
          <div className="mt-1 text-[11px] text-muted">本地小红书工作台</div>
        </div>

        <nav className="flex flex-col gap-1 px-3">
          {NAV.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) =>
                [
                  "group relative flex flex-col rounded-lg px-3 py-2 transition-colors",
                  isActive ? "bg-accent-soft text-white" : "text-muted hover:bg-panel-2 hover:text-ink"
                ].join(" ")
              }
            >
              {({ isActive }) => (
                <>
                  {isActive && (
                    <span className="absolute left-0 top-2 bottom-2 w-[3px] rounded-r bg-accent" />
                  )}
                  <span className="text-[13px] font-medium">{item.label}</span>
                  <span className="mt-0.5 text-[11px] text-muted">{item.hint}</span>
                </>
              )}
            </NavLink>
          ))}
        </nav>

        <div className="mt-auto px-5 py-4 text-[11px] text-muted">
          <div className="flex items-center gap-2">
            <span
              className={[
                "inline-block h-1.5 w-1.5 rounded-full",
                online === null ? "bg-muted" : online ? "bg-emerald-400" : "bg-red-400"
              ].join(" ")}
            />
            {online === null ? "检查服务…" : online ? "本地服务已连接" : "本地服务未启动"}
          </div>
          <div className="mt-1">v0.1.0</div>
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-14 shrink-0 items-center justify-between border-b border-line px-6">
          <h1 className="text-[15px] font-medium">{title}</h1>
          <div className="flex items-center gap-3">
            <span className="rounded-full border border-line px-2.5 py-1 text-[11px] text-muted">本地模式</span>
          </div>
        </header>

        <main className="min-h-0 flex-1 overflow-auto px-6 py-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
