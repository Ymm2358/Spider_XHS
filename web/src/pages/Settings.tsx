import Page from "../components/Page";

const SECTIONS = [
  { title: "模型", desc: "OpenAI 兼容接口、模型名、密钥。写稿和改写都用这里。" },
  { title: "Cookie", desc: "扫码续期、导入、过期提醒。" },
  { title: "采集", desc: "关键词、频率、请求间隔、代理。" },
  { title: "导出", desc: "PDF 模板、分享图尺寸、输出目录。" },
  { title: "关于", desc: "版本、数据目录、日志位置。" }
];

export default function Settings() {
  return (
    <Page title="设置" description="本地配置。改完即时生效，不需要重启前端。">
      <div className="grid gap-3 md:grid-cols-2">
        {SECTIONS.map((section) => (
          <section key={section.title} className="rounded-xl border border-line bg-panel px-4 py-4">
            <div className="flex items-center justify-between">
              <h3 className="text-[13px] font-medium">{section.title}</h3>
              <span className="text-[11px] text-muted">未接入</span>
            </div>
            <p className="mt-2 text-[11px] leading-5 text-muted">{section.desc}</p>
          </section>
        ))}
      </div>
    </Page>
  );
}
