# Erebus

A GUI CLI hybrid that combines CLI with graphical file exploerer and text editor.

## Install (Arch Linux)

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

## Development

Run directly from the repo without installing:

```bash
cd app/
python main.py
```

## Project Structure

```
erebus/
├── PKGBUILD           ← Arch package build script
├── erebus.install     ← pacman install hooks
├── requirements.txt   ← pip deps (for non-Arch dev environments)
└── app/
    ├── main.py        ← entry point (pywebview window)
    ├── config_loader.py ← TOML loader with defaults fallback
    ├── defaults.py    ← single source of truth for all config values
    └── index.html     ← full UI shell
```
