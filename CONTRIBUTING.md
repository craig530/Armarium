# Contributing to Armarium

Thanks for your interest in Armarium! This is a small self-hosted project,
and contributions of any size — bug reports, ideas, documentation fixes, or
code — are genuinely welcome.

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
   requests are much easier to review than large ones.
3. If you've changed backend code, run the test suite:

   ```bash
   cd backend
   pip install -r requirements.txt
   pytest -v
   ```

4. If you've changed frontend code, make sure it builds cleanly:

   ```bash
   cd frontend
   npm install
   npm run build
   ```

5. Update any relevant documentation (README, `.env.example`, etc.) if your
   change affects how Armarium is configured or used.
6. Open a pull request against `main` describing what you changed and why.
   The pull request template will guide you through the details we'd find
   useful.

## Code style

There's no strict style guide — just try to follow the conventions already
used in the surrounding code (naming, structure, formatting) so the codebase
stays consistent.

## Questions

If you're not sure where to start, or want to discuss an idea before writing
any code, feel free to open an issue — discussion is always welcome before
you put in the work.
