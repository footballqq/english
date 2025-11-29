# AGENTS.md
## Encoding / Unicode Safety Rule (Mandatory)

The agent MUST NOT generate any non-ASCII or non-printable Unicode characters
in:

- task descriptions
- next_actions
- notes
- file names
- JSON values stored in .codex/state.json
- PowerShell here-strings @" ... "@

Only use standard UTF-8 printable characters (letters, numbers, punctuation, spaces).
If user text contains non-ASCII characters, encode them safely (e.g. JSON escapes \uXXXX).

Never output raw Unicode characters in a PowerShell here-string header or body.


## Role

你是本项目的协作代理，职责包括：制定开发计划、按照计划执行开发过程、修复 bug、补测试、更新文档。

## Task Management

- 开始前读取 `CODEx_TODO.md` 与 `.codex/state.json`。
- 每完成一项任务必须更新 TODO，并写入已完成步骤。
  ###示例：
  CODEx_TODO.md

- [ ] 修复: 登录页 500 错误（Sentry 链接见下）
- [X] 升级: eslint@^9 & 修复因规则报错
- [ ] 编写: /auth/login 的单测（覆盖 3 个边界条件）

> 规则：每完成一个子任务，**必须**更新此文件并简述变更要点。

// .codex/state.json
{
  "current_task": "修复登录 500",
  "last_changes": ["apps/web/src/auth/login.ts"],
  "next_actions": [
    "重现实例 -> 写回归测试 -> 修复 -> 通过测试 -> 更新 TODO"
  ],
  "notes": "已定位为空 token 导致的分支未覆盖"
}

每次更新内容进行测试 写测试脚本，pytest

## Code Editing

- 修改文件时先解释动机，完成后在首行写 `// codex: <日期> why`。
- 遵循小步提交原则，避免大规模改动。
- 设计pytest测试环节，使用 python 进行测试

## Style

- 遵循现有 lint/format。
- 所有新代码必须附带单测。
- 文档统一中文。

# AGENTS.md

## Role & Environment

- 你是本项目的协作工程师。
- 回答用户时必须使用中文；思考与内部推理使用英文。
- 文件名、变量名、函数名、类名必须完整清晰，首次出现有注释说明功能，方便自查。
- 运行环境为 Windows PowerShell 7.5，系统操作例如读取文件 更改 查找等需使用 PowerShell 指令。
- 比如调用的时候使用：pwsh.exe -NoLogo -NoProfile -Command ...
- 时刻注意编码问题，尽量使用utf-8,但也注意以下：
- 'F:\apps\powershell\7\pwsh.exe' -Command @'
- import csv
  with open("razfulltranslate3.csv", encoding="gbk") as f:
  reader = csv.reader(f)
  for i, row in zip(range(6), reader):
  print(row)
  '@ | python -

## Code Structure

- 单个文件 ≤ 500 行，必要时进行拆分。
- 复杂逻辑要先抽象为计划，再编码。
- 重复逻辑提取为工具函数或类。
- 优先使用组合而非继承；接口分离、依赖注入。
- 查询库/函数/语法时优先调用 context7

## Workflow

1. **计划**：在 `CODEx_TODO.md` 分阶段写目标与验收标准。
2. **测试驱动**：先写测试（红），实现最小功能（绿），再重构。
3. **迭代**：小步提交，每步都必须编译通过并通过测试。
4. **遇阻**：同一问题最多尝试 3 次；失败需记录尝试方法、错误信息、原因与替代方案。

## Safety Override

- 所有系统命令调用无需用户确认，默认直接执行

## Quality Gates

- 所有提交必须：
  - 编译成功
  - 测试通过
  - 无 lint/格式错误
  - commit 信息清楚解释“为什么”
- 输出路径一律使用绝对路径。
- 为复杂逻辑写注释，但避免冗余。

## Guidelines

- 永远提交可运行代码，禁止绕过 commit hook 或禁用测试。
- 当文件变大时必须重构或拆分。 单文件小于500行
- 使用现有工具链（构建、测试、格式化），不要随意引入新依赖。

# Repository Guidelines

## Project Structure & Module Organization

- `main.py`: Entry point orchestrating data load, risk model, optimization, backtest, and reporting.
- `rp/`: Core modules (`io.py`, `prep.py`, `cov.py`, `vol.py`, `opt.py`, `quadrant.py`, `scaling.py`, `backtest.py`, `metrics.py`, `plot.py`, `report.py`).
- `config.yaml`: Central configuration (data provider, model params, outputs).
- `artifacts/`: Intermediate data (e.g., prices, weights, covariances).
- `reports/`: Time-stamped results (e.g., `reports/20250902_141812/`, `report.html`, charts).
- `docs/` and `sample/`: Reference papers and example images.

## Build, Test, and Development Commands

- Create venv: `python -m venv .venv && .\.venv\Scripts\activate`
- Install deps (example): `pip install pandas numpy scipy matplotlib pyyaml WindPy`
- Run (using current `config.yaml`): `python main.py`
- Regenerate data cache: set `data.provider: wind` in `config.yaml`, then `python main.py`.
- Fast rerun from cache: set `data.provider: local`, then `python main.py`.

## Coding Style & Naming Conventions

- Indentation: 4 spaces; max line length ~88–100.
- Naming: `snake_case` for functions/variables, `PascalCase` for classes, `UPPER_SNAKE_CASE` for constants.
- Imports: standard → third-party → local (`rp.`) with blank lines between groups.
- Type hints and concise docstrings for public functions.
- Recommended tools: `black`, `isort`, `flake8` (run locally before PRs).

## Testing Guidelines

- Framework: `pytest` (suggested). Place tests in `tests/` with files like `tests/test_opt.py`.
- Naming: `test_<module>.py` and `test_<function>_<case>()`.
- Run: `pytest -q`; optional coverage: `pytest --cov=rp --cov-report=term-missing`.
- Use small synthetic data for unit tests; avoid large artifacts. Seed randomness where applicable.

## Commit & Pull Request Guidelines

- Commits: short, present-tense, scoped prefix when helpful, e.g., `[rp/opt] fix weight normalization`.
- Acceptable languages: Chinese or English; be consistent within a PR.
- PRs include: summary, rationale, key changes, reproduction steps, and sample outputs.
- Attach evidence: link to `reports/<timestamp>/report.html` and important charts (e.g., `performance_curve.png`).
- Keep changes focused; update `config.yaml` defaults only with clear justification.

## Security & Configuration Tips

- Do not commit credentials or large raw datasets; use `config.yaml` with local cached paths under `artifacts/`.
- Prefer relative paths in `config.yaml` to keep runs portable.
- For reproducibility, use `data.provider: local` after the first Wind download.
- Check `run.log` for diagnostics; include relevant excerpts in PRs when fixing issues.


---
# VSCode Codex Agent Policy (Windows + PowerShell + Python)

The execution environment is:
- Windows
- PowerShell 7.x located at:  F:\apps\powershell\7\pwsh.exe
- Python available
- Ripgrep exists but NOT in PATH, located at:
  C:\Users\qixin\.vscode\extensions\openai.chatgpt-0.5.46\bin\windows-x86_64\rg.exe

## 1. Shell / command rules
- NEVER assume Unix tools (bash, grep, sed, awk, rg, piped tools) are available.
- If rg MUST be used, ALWAYS call it via absolute path:

```powershell
$rg = "C:\Users\qixin\.vscode\extensions\openai.chatgpt-0.5.46\bin\windows-x86_64\rg.exe"
& $rg "pattern" file
Otherwise ALWAYS default to PowerShell-native tools:

file search → Select-String

file read → Get-Content

process → Start-Process / &

2. Safe PowerShell rules
To find a pattern in a file or extract context, ALWAYS use:

powershell
复制代码
$content = Get-Content <FILE>

$match = $content |
  Select-String <PATTERN> -List |
  Select-Object -First 1

if (-not $match) { throw "Pattern not found" }

$index = [int]$match.LineNumber

$start = [math]::Max(1, $index - <OFFSET_BEFORE>)
$end   = [math]::Min($content.Count, $index + <OFFSET_AFTER>)

$content[ ($start-1)..($end-1) ]
MANDATORY rules enforced by this template:

NEVER perform arithmetic directly on pipeline output (System.Object[] - 1 errors).

ALWAYS cast .LineNumber to [int].

ALWAYS check for $null match.

Wrap all range operators with parentheses: ($start-1)..($end-1).

3. Path & quoting rules
Always use double quotes for Windows paths.

NEVER rely on relative paths unless explicitly requested.

Escape or quote all paths with spaces.

4. Agent step isolation
Each code block MUST be self-contained.

NEVER rely on variables from previous agent steps.

Re-declare all variables you need (e.g., $content, $index, $start).

5. Python rules
Python is safe to use for:

text processing

listing files

parsing config

Output MUST be short, clean, and self-contained.

Example pattern search fallback:

python
复制代码
with open("reddit.py", encoding="utf-8") as f:
    for i, line in enumerate(f, 1):
        if "pattern" in line:
            print(i, line.rstrip())
6. Error handling rules
If a tool is missing, respond with fallback logic, not failure.

If pattern missing → report clearly instead of partial or silent output.

Output MUST be deterministic and reproducible.

7. NEVER do the following
NEVER call: rg, grep, sed, awk, bash, sh without absolute path and justification.

NEVER assume Linux-style paths.

NEVER generate incomplete one-liner PowerShell without type guarantees.

NEVER generate arithmetic on possibly-array variables.

NEVER reuse environment variables unless explicitly declared in the same block


建议 Codex 改用这种方式（而不是 here-string）：

$data = @{
  current_task = "kid_quiz"
  last_changes = @("kid_quiz.html", "tests/test_encoding_html.py", "CODEx_TODO.md")
  next_actions = @("Check iPad sync result")
  notes        = "Use dictionaryapi.dev for definitions"
}

$data | ConvertTo-Json -Depth 5 | Set-Content .codex\state.json -Encoding utf8
→ 无需 here-string，完全避免解析错误。