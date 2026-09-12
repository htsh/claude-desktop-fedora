# Repository Guide

## Purpose and boundaries

- This repository contains Fedora packaging only. `claude-desktop.spec` is the implementation; `README.md` documents the user-facing build and compatibility behavior.
- Claude Desktop is Anthropic's proprietary upstream binary. Do not commit, publish, or attach `.rpm`, `.deb`, extracted `usr/`, archive members, or rpmbuild scratch trees. The SRPM also embeds the proprietary `.deb` and must not be redistributed without permission.
- Keep generated files outside the repository. The ignored build-artifact patterns in `.gitignore` are a safety net, not a place to build or unpack by default.
- The package is currently x86_64-only because `Source0` selects the amd64 `.deb` and Cowork depends on the x86 QEMU stack. Do not add architectures until the source name, payload, and dependencies are architecture-aware.

## Repository layout

- `claude-desktop.spec`: source metadata, checksum verification, dependency mapping, Debian-to-Fedora compatibility changes, payload ownership, and changelog.
- `claude-desktop.rpmlintrc`: narrow allowlist for reviewed diagnostics inherent to the proprietary Electron payload; unrecognized rpmlint errors remain fatal in CI.
- `README.md`: build/install instructions, supported Fedora/architecture claims, compatibility rationale, and the upstream-update checklist.
- `.github/workflows/build.yml`: Fedora-container CI that builds the RPM and asserts the packaging invariants below. It scrapes `%global deb_version`, `deb_sha256`, and `appname` out of the spec with `awk`, so renaming those globals breaks it.
- `CLAUDE.md`: condensed command reference and spec architecture for coding agents.
- `.gitignore`: proprietary inputs/outputs and local rpmbuild or extraction artifacts.
- `LICENSE` (packaging only, MIT) and `SECURITY.md` (disclosure policy).
- There is no application source and no automated test suite. CI is the only test harness.

## Change workflow

- Inspect the current worktree before editing and preserve unrelated user changes.
- For a packaging-only change, increment `Release` and add a matching `%changelog` entry. Do not change `Version` or `%global deb_version`.
- For an upstream update:
  1. Set `Version` and `%global deb_version` to the same upstream version.
  2. Reset `Release` to `1`.
  3. Download the amd64 `.deb` directly from the `Source0` URL and replace `%global deb_sha256` with its SHA-256 digest.
  4. Update `%changelog` and every versioned download filename/URL in `README.md`.
  5. Run `ar t` and inspect the extracted payload before assuming the archive member names, desktop file, application paths, dependencies, or `%files` manifest are unchanged.
- Use an actual calendar date in `%changelog`, keep entries newest-first, and summarize the packaging behavior that changed.
- Keep the spec and README consistent. If a dependency, supported platform, command, path, or workaround changes, update both where applicable.

## Build and verification

- One-time setup: `sudo dnf install rpmdevtools binutils rpmlint && rpmdev-setuptree`.
- Put the upstream archive at `~/rpmbuild/SOURCES/claude-desktop_<deb_version>_amd64.deb`. The current `%prep` expects `data.tar.xz`; verify that with `ar t` on every upstream update.
- Fast syntax/macro check: `rpmspec --parse claude-desktop.spec >/dev/null`.
- Do not lint the spec on its own from the repo root. rpmlint auto-discovers `claude-desktop.rpmlintrc` from the working directory even without `--rpmlintrc`, every filter in it matches a built-RPM finding, and unmatched filters are reported as `unused-rpmlintrc-filter` errors — so a spec-only target set always exits 64. Lint both together after a build: `rpmlint --rpmlintrc claude-desktop.rpmlintrc claude-desktop.spec "$RPM"`. Without the `.deb`, `rpmspec --parse` is the available spec check.
- Full build: `rpmbuild -ba claude-desktop.spec`. Outputs belong in `~/rpmbuild/RPMS/x86_64/` and `~/rpmbuild/SRPMS/`, never in this repository.
- Inspect the built manifest and modes with `rpm -qplv ~/rpmbuild/RPMS/x86_64/claude-desktop-*.rpm`.
- Review RPM diagnostics from the build. Do not suppress errors or warnings without understanding whether they apply to the repackaged Electron payload.
- Runtime-affecting changes require installing and launching the RPM on Fedora. Cowork-related changes require booting its QEMU VM, not merely opening the desktop application.
- In the final verification report, distinguish checks actually run from checks that could not be run because the proprietary `.deb`, rpmbuild tools, hardware virtualization, or a Fedora runtime was unavailable.

## Packaging invariants

- Keep the application under `/usr/lib/claude-desktop`. Do not replace it with `%{_libdir}` (`/usr/lib64` on Fedora); upstream's payload and launcher use `/usr/lib`.
- Preserve the Fedora compatibility work unless inspection proves it obsolete:
  - Patch desktop `Exec` lines with `--disable-vulkan` to keep Electron usable on native Wayland.
  - Provide `/usr/bin/virtiofsd` as a relative symlink to Fedora's `/usr/libexec/virtiofsd`.
  - Map Debian's `OVMF_{CODE,VARS}_4M.fd` paths to Fedora's 4M `.qcow2` firmware. Do not substitute Fedora's 2M bare `.fd` images.
- In `%files`, list only the two OVMF symlinks, not `/usr/share/OVMF/`; `edk2-ovmf` owns that directory.
- Keep `chrome-sandbox` root-owned with mode `4755`. This is security-sensitive and must be verified in `rpm -qplv` output after a full build.
- Preserve the upstream license by copying it into `%{_datadir}/licenses/%{name}` before removing Debian documentation.
- Keep checksum verification before archive extraction. Never update `%global deb_sha256` without calculating it from the exact `.deb` named by `Source0`.
- Do not claim this is an official Anthropic or Fedora package, and do not add COPR publishing instructions while redistribution permission is absent.

## Publishing constraints

This repository is public. The pre-publish work is complete: the git history has
never contained a proprietary binary, CI builds without publishing, `LICENSE` and
`SECURITY.md` are in place, and `main` requires a passing `build` check, with
force-pushes and deletion blocked. Review is not required — this is a solo
project, and the maintainer pushes to `main` directly. Keep it that way:

- CI must never upload or cache the `.rpm` or `.src.rpm`, and must delete build output in an `always()` step. Adding an artifact-upload step would publish Anthropic's binaries.
- Ignored binaries do not show up in plain `git status`. Check with `git status --ignored --short` plus a `find` for `.rpm`, `.deb`, and archive files before concluding the tree is clean.
- No reachable commit may ever contain the proprietary payload. Audit with `git log --all --pretty=format: --name-only | sort -u` after any history rewrite or bulk add.
- `LICENSE` covers this packaging only (MIT), not the Claude Desktop application.
- Releases carry no attached artifacts; users build from the spec against upstream's own `.deb`.
