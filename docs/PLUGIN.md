# how on Omarchy

How `how` fits into Omarchy: as a system package, as an Omarchy plugin, and how each one is updated.
`how` is a terminal tool only. It adds no bar icon, no window and no background process.

## Choosing a channel

| | AUR package `how-omarchy` | Omarchy plugin | Install script |
|---|---|---|---|
| Installed file | `/usr/bin/how` | `~/.local/bin/how`, a symlink into the plugin checkout | `~/.local/bin/how` (a copy) |
| Updated by | `omarchy update` | `omarchy plugin update io.github.mdsyseng.how` | `how update` (re-runs the installer after you confirm) |
| Removed by | `yay -R how-omarchy` | removing the plugin | deleting the file |
| Recommended | yes | when you manage tools as plugins | on non-Arch systems |

Install only one. `how doctor` and `how update` report which one is running.

## How `how` detects its channel

`how` resolves the real path of its own file:

- under `/usr/bin/` → **package**
- under a `…/omarchy/plugins/…` directory → **plugin**
- anything else → **script**

This is a local check on a path. It does not contact any server.

## Package (`how-omarchy`)

```bash
yay -S how-omarchy                  # or, on Omarchy: omarchy pkg aur add how-omarchy
```

The package is named `how-omarchy` because `how` and `how-cli` are already taken on the AUR by unrelated
projects. **It is not on the AUR yet**: the owner publishes it once, after the 1.0.0 release. Until then,
use the plugin or the install script.

The package installs the single `how` script to `/usr/bin/how`, with the licence and README. It depends
only on `python`.

<!-- TODO(packaging): confirm PKGBUILD source (git tag v${pkgver} or release tarball) and checksum (pinned sha256 vs SKIP). -->
<!-- TODO(packaging): list the exact files the package installs (README/LICENSE paths under /usr/share). -->

### Update flow

`omarchy update` updates system and AUR packages, so a new `how-omarchy` release arrives with it.
Omarchy recommends `omarchy update` over calling `yay -Syu` directly. `how` itself never checks for updates.

## Omarchy plugin

```bash
omarchy plugin add https://github.com/mtudls/how.git --enable
```

The plugin is a checkout of this repository. `manifest.json` describes it to Omarchy; `Service.qml` is a
headless service with no UI.

The plugin id is `io.github.mdsyseng.how`.

<!-- TODO(packaging): plugin checkout directory (e.g. ~/.config/omarchy/plugins/io.github.mdsyseng.how). -->
<!-- TODO(packaging): what Service.qml does on enable (creates the ~/.local/bin/how symlink? runs anything else?) and whether it runs on every session start. -->
<!-- TODO(packaging): the exact manifest.json fields (id, version, kinds, entryPoints). -->

### Update flow

```bash
omarchy plugin update io.github.mdsyseng.how
```

Because `~/.local/bin/how` is a symlink into the plugin checkout, updating the plugin updates `how`.
`omarchy update` does **not** update plugins; run the command above.

### Removal

<!-- TODO(packaging): exact command to remove the plugin, and whether removal deletes the ~/.local/bin/how symlink. -->

`how uninstall` prints the removal commands for the channel in use.

## Install script

The script installs a tagged release to `~/.local/bin/how` (override with `HOW_INSTALL_DIR`) and verifies
the download against the release's `SHA256SUMS`.

<!-- TODO(packaging): exact curl one-liner / download-and-verify commands, release asset names, and whether install.sh itself verifies SHA256SUMS. -->
<!-- TODO(packaging): supported environment variables (HOW_VERSION, HOW_INSTALL_DIR, ...) and flags. -->

### Update flow

`how update` shows the channel, and for script installs offers to re-run the installer. Nothing is
downloaded until you confirm.

## Releasing

The version lives in three places and must match: `__version__` in `how`, `pkgver` in `PKGBUILD`, and
`version` in `manifest.json`. A `vX.Y.Z` tag triggers the release workflow.

<!-- TODO(packaging): release workflow outputs (assets, SHA256SUMS) and the step that updates the package (AUR push or Omarchy repo PR). -->
