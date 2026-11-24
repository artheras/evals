# Aria Evals

[English](README.md) | 简体中文

[Aria Code](https://github.com/artheras/aria-code) 的公开评测示例与可复现运行记录仓库。

本仓库包含 30 个原创合成公开任务。每个任务都配有在 Agent 执行期间保持隐藏的可执行评分器（grader）、参考解法，以及用于校准评分器可靠性的故意错误解法。

| 分组 | 任务数 | 预期产物 | 评判方式 |
|---|---|---|---|
| Demonstrations（基础示例） | 3 | 文本产物 | 精确校验（迷宫路径、括号修复、词频统计） |
| Coding, finance, logistics（编码/金融/物流） | 12 | 文本或 CSV 产物 | 与预期输出精确匹配 |
| Firmware（固件） | 5 | 实现指定头文件的 C99 源码 | 使用系统 C 编译器结合隐藏测试框架编译运行 |
| Control（控制） | 5 | MuJoCo 模型的 Python 控制器 | 物理仿真；检查稳定性、约束与目标达成（含未告知的外部扰动） |
| 3D（三维网格） | 5 | OBJ 网格文件 | 几何校验：闭合性、法线一致性、外向性、尺寸、拓扑与体积 |

这些示例规模较小、完全公开，供社区校验与贡献使用，不代表模型在未见任务上的泛化表现。

物理 AI 相关分组在评分时除了 `pytest` 外，还需要 `numpy`、`mujoco`、`trimesh`（可通过 `dev` 可选依赖安装）以及 C 编译器（`cc`、`gcc` 或 `clang`）。缺少 Python 依赖的任务会被引擎记为 `error` 并从得分中排除；而 `requires` 字段仅支持声明可导入的 Python 模块，因此 Firmware 任务通过标签 `requires-c-compiler` 标记。在没有 C 编译器的机器上执行时，CLI 预检会提前阻断提示，避免产生因 exit 127 导致的误判 `fail`。

其中 8 个任务带有 `overlaps-engine-suite` 标签（`max-drawdown-v1`、`fifo-realized-gains-v1`、`dock-door-schedule-v1`、`billable-weight-charges-v1`、`reorder-plan-v1`、`serpentine-pick-path-v1`、`loan-amortization-v1`、`portfolio-weights-v1`），因为 Aria Code 自带评测套件中存在相似题目。汇总报告会同时给出含与不含这 8 个任务的完成率；详见[多仓库协作说明](docs/collaboration.md#tasks-that-overlap-the-engines-own-suites)与[任务结构说明](docs/task-anatomy.md)。

## 隔离评测机制

每个评分器都在 Agent 的工作区中运行，因此必须防止 Agent 留下的文件干扰评分。所有任务均使用如下隔离命令校验：

```bash
{python} -I -m pytest -q --noconftest -p no:cacheprovider --import-mode=importlib -c /dev/null <grader>
```

- `-I`：将工作区和 `PYTHON*` 环境变量排除在解释器路径之外，防止恶意植入 `pytest.py` 或 `sitecustomize.py`。
- `--import-mode=importlib`：阻止 pytest 将工作区插入 `sys.path`（防止 `numpy.py` 等同名文件遮蔽真实模块）。
- `-c /dev/null`：忽略工作区中的 `pytest.ini`、`pyproject.toml`、`tox.ini` 或 `setup.cfg`。
- `--noconftest`：忽略 `conftest.py`。

Control 任务不会直接 `import` 提交的 `controller.py`，而是在独立的 `-I` 子进程中通过 `(t, qpos, qvel)` 通信，仿真器与全部断言留在评分进程中。任何提前退出的控制器都会直接判定失败。

## 快速开始

请使用 Python 3.12 或 3.13，并在仓库根目录执行：

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
aria-evals doctor
aria-evals validate
python -m pytest -q tests
```

使用官方 pinned 引擎执行无模型调用的预检（preflight）：

```bash
python -m pip install -e '.[dev,runner]'
aria-evals check --output runs/preflight
```

`check` 会调用引擎的空操作求解器，所有未完成任务都必须返回原生结果 `fail`，以此确认空答案无法通过。

## 运行模型评测与结果对比

在本地按 Aria Code 支持的方式配置模型提供商凭据（请勿将密钥写入仓库或贴入 Issue）：

```bash
aria-evals run \
  --model YOUR_MODEL \
  --provider YOUR_PROVIDER \
  --repeat 3 \
  --solve-timeout 900 \
  --output runs/model
```

如需计算费用，可参考 [`prices/examples/template.json`](prices/examples/template.json) 创建本地价格表并通过 `--prices` 传入。运行完成后，可使用以下命令对比两次评测的 `summary.json`（或运行目录）：

```bash
aria-evals diff runs/baseline runs/model
```

## 在 GitHub Actions 中运行

可通过 **Actions → Model evaluation → Run workflow** 在 GitHub Runner 上手动触发模型评测（需先配置对应的 Repository Secret：`OPENAI_API_KEY`、`DEEPSEEK_API_KEY`、`GOOGLE_API_KEY` 或 `ANTHROPIC_API_KEY`）。`Proof` 工作流会在 PR 和 `main` 分支推送时自动运行离线校准与引擎预检，不消耗模型额度。

## 评测结果与基线归档

聚合评测记录与披露规范见 [`results/`](results/README.md)，其中已收录上游基准参考 [Aria Code Evals #14](results/aria-code-evals-14.md)（`google/gemini-3.5-flash`，`repeat=1`，含优势拆解与已知短板说明）。

## 许可协议

本仓库原创文件采用 [Apache License 2.0](LICENSE) 协议开源（历史 MIT 说明见 [NOTICE](NOTICE)）。Aria Code 作为独立依赖遵循其自身协议。
