# Releasing to PyPI (GitHub Actions)

This project is set up to publish to PyPI automatically when you push a git tag like `v0.0.1`.

## 1) Configure PyPI trusted publishing (recommended)

1. Create the project on PyPI (first upload can be done by the workflow once trusted publishing is configured).
2. In PyPI, go to your project → **Publishing** / **Trusted Publishers**.
3. Add a GitHub trusted publisher:
   - **Owner**: your GitHub username/org
   - **Repository**: your repo name
   - **Workflow**: `publish.yml`
   - **Environment**: (leave empty unless you use GitHub Environments)

This uses OpenID Connect (OIDC), so you do not need to store a PyPI API token in GitHub.

## 2) Release steps

1. Update versions:
   - `pyproject.toml` (`[project].version`)
   - `src/django_honeywords/__init__.py` (`__version__`)
2. Run tests locally:

```bash
pytest -q
```

3. Commit and push.
4. Create and push a tag:

```bash
git tag v0.0.1
git push origin v0.0.1
```

GitHub Actions will build `sdist`/`wheel` and publish to PyPI.

## 3) Optional: TestPyPI

You can duplicate the workflow for TestPyPI (recommended for the first time) by configuring another trusted publisher for TestPyPI and using the `repository-url` input of `gh-action-pypi-publish`.
