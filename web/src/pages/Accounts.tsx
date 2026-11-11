import Empty from "../components/Empty";
import Page from "../components/Page";

export default function Accounts() {
  return (
    <Page
      title="账号"
      description="扫码或导入 Cookie 绑定账号。绑定后可以查看登录状态、健康巡检结果和最近使用时间。"
      actions={
        <button
          type="button"
          className="rounded-lg bg-accent px-3 py-1.5 text-[12px] font-medium text-white opacity-60"
          disabled
        >
          添加账号
        </button>
      }
    >
      <Empty
        title="还没有绑定账号"
        description="P4 会把这里接上扫码登录和 Cookie 导入。现在只是外壳，按钮还没有行为。"
      />
    </Page>
  );
}
