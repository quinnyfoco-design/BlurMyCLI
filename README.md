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
