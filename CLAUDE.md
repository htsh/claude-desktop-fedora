# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

`AGENTS.md` holds the full change workflow, packaging invariants, and verification
expectations. Read it before making non-trivial edits — this file is the summary.

## What this repo is

Fedora packaging *only*. `claude-desktop.spec` repackages Anthropic's official
amd64 `.deb` for Claude Desktop, adding the filesystem shims Cowork's QEMU VM
needs on Fedora. There is no application source and no test suite; the "code" is
one spec file plus a CI workflow that builds it.

The proprietary payload must never enter the repo, git history, or a Release.
That includes the SRPM, which embeds the whole `.deb`. `.gitignore` is a safety
net, not permission to build inside the worktree.

## Commands

```bash
# One-time setup
sudo dnf install rpmdevtools binutils rpmlint && rpmdev-setuptree

# Fetch upstream source (must land here for rpmbuild to find it)
curl --fail --location \
  -o ~/rpmbuild/SOURCES/claude-desktop_1.24012.11_amd64.deb \
  'https://downloads.claude.ai/claude-desktop/apt/stable/pool/main/c/claude-desktop/claude-desktop_1.24012.11_amd64.deb'

rpmspec --parse claude-desktop.spec >/dev/null   # fast syntax/macro check, no source needed
rpmlint claude-desktop.spec                      # spec lint (dates, deps, path ownership)
rpmbuild -ba claude-desktop.spec                 # full build
rpm -qplv ~/rpmbuild/RPMS/x86_64/claude-desktop-*.rpm   # inspect manifest + modes
```

`rpmspec --parse` and `rpmlint` are the only checks runnable without the
proprietary `.deb` — reach for them first, and say so when that's all you ran.

`.github/workflows/build.yml` does the same sequence in a `fedora:latest`
container on pushes/PRs to `main`, then asserts the four things most likely to
regress silently: `chrome-sandbox` is `-rwsr-xr-x`, the `virtiofsd` symlink
target, both OVMF symlinks, and `--disable-vulkan` in the extracted desktop
file. It scrapes `%global deb_version`/`deb_sha256`/`appname` out of the spec
with `awk`, so renaming those globals breaks CI. It deletes all build output in
an `always()` step and uploads nothing.

## Architecture of the spec

Three stages, each with a reason to exist:

- **`%prep`** — verifies `%global deb_sha256` against `Source0` *before*
  extraction, then `ar x` + `tar -xf data.tar.xz`. The archive member name is an
  upstream assumption; re-check it with `ar t` on every version bump.
- **`%install`** — copies the tree verbatim, then applies the Fedora
  compatibility layer (see below). Also relocates the upstream copyright to
  `%{_datadir}/licenses/%{name}/LICENSE` *before* deleting `/usr/share/doc`.
- **`%files`** — lists the payload plus the three created symlinks, but
  deliberately not `/usr/share/OVMF/`, which `edk2-ovmf` owns.

The compatibility layer is the substance of the package. Don't remove a piece
without proving on a Fedora runtime that it's obsolete:

| Shim | Why |
|---|---|
| `--disable-vulkan` patched into the `.desktop` `Exec` line | Electron aborts on native Wayland with Vulkan on; without this it falls back to blurry XWayland |
| `/usr/bin/virtiofsd` → `../libexec/virtiofsd` | App looks in `/usr/bin`, Fedora installs to `/usr/libexec` |
| `/usr/share/OVMF/OVMF_{CODE,VARS}_4M.fd` → `../edk2/ovmf/*_4M.qcow2` | App wants Debian's 4M `.fd` names; Fedora's 4M firmware is qcow2 (QEMU sniffs the format). Fedora's bare `.fd` files are 2M and will not boot the VM |
| `chmod 4755 chrome-sandbox` | Preserves upstream's setuid helper; security-sensitive, verify in `rpm -qplv` |
| Hardcoded `/usr/lib/claude-desktop` | Upstream payload and launcher use `/usr/lib`; `%{_libdir}` would wrongly resolve to `/usr/lib64` |

`ExclusiveArch: x86_64` is load-bearing: `Source0` names the amd64 `.deb` and the
Cowork deps are x86 QEMU. Adding `aarch64` without making source name and
dependencies arch-aware would ship x86_64 binaries in an ARM RPM.

## Editing rules that bite

- Packaging-only change: bump `Release`, add a `%changelog` entry with a real
  calendar date, newest-first. Leave `Version` and `%global deb_version` alone.
- Upstream bump: set `Version` *and* `%global deb_version` together, `Release` to
  `1`, recompute `%global deb_sha256` from the exact `.deb` at the `Source0`
  URL, then update every versioned filename/URL in `README.md` and this file.
- Spec and `README.md` must stay in sync on dependencies, paths, supported
  platforms, and workarounds.
- Don't claim official Anthropic or Fedora status, and don't add COPR
  instructions while redistribution permission is absent.
- Cowork-affecting changes are only verified by booting the QEMU VM — opening the
  app is not enough. In any verification report, separate what you actually ran
  from what the missing `.deb`, rpmbuild tools, KVM, or Fedora runtime blocked.

Two stale spots in `AGENTS.md` to ignore: its "Repository layout" section says
there is no CI configuration (there is, see above), and most of its
"Pre-publish checklist" is done — CI, `LICENSE`, and `SECURITY.md` all exist
now. The live items there are the git-history audit and branch protection.
