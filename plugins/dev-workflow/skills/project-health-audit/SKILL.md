---
name: project-health-audit
description: Audit a codebase's engineering health — unit/integration tests, health-check endpoint, lint/format setup, CI pipeline, git hooks — and report what exists and is really used, what is half-done, and what is missing, with file evidence. Works for Django/Python and Node/Next.js projects, including Turborepo/Yarn-workspace monorepos. Use this skill whenever the user asks whether a project has tests, a health check, linting, CI or pre-commit hooks, even about only one of them (e.g. "โปรเจคนี้มี unit test มั้ย", "เรามี api health check มั้ย", "ของ django นับเป็น unit test มั้ย", "มี CI มั้ย", "does this repo have tests?"), or wants a production-readiness / project health check before handover or go-live.
---

# Project Health Audit

People ask "does this project have X?" to decide what to build next, to answer a lead or client, or before go-live. A confident wrong answer — "no tests" when tests live in another workspace, or "yes, health check" when it's a stub behind auth — costs more than no answer. So this skill is about **evidence**: every status points to a file, and "missing" is said only after a real search.

## 1. Decide the scope

- **Single question** ("มี unit test มั้ย") → answer that item first, briefly, with evidence. End with one line offering the full audit. Someone who asked one thing doesn't want a five-section report.
- **General request** ("เช็คความพร้อมโปรเจค", "audit this repo") → full report (section 4).
- Project root = current working directory unless the user names another path. In a monorepo, audit the whole repo but report per workspace where they differ.

## 2. Collect candidates with the scanner

Run the bundled read-only scanner. This skill's base directory is shown when the skill loads:

```bash
python "<skill-base-dir>/scripts/scan.py" "<project-root>"
```

Use `python3` on macOS/Linux. On Windows PowerShell, write the output to a file and read that file; piping it into another program can mangle the encoding. The scanner walks the repo, skipping `node_modules`, `.venv`, `dist`, `.next` and the like, and prints JSON with these keys:

| Key | Holds |
|---|---|
| `stack` | root markers, monorepo markers, frameworks, `manage.py` locations |
| `packages` | every package.json: test/lint-related scripts and test/lint/hook deps |
| `python` | deps and `[tool.*]` sections from requirements / pyproject / setup.cfg |
| `tests` | files with test cases (estimated count), Django boilerplate `tests.py`, files named like tests that contain none, test configs |
| `health` | route files, code mentions (file:line), infra checks (Docker `HEALTHCHECK`, compose `healthcheck:`, k8s probes, nginx) |
| `lint` | lint/format config files |
| `ci` | each pipeline file, what it mentions (test/lint/build/deploy), step lines |
| `hooks` | `core_hooks_path`, hooks installed in `.git/hooks`, husky hooks and their commands, pre-commit framework hook ids |
| `hygiene` | mixed lockfiles, env examples, Dockerfiles, compose files |

If Python isn't available, do the same searches with Glob/Grep, using the patterns at the end of this file.

## 3. Verify: the scanner finds candidates, not answers

Read the key files before deciding a status. Common traps by category:

**Tests**
- Django's `startapp` creates `tests.py` containing only `# Create your tests here.`, which means there are no tests. These show up in `tests.django_boilerplate_tests_py`.
- `tests.named_like_tests_but_no_cases` is mostly settings modules (`settings/ci_test.py`), management commands (`test_smtp.py`), views and ad-hoc scripts, which aren't tests. One exception: a set of scripts with their own harness (a `check()` helper, a `run_tests.sh`, `sys.exit(1)` on failure) is a real test suite that the test runner simply can't discover. Report it as such.
- Watch for side effects at import time. Django's runner imports every `test*.py` inside a package, so a management command named `test_*.py` that connects to SMTP, an API or a database at module level will run during `manage.py test`. Warn about it before anyone runs the full suite.
- npm's default `"test": "echo \"Error: no test specified\" && exit 1"` is not a test suite (`test_script_is_npm_placeholder`). A script named `test:email` or similar may be a manual helper rather than a test, so read what it runs.
- Type-checking (`tsc --noEmit`) and lint are not tests. Don't count them.
- Having test files doesn't mean the tests run. Check whether CI or a script actually runs them. In a monorepo, also check that turbo.json has a `test` task and that the packages define one.
- `total_cases_estimate` comes from a regex, so report it as approximate ("~40 cases"). If the runner left logs or reports (`.turbo/*test*.log`, JUnit XML, coverage output), prefer the executed count from there and say where it came from. Parametrized tests often make the real number much higher.

**Health check**
- A route that only returns 200 proves the process is alive (liveness). One that also checks the DB or cache is readiness. Say which it is.
- Check that the route is reachable: it's included in the root `urls.py`, and it isn't blocked by auth. Look at Next.js `middleware.ts` matchers, DRF `DEFAULT_PERMISSION_CLASSES`, global auth guards, and any route registered after an auth middleware.
- Health checks can also live outside the app, in `health.infra`. A compose `healthcheck:` that calls the app's `/health` is good evidence that the route is really used.
- If the repo has nothing but the app runs behind a load balancer or a platform, mark ❓, because the check may be configured on the server.

**Lint / format**
- A config file doesn't mean lint is enforced. ✅ needs the linter to run somewhere automatic, either a CI step or a git hook. Config alone is 🟡.
- In Python projects the linters often appear only in `.pre-commit-config.yaml` (black / isort / flake8 hook ids), with no config file. That still counts as configured.

**CI**
- List what each pipeline actually does: lint, test, build or deploy. If a pipeline only builds and deploys, nothing gates tests or lint before production. Say this plainly; it's often the most useful finding.
- Resolve script aliases through `packages[].scripts`. For example, `yarn ci` may run `biome ci .`, which is lint, not tests. `npm ci` is an install step, not a check.
- CI configured outside the repo can't be seen from here (a Jenkins server, Vercel or Netlify dashboards). Mark it ❓ and say what to ask.

**Git hooks**
- A config file only takes effect once it's installed:
  - **husky**: active when `core_hooks_path` is `.husky/_` (v9) or `prepare`/`postinstall` runs `husky`. With `husky || true`, a failed install is silent.
  - **pre-commit framework**: active only when `pre-commit` appears in `installed_in_git_hooks`. If it doesn't, each developer has to run `pre-commit install` once. This is a common gap.
- Show what the pre-commit hook runs. Hooks run only on the developer's machine and can be skipped with `--no-verify`, so they complement CI and never replace it.

**Hygiene (mention only if found)**
- `hygiene.mixed_lockfiles`: for example, `yarn.lock` and `package-lock.json` in the same directory. This causes yarn's "package-lock.json found" warning and makes installs differ between machines and CI.
- No `.env.example` while the code reads env vars makes onboarding harder.

## 4. Report

Write the report in the user's language, translating the headings below. Use this structure:

```markdown
# Project Health: <project name>
**Stack:** <e.g. Django 5 + DRF, Celery> / <Next.js 15 + Express, Turborepo + pnpm workspaces>

| Area | Status | Evidence |
|---|---|---|
| Unit / integration tests | 🟡 | 3 files, ~34 cases (`catalog/tests.py` 21); 8 more apps are boilerplate |
| Health check | ✅ | `GET /health/` → `core/views.py:13`, also checks the DB |
| Lint / format | 🟡 | black/isort/flake8 in `.pre-commit-config.yaml`, but the hook is not installed |
| CI | 🟡 | `.github/workflows/deploy.yml` only builds and deploys; no test or lint step |
| Git hooks | 🟡 | config exists, but `.git/hooks` has no hook installed |

## Details
<2–4 bullets per area, with file paths (file:line where it helps)>

## Recommendations (best value first)
1. <smallest change with the biggest gain first, with the file and command>
```

What each status means:
- ✅ Exists **and** is enforced or used
- 🟡 Partial: exists but is boilerplate, isn't wired into CI or hooks, isn't installed, or is liveness-only
- ❌ Searched and found nothing
- ❓ Can't be verified from the code: configured outside the repo. Say what to ask and whom.

Give at most five recommendations. Make each one concrete (which file, which command) and order them by value per effort. Typical high-value items:
- add a test step to an existing CI workflow
- run `pre-commit install` and document it
- delete the stray lockfile

Offer to implement them, but don't change the project unasked. This skill is a read-only audit.

## Don't do these without asking

- **Run the test suite, install dependencies, or start servers.** Django's test runner creates a test database on whatever server the settings point at, and tests may call external services. Suggest the command instead (`python manage.py test`, `yarn test`).
- **Edit files.**

## Common follow-up questions

**"Do Django tests count as unit tests?"** (e.g. "ของ django นับเป็น unit test มั้ย")
- `django.test.TestCase` runs each test inside a transaction against a real test database, so strictly speaking it's an integration test.
- `SimpleTestCase` (no DB), plain `unittest.TestCase`, and pytest functions without `@pytest.mark.django_db` are closer to true unit tests.
- In everyday talk, teams call all of these "unit tests", and that's fine. Explain the difference in two lines, then say what the project actually has. If it's easy to tell, give the split, e.g. how many test classes subclass `TestCase` vs `SimpleTestCase`.

**Next.js / React**
- Component and unit tests use Vitest or Jest with Testing Library. End-to-end tests use Playwright or Cypress.
- Report the two kinds separately. Having only one of them is worth a 🟡 note, not ❌.

## Manual search patterns (when the scanner can't run)

Always exclude `node_modules`, `.venv`, `venv`, `dist`, `build`, `.next`.

- **JS/TS tests**: Glob `**/*.{test,spec}.{ts,tsx,js,jsx}`, `**/__tests__/**`, `**/*.cy.ts`
- **Python tests**: Glob `**/test_*.py`, `**/*_test.py`, `**/tests.py`, `**/tests/**/*.py`, then Grep `def test` to confirm real cases
- **Test config**: `jest.config.*`, `vitest.config.*`, `playwright.config.*`, `pytest.ini`, `conftest.py`, `[tool.pytest` in pyproject.toml
- **Health in code**: Grep `healthz`, `readyz`, `health[_-]?check`, `/health\b`, `['"]health/?['"]`, `['"]/?ping/?['"]`
- **Health in infra**: Grep `HEALTHCHECK` (Dockerfile), `healthcheck:` (compose), `livenessProbe` / `readinessProbe` (k8s)
- **Lint**: `biome.json*`, `eslint.config.*`, `.eslintrc*`, `.prettierrc*`, `ruff.toml`, `.flake8`, `[tool.ruff` / `[tool.black` in pyproject.toml
- **CI**: `.github/workflows/*.yml`, `.gitlab-ci.yml`, `bitbucket-pipelines.yml`, `azure-pipelines.yml`, `Jenkinsfile`
- **Hooks**: `.husky/*`, `.pre-commit-config.yaml`, `lefthook.yml`, `lint-staged` key in package.json, `git config core.hooksPath`, `ls .git/hooks`
