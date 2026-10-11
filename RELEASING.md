# Releasing PCPulse

Releases are automated. Pushing a version tag tests the code, publishes to PyPI,
and creates a GitHub Release with the matching CHANGELOG notes.

## One-time setup (PyPI Trusted Publishing)

1. On pypi.org, open the `pcpulse` project and find its Publishing settings.
2. Add a GitHub publisher with these values:
   - Owner: `matthewpara567`
   - Repository: `pcpulse`
   - Workflow name: `release.yml`
   - Environment name: `pypi`
3. On GitHub, open the repo's Settings and create an environment called `pypi`.

## Each release

1. Update `__version__` in `src/pcpulse/__init__.py`.
2. In `CHANGELOG.md`, rename `## Unreleased` to `## X.Y.Z`. The text under it
   becomes the GitHub Release notes.
3. Commit and push to `main`, and wait for CI to go green.
4. Tag and push by name: `git tag -a vX.Y.Z -m "Release X.Y.Z"; git push origin vX.Y.Z`
   (`git push --follow-tags` does not push lightweight tags, so push the tag by name.)

The workflow stops early if the tag doesn't match the package version or if
CHANGELOG.md has no section for it. PyPI never accepts the same version twice,
so always bump before tagging.

## Manual fallback

`python -m build && python -m twine check dist/* && python -m twine upload dist/*`
