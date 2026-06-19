# Contributing to Armarium

Thanks for your interest in Armarium! This is a small self-hosted project,
and contributions of any size — bug reports, ideas, documentation fixes, or
code — are genuinely welcome.

Before making structural changes (new models, routers, repositories, stores,
migrations, or anything touching auth/SSRF handling), read
[ARCHITECTURE.md](ARCHITECTURE.md) — it's the canonical reference for how the
codebase is organised and the conventions to follow, for human contributors
and AI assistants alike. [CLAUDE.md](CLAUDE.md) is the entry point used by
[Claude Code](https://claude.com/claude-code) and points to the same document.
For a full local environment setup (VS Code on macOS/Linux, running the test
suites, linting), see [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md).

## Reporting a bug

If something isn't working as expected:

1. Check the [existing issues](../../issues) to see if it's already been
   reported.
2. If not, open a new issue using the **Bug report** template. Please
   include:
   - Steps to reproduce the problem
   - What you expected to happen vs. what actually happened
   - Your environment (how you're running Armarium, browser, etc.)
   - Any relevant logs (`docker compose logs`) or screenshots

## Suggesting a feature

Have an idea for something Armarium should do?

1. Check the [existing issues](../../issues) to see if it's already been
   suggested.
2. Open a new issue using the **Feature request** template, describing the
   problem you're trying to solve, your proposed solution, and any
   alternatives you've considered. "Problem first" suggestions are easier to
   discuss than "please add feature X" — it helps to know *why* you need it.

## Submitting a pull request

1. **Fork** the repository and create a new branch for your change.
2. Make your changes, keeping them focused — smaller, single-purpose pull
   requests are much easier to review than large ones. If you change the
   schema, that's an Alembic revision (`alembic revision --autogenerate`) —
   there's no other migration mechanism (see ARCHITECTURE.md §4.3).
3. If you've changed backend code, run the test suite and quality gates from
   `backend/` (with `.venv` activated):

   ```bash
   pip install -r requirements.txt -r requirements-dev.txt
   python -m pytest -q   # 234+ tests
   ruff check app
   bandit -r app -ll
   pip-audit
   ```

4. If you've changed frontend code, run the equivalent checks from
   `frontend/`:

   ```bash
   npm install
   npm run build
   npm test -- --run
   npm run lint
   ```

5. Update any relevant documentation (README, ARCHITECTURE.md, CLAUDE.md,
   `.env.example`, etc.) if your change affects how Armarium is configured,
   used, or built — ARCHITECTURE.md explicitly says to keep itself in sync
   with the code.
6. Open a pull request against `main` describing what you changed and why.
   The pull request template will guide you through the details we'd find
   useful. CI runs the same checks above (plus an Alembic-on-PostgreSQL
   check) on every PR.

## Code style

There's no strict style guide — just try to follow the conventions already
used in the surrounding code (naming, structure, formatting) so the codebase
stays consistent. See ARCHITECTURE.md for the layering conventions (routers →
repositories → models) and frontend source-of-truth modules
(`lib/mediaIcons.js`, `lib/categories.js`, `lib/navigation.js`).

## Using Claude Code

This repository includes [CLAUDE.md](CLAUDE.md) and
[ARCHITECTURE.md](ARCHITECTURE.md), which give [Claude Code](https://claude.com/claude-code)
(and other AI assistants) the same conventions described above. If you use
Claude Code to help with a contribution, it will pick these up automatically
— see [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) for setup notes. Please
still review AI-assisted changes yourself before opening a PR: the same
quality gates (tests, lint, SAST) apply regardless of how the code was
written.

## Questions

If you're not sure where to start, or want to discuss an idea before writing
any code, feel free to open an issue — discussion is always welcome before
you put in the work.
