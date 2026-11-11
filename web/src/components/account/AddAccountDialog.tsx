import { useCallback, useEffect, useState } from "react";

import { api } from "../../lib/api";
import type { LoginSession } from "../../lib/types";

const STATUS_TEXT: Record<string, string> = {
  pending: "等待扫码",
  scanned: "已扫码，请在手机上确认",
  confirmed: "已确认，正在写入账号",
  expired: "二维码已过期，请刷新"
};

type Props = {
  onDone: () => void;
};

export default function AddAccountDialog({ onDone }: Props) {
  const [tab, setTab] = useState<"qr" | "cookie">("qr");

  return (
    <div>
      <div className="mb-4 flex gap-1 rounded-lg bg-bg p-1">
        {[
          { key: "qr", label: "扫码登录" },
          { key: "cookie", label: "导入 Cookie" }
        ].map((item) => (
          <button
            key={item.key}
            type="button"
            onClick={() => setTab(item.key as "qr" | "cookie")}
            className={[
              "flex-1 rounded-md px-3 py-1.5 text-[12px] transition-colors",
              tab === item.key ? "bg-panel-2 text-ink" : "text-muted hover:text-ink"
            ].join(" ")}
          >
            {item.label}
          </button>
        ))}
      </div>

      {tab === "qr" ? <QrLogin onDone={onDone} /> : <CookieImport onDone={onDone} />}
    </div>
  );
}

function QrLogin({ onDone }: Props) {
  const [session, setSession] = useState<LoginSession | null>(null);
  const [status, setStatus] = useState("pending");
  const [error, setError] = useState("");
  const [starting, setStarting] = useState(false);

  const start = useCallback(async () => {
    setStarting(true);
    setError("");
    setSession(null);
    setStatus("pending");
    try {
      const res = await api.post<LoginSession>("/xhs/login-sessions/pc/qrcode", { sync_creator: false });
      setSession(res);
      setStatus(res.status || "pending");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setStarting(false);
    }
  }, []);

  useEffect(() => {
    void start();
  }, [start]);

  useEffect(() => {
    if (!session || status === "confirmed" || status === "expired") return;
    const timer = window.setInterval(async () => {
      try {
        const res = await api.get<LoginSession>(`/xhs/login-sessions/${session.session_id}`);
        setStatus(res.status);
        if (res.status === "confirmed") {
          window.clearInterval(timer);
          onDone();
        }
        if (res.status === "expired") {
          window.clearInterval(timer);
        }
      } catch {
        // 单次轮询失败不打断，下一轮继续
      }
    }, 2000);
    return () => window.clearInterval(timer);
  }, [session, status, onDone]);

  return (
    <div className="flex flex-col items-center gap-3">
      <div className="flex h-[220px] w-[220px] items-center justify-center rounded-lg border border-line bg-white">
        {session?.qr_image_data_url ? (
          <img src={session.qr_image_data_url} alt="登录二维码" className="h-[200px] w-[200px]" />
        ) : (
          <span className="text-[12px] text-muted">{starting ? "生成中…" : "没有二维码"}</span>
        )}
      </div>

      <div className="text-center text-[12px] text-muted">
        {STATUS_TEXT[status] ?? status}
      </div>

      {error && <div className="text-center text-[12px] text-red-400">{error}</div>}

      <button
        type="button"
        onClick={() => void start()}
        className="rounded-lg border border-line px-3 py-1.5 text-[12px] text-muted hover:text-ink"
      >
        刷新二维码
      </button>

      <p className="text-center text-[11px] leading-5 text-muted">
        用小红书 App 扫码并在手机上确认。登录态只保存在本机。
      </p>
    </div>
  );
}

function CookieImport({ onDone }: Props) {
  const [cookie, setCookie] = useState("");
  const [syncCreator, setSyncCreator] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const submit = async () => {
    setBusy(true);
    setError("");
    try {
      await api.post("/accounts/import-cookie", {
        platform: "xhs",
        sub_type: "pc",
        cookie_string: cookie.trim(),
        sync_creator: syncCreator
      });
      onDone();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="flex flex-col gap-3">
      <label className="text-[11px] text-muted">完整 Cookie 请求头，必须包含 a1 和 web_session</label>
      <textarea
        value={cookie}
        onChange={(event) => setCookie(event.target.value)}
        rows={6}
        placeholder="a1=...; web_session=...; ..."
        className="w-full resize-none rounded-lg border border-line bg-bg px-3 py-2 text-[12px] text-ink outline-none placeholder:text-muted focus:border-accent/60"
      />

      <label className="flex items-center gap-2 text-[12px] text-muted">
        <input
          type="checkbox"
          checked={syncCreator}
          onChange={(event) => setSyncCreator(event.target.checked)}
          className="h-3.5 w-3.5 accent-[var(--color-accent)]"
        />
        同时同步创作者平台（发布用）
      </label>

      {error && <div className="text-[12px] text-red-400">{error}</div>}

      <button
        type="button"
        onClick={() => void submit()}
        disabled={busy || cookie.trim().length < 10}
        className="rounded-lg bg-accent px-3 py-2 text-[12px] font-medium text-white disabled:opacity-40"
      >
        {busy ? "验证中…" : "导入"}
      </button>
    </div>
  );
}
