# Maintainer: Mateusz Dzielinski <https://github.com/mdsyseng>
pkgname=how-cli
pkgver=0.6.6
pkgrel=1
pkgdesc="Fast, concise CLI assistant to learn how to do anything in Omarchy, Linux & your stack"
arch=('any')
url="https://github.com/mtudls/how"
license=('MIT')
depends=('python')
provides=('how')
conflicts=('how')
source=("git+https://github.com/mtudls/how.git#tag=v${pkgver}")
sha256sums=('SKIP')

package() {
  cd "$srcdir/how"
  install -Dm755 how "$pkgdir/usr/bin/how"
  install -Dm644 LICENSE "$pkgdir/usr/share/licenses/$pkgname/LICENSE"
  install -Dm644 README.md "$pkgdir/usr/share/doc/$pkgname/README.md"
}
