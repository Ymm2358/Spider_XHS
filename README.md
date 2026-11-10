# xhs-ops

把小红书的数据接进本地 agent：浏览时自动采集，桌面端看分析，需要时让 agent 写稿。

上游的签名与接口来自 [Spider_XHS](https://github.com/cv-cat/Spider_XHS)，原样放在 `vendor/spider_xhs/`，不修改。

## 项目结构

```
xhs-ops/
├── README.md                 项目说明
├── opencode.jsonc            opencode 配置：默认模型、agent 规则入口
├── requirements-xhsops.txt   本项目自己的 Python 依赖
├── .env                      本地密钥（Cookie），不进 git
├── .env.example              配置模板
├── issue.md                  当前问题与待解决项，每天开工先读
├── targets.md                目标、阶段计划、当前进度
│
├── xhsops/                   业务层
│   ├── __init__.py           包初始化，把 vendor 加进 sys.path
│   ├── __main__.py           让 python -m xhsops 可运行
│   ├── cli.py                命令行入口，所有子命令在这里分发
│   ├── config.py             路径、.env、Cookie 校验、YAML 配置
│   ├── collect.py            调上游接口采集关键词和用户主页
│   ├── ingest.py             解析插件送来的原始响应
│   ├── normalize.py          统一字段，解析「1.2万」「3天前」
│   ├── store.py              SQLite 建表与读写
│   ├── metrics.py            加权互动、log 空间 z、蓝海指数、素人率
│   ├── report.py             生成 brief.md 和 brief.json
│   ├── render.py             渲染 HTML 报告（完整版 / 分享卡）
│   ├── export.py             调浏览器无头模式，输出 PDF / PNG
│   ├── enrich.py             补作者粉丝数
│   ├── login.py              扫码登录，写回 .env
│   ├── AGENTS.md             给 agent 的选题规则
│   ├── adapters/             唯一与上游耦合的层
│   │   └── xhs_runtime.py    构造登录态、调用接口、错误归一
│   ├── web/                  本地服务（FastAPI）
│   │   └── app.py            接收插件数据，/health、/stats、/ingest
│   └── docs/                 接口样例与迁移约定
│
├── extension/                浏览器插件（MV3）
│   ├── manifest.json         权限与注入规则
│   ├── inject.js             主世界 hook fetch/XHR，只复制白名单接口
│   ├── content.js            隔离世界，转发消息
│   ├── background.js         批量上报、断线队列、暂停开关
│   ├── popup.html/js         状态、token、开关
│   └── README.md             安装与排查
│
├── config/                   可调配置
│   ├── keywords.yml          方向、关键词、focus、采集档位
│   ├── weights.yml           互动权重、爆款阈值、素人阈值
│   ├── competitors.yml       对标账号
│   └── persona.md            账号调性：活人感、语气、禁区
│
├── scripts/
│   ├── run_daily.ps1         每日采集 → 指标 → 日报 → agent → PDF
│   ├── start_server.bat      启动本地服务
│   ├── install_task.ps1      注册 Windows 计划任务（需管理员）
│   └── sync_upstream.ps1     同步上游到 vendor，doctor 门禁
│
├── vendor/spider_xhs/        上游快照，不手改，由同步脚本整层替换
│   ├── apis/                 PC 端与创作者平台接口
│   ├── xhs_utils/            签名、鉴权、JS 运行时
│   ├── UPSTREAM_COMMIT       当前对应的上游 commit
│   └── requirements.txt      上游依赖
│
├── data/                     SQLite、原始响应、插件 token（不进 git）
├── reports/                  日报、PDF、分享图（不进 git）
├── drafts/                   稿件（不进 git）
└── logs/                     每日运行日志（不进 git）
```

数据流：

```
插件 / 采集 → normalize → store → metrics → report / render → export
                  ↑
            vendor/spider_xhs（签名与接口）
```

`report.py` 出 markdown，`render.py` 出 HTML，再由 `export.py` 转 PDF 和图片。agent 读的是 `brief.json`，不读 markdown。

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
