# Releasing PCPulse

1. Update the version in `pyproject.toml` and `src/pcpulse/__init__.py`.
2. Move the `Unreleased` items in `CHANGELOG.md` under the new version.
3. Make sure CI is green on `main`.
4. Build and check: `python -m build && python -m twine check dist/*`
5. Upload: `python -m twine upload dist/*`
6. Tag and push: `git tag vX.Y.Z && git push --follow-tags`

PyPI never accepts the same version twice, so always bump before uploading.
