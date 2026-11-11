import Empty from "../components/Empty";
import Page from "../components/Page";

const COLUMNS = ["草稿", "账号", "状态", "时间"];

export default function Publish() {
  return (
    <Page
      title="发布"
      description="选草稿、选账号、确认内容，再提交到创作者平台。支持立即发布和定时。"
      actions={
        <button
          type="button"
          className="rounded-lg bg-accent px-3 py-1.5 text-[12px] font-medium text-white opacity-60"
          disabled
        >
          新建发布
        </button>
      }
    >
      <div className="overflow-hidden rounded-xl border border-line bg-panel">
        <div className="grid grid-cols-[2fr_1fr_1fr_1fr] gap-2 border-b border-line px-4 py-2.5 text-[11px] text-muted">
          {COLUMNS.map((column) => (
            <span key={column}>{column}</span>
          ))}
        </div>
        <div className="px-4 py-10">
          <Empty title="没有发布任务" description="P4 接上 /api/publish/jobs 之后，这里会显示队列、状态和失败原因。" />
        </div>
      </div>
    </Page>
  );
}
