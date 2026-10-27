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
