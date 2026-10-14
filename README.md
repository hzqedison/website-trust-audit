# 官网信任评审技能

技能版本：**0.1.0-draft**。

`website-trust-audit` 是用于软件官网信任、下载、安装与付费评审的 Codex 技能。它帮助维护者区分直接观察、官网自述、第三方资料、评审推断和用户需求。

## 工作模式

- 整理信息基线：记录现有证据和缺口，不默认提出改版、排名或评分。
- 指定范围复测/对比：只检查用户定义的站点、页面、语言、设备和层级。
- 需求澄清与 SPEC：按五章结构整理，未知项保持待确认。

入口见 [`SKILL.md`](SKILL.md)。模板、证据结构、离线验证器、协作和分发约定均随包提供。示例数据明确为合成内容，不代表真实网站事实。

## 本地安装

以下命令假设当前工作目录就是此技能包根目录（包含 `SKILL.md`）。只复制技能文件，不安装依赖。目标已存在时立即停止，不覆盖已有内容。安装文件排除 `.git`、Python 缓存、运行记录和项目证据。

### PowerShell

以下递归复制写法使用 PowerShell 7（`[IO.Path]::GetRelativePath`），不是 Windows PowerShell 5.1：

```powershell
$source = (Get-Location).Path
if (-not (Test-Path -LiteralPath (Join-Path $source 'SKILL.md'))) { throw '请在技能包根目录运行（需要存在 SKILL.md）' }
$codexHome = if ($env:CODEX_HOME) { $env:CODEX_HOME } else { Join-Path $env:USERPROFILE '.codex' }
$target = Join-Path $codexHome 'skills\website-trust-audit'
if (Test-Path -LiteralPath $target) { throw "目标已存在，请先备份并自行决定如何合并：$target" }
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $target) | Out-Null
New-Item -ItemType Directory -Path $target | Out-Null
Get-ChildItem -LiteralPath $source -File -Recurse -Force | ForEach-Object {
  $relative = [IO.Path]::GetRelativePath($source, $_.FullName)
  $parts = $relative -split '[\\/]'
  if ($parts | Where-Object { $_ -in @('.git', '__pycache__', 'evidence', 'runs') }) { return }
  if ($relative.EndsWith('.pyc', [StringComparison]::OrdinalIgnoreCase)) { return }
  $destination = Join-Path $target $relative
  New-Item -ItemType Directory -Force -Path (Split-Path -Parent $destination) | Out-Null
  Copy-Item -LiteralPath $_.FullName -Destination $destination
}
```

### POSIX shell

```sh
src="$(pwd)"
test -f "$src/SKILL.md" || { echo "请在技能包根目录运行（需要存在 SKILL.md）" >&2; exit 1; }
codex_home="${CODEX_HOME:-$HOME/.codex}"
dst="$codex_home/skills/website-trust-audit"
test ! -e "$dst" || { echo "目标已存在，请先备份并自行决定如何合并：$dst" >&2; exit 1; }
mkdir -p "$(dirname "$dst")"
mkdir "$dst"
tar -cf - --exclude-vcs --exclude='__pycache__' --exclude='*/__pycache__' --exclude='evidence' --exclude='*/evidence' --exclude='runs' --exclude='*/runs' --exclude='*.pyc' . | tar -xf - -C "$dst"
```

## 固定 Git 版本安装示例

本仓库选定为公开仓库 `hzqedison/website-trust-audit`。以下使用固定版本 `v0.1.0-draft`，在系统临时目录克隆并 detached checkout，不跟随可变分支；复制前同样拒绝已存在目标。

```sh
set -e
tmp="$(mktemp -d)"
git clone "https://github.com/hzqedison/website-trust-audit.git" "$tmp/repo"
git -C "$tmp/repo" checkout --detach v0.1.0-draft
src="$tmp/repo"
test -f "$src/SKILL.md" || { echo "指定版本不是技能包根目录" >&2; exit 1; }
codex_home="${CODEX_HOME:-$HOME/.codex}"
dst="$codex_home/skills/website-trust-audit"
test ! -e "$dst" || { echo "目标已存在，停止以免覆盖：$dst" >&2; exit 1; }
mkdir -p "$(dirname "$dst")" "$dst"
tar -cf - -C "$src" --exclude-vcs --exclude='__pycache__' --exclude='*/__pycache__' --exclude='evidence' --exclude='*/evidence' --exclude='runs' --exclude='*/runs' --exclude='*.pyc' . | tar -xf - -C "$dst"
```

GitHub 仓库 README 是本技能的阅读与分发入口：查看[仓库源码](https://github.com/hzqedison/website-trust-audit)与[固定预发布版 v0.1.0-draft](https://github.com/hzqedison/website-trust-audit/releases/tag/v0.1.0-draft)。独立 GitHub Pages 未启用，本项目没有 `github.io` 站点。详见 [`docs/publishing.md`](docs/publishing.md)。

## 调用示例

- 基线整理：`$website-trust-audit 请把现有官网评审资料整理成带证据状态的信息基线，不提出改版方案或排名。`
- 指定范围复测：`$website-trust-audit 复测 example.com 的英文首页和下载页，仅覆盖桌面端首屏、下载入口及价格条款，并与上次记录逐项对比。`
- SPEC 澄清：`$website-trust-audit 根据已确认的业务目标整理五章 SPEC；缺失的用户、约束和指标请保留待确认。`

## 反馈与协作

问题与改进建议请通过 [GitHub Issues](https://github.com/hzqedison/website-trust-audit/issues) 提交；协作修改请通过 [Pull Requests](https://github.com/hzqedison/website-trust-audit/pulls)。不要将客户私有审计证据提交到此通用技能仓库。

## 验证

在技能包根目录运行：

```sh
python -X utf8 -m unittest discover -s tests -v
python -X utf8 scripts/validate_audit.py assets/example-audit.json
```

合成示例通过只表示结构和引用校验通过，不表示网站审计已完成。

验收说明与结果记录见 [`docs/validation.md`](docs/validation.md)。
