# claude-desktop for Fedora

An RPM spec that repackages Anthropic's official Claude Desktop `.deb` for
Fedora, including the bits Cowork needs to boot its QEMU VM.

Verified working on Fedora 44 (x86_64).

This is an unofficial community package. Claude Desktop itself is proprietary
software from Anthropic; this repo only contains packaging.

## Install

Once the COPR repo is up:

```bash
sudo dnf copr enable <your-username>/claude-desktop
sudo dnf install claude-desktop
```

## Build it yourself

```bash
# One-time setup
sudo dnf install rpmdevtools
rpmdev-setuptree

# Fetch the upstream .deb
curl -L -o ~/rpmbuild/SOURCES/claude-desktop_1.24012.9_amd64.deb \
  'https://downloads.claude.ai/claude-desktop/apt/stable/pool/main/c/claude-desktop/claude-desktop_1.24012.9_amd64.deb'

# Build and install
rpmbuild -ba claude-desktop.spec
sudo dnf install ~/rpmbuild/RPMS/x86_64/claude-desktop-*.rpm
```

## What this package fixes

The upstream `.deb` assumes Debian's filesystem layout. Fedora differs in a
few places, and Cowork fails in confusing ways when it can't find what it
expects. Each of these is handled in `%install`:

| Problem | Fix |
|---|---|
| Wayland + Vulkan crashes Electron at launch | `--disable-vulkan` patched into the `.desktop` `Exec` lines |
| App opens `/usr/share/OVMF/OVMF_CODE_4M.fd`; Fedora ships the 4M firmware as **qcow2** under `/usr/share/edk2/ovmf/` | Symlink the `.qcow2` files to the Debian-style `.fd` paths — QEMU auto-detects the format |
| Fedora's bare `OVMF_CODE.fd` is 2M, but the VM needs 4M | Ignored; the qcow2 symlinks above are the 4M firmware |
| `virtiofsd` lives in `/usr/libexec/`, app looks in `/usr/bin/` | Symlink `/usr/bin/virtiofsd` → `/usr/libexec/virtiofsd` |
| `.deb` installs to `/usr/lib/`, not `/usr/lib64/` | Hardcode `/usr/lib`; do **not** use `%{_libdir}` |
| `.deb` has no `/usr/bin/claude` symlink | Only `claude-desktop` is listed in `%files` |
| Desktop file is `com.anthropic.Claude.desktop` | Exact name matched in `%files` |
| `socat` isn't preinstalled on Fedora | Declared as `Requires`; DNF pulls it in |

The `--disable-vulkan` flag is what keeps the app on native Wayland. Without
it Electron aborts with `'--ozone-platform=wayland' is not compatible with
Vulkan` and falls back to XWayland, which looks blurry under fractional
scaling.

`/usr/share/OVMF/` is owned by `edk2-ovmf`, so the spec lists only the two
symlinks it creates inside that directory — never the directory itself.

## Dependencies

**Runtime:** alsa-lib, at-spi2-core, cairo, cups-libs, dbus-libs, expat,
glib2, glibc, gtk3, hicolor-icon-theme, libX11, libXcomposite, libXdamage,
libXext, libXfixes, libXrandr, libXtst, libcap-ng, libdrm, libnotify,
libseccomp, libsecret, libxcb, libxkbcommon, mesa-libGL, nspr, nss, pango,
socat, systemd-libs, util-linux-core, virtiofsd, xdg-desktop-portal,
xdg-utils

**Cowork VM:** qemu-system-x86, edk2-ovmf. The `vhost_vsock` kernel module
autoloads — no configuration needed.

**Recommended:** gnome-keyring (credential storage), xdg-desktop-portal-gtk.
**Suggested:** libayatana-appindicator (tray icon).

## Architecture support

x86_64 only. Upstream publishes an amd64 `.deb` and nothing else, and
`Source0` points at that exact file. Adding `aarch64` to `ExclusiveArch`
without also making `deb_name` architecture-aware would produce an "aarch64"
RPM full of x86_64 binaries.

## Updating to a new upstream release

1. Bump the `Version` and `%global deb_version` fields in `claude-desktop.spec`
   (they must match).
2. Grab the new `.deb` from the [upstream pool][pool].
3. `rpmbuild -ba claude-desktop.spec`
4. If it fails, the `.deb`'s internal layout probably changed — check for
   renamed binaries or new hardcoded Debian paths.

[pool]: https://downloads.claude.ai/claude-desktop/apt/stable/pool/main/c/claude-desktop/

## Credits

Based on the [AUR `claude-desktop` PKGBUILD][aur] by Kevin, which did the
original dependency identification and compatibility-path work. This repo
ports that to RPM and adds the Fedora-specific OVMF and virtiofsd mappings.

[aur]: https://aur.archlinux.org/packages/claude-desktop
