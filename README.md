# For founders

本项目聚合了 AMAC、企查查、CSRC 失信、裁判文书网和行政公告等多个爬虫脚本，可一键获取企业基本信息、股东穿透结构、关键人物失信记录与公开裁判文书，实现券商/风控团队的快速尽调。

## 目录
- [环境要求](#环境要求)
- [安装与配置](#安装与配置)
- [快速开始](#快速开始)
- [项目结构](#项目结构)
- [脚本速查](#脚本速查)
- [Cookie 与账号注意事项](#cookie-与账号注意事项)
- [常见问题](#常见问题)
- [支持与贡献](#支持与贡献)

## 环境要求
- **Python** ≥ 3.10（推荐 3.12.7，对齐 `requirements.txt`）
- **Chrome 浏览器**：最新稳定版，需与 ChromeDriver 匹配（`webdriver-manager` 会自动拉取）
- **操作系统**：Windows 10/11（主要运行环境），macOS 13+、Linux 亦可
- **依赖**：详见 `requirements.txt`，覆盖 Selenium、requests、BeautifulSoup、lxml 等

## 安装与配置
1. **获取代码**：解压打包文件或 `git clone` 到本地（`C:\Users\<you>\Documents\founders` 为推荐路径）。
2. **创建虚拟环境**（Windows PowerShell 示例）：
   ```powershell
   cd C:\Users\<you>\Documents\founders
   python -m venv .venv
   .\.venv\Scripts\activate
   ```
   macOS/Linux：
   ```bash
   python3 -m venv .venv && source .venv/bin/activate
   ```
3. **安装依赖**：
   ```bash
   pip install -r requirements.txt
   ```
   若 `pip` 没有写权限，可改用 `python -m pip install -r requirements.txt`。
4. **Chrome & 驱动**：保持浏览器最新；`webdriver-manager` 会在首次运行时自动下载驱动，失败时请检查网络或参考 FAQ。

## 快速开始
```bash
python company_pipeline.py "杭州哲石私募基金管理有限公司"
```
该命令顺序执行 AMAC → 企查查穿透 → 失信查询 → 文书网检索，所有截图与 JSON 输出统一保存在 `~/Desktop/杭州哲石私募基金管理有限公司/` 目录。

想单独调试脚本，可使用：
- `python amac.py`
- `python nested_judge/qcc_nested.py`
- `python neris.py`
- `python wenshu.py`

## 项目结构
```
founders/
├─ amac.py                # AMAC 查询与截图
├─ company_pipeline.py    # 一键流程入口
├─ neris.py               # 证监会失信查询
├─ wenshu.py              # 裁判文书网自动化
├─ zxgk/                  # 执行公告相关脚本，*有问题不使用*
├─ nested_judge/          # 企查查穿透、计算器与单测
│  ├─ qcc_nested.py
│  ├─ qcc_sim.py
│  ├─ nested_judge.py
│  └─ test_nested.py
└─ requirements.txt
```

## 脚本速查
| 脚本 | 功能 | 典型命令 | 输出 |
| --- | --- | --- | --- |
| `company_pipeline.py` | 一键全流程 | `python company_pipeline.py` | 桌面/公司/ 下的全量截图与 JSON |
| `amac.py` | AMAC 基本信息 | `python amac.py` | 桌面/公司/证监会_*.png + JSON |
| `nested_judge/qcc_nested.py` | 企查查穿透、受益人计算 | `python nested_judge/qcc_nested.py` | 桌面/公司/企查查_*.png + 股权 JSON |
| `neris.py` | 失信记录 | `python neris.py` | 桌面/姓名/CSRC_*.png + JSON |
| `wenshu.py` | 裁判文书网搜索 | `python wenshu.py` | 桌面/关键词/WENSHU_*.png + JSON |


## Cookie 与账号注意事项
1. 企查查账号属于单人 VIP，**同一时间只能在一台机器登录**，否则旧会话会被踢出。
2. 运行前手动在浏览器完成登录并抓取 Cookie，更新 `nested_judge/qcc_nested.py` 中的 `DEFAULT_COOKIES`。
3. 文书网、CSRC 登录信息保存在脚本常量中，可改为读取环境变量或本地加密文件，但请勿提交真实账号。
4. 所有脚本运行前会清理代理变量，如需自定义代理请在运行命令前设置并知晓可能被覆盖。

## 常见问题
1. **`python/pip 不是内部命令`**：重新安装 Python 并勾选 “Add Python to PATH”，或使用 `python -m pip`。
2. **ChromeDriver 下载失败**：检查网络或手动配置 HTTP 代理；也可预先下载驱动放入 `~/.wdm`。
3. **导入 selenium 失败**：确保虚拟环境已激活，再执行 `pip install selenium`。
4. **运行缓慢**：脚本模拟真实浏览器流程（含验证码处理），请避免并发执行多个脚本。
5. **截图位置**：默认为桌面根目录，按 `公司名/关键词` 分类；可在脚本中修改 `save_to_desktop` 参数。
6. **账号频繁失效**：Cookie 会过期，建议在使用前刷新；多人协同时请建立沟通机制避免互相踢出。

## 支持与贡献
- 若需扩展功能或报告问题，请先查看 `AGENTS.md` 中的贡献指南。
- 新功能请附带运行命令、截图路径或日志，便于其他成员复现。
- 如遇无法定位的问题，可检查 Python 版本、依赖安装、Chrome 更新及网络连接，再提交 issue/反馈。

---
本项目仅供学习与研究，请确保在遵守各目标网站服务条款、合规前提下使用。
