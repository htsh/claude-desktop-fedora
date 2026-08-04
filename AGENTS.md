# Repository Guide

## Purpose and boundaries

- This repository contains Fedora packaging only. `claude-desktop.spec` is the implementation; `README.md` documents the user-facing build and compatibility behavior.
- Claude Desktop is Anthropic's proprietary upstream binary. Do not commit, publish, or attach `.rpm`, `.deb`, extracted `usr/`, archive members, or rpmbuild scratch trees. The SRPM also embeds the proprietary `.deb` and must not be redistributed without permission.
- Keep generated files outside the repository. The ignored build-artifact patterns in `.gitignore` are a safety net, not a place to build or unpack by default.
- The package is currently x86_64-only because `Source0` selects the amd64 `.deb` and Cowork depends on the x86 QEMU stack. Do not add architectures until the source name, payload, and dependencies are architecture-aware.

## Repository layout

- `claude-desktop.spec`: source metadata, checksum verification, dependency mapping, Debian-to-Fedora compatibility changes, payload ownership, and changelog.
- `README.md`: build/install instructions, supported Fedora/architecture claims, compatibility rationale, and the upstream-update checklist.
- `.gitignore`: proprietary inputs/outputs and local rpmbuild or extraction artifacts.
- There is no application source, automated test suite, or CI configuration in this repository.

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

- One-time setup: `sudo dnf install rpmdevtools binutils && rpmdev-setuptree`.
- Put the upstream archive at `~/rpmbuild/SOURCES/claude-desktop_<deb_version>_amd64.deb`. The current `%prep` expects `data.tar.xz`; verify that with `ar t` on every upstream update.
- Fast syntax/macro check: `rpmspec --parse claude-desktop.spec >/dev/null`.
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

## Pre-publish checklist (for GitHub)

Before making this repo public:

1. **Verify `.gitignore` covers all proprietary artifacts.** The current patterns cover `.rpm`, `.deb`, `.tar.xz`, rpmbuild scratch dirs, and extracted `usr/` — that's correct. Do a dry run: `git status` should show zero untracked binaries.

2. **Audit the git history.** The initial commits may have included a built `.rpm` before the `.gitignore` was added. Run `git log --stat | grep -E '\.(rpm|deb|tar\.xz)'` and if any commits added proprietary binaries, rewrite history to exclude them (or squash into a clean initial commit). The repo must never have contained the proprietary payload in any reachable commit.

3. **Add CI that builds but doesn't publish.** A GitHub Actions workflow that runs `rpmbuild -ba claude-desktop.spec` on a Fedora container proves the spec works without distributing binaries. It should:
   - Run on pushes to `main` and PRs
   - Use a Fedora container image
   - Install `rpmdevtools binutils` and run `rpmdev-setuptree`
   - Download the `.deb` from upstream, build the RPM, verify with `rpm -qplv`
   - Run `rpmlint` on the built RPM
   - **Never** upload or cache the resulting `.rpm` or `.src.rpm` (they contain proprietary binaries)
   - Delete the build artifacts at the end of the job

4. **Add `rpmlint` to the workflow.** It catches spec issues like invalid dates, missing dependencies, and path ownership bugs.

5. **Add a LICENSE file for the packaging.** The spec and README are your work — choose MIT or Apache-2.0. Make it crystal clear this license covers only the files in this repo, not the proprietary Claude Desktop application.

6. **Add a `SECURITY.md` with a disclosure policy.** Something simple: "This repo contains only packaging. For security issues in Claude Desktop itself, contact Anthropic directly."

7. **Check the README one more time.** Make sure every versioned URL and filename references the current version (1.24012.11). The build instructions should work copy-paste for someone with a fresh Fedora install.

8. **Set up branch protection on `main`.** Require PRs, require CI to pass, and require at least one approving review before merge.
