# xhs-ops

把小红书的数据接进本地 agent：浏览时自动采集，桌面端看分析，需要时让 agent 写稿。

上游的签名与接口来自 [Spider_XHS](https://github.com/cv-cat/Spider_XHS)，原样放在 `vendor/spider_xhs/`，不修改。

## 目录

```
xhsops/                业务层：采集、指标、日报、导出、本地服务
extension/             浏览器插件（MV3），被动复制页面接口响应
config/                方向、关键词、权重、对标账号
scripts/               每日任务、上游同步、启动脚本
data/                  SQLite、原始响应归档（不入库）
reports/               日报、PDF、分享图（不入库）
drafts/                稿件（不入库）
vendor/spider_xhs/     上游快照，由同步脚本整层替换
```

## 快速开始

```
python -m venv .venv
.venv\Scripts\pip install -r vendor\spider_xhs\requirements.txt -r requirements-xhsops.txt
cd vendor\spider_xhs && npm install && cd ..\..

copy .env.example .env
:: 填入 XHS_PC_COOKIE
.venv\Scripts\python -m xhsops doctor
```

## 日常使用

```
# Cookie 失效时重新扫码，自动写回 .env
.venv\Scripts\python -m xhsops login

# 启动本地服务，插件的数据往这里送
.venv\Scripts\python -m xhsops serve

# 采集 + 指标 + 日报 + PDF
powershell -ExecutionPolicy Bypass -File scripts\run_daily.ps1

# 只重新导出 PDF / 分享图
.venv\Scripts\python -m xhsops export
```

产物：

- `reports/日期/brief.json` 结构化数据，agent 只读这个
- `reports/日期/brief.pdf` 完整报告
- `reports/日期/summary.png` 分享图
- `reports/日期/advice.md` agent 写的选题建议

## 上游同步

```
powershell -ExecutionPolicy Bypass -File scripts\sync_upstream.ps1          # 只看
powershell -ExecutionPolicy Bypass -File scripts\sync_upstream.ps1 -Apply   # 替换并验证
```

同步会整层替换 `vendor/spider_xhs/`，跑 `doctor` 验证签名，通过才提交。失败就 `git reset --hard ORIG_HEAD`，不会污染主分支。

## 注意

- 采集建议用小号，主号只做被动采集。
- 不要把小红书流量挂代理，出口 IP 突变会提高风控概率。
- Cookie 会过期，`doctor` 会直接告诉你。
