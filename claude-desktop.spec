%global appname claude-desktop
%global appdir /usr/lib/%{appname}
%global deb_version 1.40609.0
%global deb_name %{appname}_%{deb_version}_amd64
%global deb_sha256 a96e96ff8eb4d4d7ffa785aba7fc23f8684b12ac83ed2ef4060f0f09f4177a98

Name:           claude-desktop
Version:        1.40609.0
Release:        1%{?dist}
Summary:        Unofficial Fedora package for Claude Desktop

License:        Proprietary
URL:            https://claude.com/download
Source0:        https://downloads.claude.ai/claude-desktop/apt/stable/pool/main/c/%{appname}/%{deb_name}.deb

# This spec currently selects upstream's amd64 .deb. Do not add aarch64 here
# without also making the source name and payload architecture-aware; otherwise
# an ARM builder would repackage x86_64 binaries as aarch64.
ExclusiveArch:  x86_64

BuildRequires:  binutils

# ── Dependencies ──────────────────────────────────────────────
# Translated from the .deb's Depends field + namcap verification (see AUR PKGBUILD).
# Fedora package names differ from Debian's; mapped below.
Requires:       alsa-lib
Requires:       at-spi2-core
Requires:       cairo
Requires:       cups-libs
Requires:       dbus-libs
Requires:       expat
Requires:       glib2
Requires:       glibc
Requires:       gtk3
Requires:       hicolor-icon-theme
Requires:       libX11
Requires:       libXcomposite
Requires:       libXdamage
Requires:       libXext
Requires:       libXfixes
Requires:       libXrandr
Requires:       libXtst
Requires:       libcap-ng
Requires:       libdrm
Requires:       libnotify
Requires:       libseccomp
Requires:       libsecret
Requires:       libxcb
Requires:       libxkbcommon
Requires:       mesa-libGL
Requires:       nspr
Requires:       nss
Requires:       pango
Requires:       socat
Requires:       systemd-libs
Requires:       util-linux-core
Requires:       virtiofsd
Requires:       xdg-desktop-portal
Requires:       xdg-utils

# Cowork VM stack
Requires:       qemu-system-x86
Requires:       edk2-ovmf

# Optional: credential storage and tray icon
Recommends:     gnome-keyring
Recommends:     xdg-desktop-portal-gtk
Suggests:       libayatana-appindicator

%description
Unofficial Fedora package for Anthropic's Claude Desktop application,
including Chat, Cowork, and Claude Code. It repackages Anthropic's
official Debian package without modifying the proprietary application.

The Cowork feature runs inside a QEMU virtual machine, which is why
qemu-system-x86 and edk2-ovmf are hard requirements.

%prep
# A .deb is an ar archive containing debian-binary, control.tar.xz, and data.tar.xz.
# We only need data.tar.xz (the file payload).
echo "%{deb_sha256}  %{SOURCE0}" | sha256sum -c -
ar x %{SOURCE0}
tar -xf data.tar.xz

%install
# Copy the full file tree
cp -a usr/ %{buildroot}/usr/

# ── chrome-sandbox setuid ─────────────────────────────────────
# Chromium's sandbox helper; mode 4755 so it can create the browser
# sandbox on kernels where unprivileged user namespaces are disabled.
# The tarball already carries this mode; setting it explicitly documents
# that the setuid bit is intentional. Verify it in rpm -qplv.
chmod 4755 %{buildroot}%{appdir}/chrome-sandbox

# ── License file ──────────────────────────────────────────────
# Fedora convention: licenses under %%{_datadir}/licenses/%%{name}/
# The .deb ships its copyright in /usr/share/doc/. Grab it before cleanup.
install -d %{buildroot}%{_datadir}/licenses/%{name}
cp -a usr/share/doc/claude-desktop/copyright \
      %{buildroot}%{_datadir}/licenses/%{name}/LICENSE

# ── Clean up Debian cruft ─────────────────────────────────────
rm -rf %{buildroot}/usr/share/lintian
rm -rf %{buildroot}/usr/share/doc

# ── Cowork compatibility shims ────────────────────────────────
# The app hardcodes Debian filesystem paths. These symlinks map them
# to where Fedora actually installs the pieces.

# virtiofsd: Debian → /usr/bin, Fedora → /usr/libexec
ln -s ../libexec/virtiofsd %{buildroot}/usr/bin/virtiofsd

# ── Wayland + Vulkan workaround ─────────────────────────────────
# Electron on Wayland with Vulkan enabled triggers:
#   '--ozone-platform=wayland' is not compatible with Vulkan
# Disable Vulkan so the app stays on native Wayland (pixel-perfect
# fractional scaling) instead of falling back to blurry XWayland.
sed -i 's|^Exec=claude-desktop|Exec=claude-desktop --disable-vulkan|' \
    %{buildroot}/usr/share/applications/com.anthropic.Claude.desktop

# OVMF firmware: the app opens /usr/share/OVMF/OVMF_CODE_4M.fd and
# /usr/share/OVMF/OVMF_VARS_4M.fd (Debian naming).
#
# Fedora ships the 4M firmware as qcow2 under /usr/share/edk2/ovmf/.
# The bare .fd files are 2M, not 4M — those won't work.
#
# Strategy: symlink the 4M qcow2 files to the Debian-named paths.
# QEMU auto-detects image format. Verified working on Fedora 44.
install -d %{buildroot}/usr/share/OVMF
ln -s ../edk2/ovmf/OVMF_CODE_4M.qcow2 %{buildroot}/usr/share/OVMF/OVMF_CODE_4M.fd
ln -s ../edk2/ovmf/OVMF_VARS_4M.qcow2  %{buildroot}/usr/share/OVMF/OVMF_VARS_4M.fd

%files
/usr/bin/claude-desktop
%{appdir}/
/usr/share/applications/com.anthropic.Claude.desktop
/usr/share/icons/hicolor/
/usr/share/licenses/%{name}/
# Compat symlinks we created. Note /usr/share/OVMF/ itself is deliberately
# not listed — edk2-ovmf owns that directory.
/usr/bin/virtiofsd
/usr/share/OVMF/OVMF_CODE_4M.fd
/usr/share/OVMF/OVMF_VARS_4M.fd

%changelog
* Fri Aug 28 2026 Hitesh Aidasani <hitesh@gmail.com> - 1.40609.0-1
- Update to upstream version 1.40609.0
- Allowlist the statically linked github-mcp-server helper that upstream now
  bundles, so rpmlint stays fatal for unreviewed findings

* Sun Aug 23 2026 Hitesh Aidasani <hitesh@gmail.com> - 1.34493.1-1
- Update to upstream version 1.34493.1

* Tue Aug 04 2026 Hitesh Aidasani <hitesh@gmail.com> - 1.24012.11-1
- Update to upstream version 1.24012.11

* Wed Jul 29 2026 Hitesh Aidasani <hitesh@gmail.com> - 1.24012.9-2
- Mark the Fedora package as unofficial and remove the unnecessary claude conflict
- Verify the upstream Debian archive checksum before extracting it
- Correct the architecture rationale now that upstream also supports arm64

* Wed Jul 29 2026 Hitesh Aidasani <hitesh@gmail.com> - 1.24012.9-1
- Initial Fedora package, based on AUR claude-desktop PKGBUILD
- Maps Debian filesystem paths to Fedora conventions
- virtiofsd: /usr/bin/virtiofsd symlink to Fedora's /usr/libexec/virtiofsd
- OVMF: /usr/share/OVMF/OVMF_{CODE,VARS}_4M.fd symlinked to Fedora's
  /usr/share/edk2/ovmf/*_4M.qcow2 (Fedora ships the 4M firmware as qcow2;
  the bare .fd files are 2M and will not boot the Cowork VM)
- Electron: --disable-vulkan in the .desktop Exec lines, so Wayland does
  not fall back to XWayland
