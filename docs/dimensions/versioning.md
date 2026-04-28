# Dimension data versioning

The dimension data — the `dim_*` sheets in `data/dimensions/dimensions.xlsx`
together with their YAML metadata — is versioned as a single bundle. The
current version is shown on the [dimensions overview](index.md) and on each
per-dimension page.

## Bump rules

Every merge to `main` that changes `data/dimensions/dimensions.xlsx`
triggers an automatic version bump. The bump level is **derived from the
actual diff** (no commit-message labelling required) and the highest
severity in a single PR wins.

| Change to a dimension sheet | Level |
|---|---|
| `label` or `description` of an existing element changed | PATCH |
| `parent_id` or `level` of an existing element changed | MINOR |
| New element (row) added | MINOR |
| New dimension (sheet) added | MINOR |
| New column added to a flexible dimension | MINOR |
| Element `id` / primary key changed | MAJOR |
| Element (row) deleted | MAJOR |
| Dimension (sheet) removed | MAJOR |
| Column removed or renamed in a flexible dimension | MAJOR |
| No data change | none — no bump, no tag |

Contract YAML changes (the `name`, `title`, `description`, or
`contract_type` fields in `data/dimensions/dim_*.yaml`) do **not** bump the
version. Only sheet contents do.

### Pre-1.0 mapping

While the bundle is still in `0.x` the levels are mapped down by one step:

- raw `MAJOR` &rarr; effective `MINOR`
- raw `MINOR` &rarr; effective `PATCH`
- raw `PATCH` &rarr; effective `PATCH`

So a deletion against `0.1.0` produces `0.2.0` (not `1.0.0`), and a new row
produces `0.1.1`. Going to `1.0.0` is an explicit one-time decision —
manually edit `data/dimensions/VERSION`.

## Storage

- `data/dimensions/VERSION` — single-line plain text (e.g. `0.1.0`). The
  build reads this file at render time.
- `data/dimensions/CHANGELOG.md` — one entry per release; the post-merge
  workflow prepends a new entry on each bump.
- Git tag `dimensions-vX.Y.Z` on the bump commit. Diffs are taken between
  the most recent tag and `HEAD`.

## Pinning to a version

Every release publishes versioned snapshots alongside the canonical (latest)
downloads:

- canonical: `downloads/dimensions.xlsx`,
  `downloads/dimensions/dim_<name>.csv`
- versioned: `downloads/dimensions/v<version>/dimensions.xlsx`,
  `downloads/dimensions/v<version>/dim_<name>.csv`

External bookmarks against the canonical paths stay valid across releases.
Use the versioned path when you need to pin to a specific release.

## Release flow

1. Open a PR that changes `data/dimensions/dimensions.xlsx`. The
   `Excel Diff on PR` workflow posts the row-level diff and the **prospective
   version bump** as a comment.
2. Merge to `main`. The post-merge orchestrator:
    - finds the most recent `dimensions-v*` tag,
    - diffs `dimensions.xlsx` between that tag and `HEAD`,
    - computes the bump,
    - updates `VERSION`, prepends a `CHANGELOG.md` entry,
    - commits, tags `dimensions-vX.Y.Z`, and pushes.
3. The release commit's push triggers a fresh orchestrator run that
   builds and deploys the docs with the new version visible.

If no `dimensions-v*` tag exists yet the workflow logs a warning and
skips the release — manually tag the seed commit (`git tag
dimensions-v0.1.0 <sha> && git push origin dimensions-v0.1.0`) once.

## Recovery

If a release commit is wrong (bad CHANGELOG, wrong bump level), revert it
with a regular `Revert "chore(dimensions): release vX.Y.Z"` PR. Tag deletion
requires admin access (`git push origin :refs/tags/dimensions-vX.Y.Z`); only
delete tags that have not been consumed by downstream pinning.
