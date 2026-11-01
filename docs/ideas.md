# Pomysły i rozwój narzędzia `how` (Ideas & Roadmap)

## 1. Lokalny RAG dla manuali systemowych i Omarchy (Local Documentation Context)

### Problem
Modele LLM na Groq mają ogólną wiedzę o Linuksie, ale mogą nie znać:
- Specyficznych, najnowszych poleceń i skryptów Omarchy (`/usr/bin/omarchy-*`, konfiguracja Quickshell, skróty Hyprland).
- Dokładnych flag i podkomend rzadziej używanych narzędzi zainstalowanych lokalnie w systemie.
- Wysłanie wszystkich manuali (`/usr/share/man` to >120 MB tekstu) w całości do Groq nie jest możliwe z powodu limitów kontekstu (TPM / token limit) i opóźnień sieciowych.

### Koncepcja rozwiązania
Automatyczny, lekki RAG działający po stronie klienta `how`, który przed wysłaniem zapytania do Groq w ułamku sekundy (<10 ms) lokalnie pobiera relevantny kontekst i dokleja go do promptu:

1. **Kontekst z `tldr` / `man`:**
   - Wykrywanie w zapytaniu nazw poleceń (np. `pacman`, `hyprctl`, `nmcli`, `ip`, `systemctl`).
   - Szybki odczyt strony skróconej dokumentacji z lokalnego `tldr <cmd>` lub wyciągu flag z `man <cmd>` / `<cmd> --help`.
   - Wstrzykiwanie 15–30 kluczowych linii oficjalnego manuala do kontekstu LLM.

2. **Indeks poleceń Omarchy (`omarchy-*` index):**
   - Lokalny plik pamięci podręcznej (np. `~/.cache/how/omarchy-index.json`) z listą dostępnych poleceń systemowych i ich jednolinijkowymi opisami.
   - Szybkie dopasowanie leksykalne/słów kluczowych do zapytania użytkownika (np. "audio", "theme", "backup") i wstrzyknięcie listy dedykowanych komend do system promptu.

3. **Semantyczny RAG w oparciu o SQLite / Embeddings (opcja zaawansowana):**
   - Wstępnie wygenerowany lokalny indeks wektorowy bazy wiedzy o Omarchy i Linuksie (np. SQLite z fts5 lub wektorami).
   - Opcja automatycznego pobierania top-k fragmentów dokumentacji.

### Korzyści
- Zawsze aktualna i dokładna składnia poleceń.
- Pełne wsparcie dla unikalnych mechanizmów Omarchy bez konieczności fine-tuningu modelu bazowego.
- Zachowanie szybkości odpowiedzi (brak narzutu przesyłania setek kilobajtów tekstu).

---

## 2. Pamięć podręczna odpowiedzi (Groq Response Caching)

### Zaimplementowane rozwiązanie
Lokalny cache odpowiedzi w oparciu o bazę SQLite (`~/.cache/how/cache.db`) w trybie WAL:
1. **Domyślna retencja:** 3 godziny.
2. **Konfigurowalna retencja:** Standardowe jednostki czasowe:
   - `m` - minutes (np. `30m`)
   - `h` - hours (np. `3h`)
   - `D` - days (np. `7D`, `14D`)
   - `M` - months (np. `1M`, `3M`)
   - pełne słowa: `minut`, `godzin`, `dni`, `miesięcy`
   - wyłączenie cache: `0`, `off`, `wyłącz`
3. **Oznaczanie odpowiedzi z cache:** Każda odpowiedź zwrócona z pamięci podręcznej jest czytelnie oznaczona tagiem `[cache]`.
4. **Zarządzanie przez CLI:**
   - `how cache` / `how cache status` - stan bazy, retencja, liczba wpisów
   - `how cache retention <czas>` / `how cache <czas>` - zmiana retencji (np. `how cache 7D`)
   - `how cache clear` - wyczyszczenie pamięci podręcznej i VACUUM
   - `how cache off` / `how cache on` - włączanie i wyłączanie
   - `how --no-cache <pytanie>` - jednorazowe pominięcie cache
   - `how --retention <czas> <pytanie>` - jednorazowe wymuszenie retencji dla zapytania
5. **Izolacja klucza:** Hasz SHA-256 z modelu, trybu verbosity oraz znormalizowanego zapytania, zapobiegający konfliktom formatów.

---

## 3. Roadmap v0.5+ (Next-Gen Architecture & Normie UX)

### 3.1 System-1 Models (`basal`, `jev`) + System-2 LLM Hybrid
- **Idea:** Use ultra-fast local System-1 reflex models (`basal`, `jev`, or embedded sub-50MB micro-encoders/grammars) as the L0 reflex layer before hitting cloud LLMs:
  - **L0 (`<3 ms`, offline System-1 `basal`/`jev`):** Classifies intent (`how` vs `where` vs `fix`), scores command danger level (`read-only` vs `mutating` vs `destructive`), and directly synthesizes canonical commands for the top ~500 common Linux/Omarchy operations offline.
  - **L1 (`~150 ms`, Groq LPU Fast Path):** Handles parameterized commands combined with local `tldr`/`man`/`omarchy-*` RAG.
  - **L2 (`~1–3 s`, Deep Thinking `-t`):** Escalates multi-step debugging, boot/kernel/Wayland triage, and failure recovery to reasoning models (`deepseek-r1`, `o3-mini`, `claude-3-7-sonnet`, `gemini-2.5-pro`).

### 3.2 Repeat-Question Memory ("Did the previous answer not work?")
- **Problem:** When a user asks the exact same question a second time within minutes, returning the identical `[cache]` answer silently is frustrating—the user is re-asking *because the first suggestion didn't solve their problem*.
- **Solution:**
  - Track `hit_count` and `last_hit_at` inside `response_cache` (`~/.cache/how/cache.db`).
  - When the same query is asked again within a short window (e.g. `<30 minutes`), `how` asks:
    ```text
    ? You asked this 2m ago. Did the previous answer not work?
      [Y] Try a fresh Deep Thinking solution (bypasses cache + escalates to -t)
      [e] Attach last terminal error / exit code and fix it
      [n] Show the cached command again
    ```
  - In non-interactive (`-0`) mode, keep deterministic cache behavior while printing a one-line stderr hint.

### 3.3 From `how` to `where` — and the Unified `om` CLI ("Friendly Fast Omarchy CLI — om!")
- **Expanding the Verb Paradigm:**
  - `how <task>` → **Procedural knowledge** (*"how to record screen"*, *"how to free disk space"*).
  - `where <thing>` → **Spatial & system discovery** (*"where is hyprland monitor config"*, *"where are nginx error logs"*, *"where is the largest folder in home"*, *"where is port 8080 used"*). Combines fast local probes (`fd`, `plocate`, `rg`, `ss`, `systemctl`, XDG paths) with LLM ranking.
- **Unified Wrapper: `om` (Omarchy CLI):**
  - `om` is a 2-keystroke, zero-friction entry point for the whole ecosystem:
    - `om how to ...` (or just `om to ...`) → delegates to `how`
    - `om where is ...` → locates files, configs, logs, binaries, and listening ports
    - `om fix` → inspects the last failed shell command + journalctl/stderr and proposes a targeted fix
    - `om !` / `om run` → safely previews and executes the last suggested command
    - `om status` → unified health, context permissions, cache, and model dashboard

### 3.4 Dual-Persona Design: World's Best Systems Programmer × Simplest "Normie" User
- **What the Simplest User ("Normie") Needs:**
  1. **Forgiving Natural Input:** Whether a user types `how toupdate system`, `how do i update my system`, or `how update`, it just works without complaining about flags.
  2. **Safety Traffic Lights:** Every suggested command gets an automatic plain-English safety badge:
     - `🟢 Safe (read-only)` — only inspects info (`ls`, `df`, `ip`, `pacman -Si`)
     - `🟡 Changes system/files` — edits configs or installs packages (`pacman -S`, `cp`, `sed -i`)
     - `🔴 Destructive / Admin` — deletes data or alters boot/partitions (`rm -rf`, `dd`, `mkfs`); requires explicit confirmation in `how run`.
  3. **No Copy-Paste Gymnastics:** `how run` (or `how !`) runs the command right away with confirmation, and clipboard copy happens automatically in the background.
- **What the Best Systems Programmer Demands:**
  1. **Zero-Dependency Readable Source + Native Binary Speed:** Keep `how` as clean, auditable single-file Python (`#!/usr/bin/env python3`), while `install.sh` and `how build` deterministically transpile the Python AST to a native Rust binary (`1.1 ms` startup, 0 external crates, 0 LLM involved).
  2. **Graduated Context Trust (`careful` / `dry-run` / `yolo`):** Step-by-step approval with exact `--dry-run` shell equivalents in `careful` mode, or transparent `🔎 Read: OS[...], Stack[...], Docs[...]` receipts in `yolo` mode.
  3. **Hermetic Bubblewrap Sandboxing:** Any untrusted CLI `--help` probe runs inside `bwrap --ro-bind / / --unshare-all --cap-drop ALL`.


