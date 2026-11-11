import { useCallback, useEffect, useState } from "react";

import AddAccountDialog from "../components/account/AddAccountDialog";
import Empty from "../components/Empty";
import Modal from "../components/Modal";
import Page from "../components/Page";
import { api } from "../lib/api";
import type { Account, Page as PageData } from "../lib/types";

const STATUS_META: Record<string, { text: string; dot: string }> = {
  active: { text: "正常", dot: "bg-emerald-400" },
  ok: { text: "正常", dot: "bg-emerald-400" },
  expired: { text: "已过期", dot: "bg-red-400" },
  invalid: { text: "已失效", dot: "bg-red-400" },
  unknown: { text: "未检查", dot: "bg-muted" }
};

function statusOf(status: string) {
  return STATUS_META[status] ?? { text: status || "未知", dot: "bg-muted" };
}

function typeOf(subType: string) {
  return subType === "creator" ? "发布" : "采集";
}

function formatTime(value: string | null) {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString("zh-CN", { hour12: false });
}

export default function Accounts() {
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [open, setOpen] = useState(false);
  const [busyId, setBusyId] = useState<number | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const data = await api.get<PageData<Account>>("/accounts?platform=xhs");
      setAccounts(data.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const check = async (account: Account) => {
    setBusyId(account.id);
    try {
      await api.post(`/accounts/${account.id}/check`);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusyId(null);
    }
  };

  const remove = async (account: Account) => {
    if (!window.confirm(`删除账号「${account.nickname || account.id}」？本地保存的 Cookie 会一起删掉。`)) {
      return;
    }
    setBusyId(account.id);
    try {
      await api.delete(`/accounts/${account.id}`);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusyId(null);
    }
  };

  return (
    <Page
      title="账号"
      description="采集账号和发布账号可以分开绑定。采集建议用小号，发布用主号的创作者平台。"
      actions={
        <button
          type="button"
          onClick={() => setOpen(true)}
          className="rounded-lg bg-accent px-3 py-1.5 text-[12px] font-medium text-white"
        >
          添加账号
        </button>
      }
    >
      {error && (
        <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-[12px] text-red-300">
          {error}
        </div>
      )}

      {loading ? (
        <div className="rounded-xl border border-line bg-panel px-4 py-10 text-center text-[12px] text-muted">
          加载中…
        </div>
      ) : accounts.length === 0 ? (
        <Empty
          title="还没有绑定账号"
          description="扫码或导入 Cookie 之后，这里会显示账号状态、类型和最近检查时间。"
          action={
            <button
              type="button"
              onClick={() => setOpen(true)}
              className="rounded-lg border border-line px-3 py-1.5 text-[12px] text-muted hover:text-ink"
            >
              添加第一个账号
            </button>
          }
        />
      ) : (
        <div className="grid gap-3 md:grid-cols-2">
          {accounts.map((account) => {
            const meta = statusOf(account.status);
            return (
              <article key={account.id} className="rounded-xl border border-line bg-panel p-4">
                <div className="flex items-start gap-3">
                  <div className="flex h-10 w-10 shrink-0 items-center justify-center overflow-hidden rounded-full bg-panel-2 text-[13px] text-muted">
                    {account.avatar_url ? (
                      <img src={account.avatar_url} alt="" className="h-full w-full object-cover" />
                    ) : (
                      (account.nickname || "?").slice(0, 1)
                    )}
                  </div>

                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <span className="truncate text-[13px] font-medium">
                        {account.nickname || "未命名账号"}
                      </span>
                      <span className="rounded border border-line px-1.5 py-0.5 text-[10px] text-muted">
                        {typeOf(account.sub_type)}
                      </span>
                    </div>
                    <div className="mt-1 flex items-center gap-1.5 text-[11px] text-muted">
                      <span className={`inline-block h-1.5 w-1.5 rounded-full ${meta.dot}`} />
                      {meta.text}
                      <span className="text-line">·</span>
                      <span>检查于 {formatTime(account.updated_at)}</span>
                    </div>
                    {account.status_message && (
                      <p className="mt-1 truncate text-[11px] text-muted">{account.status_message}</p>
                    )}
                  </div>
                </div>

                <div className="mt-3 flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => void check(account)}
                    disabled={busyId === account.id}
                    className="rounded-md border border-line px-2.5 py-1 text-[11px] text-muted hover:text-ink disabled:opacity-40"
                  >
                    {busyId === account.id ? "检查中…" : "检查状态"}
                  </button>
                  <button
                    type="button"
                    onClick={() => void remove(account)}
                    disabled={busyId === account.id}
                    className="rounded-md border border-line px-2.5 py-1 text-[11px] text-muted hover:border-red-500/40 hover:text-red-300 disabled:opacity-40"
                  >
                    删除
                  </button>
                </div>
              </article>
            );
          })}
        </div>
      )}

      <Modal open={open} title="添加账号" onClose={() => setOpen(false)}>
        <AddAccountDialog
          onDone={() => {
            setOpen(false);
            void load();
          }}
        />
      </Modal>
    </Page>
  );
}
