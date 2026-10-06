# CivicFlow GitHub Workflow

Use four feature branches plus one integration branch:

- `feature/citizen-reporting`
- `feature/municipal-operations`
- `feature/intelligence-analytics`
- `feature/platform-admin`
- `develop`
- `main`

Feature branches merge through pull requests into `develop`. After integration tests pass, `develop` is promoted to `main`.

Commits should represent real work: feature implementation, schema migrations, bug fixes, tests, refactoring, UI work, performance fixes and documentation. Pull requests should have a meaningful scope and describe how the change was tested.

## Example bootstrap

After the owner creates `develop`, each developer clones the repository and creates one branch from `develop`. Keep commits focused and open a pull request when a feature is testable. Never force-push or reset another contributor's branch.

Example: `git checkout develop && git pull origin develop && git checkout -b feature/citizen-reporting && git push -u origin feature/citizen-reporting`.
