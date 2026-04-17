"""mkdocs hook: expose binary template files from `data/templates/` as site assets.

The templates live under `data/` (they are data, not docs) but must be reachable
as downloads from the result-submission page. Registering them as mkdocs `File`
objects gives us three things at once:

  * they are copied verbatim into `site/templates/<filename>` during the build;
  * relative links written in markdown (`../templates/foo.xlsx`) are validated
    by mkdocs and do not trip `--strict`;
  * the URL is project-page safe (resolves under `/<repo>/` on GitHub Pages),
    unlike the legacy absolute `/data-model/files/...` hrefs.
"""

from pathlib import Path

from mkdocs.structure.files import File, InclusionLevel

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_TEMPLATES_DIR = _PROJECT_ROOT / "data" / "templates"


def on_files(files, config):
    """Append every file under data/templates/ so mkdocs ships it to /templates/.

    Uses `File.generated` with `abs_src_path` so mkdocs copies the binary from
    disk verbatim (no in-memory round-trip) and marks it `NOT_IN_NAV` —
    without an explicit inclusion level the file defaults to UNDEFINED, which
    link-validation treats as excluded and trips the "link to … which is
    excluded from the built site" warning.
    """
    if not _TEMPLATES_DIR.is_dir():
        return files
    for path in sorted(_TEMPLATES_DIR.iterdir()):
        if not path.is_file():
            continue
        files.append(
            File.generated(
                config,
                src_uri=f"templates/{path.name}",
                abs_src_path=str(path),
                inclusion=InclusionLevel.NOT_IN_NAV,
            )
        )
    return files
