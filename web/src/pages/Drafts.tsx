import Page from "../components/Page";

export default function Drafts() {
  return (
    <Page
      title="写稿"
      description="从内容库选一条素材，交给本地 agent 改写。左边是草稿队列，右边是编辑区。"
    >
      <div className="grid min-h-[460px] gap-4 lg:grid-cols-[260px_1fr]">
        <aside className="rounded-xl border border-line bg-panel p-3">
          <div className="mb-2 flex items-center justify-between px-1">
            <span className="text-[12px] font-medium">草稿</span>
            <span className="text-[11px] text-muted">0</span>
          </div>
          <div className="rounded-lg border border-dashed border-line px-3 py-6 text-center text-[11px] text-muted">
            还没有草稿
          </div>
        </aside>

        <section className="flex flex-col rounded-xl border border-line bg-panel">
          <div className="flex items-center justify-between border-b border-line px-4 py-2.5">
            <span className="text-[12px] text-muted">编辑区</span>
            <div className="flex gap-2">
              <button
                type="button"
                className="rounded-md border border-line px-2.5 py-1 text-[11px] text-muted"
                disabled
              >
                交给 agent
              </button>
              <button
                type="button"
                className="rounded-md bg-accent px-2.5 py-1 text-[11px] font-medium text-white opacity-60"
                disabled
              >
                保存
              </button>
            </div>
          </div>
          <div className="flex flex-1 flex-col gap-3 px-4 py-4">
            <div className="h-8 w-3/4 rounded bg-panel-2" />
            <div className="h-3 w-full rounded bg-panel-2" />
            <div className="h-3 w-11/12 rounded bg-panel-2" />
            <div className="h-3 w-10/12 rounded bg-panel-2" />
            <div className="h-3 w-9/12 rounded bg-panel-2" />
            <p className="mt-auto text-[11px] text-muted">P4 接上草稿接口和 agent 之后，这里可以编辑正文、换封面、调顺序。</p>
          </div>
        </section>
      </div>
    </Page>
  );
}
