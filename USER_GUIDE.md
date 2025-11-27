# 用户使用指南

面向业务、客户成功或运营同事的快速手册，帮助你在没有开发背景的情况下独立完成一次企业尽调。按顺序完成以下步骤即可。

## 1. 准备环境
1. 打开 PowerShell（Windows）或 Terminal（macOS/Linux），进入项目目录，例如 `cd C:\Users\你\Documents\founders`。
2. 首次使用请创建虚拟环境并安装依赖：
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\activate   # macOS/Linux 运行: source .venv/bin/activate
   pip install -r requirements.txt
   ```
3. 升级 Chrome 至最新稳定版；首次运行脚本时 `webdriver-manager` 会自动下载匹配的 ChromeDriver。

## 2. 账号与 Cookie 准备
1. **企查查账号**：同一时间只能有一台机器登录。
   - 用浏览器登录后，打开开发者工具F12 → Application → Cookies，复制最新的 `QCCSESSID`、`acw_tc`、`qcc_did`，粘贴进 `nested_judge/qcc_nested.py` 和 `nested_judge/qcc_sim.py` 的 `DEFAULT_COOKIES`。
2. **裁判文书网**：`wenshu.py` 的账号密码写在 `WENSHU_ACCOUNT` 中，可按需要改成你的账号或通过环境变量读取；若官方要求验证码，请人工处理后按提示继续。所有验证码等操作一定以控制台的输出为准。
3. **CSRC / ZXGK**：脚本会自动清除代理环境变量，若必须使用代理，请在运行命令前手动设置。

## 3. 执行一键流程
1. 激活虚拟环境后运行：
   ```bash
   python company_pipeline.py
   ```
2. 程序会依次执行 AMAC → 企查查穿透 → 失信查询 → 文书网检索。
3. 结果全部写入 `~/Desktop/目标公司名称/`：
   - 截图命名为 `来源_查询词_时间戳.png`；
   - `目标公司名称.json` 会包含 AMAC、企查查、失信、文书网等条目，脚本会以 `(item, name)` 为唯一键自动覆盖旧记录。
4. 运行结束后检查终端输出是否包含 “流程结束”。若途中报错，可重试（脚本会在网络抖动时自动重试文书网 3 次）。

## 4. 单个脚本快捷入口
| 场景 | 命令示例 | 备注 |
| --- | --- | --- |
| AMAC 基本信息 | `python amac.py` | 输出 `证监会_公司_时间.png` 与 JSON |
| 企查查穿透 | `python nested_judge/qcc_nested.py` | 自动构建 `ShareholderCalculator` | 
| CSRC 失信 | `python neris.py` | 若提示人机验证，请按终端提示操作 |
| 裁判文书网 | `python wenshu.py` | 需要手动输入验证码到控制台，截图/JSON 会写到 pipeline 指定文件夹 |

## 5. 结果校验与文件管理
1. 桌面文件夹内的 JSON 可以直接用 VS Code、记事本或 Excel 打开，确认 `item`、`name`、`ret_url` 等字段。
2. 如需分享给同事，打包整个 `~/Desktop/目标公司名称/` 文件夹即可；所有截图与 JSON 已经按来源分类。
3. 如果重复运行同一个查询，脚本会覆盖对应 `(item, name)` 的记录，不会产生重复条目；如果想保留历史，可先备份旧 JSON。

## 6. 常见问题速查
- **脚本停在登录界面**：检查是否被远程登录踢下线，或 Cookie 是否过期。
- **ChromeDriver 下载失败**：确认网络可访问 Google 域名，必要时使用稳定代理。
- **无法写入桌面**：确保当前用户对 `~/Desktop` 有写权限；也可把脚本参数 `save_to_desktop=False` 并自行指定目录。

如上述步骤仍无法解决问题，请在 `README.md` 建议的渠道反馈，并附上运行命令与终端日志。
