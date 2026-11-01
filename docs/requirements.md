# `how` — Product Requirements & Evolution Log

What users needed at each stage of `how`, and the resulting capability.
*(Expand any milestone below to read the original user prompts in Polish and English.)*

---

## Core Capabilities Summary (Effect Oriented)

1. **Instant CLI "How-To" Assistant** — Ask in plain words inside your terminal and get an exact command for Omarchy, Linux, or developer tools.
2. **Zero-Friction Login** — Authenticate with a free Groq API key directly from the terminal (`how auth login`).
3. **Resilient Model Selection** — Pick or health-check models (`how model check`) with automatic fallback if a model goes offline.
4. **Parent-Shell Output & One-Keystroke Run** — Never traps you in a subshell; copies the command to clipboard and lets you execute via `how run`.
5. **Verbosity Control** — Choose between command-only (`-0`), one-sentence summary (`--low`), or standard explanation.
6. **Strict Honesty** — Replies `"I don't know"` when uncertain instead of inventing broken flags.
7. **Local Documentation Context** — Reads local `# omarchy:*` headers, `tldr`, `man`, and sandboxed `--help` so flags match your installed version.
8. **Sliding Response Cache** — Remembers recent answers (`3h` default; configurable in `m`, `h`, `D`, `M`) and refreshes the timer whenever reused.
9. **Graduated Context Discovery & Native Rust Speed** — Step-by-step `[dry-run]` approval (`careful`) or instant auto-read with receipt (`yolo`), compiled from readable Python into a `~1 ms` native Rust binary.

---

## Full Prompt History (Way / Form)

<details>
<summary><b>Prompts 1–7: Core idea, terminal auth, dynamic models & Omarchy plugin packaging</b></summary>

### Prompt 1: Idea and core requirements
**Original (PL):**
> czy w omarchy jest wbudowane narzędzie w cli, które używa jakiegoś mega szybkiego llm-a (na groq) który jest wyspecjalizowany w podpowiedziach 'how to'? Jak nie ma, to czy jesteś w stanie napisać taką wtyczkę? Która loguje się pięknie przez terminal (takie flow jak antigravity cli/github cli)? I znajdź model na groq który ma sowity darmowy plan, oraz jest w stanie doskonale sobie radzić z pytaniami o omarchy i ogólnie o rzeczy developerskie na linux, oraz (ważne!) jest w stanie przeszukiwać internet!

**English:**
> Is there a built-in CLI tool in Omarchy that uses a super fast LLM (on Groq) specialized in 'how to' tips? If not, can you write such a plugin/tool? One that authenticates cleanly through the terminal (a flow like Antigravity CLI / GitHub CLI)? And find a model on Groq that has a generous free tier, handles questions about Omarchy and general Linux developer topics exceptionally well, and (importantly!) is capable of searching the internet!

### Prompt 2: Installation in the system
**Original (PL):**
> możesz ty mi to zainstalować? (poproś o uprawnienia jak nie masz)

**English:**
> Can you install it for me? (Ask for permissions if you don't have them).

### Prompt 3: Authentication debugging and in-place fix
**Original (PL):**
> nie loguje się do groq. Edytuj kod tam gdzie jest zainstalowany.

**English:**
> It does not log in to Groq. Edit the code in place where it is installed.

### Prompt 4: Automatic browser opening for authentication
**Original (PL):**
> dodatkowa uwaga: antigravity logs in to google, than it opens the browser itself. but how requires to open browser manually. change that.

**English:**
> Additional note: Antigravity logs in to Google, then it opens the browser automatically. But `how` requires opening the browser manually. Change that.

### Prompt 5: Dynamic model selection and prompt automation
**Original (PL):**
> niech how ma do wyboru modele (czy można pobrać listę modeli z api groq?), i niech je wybiera w cli. oraz: użycie ma wyglądać tak: `how to ping internet?` -> `how` wywołuje pytanie na groq: `"In Omarchy console how to ping internet?"`

**English:**
> Make `how` allow selecting models (fetch the list from Groq API) and select them in the CLI. Also automate query formatting: `how to ping internet?` -> `"In Omarchy console how to ping internet?"`

### Prompt 6: Exploring tools and GitHub issues
**Original (PL):**
> jest lepiej, ale dalej niedoskonale. Jesteś pewien, że nie ma takiego toola? Oraz: czy na githubie Omarchy nie ma takiego projektu/issue?

**English:**
> It's better, but still imperfect. Are you sure there is no such tool? Also: is there no such project/issue on the Omarchy GitHub?

### Prompt 7: Packaging and plugin investigation
**Original (PL):**
> 1. to co jest zrobione kod 'how' wpakuj do /home/m/how oraz utwórz tam requirements z moimi promptami (oraz tłumaczeniem na angielski pod spodem) i z nagłówkiem English version below.
> 2. Dowiedz się jak stworzyć plugin do Omarchy i jak wygląda proces publikacji.

**English:**
> 1. Put the completed code of `how` into `/home/m/how` and create a requirements document there with my prompts (and an English translation underneath) with the heading "English version below".
> 2. Find out how to create a plugin for Omarchy and what the publishing process looks like.

</details>

<details>
<summary><b>Prompts 8–16: Command execution UX, model health checks, multi-key auth & parent-shell output</b></summary>

### Prompt 8: Interactive edit field & System-1 model idea
**Original (PL):**
> Możesz dodać taką funkcję, że jeżeli z pewnym prawdopodobieństwem odpowiedzią na pytanie jest konkretna komenda, od razu dać tą komendę w polu edycji? Dodatkowy pomysł: użyć modelu system 1 (n.p. polski model basal) do oceny czy odpowiedź jest dobra.

**English:**
> Can you add a feature where, if with a certain probability the answer to the question is a concrete command, immediately put that command into the edit field? Additional idea: use a System 1 model (e.g. Polish model Basal) to evaluate whether the answer is good.

### Prompt 9: Confirm browser opening on login
**Original (PL):**
> dodatkowa uwaga do how auth login. Od razu otwiera przeglądarkę, ale wolałbym, żeby pytał (press any key)

**English:**
> Additional note for `how auth login`. It immediately opens the browser, but I would prefer if it asked (press any key).

### Prompt 10: Disambiguate queries vs subcommands & `how model check`
**Original (PL):**
> dodaj `how model check` który sprawdza prosty prompt dla każdego z dostępnych modeli. Jeśli sprawdzenie kończy się niepowodzeniem to przy liście modeli dodaj `x` dla niedziałających. Dodatkowe edge-case'y: `how auth works on omarchy?`

**English:**
> Add `how model check` which tests a simple prompt for each available model and marks broken ones with `x`. Fix edge case where natural questions starting with `auth` are mistaken for subcommands.

### Prompts 11–15: Cancel option, key selection, key naming, bash quoting & history
**English:**
> Add a keyboard option to cancel during API key entry; allow selecting existing keys; name keys during login; handle parentheses in unquoted queries; log proposed commands and support optional `~/.bash_history` integration.

### Prompt 16: Never spawn a child subshell; print directly to parent console
**Original (PL):**
> podpowiedź ma być wypisana w konsoli-rodzicu i żadna inna konsola nie jest potrzebna i how nie może niczego takiego sam uruchamiać!

**English:**
> The suggestion must be printed directly in the parent console, no child subshell is needed, and `how` must never launch a subshell on its own.

</details>

<details>
<summary><b>Prompts 17–27: Omarchy CLI minimalism, verbosity, honesty, local RAG, sliding cache & CI/CD</b></summary>

### Prompts 17–20: Omarchy CLI standards, verbosity (`zero`/`low`/`normal`), and `"I don't know"`
**English:**
> Align with Omarchy CLI standards; add `zero` (command only), `low` (minimal description), and `normal` verbosity modes; remove interactive bloat; return `"I don't know"` when the model is uncertain.

### Prompts 21–23: Local documentation RAG & response cache (`m`, `h`, `D`, `M`)
**English:**
> Attach local documentation context (`tldr`, `man`, `--help`, `# omarchy:*` headers); cache responses in SQLite (`3h` default) with `m`, `h`, `D`, `M` retention units and `[cache]` tags.

### Prompts 24–27: Minimalist `--help`, English localization, sliding cache & CI/CD pipelines
**English:**
> Radically simplify `--help` in minimalist Omarchy style; remove `init`; localize all user-facing strings to English; refresh cache expiration window on hit (sliding TTL); add GitHub Actions for V&V, linting, SAST security, secret scanning, and automated releases.

</details>

<details>
<summary><b>Prompts 28–30: Deep Thinking triage, graduated context (`careful`/`yolo`/`dry-run`), Rust transpiler & roadmap</b></summary>

### Prompt 28: Environment awareness, Deep Thinking tier & Groq Triage
**English:**
> Add permission-gated OS & local project stack discovery; support slower deep-thinking models (`-t` / `--think`) for complex troubleshooting; add Groq question triage (`how triage`).

### Prompt 29: Graduated context discovery & automatic local Python-to-Rust transpilation
**English:**
> 1. Make context discovery controllable and graduated: step-by-step user approval by default with `[dry-run]` commands in `careful` mode, plus `yolo` mode that goes ahead and states what it read (`🔎 Read: ...`).
> 2. Keep readable Python in the repo, and automatically transpile it locally to a native Rust binary without needing any LLM (`./install.sh`, `how build`).
> 3. Improve overall product clarity, minimalism, speed, and ease of comprehension (`how status`, `how run`).

### Prompt 30: Extensive testing, Free-Plan CI optimization, `v0.4.0` release & `v0.5+` roadmap
**English:**
> 0.1 Extensive tests for the solution and GitHub Actions pipeline review to squeeze maximum safety and quality out of the Free Plan.
> 0.2 Commit, push, and release after test-and-fix loops.
> Roadmap for later:
> 1. System-1 models (`basal`, `jev`) mixed with LLMs.
> 2. Repeat-question memory: ask if the previous cached answer didn't work.
> 3. Expand beyond `how` to `where` (find any file/config/log) under a unified friendly Omarchy CLI wrapper: `om`.
> 4. Dual-persona design: best programmer in the world + simplest everyday user ("normie").

</details>
