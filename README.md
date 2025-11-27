# 企业信息爬虫工具集

本项目提供了一系列用于查询企业信息、股东结构、法定代表人、失信记录、裁判文书和计算、判断受益所有人的自动化爬虫工具。

## 📋 目录

- [环境要求](#环境要求)
- [Windows 安装指南](#windows-安装指南)
- [快速开始](#快速开始)
- [脚本说明](#脚本说明)
- [常见问题](#常见问题)

## 🔧 环境要求

- **Python**: 3.12.7
- **Chrome 浏览器**: 最新版本（用于 Selenium 自动化）
- **操作系统**: Windows 10/11

## 💻 Windows 安装指南

### 步骤 1: 安装 Python

1. 访问 [Python 官网](https://www.python.org/downloads/)
2. 下载 Python 3.8 或更高版本的 Windows 安装程序（推荐 Python 3.12.7）
3. 运行安装程序，**重要**：勾选 **"Add Python to PATH"**（将 Python 添加到系统路径）
4. 点击 "Install Now" 完成安装

### 步骤 2: 验证 Python 安装

打开 **命令提示符**（按 `Win + R`，输入 `cmd`，按回车），运行：

```bash
python --version
```

如果显示 Python 版本号（如 `Python 3.12.7`），说明安装成功。

### 步骤 3: 安装 Chrome 浏览器

1. 访问 [Chrome 官网](https://www.google.com/chrome/)
2. 下载并安装 Chrome 浏览器
3. 确保 Chrome 已更新到最新版本

### 步骤 4: 安装项目依赖

1. 打开命令提示符（`Win + R` → `cmd`）
2. 使用 `cd` 命令进入项目目录：

```bash
cd C:\Users\你的用户名\Documents\founders
```

（请将路径替换为你的实际项目路径）

3. 安装依赖包：

```bash
pip install -r requirements.txt
```

如果遇到权限问题，可以尝试：

```bash
python -m pip install -r requirements.txt
```

### 步骤 5: 安装 ChromeDriver（自动管理）

本项目使用 `webdriver-manager` 自动管理 ChromeDriver，通常无需手动安装。如果遇到问题，请参考[常见问题](#常见问题)部分。

## 🚀 快速开始

### ✨‼️ 全局脚本信息一次性爬取使用

#### 1. 确保企查查账号同时无其他人使用

公司注册的企查查账号是单人vip账号，官方不支持多人使用。

即：账号原先一个电脑上登录，此时另外一台电脑登录了同一个账号，会导致第一个电脑上的登录失效。

#### 2. 获取 + 修改 cookie

 > cookie 是账号登录密钥，通行密钥，（经程序编写）是企查查网站上通过人机验证的密钥



### 单个脚本使用

#### 1. AMAC 企业信息查询 (`amac.py`)

查询中国证券投资基金业协会的企业信息：

```bash
python amac.py "公司名称"
```

或直接运行后输入：

```bash
python amac.py
```

**输出**：
- 截图保存到：`桌面/公司名称/证监会_公司名称_时间戳.png`
- JSON 数据保存到：`桌面/公司名称/公司名称.json`

#### 2. 企查查股东结构查询 (`nested_judge/qcc_nested.py`)

查询公司股东结构（支持多层穿透）：

```bash
python nested_judge/qcc_nested.py "公司名称"
```

**输出**：
- 截图保存到：`桌面/公司名称/企查查_公司名称_时间戳.png`
- JSON 数据包含完整的股东结构信息

#### 3. 失信记录查询 (`neris.py`)

查询法定代表人的失信记录：

```bash
python neris.py "法定代表人姓名"
```

**输出**：
- 截图保存到：`桌面/姓名/CSRC_失信查询_姓名_时间戳.png`
- JSON 数据保存到：`桌面/姓名/姓名.json`

#### 4. 裁判文书查询 (`wenshu.py`)

查询裁判文书：

```bash
python wenshu.py "关键词"
```

**输出**：
- 截图保存到：`桌面/关键词/WENSHU_查询_关键词_时间戳.png`
- JSON 数据保存到：`桌面/关键词/关键词.json`

### 一键流程 (`company_pipeline.py`)

自动执行完整的查询流程：

```bash
python company_pipeline.py "公司名称"
```

**流程**：
1. 通过 AMAC 查询公司基本信息
2. 通过企查查查询股东结构并计算受益所有人
3. 查询法定代表人和受益所有人的失信记录
4. 查询相关裁判文书

## 📝 脚本说明

### `amac.py`
- **功能**: 查询中国证券投资基金业协会的企业信息
- **输入**: 公司名称
- **输出**: 企业信息 JSON + 截图

### `nested_judge/qcc_nested.py`
- **功能**: 查询企查查的股东结构（支持多层穿透）
- **输入**: 公司名称
- **输出**: 股东结构 JSON + 截图
- **注意**: 需要有效的企查查 Cookie（见脚本内注释）

### `neris.py`
- **功能**: 查询证监会失信记录
- **输入**: 法定代表人姓名
- **输出**: 失信记录 JSON + 截图

### `wenshu.py`
- **功能**: 查询中国裁判文书网
- **输入**: 搜索关键词
- **输出**: 查询结果 JSON + 截图
- **注意**: 需要登录，脚本会自动处理登录流程

### `company_pipeline.py`
- **功能**: 一键执行完整查询流程
- **输入**: 公司名称
- **输出**: 所有相关信息的 JSON 和截图

## ❓ 常见问题

### Q1: 提示 "python 不是内部或外部命令"

**解决方案**：
1. 重新安装 Python，确保勾选 "Add Python to PATH"
2. 或手动添加 Python 到系统路径：
   - 右键"此电脑" → "属性" → "高级系统设置" → "环境变量"
   - 在"系统变量"中找到 `Path`，添加 Python 安装路径（如 `C:\Python311` 和 `C:\Python311\Scripts`）

### Q2: 提示 "pip 不是内部或外部命令"

**解决方案**：
```bash
python -m pip install -r requirements.txt
```

### Q3: ChromeDriver 相关错误

**解决方案**：
1. 确保 Chrome 浏览器已安装并更新到最新版本
2. 项目使用 `webdriver-manager` 自动管理，通常无需手动操作
3. 如果仍有问题，检查网络连接（需要下载 ChromeDriver）

### Q4: 提示 "无法找到模块 selenium"

**解决方案**：
```bash
pip install selenium
```

或重新安装所有依赖：
```bash
pip install -r requirements.txt
```

### Q5: 企查查需要登录怎么办？

**解决方案**：
1. 手动登录企查查网站
2. 使用浏览器开发者工具（F12）获取 Cookie
3. 修改 `nested_judge/qcc_nested.py` 中的 `DEFAULT_COOKIES` 字典
4. 注意：因为多人使用同一账号不被官方支持，账号登录存在一定问题，Cookie 会过期，需要每次使用中更新

### Q6: 脚本运行很慢

**原因**：
- 脚本使用真实浏览器自动化，需要等待页面加载
- 某些网站有反爬虫机制，需要模拟人类操作

**建议**：
- 耐心等待，不要频繁运行
- 避免同时运行多个脚本实例

### Q7: 截图保存位置

所有截图和 JSON 文件默认保存在 **桌面**，按公司名称或查询关键词创建文件夹。

### Q8: 代理设置问题

如果遇到网络连接问题，脚本会自动清除系统代理设置。如果使用 VPN 或代理，可能需要：
1. 暂时关闭代理
2. 或修改脚本中的代理清除逻辑

## 📦 依赖包说明

- **selenium**: 浏览器自动化框架
- **webdriver-manager**: 自动管理 ChromeDriver
- **beautifulsoup4**: HTML 解析
- **requests**: HTTP 请求库
- **lxml**: XML/HTML 解析器

## ⚠️ 注意事项

1. **Cookie 管理**: 某些脚本需要有效的 Cookie，需要定期更新
2. **并发限制**: 不要同时运行多个爬虫实例，可能导致账号被限制
3. **合规使用**: 请遵守网站的使用条款，合理使用爬虫工具
4. **数据准确性**: 爬取的数据仅供参考，请以官方数据为准

## 📞 技术支持

如遇到问题，请检查：
1. Python 版本是否符合要求
2. 所有依赖是否已正确安装
3. Chrome 浏览器是否已安装
4. 网络连接是否正常

## 📄 许可证

本项目仅供学习和研究使用。
