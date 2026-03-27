# Maintainer: Chase <you@example.com>
pkgname=erebus
pkgver=0.2.0
pkgrel=1
pkgdesc="A keyboard-driven terminal IDE shell built with pywebview"
arch=('any')
url="https://github.com/chasebrowndev/erebus"
license=('MIT')
depends=('python' 'python-pywebview' 'python-gobject' 'webkit2gtk-4.1' 'gtk3' 'ttf-jetbrains-mono')
optdepends=('python-tomli: TOML config support for Python < 3.11'
            'ttf-fira-code: alternative monospace font'
            'ttf-cascadia-code: alternative monospace font'
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
    # Install annotated example config so post_install hint and README work
    install -dm755 "$pkgdir/etc/erebus"
    cat > "$pkgdir/etc/erebus/config.toml.example" << 'EXAMPLE'
# Erebus example configuration
# Copy to ~/.config/erebus/config.toml and edit as desired.
# All keys are optional — only include values you want to override.

[shell]
# command = "bash"   # shell binary to run in terminal tabs
# scrollback = 10000

[editor]
# provider = "builtin"   # builtin | nano | nvim | vim | micro | ...
# command  = "nvim"      # binary to exec (for non-builtin editors)
# tab_size = 4
# word_wrap = false
# line_numbers = true

[terminal]
# emulator = "kitty"   # external terminal for "Open in Terminal"

[ui]
# start_path = "~"   # directory the explorer opens to on launch

[theme]
# preset         = "erebus-default"
# font_family    = "JetBrains Mono"
# font_size      = 13
# background     = "#0a0a0a"
# surface        = "#111111"
# surface_2      = "#181818"
# border         = "#222222"
# accent         = "#ff2a2a"
# accent_dim     = "#8b0000"
# text           = "#e0e0e0"
# text_muted     = "#555555"
# text_dim       = "#333333"
# rounded_corners = false
}
