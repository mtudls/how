# Maintainer: Mateusz Dzielinski <https://github.com/mdsyseng>
pkgname=how-cli
pkgver=0.6.5
pkgrel=1
pkgdesc="Fast, concise CLI assistant to learn how to do anything in Omarchy, Linux & your stack"
arch=('x86_64' 'aarch64')
url="https://github.com/mdsyseng/how"
license=('MIT')
depends=('python')
makedepends=('rust')
provides=('how')
conflicts=('how')
source=("git+https://github.com/mdsyseng/how.git#tag=v${pkgver}")
sha256sums=('SKIP')

build() {
  cd "$srcdir/how"
  python3 scripts/transpile_rust.py how -o how-bin
}

package() {
  cd "$srcdir/how"
  install -Dm755 how-bin "$pkgdir/usr/bin/how"
  install -Dm644 LICENSE "$pkgdir/usr/share/licenses/$pkgname/LICENSE"
  install -Dm644 README.md "$pkgdir/usr/share/doc/$pkgname/README.md"
}
