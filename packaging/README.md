# Packaging and releases (maintainer notes)

`how` ships through three channels. All of them come from one tag.

| Channel | Files in this repo | Upgrades with |
|---|---|---|
| AUR package `how-omarchy` → `/usr/bin/how` | `PKGBUILD`, `.SRCINFO` | `omarchy update` (runs `yay -Sua` for AUR packages) |
| Omarchy plugin → `~/.local/bin/how` symlink | `manifest.json`, `Service.qml`, `scripts/plugin-link.sh` | `omarchy plugin update io.github.mdsyseng.how` |
| `install.sh` → `~/.local/bin/how` copy | `install.sh` | `how update` (re-runs the installer after confirming) |

The package is called `how-omarchy` because `how` (saeziae/how) and `how-cli`
(patrykgruszka/how-cli) already exist on the AUR, and both install `/usr/bin/how`.
The PKGBUILD declares `provides=(how)` and `conflicts=(how how-cli)`.

## Cutting a release

```bash
mise run release 1.0.1      # bumps how, PKGBUILD, .SRCINFO, manifest.json, install.sh;
                            # runs tests; commits and tags v1.0.1 LOCALLY; pushes nothing
git show v1.0.1             # review
git push origin main v1.0.1 # this starts .github/workflows/release.yml
```

The release workflow:

1. checks tag == `__version__` == `pkgver` == manifest `version` == installer default (`scripts/check_release.py`),
2. runs the tests,
3. downloads the tag tarball and writes its sha256 into `PKGBUILD` and `.SRCINFO` (the repo keeps `SKIP`),
4. writes `SHA256SUMS.txt` (over `how`, `install.sh`, `PKGBUILD`, `.SRCINFO`), adds GitHub build-provenance attestations,
5. creates the GitHub release with those files,
6. builds the package in an `archlinux:base-devel` container, runs `namcap`, installs it and runs `how --version`,
7. pushes `PKGBUILD` + `.SRCINFO` to the AUR **only if** the `AUR_SSH_PRIVATE_KEY` secret is set; otherwise it logs a notice and stops.

Anyone can check a downloaded file's provenance with
`gh attestation verify how --repo mtudls/how`.

## One-time AUR setup (by hand, once)

1. Create an account on https://aur.archlinux.org and log in.
2. Make a key used only for this:
   `ssh-keygen -t ed25519 -C "how AUR release" -f ~/.ssh/aur_how -N ""`
3. AUR → *My Account* → *SSH Public Key*: paste `~/.ssh/aur_how.pub`, save.
4. GitHub → repo *Settings* → *Secrets and variables* → *Actions*:
   - secret `AUR_SSH_PRIVATE_KEY` = contents of `~/.ssh/aur_how`
   - optional variables `AUR_GIT_NAME` / `AUR_GIT_EMAIL` for the AUR commit author.
   Consider putting the secret on a protected `release` environment.
5. Nothing else: the first push creates the `how-omarchy` package on the AUR.
   (To publish by hand instead: `git clone ssh://aur@aur.archlinux.org/how-omarchy.git`,
   copy `PKGBUILD` and `.SRCINFO` from the GitHub release assets, commit, `git push`.)
6. After the first publish, check https://aur.archlinux.org/packages/how-omarchy and
   adopt it under your account if it was pushed by a different one.

The workflow pins the AUR host key fingerprint (`AUR_ED25519_FINGERPRINT` in
`release.yml`). Compare it once with the fingerprints listed on the AUR home page.

## Local checks

```bash
mise run lint                      # ruff, flake8, shellcheck (if installed), versions, manifest
makepkg --printsrcinfo | diff -u .SRCINFO -    # on Arch: .SRCINFO matches PKGBUILD
namcap PKGBUILD
```

## Plugin notes

- Omarchy clones plugins to `~/.config/omarchy/plugins/<manifest id>/` and updates them with
  `omarchy plugin update [id]` (fast-forward, shows the diff first). `omarchy update` does not
  update plugins.
- `Service.qml` runs `scripts/plugin-link.sh` once each time the shell loads the enabled
  service. The script only creates or repoints the `~/.local/bin/how` symlink; it never
  replaces a regular file it did not recognise, steps aside if `/usr/bin/how` exists, uses
  no network and no sudo, and logs to `~/.local/state/how/plugin.log`.
- Plugin folders may not contain symlinks (`omarchy plugin validate`); keep it that way.
- The plugin id stays `io.github.mdsyseng.how`. The id decides the checkout folder and is
  what `shell.json` records as enabled, so renaming it would orphan every existing install.
