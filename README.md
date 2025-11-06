# GP-review
Track Google Play Reviews for your apps after release and generate a short summary for each app. 

# Google Play 舆情分析系统 - 使用指南

## 📋 系统简介

这是一个自动化的Google Play应用舆情分析工具，可以：
- 监控应用更新后的用户评论
- 使用Gemini AI生成专业分析报告
- 自动生成数据可视化图表
- 支持批量分析多个应用

---

## 🚀 快速开始

### 第一步：环境准备

#### 1.1 安装Python
确保您的电脑已安装Python 3.8或更高版本。

**检查Python版本：**
```bash
python --version
# 或
python3 --version
```

**如果未安装，请访问：** https://www.python.org/downloads/

---

#### 1.2 创建项目文件夹
```bash
# 创建项目目录
mkdir google-play-monitor
cd google-play-monitor

# 创建虚拟环境（推荐）
python -m venv venv

# 激活虚拟环境
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate
```

---

#### 1.3 安装依赖包
将以下内容保存为 `requirements.txt`：

```
google-generativeai>=0.3.0
requests>=2.31.0
beautifulsoup4>=4.12.0
google-play-scraper>=1.2.0
pandas>=2.0.0
matplotlib>=3.7.0
```

然后运行：
```bash
pip install -r requirements.txt
```

**或者直接安装：**
```bash
pip install google-generativeai requests beautifulsoup4 google-play-scraper pandas matplotlib
```

---

### 第二步：获取Gemini API Key

#### 2.1 访问Google AI Studio
打开浏览器访问：https://aistudio.google.com/app/apikey

#### 2.2 创建API Key
1. 使用Google账号登录
2. 点击「Create API Key」
3. 复制生成的API Key（格式类似：`AIzaSyXXXXXXXXXXXXXXXX`）

⚠️ **重要：** 请妥善保管您的API Key，不要分享给他人。

---

### 第三步：运行程序

#### 3.1 下载脚本
将 `play_store_monitor.py` 文件放入项目文件夹。

#### 3.2 运行
```bash
python play_store_monitor.py
```

#### 3.3 按提示操作

**步骤1：输入API Key**
```
请输入您的Gemini API Key（留空则跳过AI分析）: 
```
- 粘贴您的API Key（推荐）
- 或直接回车跳过（将不使用AI分析）

**步骤2：输入应用ID**
```
输入应用ID或'file': 
```

选项：
- **单个应用**：`com.yg.mini.games`
- **多个应用（逗号）**：`com.app1,com.app2,com.app3`
- **多个应用（空格）**：`com.app1 com.app2 com.app3`
- **从文件加载**：输入 `file`，然后提供文件路径

输入完成后按**回车**（空行）继续。

---

## 📱 如何找到应用ID

1. 打开Google Play商店网页版
2. 搜索并打开目标应用
3. 查看URL，例如：
   ```
   https://play.google.com/store/apps/details?id=com.yg.mini.games
   ```
4. `id=` 后面的部分就是应用ID：`com.yg.mini.games`

---

## 📊 输出文件说明

程序运行完成后，会在当前目录生成以下文件：

### 对每个应用：
1. **`{app_id}_newsletter_{日期}.md`**
   - Markdown格式的分析报告
   - 包含AI分析和数据摘要
   - 可直接复制到邮件

2. **`{app_id}_charts.png`**
   - 数据可视化图表
   - 包含评分分布、趋势图、情感分析

### 批量分析汇总：
3. **`batch_summary_{时间戳}.txt`**
   - 所有应用的分析状态汇总
   - 成功/跳过/错误统计

---

## ⚙️ 系统规则

### 分析条件
程序只分析满足以下条件的应用：
- ✅ **7-30天内更新**：进行完整分析
- ⏭️ **7天内更新**：跳过（评论数据不足）
- ❌ **30天以上未更新**：跳过（可能已废弃）

### 分析内容
- 评论时间范围：应用最后更新日期 → 今天
- 评论来源：美国区Google Play（英文评论）
- AI分析重点：Bug报告、功能反馈、产品趋势

---

## 🔧 常见问题

### Q1: 提示"ModuleNotFoundError"
**解决方案：** 重新安装依赖
```bash
pip install --upgrade -r requirements.txt
```

### Q2: API调用超时或失败
**可能原因：**
- API Key无效或过期
- 网络连接问题
- API配额用完

**解决方案：**
1. 检查API Key是否正确
2. 访问 https://aistudio.google.com 检查配额
3. 重试或选择不使用AI分析

### Q3: 找不到应用或评论
**可能原因：**
- 应用ID错误
- 应用在美国区不可用
- 评论时间范围内无新评论

**解决方案：**
1. 确认应用ID正确
2. 检查应用在Google Play是否可访问

### Q4: 中文字体显示问题
**解决方案（Mac）：**
```bash
# 系统已安装中文字体，程序会自动尝试使用
# 如仍有问题，可安装额外字体
```

**解决方案（Windows）：**
```bash
# Windows通常自带中文字体，无需额外操作
```

---

## 💡 使用技巧

### 1. 批量分析
创建文本文件 `apps.txt`，每行一个应用ID：
```
com.app1
com.app2
com.app3
```

运行时输入 `file`，然后输入 `apps.txt`

### 2. 定时运行（可选）
**Mac/Linux（使用cron）：**
```bash
# 编辑crontab
crontab -e

# 添加定时任务（每天上午10点运行）
0 10 * * * cd /path/to/project && /path/to/venv/bin/python play_store_monitor.py
```

**Windows（使用任务计划程序）：**
1. 打开「任务计划程序」
2. 创建基本任务
3. 设置触发器（每天/每周）
4. 操作：启动程序 → 选择 `python.exe` 和脚本路径

### 3. 保存API Key（避免每次输入）
**方法1：环境变量**
```bash
# Mac/Linux
export GEMINI_API_KEY="your-api-key-here"

# Windows
set GEMINI_API_KEY=your-api-key-here
```

**方法2：配置文件**
创建 `config.json`：
```json
{
  "gemini_api_key": "your-api-key-here"
}
```

---

## 📞 技术支持

### 问题反馈
如遇到问题，请提供：
1. 错误信息截图
2. Python版本
3. 操作系统版本
4. 分析的应用ID

### 相关链接
- Google Play Scraper文档：https://github.com/JoMingyu/google-play-scraper
- Gemini API文档：https://ai.google.dev/docs
- Python官网：https://www.python.org

---

## 📄 许可声明

本工具仅供学习和研究使用。请遵守：
- Google Play服务条款
- Gemini API使用政策
- 相关数据隐私法规

**注意：** 大规模爬取可能违反服务条款，请合理使用。

---

## 🎓 快速参考卡

```
┌─────────────────────────────────────────┐
│  启动命令：python play_store_monitor.py │
├─────────────────────────────────────────┤
│  输入示例：                              │
│  • 单个：com.app.name                   │
│  • 多个：com.app1,com.app2              │
│  • 文件：file → apps.txt                │
├─────────────────────────────────────────┤
│  输出文件：                              │
│  • {app_id}_newsletter_{date}.md       │
│  • {app_id}_charts.png                 │
│  • batch_summary_{timestamp}.txt       │
├─────────────────────────────────────────┤
│  分析条件：7-30天内更新的应用           │
└─────────────────────────────────────────┘
```

---

**版本：** 1.0  
**更新日期：** 2025年1月

祝使用愉快！🎉
