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
