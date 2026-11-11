import Page from "../components/Page";

const FILTERS = ["全部", "未分类", "日常", "摄影", "参考账号"];

export default function Library() {
  return (
    <Page
      title="内容库"
      description="采集进来的笔记统一存在这里。后面会支持标签、批量操作和导出。"
      actions={
        <button
          type="button"
          className="rounded-lg border border-line px-3 py-1.5 text-[12px] text-muted"
          disabled
        >
          导出
        </button>
      }
    >
      <div className="flex flex-wrap items-center gap-1.5">
        {FILTERS.map((filter, index) => (
          <span
            key={filter}
            className={[
              "rounded-full border px-2.5 py-1 text-[11px]",
              index === 0 ? "border-accent/50 bg-accent-soft text-white" : "border-line text-muted"
            ].join(" ")}
          >
            {filter}
          </span>
        ))}
      </div>

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
        {Array.from({ length: 8 }).map((_, index) => (
          <article key={index} className="overflow-hidden rounded-xl border border-line bg-panel">
            <div className="aspect-[4/5] bg-panel-2" />
            <div className="space-y-2 px-3 py-3">
              <div className="h-2.5 w-4/5 rounded bg-panel-2" />
              <div className="h-2.5 w-3/5 rounded bg-panel-2" />
              <div className="flex items-center justify-between pt-1 text-[10px] text-muted">
                <span>占位卡片</span>
                <span>—</span>
              </div>
            </div>
          </article>
        ))}
      </div>
    </Page>
  );
}
