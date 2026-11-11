import Empty from "../components/Empty";
import Page from "../components/Page";

const TABS = ["关键词搜索", "笔记链接", "用户主页", "插件数据"];

export default function Collect() {
  return (
    <Page
      title="采集"
      description="按关键词、笔记链接或用户主页抓取内容。插件被动采集到的数据也会汇总在这里。"
    >
      <div className="rounded-xl border border-line bg-panel p-4">
        <div className="flex flex-wrap items-center gap-2">
          <input
            className="min-w-[240px] flex-1 rounded-lg border border-line bg-bg px-3 py-2 text-[12px] text-ink outline-none placeholder:text-muted focus:border-accent/60"
            placeholder="输入关键词，比如：日常记录"
            disabled
          />
          <button
            type="button"
            className="rounded-lg bg-accent px-4 py-2 text-[12px] font-medium text-white opacity-60"
            disabled
          >
            开始采集
          </button>
        </div>
        <div className="mt-3 flex flex-wrap gap-1.5">
          {TABS.map((tab, index) => (
            <span
              key={tab}
              className={[
                "rounded-full border px-2.5 py-1 text-[11px]",
                index === 0 ? "border-accent/50 bg-accent-soft text-white" : "border-line text-muted"
              ].join(" ")}
            >
              {tab}
            </span>
          ))}
        </div>
      </div>

      <Empty
        title="还没有采集任务"
        description="P4 接上后端 /api/xhs/crawl/* 之后，这里会显示任务进度和入库结果。"
      />
    </Page>
  );
}
