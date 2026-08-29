# claude-desktop for Fedora

An RPM spec that repackages Anthropic's official Claude Desktop `.deb` for
Fedora, including the bits Cowork needs to boot its QEMU VM.

Verified working on Fedora 44 (x86_64).

This is an unofficial community package. Claude Desktop itself is proprietary
software from Anthropic; this repo only contains packaging.

The resulting RPM and SRPM contain Anthropic's proprietary application. This
project does not redistribute either artifact and cannot be hosted on Fedora
COPR without explicit redistribution permission from Anthropic.

## Build and install

```bash
# One-time setup
sudo dnf install rpmdevtools binutils
rpmdev-setuptree

# Fetch the proprietary application directly from Anthropic
curl --fail --location \
  -o ~/rpmbuild/SOURCES/claude-desktop_1.40609.0_amd64.deb \
  'https://downloads.claude.ai/claude-desktop/apt/stable/pool/main/c/claude-desktop/claude-desktop_1.40609.0_amd64.deb'

# Build (the spec verifies the .deb's pinned SHA-256 before extraction)
rpmbuild -ba claude-desktop.spec

# Install
sudo dnf install ~/rpmbuild/RPMS/x86_64/claude-desktop-*.rpm
```

Do not publish the generated RPM or SRPM; the SRPM embeds the complete upstream
`.deb`, not just this packaging source.

Like Anthropic's Debian package, the RPM installs Electron's `chrome-sandbox`
as a root-owned setuid executable (mode `4755`). The spec preserves and verifies
that security-sensitive permission intentionally.

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

**Cowork VM:** qemu-system-x86, edk2-ovmf, hardware virtualization enabled,
at least 8 GB RAM, and about 25 GB free disk space. Grant your user access to
KVM, then log out and back in:

```bash
sudo usermod -aG kvm "$USER"
```

The `vhost_vsock` kernel module should autoload when needed.

**Recommended:** gnome-keyring (credential storage), xdg-desktop-portal-gtk.
**Suggested:** libayatana-appindicator (tray icon).

## Architecture support

x86_64 only. Anthropic also supports arm64 Linux, but this spec currently points
to the amd64 `.deb` and maps the x86 Cowork VM dependencies. Adding `aarch64`
to `ExclusiveArch` without making the source and dependencies architecture-aware
would produce an "aarch64" RPM containing x86_64 binaries.

## Updating to a new upstream release

1. Set `Version` and `%global deb_version` to the new version in
   `claude-desktop.spec`, and reset `Release` to `1`.
2. Grab the new `.deb` from Anthropic and update `%global deb_sha256` with its
   `sha256sum` output.
3. Update the `%changelog` and the versioned download command above.
4. Check `ar t` output and the extracted filesystem layout before building.
5. Run `rpmbuild -ba claude-desktop.spec` and inspect the resulting RPM with
   `rpm -qplv`.

## Comparison with other Fedora builds

[`bsneed/claude-desktop-fedora`][bsneed] is the other Fedora packaging in
circulation. It predates Anthropic's official Linux packages, so it takes a
fundamentally different approach: its build script downloads the **Windows**
installer, unpacks `app.asar`, and substitutes a hand-written Linux
implementation of the `claude-native-bindings` native module. It is not a Wine
wrapper — the Electron app runs natively — but the payload is still Windows
build output, reassembled.

This repo repackages the official Linux `.deb` Anthropic publishes for Debian
and Ubuntu. That difference drives the rest:

| | This repo | `claude-desktop-fedora` |
|---|---|---|
| Upstream source | Official Linux `.deb`, SHA-256 pinned in the spec | Windows installer, unpacked and patched |
| Native module | Anthropic's own Linux binary | Community reimplementation |
| Cowork / QEMU VM | Supported; `virtiofsd` and 4M OVMF mapped to Fedora's paths | Not addressed |
| Wayland | `--disable-vulkan` keeps Electron on native Wayland | Not addressed |
| Packaging | `.spec` built by `rpmbuild`, linted, CI-verified | `build-fedora.sh` shell script |
| Version pinning | `Version` + checksum in the spec | Edit `CLAUDE_DOWNLOAD_URL` in the script |

The practical difference is feature coverage. Because the payload is Anthropic's
own Linux build, everything upstream ships works as shipped — including Cowork,
which boots a QEMU virtual machine and needs `virtiofsd` and 4M OVMF firmware at
the paths Debian uses. Supplying those on Fedora is most of what the
[compatibility table](#what-this-package-fixes) above is doing. A package built
from the Windows installer has no Linux VM stack to point at.

The tradeoff is scope: x86_64 only, and it tracks whatever version Anthropic has
published for Linux.

[bsneed]: https://github.com/bsneed/claude-desktop-fedora

## Credits

Based on the [AUR `claude-desktop` PKGBUILD][aur] by Kevin, which did the
original dependency identification and compatibility-path work. This repo
ports that to RPM and adds the Fedora-specific OVMF and virtiofsd mappings.

[aur]: https://aur.archlinux.org/packages/claude-desktop
