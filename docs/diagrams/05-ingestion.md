# Repository ingestion

How a GitHub repository becomes the list of Python modules the analyzer sees
(`ingest/git_loader.py`, `ingest/filters.py`).

## How it works

1. The commit's tarball is streamed into an anonymous temporary file, capped at
   `CRYPTOAUDIT_MAX_REPO_MB`. Git history is not downloaded.
2. The archive is read member by member **in memory**. Nothing is extracted to disk and nothing is
   executed.
3. Every byte read counts towards `CRYPTOAUDIT_MAX_UNPACKED_MB`; going over it fails the scan with
   `LIMIT_EXCEEDED` (protection against decompression bombs).
4. Each `.py` file that passes the checks becomes a `ModuleInput(module_name=path, source)`.
5. `.zip` archives in the repository are opened in memory, **one level deep**. Their `.py` members
   become modules named `archive.zip/path/inside.py` and pass the same checks.
6. Everything rejected is recorded as a `SkippedFile` with a reason, which the scan page lists.

## Checks and limits

| Check | Setting / rule | Result when it fails |
|---|---|---|
| Path is relative and safe (no `..`, absolute paths or backslashes) | always | skipped: unsafe path |
| Regular file (no symlinks or devices) | always | skipped: not a regular file |
| Not in an excluded directory (`.git`, `.venv`, `venv`, `env`, `node_modules`, `__pycache__`, `build`, `dist`, `.tox`, `.mypy_cache`, `__MACOSX`) | always | ignored |
| File size | `CRYPTOAUDIT_MAX_FILE_KB` (1024) | skipped: file too large |
| Number of Python files | `CRYPTOAUDIT_MAX_PYTHON_FILES` (5000) | skipped: file count limit reached |
| UTF-8 text | always | skipped: not UTF-8 |
| Archive size | `CRYPTOAUDIT_MAX_ARCHIVE_MB` (100) | skipped: archive too large |
| Archive readable | always | skipped: unreadable zip archive |
| Nested or encrypted archive members | always | skipped with that reason |
| Read `.zip` contents at all | `CRYPTOAUDIT_SCAN_ARCHIVES` (true) | archives ignored |

Sizes inside a zip are checked on the bytes actually read, not on the size the archive declares.

## Diagram

```mermaid
flowchart TD
    start(["fetch_repository(owner, name, ref)"]) --> dl["GitHubClient.download_tarball_to<br/>stream into TemporaryFile"]
    dl --> cap{"> MAX_REPO_MB?"}
    cap -- yes --> err1[/"LIMIT_EXCEEDED: scan fails"/]
    cap -- no --> open["tarfile.open (r:*)<br/>iterate members"]
    open --> budget{"unpacked total<br/>> MAX_UNPACKED_MB?"}
    budget -- yes --> err1
    budget -- no --> path{"safe relative path?<br/>(no .., no absolute, no backslash)"}
    path -- no --> skipUnsafe["skip: unsafe path"]
    path -- yes --> kind{"file type"}
    kind -- "other files" --> ignore["ignored (not listed)"]
    kind -- ".py" --> regular{"regular file?<br/>(no symlink / device)"}
    kind -- ".zip and SCAN_ARCHIVES" --> zreg{"regular file?"}
    regular -- no --> skipNotFile["skip: not a regular file"]
    regular -- yes --> excl{"in excluded dir?"}
    excl -- yes --> ignore
    excl -- no --> size{"> MAX_FILE_KB?"}
    size -- yes --> skipBig["skip: file too large"]
    size -- no --> count{"MAX_PYTHON_FILES reached?"}
    count -- yes --> skipCount["skip: file count limit reached"]
    count -- no --> utf{"UTF-8?"}
    utf -- no --> skipUtf["skip: not UTF-8"]
    utf -- yes --> module["ModuleInput<br/>module_name = path"]

    zreg -- no --> skipNotFile
    zreg -- yes --> zsize{"> MAX_ARCHIVE_MB?"}
    zsize -- yes --> skipArc["skip: archive too large"]
    zsize -- no --> zopen["zipfile.ZipFile(BytesIO)"]
    zopen -- "corrupt / unsupported" --> skipBadZip["skip: unreadable zip archive"]
    zopen --> member{"each member"}
    member -- "unsafe path" --> skipUnsafe
    member -- "nested .zip" --> skipNested["skip: nested archive not scanned"]
    member -- "encrypted" --> skipEnc["skip: encrypted archive member"]
    member -- ".py" --> zread["read at most MAX_FILE_KB + 1 bytes<br/>(declared sizes are not trusted)<br/>count bytes towards the unpacked budget"]
    zread --> zmod["ModuleInput<br/>module_name = archive.zip/inner/path.py"]

    module --> snap[("RepositorySnapshot<br/>modules (sorted) · skipped · commit · archive_bytes")]
    zmod --> snap
    skipUnsafe & skipNotFile & skipBig & skipCount & skipUtf & skipArc & skipBadZip & skipNested & skipEnc --> snap

    classDef skip fill:#fdf1e3,stroke:#c98a1b,color:#3a2a05
    classDef fail fill:#fbe9e6,stroke:#bf3120,color:#4a120b
    classDef ok fill:#e7f4ed,stroke:#17784a,color:#0b3320
    class skipUnsafe,skipNotFile,skipBig,skipCount,skipUtf,skipArc,skipBadZip,skipNested,skipEnc skip
    class err1 fail
    class module,zmod,snap ok
```
