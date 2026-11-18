#!/usr/bin/env bash
set -euo pipefail
# Root only prepares a fresh directory; all makepkg operations use an unprivileged user.
work=$(mktemp -d /tmp/trilium-build.XXXXXXXX)
trap 'rm -rf "$work"' EXIT
cp PKGBUILD trilium-next-server.sh trilium-next-server.service "$work/"
chown -R builder:builder "$work"
runuser -u builder -- bash -euo pipefail -c '
  cd "$1"
  test "$(id -u)" -ne 0
  makepkg --printsrcinfo > .SRCINFO
  makepkg --verifysource --noconfirm
  makepkg --cleanbuild --clean --force --noconfirm
  mapfile -t packages < <(makepkg --packagelist)
  package=""
  for candidate in "${packages[@]}"; do
    test -f "$candidate"
    sha256sum "$candidate"
    if bsdtar -xOf "$candidate" .PKGINFO | grep -qx "pkgname = trilium-next-server-bin"; then
      package="$candidate"
    fi
  done
  test -n "$package"
  bsdtar -tf "$package" > package-files.txt
  for path in opt/trilium-next-server/trilium.sh usr/bin/trilium-next-server usr/lib/systemd/system/trilium-next-server.service; do
    grep -Fx "$path" package-files.txt
  done
  sha256sum "$package"
' bash "$work"
if [[ ${1:-} == --generate ]]; then
  cp "$work/.SRCINFO" .SRCINFO
else
  diff -u .SRCINFO "$work/.SRCINFO"
fi
