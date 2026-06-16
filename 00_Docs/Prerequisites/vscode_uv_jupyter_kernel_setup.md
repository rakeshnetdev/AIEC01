# VS Code, uv, and Jupyter kernel setup guide

This guide summarizes the steps needed to make a project-specific `.venv` work correctly in VS Code notebooks, especially when one project keeps defaulting to another environment.[cite:224][cite:229]

## Goal

The goal is to make the notebook in `03_Agent_Memory_LangGraph_LangChain` use that project’s own `.venv` instead of falling back to `02_Agentic_RAG_LangGraph_LangChain` or a global Python installation.[cite:224][cite:293]

## Core idea

VS Code notebooks use a Jupyter **kernel**, and that kernel must point to the same Python environment where the needed packages are installed.[cite:224][cite:307] If the wrong environment is selected, imports such as `import networkx as nx` will fail even if the package exists in another `.venv`.[cite:267][cite:268]

## Project folder to use

Work from the `03_Agent_Memory_LangGraph_LangChain` folder when the notebook belongs to that project.[cite:293][cite:295] The local virtual environment for that project should live at `03_Agent_Memory_LangGraph_LangChain/.venv`.[cite:229][cite:233]

## Verify the correct uv environment

Use this command inside the `03` project folder:

```bash
uv python find
```

If the environment is correct, the result should point to the Python interpreter inside `03_Agent_Memory_LangGraph_LangChain/.venv/bin/python3`.[cite:229][cite:230]

## Install dependencies with uv

Use `uv` to install notebook and project dependencies into the project environment:

```bash
cd /Users/sriraki/Desktop/CodePractice/ai_practice/AIEC01/03_Agent_Memory_LangGraph_LangChain
uv add ipykernel
uv add networkx
uv sync
```

`uv add` adds packages to the project, and `uv sync` brings the `.venv` in line with the project definition.[cite:229][cite:234][cite:400]

## Register the project as a Jupyter kernel

After `ipykernel` is installed, register a named kernel so VS Code shows a clear notebook option:

```bash
uv run python -m ipykernel install --user --name 03 --display-name "Python (03)"
```

This creates a visible kernel entry named `Python (03)` for notebook selection.[cite:381][cite:319]

## Check available kernels

To list installed kernels, run:

```bash
jupyter kernelspec list
```

A correct setup should show a kernel located under the `03` project’s `.venv` path.[cite:307][cite:319]

## Remove the old 02 kernel

If the notebook keeps showing the old `02` kernel, remove that kernelspec:

```bash
jupyter kernelspec remove aim-agentic-rag-langgraph-langchain
```

This removes the stale notebook kernel entry without deleting the actual project files.[cite:319][cite:224]

## Fix shell activation issues

If the terminal prompt shows the wrong project, deactivate the wrong environment and activate the right one:

```bash
deactivate
source /Users/sriraki/Desktop/CodePractice/ai_practice/AIEC01/03_Agent_Memory_LangGraph_LangChain/.venv/bin/activate
```

Activating the wrong environment can cause VS Code and Jupyter to prefer the wrong interpreter or kernel.[cite:259][cite:224]

## If `python` is not found

Sometimes `python` is missing from the shell, while `python3` points to the system interpreter instead of the project `.venv`.[cite:368][cite:369] In that case, run commands directly against the venv interpreter:

```bash
/Users/sriraki/Desktop/CodePractice/ai_practice/AIEC01/03_Agent_Memory_LangGraph_LangChain/.venv/bin/python3 -m ensurepip --upgrade
/Users/sriraki/Desktop/CodePractice/ai_practice/AIEC01/03_Agent_Memory_LangGraph_LangChain/.venv/bin/python3 -m pip install ipykernel
/Users/sriraki/Desktop/CodePractice/ai_practice/AIEC01/03_Agent_Memory_LangGraph_LangChain/.venv/bin/python3 -m ipykernel install --user --name 03 --display-name "Python (03)"
```

This bypasses the system Python and forces installation into the `03` environment.[cite:353][cite:354][cite:369]

## Reload VS Code correctly

After kernel changes, reload the editor:

1. Press `Cmd + Shift + P`.
2. Run `Developer: Reload Window`.
3. Reopen the notebook.[cite:218][cite:224]

VS Code may keep recently used kernels cached until the window is reloaded.[cite:303][cite:224]

## Select the kernel in the notebook

In the notebook, click the kernel picker in the top-right corner.[cite:224][cite:198] Then choose the kernel corresponding to the `03` environment, ideally `Python (03)` if it was registered with that display name.[cite:224][cite:381]

If VS Code only shows a generic `python3`, use it only if its path points to `03_Agent_Memory_LangGraph_LangChain/.venv`.[cite:307][cite:319]

## Verify the notebook is using the correct environment

Run this inside the notebook:

```python
import sys
print(sys.executable)
```

The output should point to the Python executable inside `03_Agent_Memory_LangGraph_LangChain/.venv`.[cite:224][cite:195]

## If imports still fail

If `networkx` or another package still fails to import, it usually means the package is not installed in the same environment the notebook is running.[cite:267][cite:268] Install the package into the `03` project with `uv add <package>` and then reselect or restart the notebook kernel.[cite:229][cite:400]

## Clean recovery sequence

If the setup remains stuck, use this sequence:

```bash
cd /Users/sriraki/Desktop/CodePractice/ai_practice/AIEC01/03_Agent_Memory_LangGraph_LangChain
uv python find
uv add ipykernel
uv add networkx
uv sync
uv run python -m ipykernel install --user --name 03 --display-name "Python (03)"
jupyter kernelspec list
```

Then reload VS Code, open the notebook again, and select `Python (03)`.[cite:229][cite:400][cite:224]

## Expected end state

A working setup should have these properties:[cite:224][cite:307]

- The terminal and project folder both point to `03_Agent_Memory_LangGraph_LangChain`.[cite:293][cite:295]
- `uv python find` returns the Python executable inside `03/.venv`.[cite:229][cite:230]
- `jupyter kernelspec list` shows a kernel backed by the `03` `.venv`.[cite:307][cite:319]
- The notebook kernel in VS Code is `Python (03)` or the generic `python3` that points to the `03` `.venv` path.[cite:224][cite:381]
- Imports such as `import networkx as nx` work inside the notebook.[cite:267][cite:268]
