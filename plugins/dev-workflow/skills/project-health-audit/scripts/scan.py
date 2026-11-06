#!/usr/bin/env python3
"""Read-only scanner for project health signals.

Collects candidate evidence for tests, health-check endpoints, lint/format
setup, CI pipelines and git hooks, plus a few hygiene items (mixed lockfiles,
env example, Docker). Prints JSON to stdout. It never executes project code
and never writes files.

Usage:
    python scan.py [PROJECT_ROOT]      (defaults to the current directory)

The output is evidence to interpret, not a verdict: a matched test file can
still be boilerplate, and a lint config can exist without being enforced.
"""
from __future__ import annotations

import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

SKIP_DIRS = {
    "node_modules", ".git", ".hg", ".svn", ".venv", "venv", "env",
    "__pycache__", ".mypy_cache", ".pytest_cache", ".ruff_cache", ".tox",
    "dist", "build", "out", ".next", ".nuxt", ".turbo", ".vercel", ".cache",
    "coverage", "htmlcov", "staticfiles", "vendor", "target", ".idea",
    ".vscode", ".yarn", ".pnpm-store", "bower_components",
}
MAX_READ_BYTES = 512 * 1024
MAX_FILES = 150_000
CAP = 40

JS_EXT = {".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"}
SOURCE_EXT = JS_EXT | {".py", ".go", ".java", ".kt", ".rb", ".php", ".cs"}

# --- tests -------------------------------------------------------------------
JS_TEST_NAME = re.compile(r"\.(test|spec|cy)\.[cm]?[jt]sx?$")
JS_TEST_DIRS = {"__tests__", "e2e", "cypress", "tests", "test"}
PY_TEST_NAME = re.compile(r"^(test_\w*|\w+_test|tests)\.py$")
JS_CASE = re.compile(r"(?m)^\s*(?:it|test)(?:\.\w+)*\s*\(")
PY_CASE = re.compile(r"(?m)^\s*(?:async\s+)?def\s+test\w*\s*\(")
TEST_CONFIG_NAME = re.compile(
    r"^((jest|vitest|vitest\.workspace|playwright|cypress|karma)\.config(\.\w+)+"
    r"|pytest\.ini|conftest\.py|tox\.ini|noxfile\.py|\.coveragerc)$"
)

# --- health ------------------------------------------------------------------
HEALTH_TEXT = re.compile(
    r"(?i)(healthz|readyz|livez|health[_-]?check|/health\b"
    r"|['\"`]health/?['\"`]|['\"`]/?ping/?['\"`])"
)
HEALTH_PATH = re.compile(
    r"(?i)(^|/)(health|healthz|healthcheck|health[-_]check|readyz|livez|ping)(/|\.[a-z]+$)"
)
DOCKER_HC = re.compile(r"(?i)^\s*HEALTHCHECK\b")
COMPOSE_HC = re.compile(r"(?i)^\s*healthcheck\s*:")
PROBE = re.compile(r"\b(livenessProbe|readinessProbe|startupProbe)\b")
NGINX_HC = re.compile(r"(?i)location\s+[=~^*]*\s*/(health|healthz|ping)\b")
COMPOSE_NAME = re.compile(r"^(docker-)?compose[\w.-]*\.ya?ml$")

# --- lint / CI / hooks ---------------------------------------------------------
LINT_NAME = re.compile(
    r"^(biome\.jsonc?|\.eslintrc(\.\w+)?|eslint\.config\.\w+|\.prettierrc(\.\w+)?"
    r"|prettier\.config\.\w+|\.stylelintrc(\.\w+)?|stylelint\.config\.\w+|ruff\.toml"
    r"|\.ruff\.toml|\.flake8|\.?mypy\.ini|\.?pylintrc|\.editorconfig|\.oxlintrc\.json"
    r"|\.isort\.cfg)$"
)
CI_PATH = re.compile(
    r"^(\.github/workflows/[^/]+\.ya?ml|\.gitlab-ci\.ya?ml|bitbucket-pipelines\.ya?ml"
    r"|azure-pipelines\.ya?ml|Jenkinsfile|\.circleci/config\.ya?ml|\.drone\.ya?ml"
    r"|\.travis\.ya?ml|buildspec\.ya?ml|cloudbuild\.ya?ml|\.woodpecker\.ya?ml)$"
)
CI_KIND = {
    # bare "test" followed by a flag is the shell builtin (`test -f x`), not a test run
    "test": re.compile(r"(?i)(\btest\b(?!\s+-[a-z]\b)|\b(tests|pytest|jest|vitest|playwright|cypress|coverage)\b)"),
    "lint": re.compile(r"(?i)\b(lint|biome|eslint|ruff|flake8|black|isort|prettier|mypy|pylint|typecheck|tsc)\b"),
    "build": re.compile(r"(?i)\bbuild\b"),
    "deploy": re.compile(r"(?i)\b(deploy|kubectl|helm|rsync|scp|ssh|pm2)\b"),
}
CI_STEP_LINE = re.compile(r"^\s*-?\s*(name|stage|stages|run|script)\s*:")
CI_BARE_BLOCK = re.compile(r"^-?\s*(run|script|stages)\s*:\s*[|>]?[-+]?$")  # "run: |" carries no info
LEFTHOOK_NAME = re.compile(r"^\.?lefthook(-local)?\.ya?ml$")
LINT_STAGED_NAME = re.compile(r"^(\.lintstagedrc(\.\w+)?|lint-staged\.config\.\w+)$")
PRECOMMIT_ID = re.compile(r"(?m)^\s*-\s*id:\s*(\S+)")
HOOKS_PATH = re.compile(r"(?im)^\s*hooksPath\s*=\s*(.+?)\s*$")

# --- dependencies ----------------------------------------------------------------
SCRIPT_KEY = re.compile(r"(?i)test|lint|format|check|typecheck|^ci$|e2e|prepare|postinstall|pre-?commit|coverage")
TEST_DEPS = {
    "jest", "vitest", "mocha", "ava", "@playwright/test", "playwright", "cypress",
    "@testing-library/react", "@testing-library/jest-dom", "@testing-library/user-event",
    "supertest", "@nestjs/testing", "ts-jest", "msw", "@vitest/coverage-v8",
}
LINT_DEPS = {"eslint", "@biomejs/biome", "prettier", "typescript", "oxlint", "stylelint", "lint-staged"}
HOOK_DEPS = {"husky", "lint-staged", "simple-git-hooks", "lefthook", "@commitlint/cli"}
HEALTH_DEPS = {"@nestjs/terminus", "@godaddy/terminus", "express-healthcheck", "lightship"}
JS_FRAMEWORKS = {
    "next", "react", "vue", "nuxt", "svelte", "@sveltejs/kit", "@nestjs/core", "express",
    "fastify", "koa", "hono", "vite", "astro", "@remix-run/react", "electron",
    "react-native", "expo", "turbo",
}
PY_DEPS = [
    "django", "djangorestframework", "fastapi", "flask", "celery",
    "pytest", "pytest-django", "pytest-cov", "coverage", "factory-boy", "model-bakery",
    "django-health-check", "ruff", "black", "flake8", "isort", "mypy", "pylint", "pre-commit",
]
PY_DEP_FILE = re.compile(r"^(requirements[\w.-]*\.txt|pyproject\.toml|Pipfile|setup\.cfg|setup\.py)$")
PYPROJECT_TOOL = re.compile(r"(?m)^\[tool\.([\w.-]+)\]")
SETUP_CFG_SECTION = re.compile(r"(?m)^\[(flake8|tool:pytest|isort|mypy|coverage:\w+|pycodestyle)\]")
INTERESTING_TOOLS = ("ruff", "black", "isort", "mypy", "pytest", "coverage", "pylint", "poetry", "django-stubs")

LOCKFILES = {"package-lock.json", "yarn.lock", "pnpm-lock.yaml", "bun.lockb", "bun.lock", "npm-shrinkwrap.json"}
ENV_EXAMPLE = re.compile(r"^(\.env\.(example|sample|template|dist)|env\.example)$")
ROOT_MARKERS = {
    "package.json", "pyproject.toml", "requirements.txt", "Pipfile", "setup.py", "manage.py",
    "go.mod", "pom.xml", "build.gradle", "build.gradle.kts", "Cargo.toml", "composer.json",
    "Gemfile", "turbo.json", "nx.json", "pnpm-workspace.yaml", "lerna.json", "Dockerfile",
    "docker-compose.yml", "docker-compose.yaml", "compose.yml", "compose.yaml",
}


def py_dep_regex(name: str) -> re.Pattern:
    body = "[-_]".join(re.escape(part) for part in re.split(r"[-_]", name))
    return re.compile(r"(?im)(?:^|[\s\"'\[,(])" + body + r"(?=[\s\"'=<>~!\[\];,)]|$)")


PY_DEP_RES = [(n, py_dep_regex(n)) for n in PY_DEPS]


def read(p: Path) -> str:
    try:
        if p.stat().st_size > MAX_READ_BYTES:
            return ""
        return p.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def group_of(rel_path: str) -> str:
    parts = rel_path.split("/")
    if len(parts) > 2 and parts[0] in {"apps", "packages", "services", "libs", "modules"}:
        return "/".join(parts[:2])
    return parts[0] if len(parts) > 1 else "."


def grep_lines(text: str, rx: re.Pattern, limit: int = 10) -> list[dict]:
    hits = []
    for i, line in enumerate(text.splitlines(), 1):
        if rx.search(line):
            hits.append({"line": i, "text": line.strip()[:160]})
            if len(hits) >= limit:
                break
    return hits


def compact(d: dict) -> dict:
    return {k: v for k, v in d.items() if v not in (None, [], {}, "", False)}


def find_git_dir(root: Path) -> tuple[Path | None, Path | None]:
    for d in [root, *root.parents]:
        g = d / ".git"
        if g.is_dir():
            return d, g
        if g.is_file():  # worktree or submodule: "gitdir: <path>"
            m = re.match(r"gitdir:\s*(.+)", read(g).strip())
            if m:
                return d, (d / m.group(1).strip()).resolve()
    return None, None


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    if not root.is_dir():
        print(json.dumps({"error": f"not a directory: {root}"}))
        return 2

    files: list[Path] = []
    truncated = False
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS and not d.endswith(".egg-info"))
        for name in sorted(filenames):
            files.append(Path(dirpath) / name)
            if len(files) >= MAX_FILES:
                truncated = True
                break
        if truncated:
            break

    def rel(p: Path) -> str:
        return p.relative_to(root).as_posix()

    lockfiles: dict[str, list[str]] = defaultdict(list)
    env_examples, manage_py, dockerfiles, compose_files, monorepo_markers = [], [], [], [], []
    lint_configs, test_configs, ci_paths, package_jsons, py_dep_files = [], [], [], [], []
    precommit_files, lefthook_files, lint_staged_files = [], [], []
    test_files: list[dict] = []
    health_route_files: list[str] = []
    health_code: list[dict] = []
    health_infra: list[dict] = []

    for p in files:
        r = rel(p)
        name = p.name
        suffix = p.suffix.lower()
        dir_parts = r.split("/")[:-1]

        if name in LOCKFILES:
            lockfiles[Path(r).parent.as_posix()].append(name)
        if ENV_EXAMPLE.match(name):
            env_examples.append(r)
        if name == "manage.py":
            manage_py.append(r)
        if name in {"turbo.json", "nx.json", "pnpm-workspace.yaml", "lerna.json"}:
            monorepo_markers.append(r)
        if LINT_NAME.match(name):
            lint_configs.append(r)
        if TEST_CONFIG_NAME.match(name):
            test_configs.append(r)
        if CI_PATH.match(r):
            ci_paths.append(p)
        if name == "package.json":
            package_jsons.append(p)
        if PY_DEP_FILE.match(name) or ("requirements" in dir_parts and suffix == ".txt"):
            py_dep_files.append(p)
        if name == ".pre-commit-config.yaml":
            precommit_files.append(p)
        if LEFTHOOK_NAME.match(name):
            lefthook_files.append(r)
        if LINT_STAGED_NAME.match(name):
            lint_staged_files.append(r)

        # infra-level health checks
        if name.startswith("Dockerfile") or name.endswith(".dockerfile"):
            dockerfiles.append(r)
            for h in grep_lines(read(p), DOCKER_HC, 3):
                health_infra.append({"file": r, "kind": "docker HEALTHCHECK", **h})
        elif COMPOSE_NAME.match(name):
            compose_files.append(r)
            for h in grep_lines(read(p), COMPOSE_HC, 10):
                health_infra.append({"file": r, "kind": "compose healthcheck", **h})
        elif suffix in {".yml", ".yaml"}:
            for h in grep_lines(read(p), PROBE, 6):
                health_infra.append({"file": r, "kind": "k8s probe", **h})
        elif suffix == ".conf":
            for h in grep_lines(read(p), NGINX_HC, 4):
                health_infra.append({"file": r, "kind": "nginx location", **h})

        if suffix not in SOURCE_EXT:
            continue
        text = None

        # tests
        is_test = False
        if suffix == ".py":
            is_test = bool(PY_TEST_NAME.match(name)) or ("tests" in dir_parts and name.startswith("test"))
            case_rx = PY_CASE
        elif suffix in JS_EXT:
            by_name = bool(JS_TEST_NAME.search(name))
            by_dir = bool(set(dir_parts) & JS_TEST_DIRS) and not name.endswith(".d.ts")
            is_test = by_name or by_dir
            case_rx = JS_CASE
        if is_test:
            text = read(p)
            cases = len(case_rx.findall(text))
            if cases or suffix == ".py" or JS_TEST_NAME.search(name):
                entry = {"path": r, "cases": cases}
                if cases == 0 and "Create your tests here" in text:
                    entry["django_boilerplate"] = True
                test_files.append(entry)

        # health in code
        if HEALTH_PATH.search(r):
            health_route_files.append(r)
        if text is None:
            text = read(p)
        if len(health_code) < CAP and HEALTH_TEXT.search(text):
            for h in grep_lines(text, HEALTH_TEXT, 5):
                health_code.append({"file": r, **h})

    # package.json files
    packages = []
    frameworks: set[str] = set()
    for p in package_jsons:
        try:
            data = json.loads(read(p) or "{}")
        except ValueError:
            continue
        if not isinstance(data, dict):
            continue
        deps: dict = {}
        for key in ("dependencies", "devDependencies"):
            if isinstance(data.get(key), dict):
                deps.update(data[key])
        scripts = data.get("scripts") if isinstance(data.get("scripts"), dict) else {}
        fw = sorted(d for d in deps if d in JS_FRAMEWORKS)
        frameworks.update(fw)
        packages.append(compact({
            "path": rel(p),
            "name": data.get("name"),
            "workspaces": data.get("workspaces"),
            "scripts": {k: v for k, v in scripts.items() if SCRIPT_KEY.search(k)},
            "test_script_is_npm_placeholder": "no test specified" in str(scripts.get("test", "")),
            "frameworks": fw,
            "test_deps": sorted(d for d in deps if d in TEST_DEPS),
            "lint_deps": sorted(d for d in deps if d in LINT_DEPS),
            "hook_deps": sorted(d for d in deps if d in HOOK_DEPS),
            "health_deps": sorted(d for d in deps if d in HEALTH_DEPS),
            "hook_config_keys": [k for k in ("lint-staged", "simple-git-hooks", "husky") if k in data],
        }))

    # python dependency files
    python = []
    for p in py_dep_files:
        text = read(p)
        found = [n for n, rx in PY_DEP_RES if rx.search(text)]
        tools = []
        if p.name == "pyproject.toml":
            tools = sorted({t for t in PYPROJECT_TOOL.findall(text) if t.split(".")[0] in INTERESTING_TOOLS})
        elif p.name == "setup.cfg":
            tools = sorted(set(SETUP_CFG_SECTION.findall(text)))
        frameworks.update(n for n in found if n in {"django", "djangorestframework", "fastapi", "flask"})
        python.append(compact({"path": rel(p), "deps": found, "tool_sections": tools}))

    # CI
    ci = []
    for p in ci_paths:
        text = read(p)
        # ignore comments: "# There are no tests yet" must not count as a test step
        code = "\n".join(l for l in text.splitlines() if not l.strip().startswith("#"))
        kinds = sorted(k for k, rx in CI_KIND.items() if rx.search(code))
        # Step names / run lines outline the pipeline; test & lint lines are
        # what the audit cares about. Deploy plumbing (ssh, scp...) is noise.
        lines = []
        for i, line in enumerate(text.splitlines(), 1):
            s = line.strip()
            if not s or s.startswith("#") or CI_BARE_BLOCK.match(s):
                continue
            if CI_STEP_LINE.match(line) or CI_KIND["test"].search(s) or CI_KIND["lint"].search(s):
                lines.append({"line": i, "text": s[:160]})
                if len(lines) >= 20:
                    break
        ci.append({"path": rel(p), "mentions": kinds, "lines": lines})

    # git hooks
    git_root, git_dir = find_git_dir(root)
    hooks: dict = {"git_repo": bool(git_dir)}
    if git_dir:
        hooks["git_root"] = git_root.as_posix() if git_root != root else "."
        m = HOOKS_PATH.search(read(git_dir / "config"))
        hooks["core_hooks_path"] = m.group(1) if m else None
        hooks_dir = git_dir / "hooks"
        if hooks_dir.is_dir():
            hooks["installed_in_git_hooks"] = sorted(
                h.name for h in hooks_dir.iterdir() if h.is_file() and not h.name.endswith(".sample")
            )
    husky = []
    for base in {root, git_root} - {None}:
        husky_dir = base / ".husky"
        if husky_dir.is_dir():
            for h in sorted(husky_dir.iterdir()):
                if h.is_file() and not h.name.startswith("."):
                    cmds = [l.strip() for l in read(h).splitlines() if l.strip() and not l.strip().startswith("#")]
                    husky.append({"hook": h.name, "path": h.as_posix(), "commands": cmds[:10]})
    hooks["husky"] = husky
    hooks["pre_commit_framework"] = [
        {"path": rel(p), "hook_ids": PRECOMMIT_ID.findall(read(p))[:CAP]} for p in precommit_files
    ]
    hooks["lefthook"] = lefthook_files
    hooks["lint_staged_files"] = lint_staged_files

    real_tests = sorted((t for t in test_files if t["cases"]), key=lambda t: -t["cases"])
    test_groups: dict[str, dict] = defaultdict(lambda: {"files": 0, "cases": 0})
    for t in real_tests:
        g = test_groups[group_of(t["path"])]
        g["files"] += 1
        g["cases"] += t["cases"]
    django_boilerplate = [t["path"] for t in test_files if t.get("django_boilerplate")]
    # Named like tests but no test functions: usually settings modules,
    # management commands, views or ad-hoc scripts (e.g. test_smtp.py), not
    # tests -- unless they use their own harness (check() + run_tests.sh).
    no_cases = [t["path"] for t in test_files if not t["cases"] and not t.get("django_boilerplate")]

    result = {
        "root": root.as_posix(),
        "files_scanned": len(files),
        "truncated": truncated,
        "stack": compact({
            "root_markers": sorted(n for n in os.listdir(root) if n in ROOT_MARKERS),
            "monorepo_markers": monorepo_markers,
            "frameworks": sorted(frameworks),
            "django_manage_py": manage_py,
        }),
        "packages": packages[:CAP],
        "python": python[:CAP],
        "tests": {
            "test_files": len(real_tests),
            "total_cases_estimate": sum(t["cases"] for t in real_tests),
            "by_group": dict(sorted(test_groups.items())),
            "files_with_cases": real_tests[:CAP],
            "django_boilerplate_tests_py": django_boilerplate[:CAP],
            "named_like_tests_but_no_cases": no_cases[:CAP],
            "configs": test_configs[:CAP],
        },
        "health": {
            "route_files": health_route_files[:CAP],
            "code_mentions": health_code[:CAP],
            "infra": health_infra[:CAP],
        },
        "lint": {"configs": lint_configs[:CAP]},
        "ci": ci,
        # Not compacted: an empty installed_in_git_hooks / null core_hooks_path
        # is itself evidence (hook config exists but was never installed).
        "hooks": hooks,
        "hygiene": compact({
            "mixed_lockfiles": {d: n for d, n in lockfiles.items() if len(n) > 1},
            "lockfiles": dict(lockfiles),
            "env_examples": env_examples,
            "dockerfiles": dockerfiles[:CAP],
            "compose_files": compose_files[:CAP],
            "readme_at_root": any((root / n).is_file() for n in ("README.md", "README.rst", "README.txt", "README")),
        }),
    }

    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass
    print(json.dumps(result, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
