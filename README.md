# **BlurMyCLI<sup>v0.0.1</sup>** 

### **֎** Description:
BlurMyCLI is a simple, user friendly and CLI focused set of Hyprland dotfiles with CLI utils.

##
**Thanks to**:

- BlurMyShell, inspiration for the name.
- Omarchy, inspiration for the whole project.

#
> [!Warning]
> I am trying my best to make this compatible with other distros than Arch but currently, for the best compatibility use Arch with these dotfiles.

#
## Installation

Run the interactive installer:

```sh
./install.py
```

The installer will:
- Detect your OS and warn if not Arch Linux
- Check all dependencies (distro-agnostic, uses `which` not pacman)
- Ask if you want Hyprland blur effects
- Ask if you want recommended CLI utils (cli-menu, cli-search, cli-launch, eightfetch)
- Handle existing configs (backup, overwrite, or skip)
- Show a summary before making any changes
- Copy configs to `~/.config/`, install utils to `~/.local/bin/`