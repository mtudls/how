# Requirements & Prompts History for `how` CLI
## (English version below)

Zestawienie promptów użytkownika definiujących wymagania funkcjonalne, architekturę oraz proces iteracji narzędzia `how`.

---

## Prompt 1: Idea and core requirements

### Wersja oryginalna (PL):
> czy w omarchy jest wbudowane narzędzie w cli, które używa jakiegoś mega szybkiego llm-a (na groq) który jest wyspecjalizowany w podpowiedziach 'how to'?
> Jak nie ma, to czy jesteś w stanie napisać taką wtyczkę?
> Która loguje się pięknie przez terminal (takie flow jak antigravity cli/github cli)?
> I znajdź model na groq który ma sowity darmowy plan, oraz jest w stanie doskonale sobie radzić z pytaniami o omarchy i ogólnie o rzeczy developerskie na linux, oraz (ważne!) jest w stanie przeszukiwać internet!

### English version below
> Is there a built-in CLI tool in Omarchy that uses a super fast LLM (on Groq) specialized in 'how to' tips?
> If not, can you write such a plugin/tool?
> One that authenticates cleanly through the terminal (a flow like Antigravity CLI / GitHub CLI)?
> And find a model on Groq that has a generous free tier, handles questions about Omarchy and general Linux developer topics exceptionally well, and (importantly!) is capable of searching the internet!

---

## Prompt 2: Installation in the system

### Wersja oryginalna (PL):
> możesz ty mi to zainstalować? (poproś o uprawnienia jak nie masz)

### English version below
> Can you install it for me? (Ask for permissions if you don't have them).

---

## Prompt 3: Authentication debugging and in-place fix

### Wersja oryginalna (PL):
> …/cf/koko ✗ how auth login
> 
> ◆ Groq CLI Authentication (Omarchy Helper)
> 
> Aby uzyskać darmowy klucz API (0$, bez karty kredytowej), wejdź na:
>   https://console.groq.com/keys
> 
> Wklej swój Groq API Key (gsk_...): 
> 
> ✗ Błąd: Klucz API jest nieprawidłowy lub brak połączenia z Groq.
> 
> nie loguje się do groq.
> Edytuj kod tam gdzie jest zainstalowany.

### English version below
> …/cf/koko ✗ how auth login
> 
> ◆ Groq CLI Authentication (Omarchy Helper)
> 
> To obtain a free API key ($0, no credit card required), go to:
>   https://console.groq.com/keys
> 
> Paste your Groq API Key (gsk_...): 
> 
> ✗ Error: API key is invalid or unable to connect to Groq.
> 
> It does not log in to Groq.
> Edit the code in place where it is installed.

---

## Prompt 4: Automatic browser opening for authentication

### Wersja oryginalna (PL):
> dodatkowa uwaga: antigravity logs in to google, than it opens the browser itself. but how requires to open browser manually. change that.

### English version below
> Additional note: Antigravity logs in to Google, then it opens the browser automatically. But `how` requires opening the browser manually. Change that.

---

## Prompt 5: Dynamic model selection and prompt automation

### Wersja oryginalna (PL):
> Teraz dostałem to:
> /cf/koko ❯ how to ping someone
> 
> how ❯ (model: groq/compound)
> 
> ✗ Błąd Groq API (404): The model `groq/compound` does not exist or you do not have access to it.
> 
> niech how ma do wyboru modele (czy można pobrać listę modeli z api groq?), i niech je wybiera w cli.
> 
> oraz: 
> użycie ma wyglądać tak:
> 
> how to ping internet?
> how wywołuje pytanie na groq: "In Omarchy console how to ping internet?"
> 
> Jakoś to zautomatyzuj tak, żeby było optymalnie.
> Myśl nad tym długo jak poprawiać flow użytkownika :)

### English version below
> Now I got this:
> /cf/koko ❯ how to ping someone
> 
> how ❯ (model: groq/compound)
> 
> ✗ Groq API Error (404): The model `groq/compound` does not exist or you do not have access to it.
> 
> Make `how` allow selecting models (is it possible to fetch the list of models from Groq API?), and let it select them in the CLI.
> 
> Also:
> The usage must look like this:
> 
> how to ping internet?
> `how` triggers the query on Groq: "In Omarchy console how to ping internet?"
> 
> Automate this somehow so it is optimal.
> Think deeply about how to improve the user flow :)

---

## Prompt 6: Exploring tools and GitHub issues

### Wersja oryginalna (PL):
> jest lepiej, ale dalej niedoskonale.
> Jesteś pewien, że nie ma takiego toola? Oraz: czy na githubie Omarchy nie ma takiego projektu/issue?

### English version below
> It's better, but still imperfect.
> Are you sure there is no such tool? Also: is there no such project/issue on the Omarchy GitHub?

---

## Prompt 7: Packaging and plugin investigation

### Wersja oryginalna (PL):
> nie, nie mam na myśli tego co znalazłeś, ale mniejsza o to.
> Na ten moment zróbmy tak:
> 
> 1. to co jest zrobione kod 'kow' wpakuj do /home/m/how oraz utwórz tam requirements z moimi proomptami (oraz tłumaczeniem na angielski pod spodem) i z nagłówkiem English version below.
> 2. Dowiedz się jak stworzyć plugin do Omarchy i jak wygląda proces publikacji.

### English version below
> No, that's not what I had in mind, but never mind that.
> For now, let's do this:
> 
> 1. Put the completed code of `how` into `/home/m/how` and create a requirements document there with my prompts (and an English translation underneath) with the heading "English version below".
> 2. Find out how to create a plugin for Omarchy and what the publishing process looks like.

---

## Prompt 8: Interactive edit field for executable commands

### Wersja oryginalna (PL):
> Możesz dodać taką funkcję, że jeżeli z pewnym prawdopodobieństwem odpowiedzią na pytanie jest konkretna komenda, od razu dać tą komendę w polu edycji? 
> Dodatkowy pomysł: użyć modelu system 1 (n.p. polski model basal) do oceny czy odpowiedź jest dobra.
> to może ten UX najpierw. Przetestujmy go.

### English version below
> Can you add a feature where, if with a certain probability the answer to the question is a concrete command, immediately put that command into the edit field?
> Additional idea: use a System 1 model (e.g. Polish model Basal) to evaluate whether the answer is good.
> Maybe this UX first. Let's test it.

---

## Prompt 9: Confirm browser opening on login

### Wersja oryginalna (PL):
> doadkowa uwaga do how auth login. Odrazu otwiera przeglądarkę, ale wolałbym, żeby pytał (press any key)

### English version below
> Additional note for `how auth login`. It immediately opens the browser, but I would prefer if it asked (press any key).

---

## Prompt 10: Disambiguate queries vs subcommands & model health check

### Wersja oryginalna (PL):
> w międzyczasie dodaj how model check (o ile nie gryzie się z nazwami modeli) ((lub modelcheck)) który sprawdza jakiś prosty prompt dla każdego z dostępnych modeli, bo nie każdy jest dostępny.
> Jeśli sprawdzenie kończy się niepowodzeniem to przy liście modeli dodaj x dla niedziałających.
> dodatkowe edge-case'y:
> how master ❯ how auth works on omarchy?
> Nieznana komenda auth: works

### English version below
> In the meantime add `how model check` (as long as it doesn't clash with model names) ((or `modelcheck`)) which tests a simple prompt for each available model, because not every model is available.
> If the check fails, add an `x` next to broken ones in the model list.
> Additional edge cases:
> `how master ❯ how auth works on omarchy?`
> `Nieznana komenda auth: works`

---

## Prompt 11: Cancel option in API key prompt

### Wersja oryginalna (PL):
> Skopiuj klucz API z otwartej strony (lub utwórz nowy: 'Create API Key') i wklej poniżej:
> tu dodaj opcję klawiszową aby anulować.

### English version below
> Copy the API key from the opened page (or create a new one: 'Create API Key') and paste below:
> add a keyboard option to cancel here.

---

## Prompt 12: Detect and select from existing API keys in auth login

### Wersja oryginalna (PL):
> dodatkowo: przy auth login sprawdź czy są jakieś klucze i daj opcję wyboru ich

### English version below
> Additionally: during `auth login`, check if there are any existing keys and give an option to select them.

---

## Prompt 13: Name keys during login

### Wersja oryginalna (PL):
> a klucze niech mają nazwy z loginu

### English version below
> And let keys have names from login.

---

## Prompt 14: Edge case - bash syntax error with unquoted parentheses

### Wersja oryginalna (PL):
> edge case:
> how master  ❯ how to switch gh user (log to another account)
> bash: syntax error near unexpected token `('

### English version below
> edge case:
> how master  ❯ how to switch gh user (log to another account)
> bash: syntax error near unexpected token `('

---

## Prompt 15: Multi-token authentication management, emails, usage limits, and command edit field history

### Wersja oryginalna (PL):
> najpierw dodaj obsługę logowania/tokenów:
> 1. podczas logowania poproś o informację o mailu powiązanym z tokenem i zapisz przy tokenie.
> 2. dodaj flow zmiany aktywnego tokenu.
> 3. dodaj flow pobierania i wyświetlania % zużycia limitu dla każdego tokenu (aktywny zaznaczony *) wraz z mailem przypisanym.
> 4. dodaj ew. inne przydatne funkcje tu.
> 5. Najlepiej jeśli propozycja wykonywanej komendy była by w standardowym polu edycji, a nie w innynm, bo tak to nie będzie historii tych komend poponowanych. Jeśli nie da się łatwo to napisz, że za trundo.

### English version below
> First, add login / token management:
> 1. During login, ask for the email associated with the token and save it alongside the token.
> 2. Add a flow to switch the active token.
> 3. Add a flow to fetch and display the % limit usage for each token (active marked with *) along with the assigned email.
> 4. Add any other useful functions here.
> 5. It would be best if the proposed command appeared in the standard edit field rather than a different one, because otherwise there won't be a history of those proposed commands. If it can't be done easily, say that it's too difficult.

---

## Prompt 16: No child console or subshell; output suggestions directly to parent console

### Wersja oryginalna (PL):
> 1. w trakcie wyołania narzędzia how w onsoli-rodzicu podpowiedź jest sugerowana w konsoli-dziecku (która jest uruchomiona wewnątrz konsoli-rodzica). Jest to zachowanie niepożądane. podpowiedź ma być wypiasna w konsoli-rodzicu i żadna inna konsola nie jest potrzebna i how nie może niczego takiego sam uruchamiać!
> Zaproponuj implementacje która to uwzględnia.

### English version below
> 1. When running the `how` tool in the parent console, the suggestion is prompted inside a child console (which is launched inside the parent console). This is undesired behavior. The suggestion must be printed directly in the parent console, no other console is needed, and `how` must never execute anything like that on its own!
> Propose an implementation that takes this into account.

---

## Prompt 17: Align with Omarchy CLI tool standards

### Wersja oryginalna (PL):
> ok, to uwzględnij te wymagania (jak narzędzia cli) i dostosuj how do tych wymagań.

### English version below
> ok, so take these requirements into account (like cli tools) and adapt `how` to these requirements.

---

## Prompt 18: Verbosity modes: zero, low, normal

### Wersja oryginalna (PL):
> ok. Dodaj trybw verbosity, zero (tylko podpowiedź komendy) low (minimalny opis co to jest) normal (dotychczasowy poziom opisu)

### English version below
> ok. Add verbosity modes: zero (only command suggestion), low (minimal description of what it is), normal (current description level).

---

## Prompt 19: Remove interactive mode & maximally simplify auth

### Wersja oryginalna (PL):
> tryb interaktywny wydaje się niepotrzebny. Upraszczać na maksa!
> uprość opcje auth

### English version below
> Interactive mode seems unnecessary. Simplify to the maximum!
> Simplify auth options.

---

## Prompt 20: Safe uncertainty handling ("niewiem")

### Wersja oryginalna (PL):
> ważna uwaga: jeśli model nie jest pewien odpowiedzi, niech how zwraca odpowiedź niewiem.

### English version below
> Important note: if the model is not certain of the answer, make `how` return the answer "niewiem".

---

## Prompt 21: Local RAG (concept 1 from ideas.md)

### Wersja oryginalna (PL):
> zaimpelementuj pomysł 1 z ideas w koncepcji 1

### English version below
> implement idea 1 from ideas.md in concept 1 (local documentation context from tldr/man/--help).

---

## Prompt 22: Response caching with configurable retention

### Wersja oryginalna (PL):
> dodaj caching odpowiedzi (z domyślną retencją 3 godziny) i z możliwością ustawienia dowolnej retencji n minut godzin dni miesięcy

### English version below
> add response caching (with default retention of 3 hours) and with the ability to set any retention of n minutes hours days months

---

## Prompt 23: Standardized retention units (m, h, D, M) and [cache] response tag

### Wersja oryginalna (PL):
> niech retention będzie określane: m - minutes; h - hours; D - days; M - months.
> Dodatkowo: niech odpowiedź z cache będzie oznaczona [cache]

### English version below
> Let retention be specified as: m - minutes; h - hours; D - days; M - months.
> Additionally: let the response from cache be marked [cache].

---

## Prompt 24: Radically simplify help (Omarchy minimalist CLI style)

### Wersja oryginalna (PL):
> małe szybkie zadanko - uprość readme (radykalnie). Niech ma minimalistyczny styl (wg guidelines omarchy)
> tzn help.

### English version below
> Small quick task - radically simplify readme. Let it have a minimalist style (according to Omarchy guidelines).
> I mean help.

---

## Prompt 25: Remove init command

### Wersja oryginalna (PL):
> po co jest init?
> wywalić to!

### English version below
> What is init for?
> Remove it!

---

## Prompt 26: Complete English localization and Omarchy plugin release research

### Wersja oryginalna (PL):
> ok, teraz czyścimy. 
> 1. zmień wszystkie (widoczne dla użytkownika) rzeczy (help, nie wiem, etc) na angielskie. 
> 2. przygotowujemy się do opublikowania pluignu. zanim to zrobimy, zrób reaserch (albo zleć innemu agentowi) jak wyglądaja najpopularniejsze/najlepiej przyjęte opisy/readme/meta-dane pluginów Omarchy. Wyciągnij wnioski i zrób plan przygotowania release'a na bardzo dobrym poziomie (jednocześnie kierując sie minimalizmem).

### English version below
> OK, now we clean up.
> 1. Change all user-visible things (help, "I don't know", etc.) to English.
> 2. We are preparing to publish the plugin. Before we do, research (or delegate to another agent) what the most popular/well-received Omarchy plugin descriptions/READMEs/metadata look like. Draw conclusions and make a top-quality release preparation plan (while following minimalism).

---

## Prompt 27: Sliding cache expiration, GitHub Actions & parallel release preparation

### Wersja oryginalna (PL):
> zadania:
> 1. Zmiana zachowania polegająca na tym, że użyty cache odświeża się, to znaczy jego czas wygasania zaczyna się liczyć od nowa dla danej użytej komendy.
> 2. Dodaj do folderu .github zalecane przeze mnie akcje na GitHubie, między innymi takie jak skanowanie podatności, skanowanie nowszych wersji przy pomocy Renovate, skanowanie sekretów oraz takie skany jakości i bezpieczeństwa, które są zalecane przez Omarchy. Dodaj także ci do wersjonowania, tagowania i wydawania. Na razie nie triggeruj wydwania.
> 3. Wykonaj plan przygotowania minimalistycznego wydania, ten który napisałeś powyżej, w dwóch równoległych procesach. Jeden proces to struktura repozytorium, druga jednolity instalator.

### English version below
> Tasks:
> 1. Change behavior so that used cache is refreshed, meaning its expiration window starts anew for that used command upon hit.
> 2. Add recommended GitHub Actions to .github folder, including vulnerability scanning, dependency updates via Renovate, secret scanning, and quality/security scans recommended by Omarchy. Also add CI for versioning, tagging, and releases. Do not trigger release yet.
> 3. Execute the minimalist release preparation plan described above in two parallel processes: one process for repository structure, second for unified installer.








