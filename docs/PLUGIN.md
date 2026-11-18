# how on Omarchy

How `how` fits into Omarchy: as a system package, as an Omarchy plugin, or through the install script, and
how each one is updated. `how` is a terminal tool only. It adds no bar icon, no window and no background process.

## Choosing a channel

| | AUR package `how-omarchy` | Omarchy plugin | Install script |
|---|---|---|---|
| Installed file | `/usr/bin/how` | `~/.local/bin/how`, a symlink into the plugin checkout | `~/.local/bin/how` (a verified copy) |
| Updated by | `omarchy update` | `omarchy plugin update io.github.mdsyseng.how` | `how update` (re-runs the installer after you confirm) |
| Removed by | `yay -Rns how-omarchy` | `omarchy plugin remove io.github.mdsyseng.how`, then `rm -f ~/.local/bin/how` | `install.sh --uninstall` |
| Use it when | you want `how` to update with the system (recommended) | you manage desktop add-ons as plugins | you are not on Arch, or want a user-only install |

Install only one. `how doctor` and `how update` report which one is running, and `how uninstall` prints the
removal commands for it.

## How `how` detects its channel

`how` resolves the real path of its own file:

- under `/usr/bin/` → **package**
- under a `…/omarchy/plugins/…` directory → **plugin** (the symlink in `~/.local/bin` resolves there)
- anything else → **script**

This is a local check on a path. It does not contact any server.

## Package (`how-omarchy`)

```bash
yay -S how-omarchy                  # or, on Omarchy: omarchy pkg aur add how-omarchy
```

The package is named `how-omarchy` because `how` and `how-cli` are already taken on the AUR by unrelated
projects that also install `/usr/bin/how`; it declares `conflicts=('how' 'how-cli')`.
**It is not on the AUR yet**: the owner publishes it once, after the 1.0.0 release. Until then, use the
plugin or the install script.

The package depends only on `python`, with `wl-clipboard`, `xclip` or `xsel` as optional dependencies for
copying. It builds from the `v<pkgver>` tag tarball of this repository, runs `how --version` as a check, and installs:

- `/usr/bin/how`
- `/usr/share/licenses/how-omarchy/LICENSE`
- `/usr/share/doc/how-omarchy/README.md`

The repository keeps `sha256sums=('SKIP')`. On a `vX.Y.Z` tag the release workflow pins the tag tarball's real SHA-256 into the released `PKGBUILD` and `.SRCINFO`, and pushes them to the AUR only when the `AUR_SSH_PRIVATE_KEY` repository secret exists. The one-time owner steps (AUR account, key, secret) are in [packaging/README.md](../packaging/README.md).

### Update flow

`omarchy update` updates system and AUR packages, so a new `how-omarchy` release arrives with it.
Omarchy points users to `omarchy update` rather than calling `yay -Syu` directly. `how` itself never checks
for updates.

## Omarchy plugin

```bash
omarchy plugin add https://github.com/mtudls/how.git --enable
```

The plugin is a checkout of this repository in `~/.config/omarchy/plugins/io.github.mdsyseng.how`.

- `manifest.json` describes it to Omarchy: id `io.github.mdsyseng.how`, kinds `service` and `cli`,
  entry points `Service.qml` and `how`.
- `Service.qml` is a headless service with no UI. When the plugin is enabled it runs
  `scripts/plugin-link.sh` once, which makes `~/.local/bin/how` a symlink to the `how` file in the checkout.

`plugin-link.sh` uses no network and no sudo, and logs each decision to `~/.local/state/how/plugin.log`. It:

- does nothing if `/usr/bin/how` exists (the package wins);
- leaves alone any `~/.local/bin/how` it does not recognise, such as a script install
  (run `install.sh --uninstall`, then disable and re-enable the plugin to switch);
- replaces a copy left by plugin versions before 1.0.0, keeping it as `~/.local/bin/how.pre-plugin-link`.

### Update flow

```bash
omarchy plugin update io.github.mdsyseng.how
```

Because `~/.local/bin/how` is a symlink into the plugin checkout, updating the plugin updates `how`.
`omarchy update` does **not** update plugins; run the command above.

### Removal

```bash
omarchy plugin remove io.github.mdsyseng.how
rm -f ~/.local/bin/how
```

Omarchy has no plugin-removal hook, so `omarchy plugin remove` leaves the `~/.local/bin/how` link dangling; the `rm` line removes it.

## Install script

```bash
curl -fsSL https://github.com/mtudls/how/releases/latest/download/install.sh | bash
```

The installer:

1. downloads `how` and the release's checksum file for one pinned release tag;
2. refuses to continue unless the SHA-256 of `how` matches;
3. places it atomically at `~/.local/bin/how` (`HOW_INSTALL_DIR` to change);
4. writes `~/.local/state/how/install-receipt`, so `--uninstall` removes exactly that file.

It never uses sudo, never edits shell rc files, and installs no cron job, hook or background updater.
Options: `--dry-run`, `--version vX.Y.Z` (or `HOW_VERSION`), `--force`, `--local` (development),
`--uninstall [--purge]`. `install.sh --help` lists them.

The checksum file is `SHA256SUMS.txt`, attached to every GitHub release. `how update` does not download anything itself: after you confirm, it re-runs the published installer, which does the verification.

### Update flow

`how update` shows the channel and, for script installs, the exact download-verify-install command, then
runs it only if you confirm. Running the installer again does the same.

## Releasing

The version must match in `how` (`__version__`), `PKGBUILD` and `.SRCINFO` (`pkgver`), `manifest.json`
(`version`) and `install.sh` (`HOW_DEFAULT_VERSION`). `python3 scripts/check_release.py vX.Y.Z` checks this
and validates `manifest.json`. A `vX.Y.Z` tag triggers the release workflow.

The release workflow checks that the versions agree, runs the tests, and creates the GitHub release with `how`, `install.sh`, `PKGBUILD`, `.SRCINFO` and `SHA256SUMS.txt` attached. It then build-tests the package in an Arch container and, if the AUR secret is configured, publishes it.
