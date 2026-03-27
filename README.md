#
# THIS PROJECT IS CURRENTLY PARTIALLY-FUNCTIONAL - HEAVY DEVELOPMENT STAGE
#

# Erebus

A GUI CLI hybrid that combines CLI with graphical file exploerer and text editor.

## Install (Arch Linux) [ non-Arch compatability in the future ] 

```bash
git clone https://github.com/chasebrowndev/Erebus
cd Erebus
makepkg -si
```

`makepkg -si` will automatically install all dependencies via pacman.

## Run

```bash
erebus
```

## Config

Erebus looks for a config file at `~/.config/erebus/config.toml`.
An annotated example is installed to `/etc/erebus/config.toml.example`.

```bash
mkdir -p ~/.config/erebus
cp /etc/erebus/config.toml.example ~/.config/erebus/config.toml
```

All keys are optional — only include values you want to override.
On first launch, Erebus will show a setup wizard to configure your shell, editor, and start path.

## Development

Run directly from the repo without installing:

```bash
cd app/
python main.py
```

## Project Structure

```
erebus/
├── PKGBUILD             ← Arch package build script
├── erebus.install       ← pacman install hooks
├── requirements.txt     ← pip deps (for non-Arch dev environments)
└── app/
    ├── main.py          ← entry point (pywebview window + JS API wiring)
    ├── config_loader.py ← TOML loader with deep-merge over defaults
    ├── defaults.py      ← single source of truth for all config values
    ├── setup.py         ← first-launch setup wizard backend
    ├── pty_bridge.py    ← pseudoterminal session manager
    ├── fs_api.py        ← filesystem API (read/write/list/delete/etc.)
    ├── git_api.py       ← git status/diff/log/branch integration
    ├── search_api.py    ← find-in-files (ripgrep or Python fallback)
    ├── file_watcher.py  ← mtime polling for external file changes
    └── index.html       ← full UI shell (editor, terminal, explorer)
```
