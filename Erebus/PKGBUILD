# Maintainer: Chase <you@example.com>
pkgname=erebus
pkgver=0.1.0
pkgrel=1
pkgdesc="A keyboard-driven terminal IDE shell built with pywebview"
arch=('any')
url="https://github.com/yourusername/erebus"
license=('MIT')

depends=(
    'python'
    'python-pywebview'
    'python-gobject'
    'webkit2gtk-4.1'
    'gtk3'
)

optdepends=(
    'python-tomli: TOML config support for Python < 3.11'
    'ttf-jetbrains-mono: recommended monospace font'
)

makedepends=('git')

install=erebus.install

# ── Source ────────────────────────────────────────────────────────────────────
# For local builds: run makepkg from the repo root.
# The PKGBUILD lives at the repo root alongside src/, so we reference
# files relative to $startdir (where makepkg was invoked from).
# For AUR/remote: swap this for a real git+https:// source.
source=("$pkgname-$pkgver::git+file://$startdir")
sha256sums=('SKIP')

package() {
    local repodir="$srcdir/$pkgname-$pkgver"
    local appdir="$pkgdir/usr/share/erebus"

    # ── Application source files ──────────────────────────────────────────────
    install -dm755 "$appdir/app"
    install -Dm644 "$repodir/app/main.py"          "$appdir/app/main.py"
    install -Dm644 "$repodir/app/config_loader.py" "$appdir/app/config_loader.py"
    install -Dm644 "$repodir/app/defaults.py"      "$appdir/app/defaults.py"
    install -Dm644 "$repodir/app/index.html"       "$appdir/app/index.html"
    install -Dm644 "$repodir/app/setup.py"      "$appdir/app/setup.py"
    install -Dm644 "$repodir/app/pty_bridge.py" "$appdir/app/pty_bridge.py"
    install -Dm644 "$repodir/app/fs_api.py"     "$appdir/app/fs_api.py"
    
    # ── /usr/bin launcher ─────────────────────────────────────────────────────
    install -dm755 "$pkgdir/usr/bin"
    cat > "$pkgdir/usr/bin/erebus" << 'LAUNCHER'
#!/usr/bin/env bash
exec python /usr/share/erebus/app/main.py "$@"
LAUNCHER
    chmod 755 "$pkgdir/usr/bin/erebus"

    # ── Desktop entry ─────────────────────────────────────────────────────────
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

    # ── Example config ────────────────────────────────────────────────────────
    install -dm755 "$pkgdir/etc/erebus"
    cat > "$pkgdir/etc/erebus/config.toml.example" << 'TOML'
# Erebus example config — copy to ~/.config/erebus/config.toml and edit.
# Only include keys you want to override; everything else falls back to defaults.

[theme]
# preset          = "erebus-default"
# font_family     = "JetBrains Mono"
# font_size       = 13
# background      = "#0a0a0a"
# surface         = "#111111"
# surface_2       = "#181818"
# border          = "#222222"
# accent          = "#ff2a2a"
# accent_dim      = "#8b0000"
# text            = "#e0e0e0"
# text_muted      = "#555555"
# text_dim        = "#333333"
# rounded_corners = false
# opacity         = 1.0

[layout]
# explorer_width    = 22       # % of window width
# terminal_height   = 32       # % of window height
# terminal_position = "bottom" # "bottom" | "right"
# show_explorer     = true
# show_terminal     = true
# show_editor       = true

[shell]
# provider   = "zsh"    # zsh | bash | fish | nushell
# scrollback = 10000

[editor]
# provider     = "builtin"  # builtin | micro | neovim
# tab_size     = 4
# word_wrap    = false
# line_numbers = true

[keybinds]
# focus_explorer  = "Ctrl+E"
# focus_terminal  = "Ctrl+T"
# focus_editor    = "Ctrl+Shift+E"
# command_palette = "Ctrl+P"
# new_tab         = "Ctrl+N"
# close_tab       = "Ctrl+W"
TOML

    # ── License ───────────────────────────────────────────────────────────────
    install -Dm644 "$repodir/LICENSE" \
        "$pkgdir/usr/share/licenses/$pkgname/LICENSE" 2>/dev/null || true
}
