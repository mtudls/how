# Security policy

## Reporting a vulnerability

Please report security issues privately through a
[GitHub security advisory](https://github.com/mtudls/how/security/advisories/new) on `mtudls/how`.
Do not open a public issue.

Include the `how --version` output, the exact command or input, what `how` showed, and what you expected.
You will get an acknowledgement, and the fix will be credited to you in the changelog unless you prefer otherwise.

## In scope

- **Classifier bypasses.** Any command that `how` shows as 🟢 safe but that changes or destroys data,
  changes system state, or runs code fetched from the network. These are security bugs, not feature requests.
- A 🔴 dangerous command that can be run without typing `run`, or a 🟡 command that runs on Enter or with `-y`.
- The executed command differing in any way from the displayed command.
- Data sent anywhere other than what `how privacy` states, or sent without the user's action.
- The API key appearing in the log, on screen (beyond its last 4 characters), or in a file with permissions wider than 0600.
- Install or update paths that skip checksum verification or can be redirected to another source.

## Out of scope

- A harmless command shown as 🟡. Unknown commands are 🟡 by design; a pull request with a test is welcome.
- A destructive command shown as 🟡 rather than 🔴. It still needs explicit confirmation; please open a normal issue.
- What the model suggests. The model can be wrong; the badge and the confirmation exist for that reason.
- Vulnerabilities in the API provider, Python, or the user's shell.

## Supported versions

| Version | Supported |
|---|---|
| 1.0.x | Yes |
| 0.6.x and older | No. Please upgrade to 1.0 |
