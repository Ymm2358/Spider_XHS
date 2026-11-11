import Page from "../components/Page";
import StatCard from "../components/StatCard";

export default function Overview() {
  return (
    <Page
      title="今天"
      description="数据接入后会在这里显示：采集量、账号状态、待发布任务、昨日互动变化。"
    >
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <StatCard label="今日采集" value="—" hint="等待接入" />
        <StatCard label="内容库" value="—" hint="等待接入" />
        <StatCard label="待发布" value="—" hint="等待接入" />
        <StatCard label="账号健康" value="—" hint="等待接入" />
      </div>

      <div className="grid gap-4 lg:grid-cols-[1.4fr_1fr]">
        <section className="rounded-xl border border-line bg-panel p-5">
          <div className="flex items-center justify-between">
            <h3 className="text-[13px] font-medium">互动趋势</h3>
            <span className="text-[11px] text-muted">近 7 天</span>
          </div>
          <div className="mt-4 flex h-[180px] items-end gap-2">
            {[38, 52, 44, 66, 58, 74, 62].map((height, index) => (
              <div
                key={index}
                className="flex-1 rounded-t bg-panel-2"
                style={{ height: `${height}%` }}
              />
            ))}
          </div>
          <p className="mt-3 text-[11px] text-muted">占位图，接入指标后替换为真实折线。</p>
        </section>

        <section className="rounded-xl border border-line bg-panel p-5">
          <h3 className="text-[13px] font-medium">待处理</h3>
          <ul className="mt-3 flex flex-col gap-2 text-[12px] text-muted">
            <li className="flex items-center justify-between rounded-lg bg-panel-2 px-3 py-2">
              <span>Cookie 即将过期</span>
              <span className="text-muted">—</span>
            </li>
            <li className="flex items-center justify-between rounded-lg bg-panel-2 px-3 py-2">
              <span>待审核草稿</span>
              <span className="text-muted">—</span>
            </li>
            <li className="flex items-center justify-between rounded-lg bg-panel-2 px-3 py-2">
              <span>失败任务</span>
              <span className="text-muted">—</span>
            </li>
          </ul>
        </section>
      </div>
    </Page>
  );
}
