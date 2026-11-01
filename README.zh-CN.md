# 前端审美（Frontend Aesthetics）

一个用于"让视觉决策有依据"的 agent 技能：先写 brief，再定方向，最后用可以跑的工具验证。它与官方 `frontend-design` 技能配合使用——后者提供立场（选定方向、不做没人选过的默认值），本技能提供决策规则、先例数据和检查手段。

支持 Claude Code、ZCode、Cursor、OpenAI Codex、VS Code Copilot，以及任何读取 Agent Skills 格式（`<技能名>/SKILL.md`）的 agent。需要 Python 3.9 或更高版本；脚本只用标准库，不联网。

## 解决什么问题

AI 生成的界面通常坏在两处：一是长得像所有页面的平均值，二是踩了没人检查过的底线。本技能两边都管：

- 强制先写 brief 再选配色、字体和布局，并让模型为每一个保留的默认值说出理由。
- 提供九个完整方向，起始配色的对比度都是算出来的，不是估的。
- 提供三个小工具：对比度检查、产品类型先例查询、源码"AI 味"与工程缺陷扫描。

它不替代 `frontend-design`，建议两个都装。

## 安装

### 通用：任何支持 Agent Skills 的 agent

复制技能目录，确保 `SKILL.md` 的上一级目录名与技能名一致：

```
git clone https://github.com/<owner>/frontend-aesthetics
cp -r frontend-aesthetics/skills/frontend-aesthetics ~/.claude/skills/
```

| Agent | 项目级 | 用户级 |
|---|---|---|
| Claude Code | `.claude/skills/frontend-aesthetics/` | `~/.claude/skills/frontend-aesthetics/` |
| Cursor | `.cursor/skills/frontend-aesthetics/` 或 `.agents/skills/...` | `~/.cursor/skills/...` 或 `~/.agents/skills/...` |
| OpenAI Codex | `.codex/skills/frontend-aesthetics/` | `~/.codex/skills/frontend-aesthetics/` |
| VS Code Copilot | `.github/skills/frontend-aesthetics/` | `~/.copilot/skills/frontend-aesthetics/` |

目录名必须与 frontmatter 的 `name` 一致。最常见的安装失败是多套了一层目录，导致 `SKILL.md` 藏进了子目录。

多个 agent 会共享部分目录：Claude Code 与 Copilot 都会读 `.claude/skills/`，Cursor、Copilot、Codex 都能读 `.agents/skills/`。因此装进 `~/.agents/skills/` 可以一次覆盖同一台机器上的多个 agent。

也可以用 `skills` CLI 从仓库直接安装：

```
npx skills add <owner>/frontend-aesthetics --skill frontend-aesthetics
```

### Claude Code 插件

```
/plugin marketplace add <owner>/frontend-aesthetics
/plugin install frontend-aesthetics@frontend-aesthetics
```

### ZCode 插件

在插件市场中把本仓库目录（或本地 clone 的目录）添加为市场源，然后安装 **前端审美**。清单在 `.zcode-plugin/plugin.json`。

### 不安装也能用

只需要一次任务时，把 `skills/frontend-aesthetics/SKILL.md` 和该任务用到的 reference 文件一起给 agent。脚本可选，但建议使用。

## 怎么用

技能会按 description 自动触发，也可以直接点名。常用提示：

- "做设置页。先写 brief 和三条'绝不能像'，给两个方向，选一个，列出 token 块。"
- "评审这个界面：找出通用默认值痕迹和踩到的无障碍底线。"
- "现在的界面很平淡，在不破坏 token 契约的前提下重做视觉。"

装了命令后可用：

- `/design-direction 本地大模型启动器的深色优先 dashboard`
- `/design-review src/pages/settings`

一次合格的回复应包含：简短的 brief、带理由的方向、token 块，以及"验证"一节（列出执行过的命令和结果）。

## 工具

在 `skills/frontend-aesthetics/` 目录下运行：

```
python scripts/wcag.py "#1f2937" "#ffffff" "#556070" "#f6f7f9"
python scripts/design_lookup.py "saas dashboard" --ux --motion
python scripts/slop_scan.py ../../../frontend/src
```

- `wcag.py FG BG ...` 输出每对颜色的对比度，并给出 AA 正文（4.5:1）、大字号与 UI（3:1）、AAA 正文（7:1）的判定。支持 `#hex`、`rgb()`、`oklch()`；超出 sRGB 的 OKLCH 会像浏览器一样被裁切。
- `design_lookup.py "<英文关键词>"` 返回匹配的产品类型、样式、经过检查的配色、字体组合和推理规则；加 `--ux`、`--motion`、`--charts` 追加更多段落。
- `slop_scan.py PATH ...` 把发现分为 `blocking`、`important`、`review`、`polish`；存在阻断级发现时退出码为 1，可用于 CI；加 `--json` 输出机器可读结果。

Windows 上若 `python` 不可用，改用 `py -3`。

## 目录结构

```
skills/frontend-aesthetics/
  SKILL.md                  工作流、底线、品味规则、"选择测试"
  references/
    principles.md           决策顺序与 brief 模板
    directions.md           九个方向及其已验证的起始 token
    color-and-type.md       配色、暗色主题、对比度、字号比例、字体、中日韩文
    layout-and-motion.md    间距、密度、圆角、层次、动效
    components-and-states.md  状态矩阵、文案规则、极限数据测试
    desktop-app.md          WebView 与桌面应用规则
    anti-slop.md            通用痕迹、为什么像默认值、该问什么
    critique.md             评审流程、九个维度、严重度、输出格式
    sources.md              每条规则的来源，以及刻意未采用的内容
  scripts/                  wcag.py、design_lookup.py、slop_scan.py
  data/                     ui-ux-pro-max 的八个 MIT CSV 文件
commands/                   可选的斜杠命令
tests/                      仅用标准库的单元测试与夹具
```

## 验证

```
python -B -m unittest discover -s tests -v
```

测试覆盖：对比度算法对公开参考值的校验、OKLCH 与 sRGB 结果一致、产品名加权匹配，以及每条扫描规则对"缺陷夹具"的命中。测试不需要网络，也不需要浏览器。

## 已知边界

- 扫描器只发现能用规则描述的模式，不判断"好不好看"。每条发现都需要人工确认。例如 `outline: none` 只有在没有替代焦点样式时才是问题。
- 配色只是起点。192 行里只有 1 行的文字配对不达标，但有 173 行的边框低于 3:1、30 行的主色与背景低于 3:1。上线前必须复核 UI 配对。
- 视觉评审需要浏览器工具。没有时只做代码级评审，技能会明确说明，而不是猜。
- 时长、密度、断点的阈值来自经验的启发式，不是标准。属于 WCAG 的条目在 `references/sources.md` 里单独标注。

## 兼容性说明

- `SKILL.md` 的 frontmatter 带有 `description`，因为 agent 靠它决定是否加载技能。早期一些设计技能没有写 description，结果永远不会被自动选中。
- 脚本要求 Python 3.9 以上，只用标准库，在所有平台输出 UTF-8。
- 不写磁盘、不联网，因此可以在评审不受信任的仓库时安全运行。

## 许可

插件自身的代码与文档采用 MIT，见 `LICENSE`。数据文件由 Next Level Builder 以 MIT 授权，见 `THIRD_PARTY_NOTICES.md`。
