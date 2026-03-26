# Maintainer: Chase <you@example.com>
pkgname=erebus
pkgver=0.2.0
pkgrel=1
pkgdesc="A keyboard-driven terminal IDE shell built with pywebview"
arch=('any')
url="https://github.com/chasebrowndev/erebus"
license=('MIT')
depends=('python' 'python-pywebview' 'python-gobject' 'webkit2gtk-4.1' 'gtk3')
optdepends=('python-tomli: TOML config support for Python < 3.11'
            'ttf-jetbrains-mono: recommended monospace font'
            'ripgrep: fast find-in-files search'
            'git: git status badges in explorer')
makedepends=('git')
install=erebus.install
source=("$pkgname-$pkgver::git+file://$startdir")
sha256sums=('SKIP')

package() {
    local repodir="$srcdir/$pkgname-$pkgver"
    local appdir="$pkgdir/usr/share/erebus"
    install -dm755 "$appdir/app"
    for f in main.py config_loader.py defaults.py setup.py pty_bridge.py fs_api.py \
              git_api.py search_api.py file_watcher.py index.html; do
        install -Dm644 "$repodir/app/$f" "$appdir/app/$f"
    done
    install -dm755 "$pkgdir/usr/bin"
    cat > "$pkgdir/usr/bin/erebus" << 'LAUNCHER'
#!/usr/bin/env bash
exec python /usr/share/erebus/app/main.py "$@"
LAUNCHER
    chmod 755 "$pkgdir/usr/bin/erebus"
    install -dm755 "$pkgdir/usr/share/applications"
    cat > "$pkgdir/usr/share/applications/erebus.desktop" << 'DESKTOP'
[Desktop Entry]
Name=Erebus
Comment=Keyboard-driven terminal IDE shell
Exec=erebus
Terminal=false
Type=Application
Categories=Development;Utility;
Keywords=terminal;editor;ide;shell;
DESKTOP
    install -Dm644 "$repodir/LICENSE" "$pkgdir/usr/share/licenses/$pkgname/LICENSE" 2>/dev/null || true
}
