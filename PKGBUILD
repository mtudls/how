# Maintainer: Mateusz Dzielinski <https://github.com/mdsyseng>
#
# AUR package for `how` (https://github.com/mtudls/how).
# Named how-omarchy because "how" and "how-cli" are already taken on the AUR
# by unrelated projects that also install /usr/bin/how.
#
# Release flow: .github/workflows/release.yml fills in the real sha256 of the
# v${pkgver} tag tarball, attaches this PKGBUILD to the GitHub release and, if
# the AUR_SSH_PRIVATE_KEY secret is set, pushes it to the AUR. See
# packaging/README.md. 'SKIP' below is replaced there; never publish it as is.

pkgname=how-omarchy
pkgver=1.0.1
pkgrel=1
pkgdesc="Ask in plain words, get one terminal command with a safety badge (Omarchy/Arch)"
arch=('any')
url="https://github.com/mtudls/how"
license=('MIT')
depends=('python')
optdepends=(
  'wl-clipboard: copy the suggested command to the clipboard on Wayland'
  'xclip: copy the suggested command to the clipboard on X11'
  'xsel: copy the suggested command to the clipboard on X11 (alternative)'
)
provides=('how')
conflicts=('how' 'how-cli')
source=("$pkgname-$pkgver.tar.gz::https://github.com/mtudls/how/archive/refs/tags/v$pkgver.tar.gz")
sha256sums=('SKIP')

check() {
  cd "how-$pkgver"
  python -m py_compile how
  python how --version
}

package() {
  cd "how-$pkgver"
  install -Dm755 how "$pkgdir/usr/bin/how"
  install -Dm644 LICENSE "$pkgdir/usr/share/licenses/$pkgname/LICENSE"
  install -Dm644 README.md "$pkgdir/usr/share/doc/$pkgname/README.md"
}
