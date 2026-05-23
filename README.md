# **BlurMyCLI<sup>v0.0.1</sup>** 

### description:
BlurMyCLI is a simple, user friendly and CLI focused set of Hyprland dotfiles with CLI utils.

##
**thanks to**:

- BlurMyShell, inspiration for the name.
- Omarchy, inspiration for the whole project.

#
> [!Warning]
> I am trying my best to make this compatible with other distros than Arch but currently, for the best compatibility use Arch with these dotfiles.

#
## installation

Run the interactive installer:

```sh
./install.py
```

the installer will:
- detect your OS and warn if not Arch Linux
- check all dependencies (distro-agnostic, uses `which` not pacman)
- ask if you want Hyprland blur effects
- ask if you want recommended CLI utils (cli-menu, cli-search, cli-launch, eightfetch)
- handle existing configs (backup, overwrite, or skip)
- show a summary before making any changes
- copy configs to `~/.config/`, install utils to `~/.local/bin/`
- add .cargo to your path

#
## binds

> This uses my binds, but if you want to configurate you can in hyprland.conf

open kitty = Super+S
kill window = Super+Q
logout of hyprland = Super+M
open dolphin = Super+E
toggle floating = Super+V
CLI applauncher = Super+Space
Browser = Super+Y
CLI quick search = Super+Shift+Space
CLI menu = Super+Alt+Space
Move windows(with mouse) = Super+LMB
Resize windows = Super+RMB
Move focus = Super+arrows OR hjkl
Move windows(with keys) = Super+Shift+arrows OR hjkl
Hide window = Super+N
Show hidden window(covers tiled windows) = Super+B
Tile hidden window(if hidden window is focused on) = Super+Shift+B
