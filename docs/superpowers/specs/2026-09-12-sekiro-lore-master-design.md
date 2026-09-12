# Sekiro Lore Master — Design Spec

**Date:** 2026-09-12
**Status:** Approved in brainstorming (revised for public use and open models), awaiting written-spec review
**Names:** the code and repository are called **`game_rag`**. "Sekiro Lore Master" is a placeholder; the public name is chosen before Level 8.
**Purpose:** A learning project. The owner is new to RAG (comfortable in Python) and wants to understand every part of a Retrieval-Augmented Generation system by building one, level by level, then publish it for anyone to use for free.

---

## 1. What we are building

A program that answers **lore questions about Sekiro: Shadows Die Twice** using only text from the Sekiro Fandom wiki, and shows which wiki pages each answer came from. Everything runs on **free, open models**.

> Example: *"Why does Owl turn on Wolf?"* → an answer built only from the retrieved wiki excerpts, with quoted evidence and `[Source: Owl → Background]`.

It is built on the owner's laptop and, at the final level, published two ways:
- **GitHub (download):** anyone can download it and run it on their own computer with Ollama.
- **Hugging Face Spaces (website):** anyone can open a link and ask questions in the browser, with no install, account, or key.

The project grows in **levels** (Section 6). Each level ends with a working program plus one new RAG skill. Later levels add Dark Souls, and eventually the rest of the FromSoftware series, using the same parts.

### Goals
- Understand the full RAG pipeline end to end: load → clean → chunk → embed → store → retrieve → augment → generate.
- Learn to **measure** RAG quality and to **diagnose** whether a failure came from search or from answer-writing.
- Publish a working, free, public Lore Master.

### Non-goals (for now)
- Gameplay help (boss strategies, walkthroughs, item farming routes).
- Training or fine-tuning any model.
- Serving many users at the same time (the free website answers one question at a time).

### 1.1 HARD RULE: zero cost, for everyone

**No part of this project may ever cost money, for the owner or for any user.** This rule overrides every other section.

- **Allowed:** free, open-source software; open models that can be downloaded and run for free; free public data; free hosting tiers that need **no credit card** (GitHub, the Hugging Face Spaces free CPU tier).
- **Forbidden:** paid AI services of any kind (including Claude, OpenAI, Voyage AI, Cohere, Groq, and paid rerankers), paid hosting or hardware upgrades, paid plan add-ons, and adding a credit card to any account used by this project.
- **No keys for users:** nobody needs an account, subscription, or API key to use the Lore Master, on the website or the downloaded version.
- **No paid code paths:** the program contains no integration with any paid or key-requiring AI service.
- If a future idea would cost money, it is dropped rather than added.

---

## 2. Decisions and why

| Decision | Choice | Why |
|---|---|---|
| Topic | Lore of the FromSoftware games, starting with **Sekiro** | Owner knows the games deeply and can spot wrong answers; lore is scattered across many small texts, which is what RAG is good at. Sekiro is the smallest, most linear, and standalone. |
| Growth path | One game first, then add games one at a time | Keeps experiments fast and failures easy to diagnose. Each added game becomes a lesson. |
| Question type | Lore first | Narrative text suits RAG; strategy pages are list- and table-heavy. |
| Data source | **Sekiro Fandom wiki** (Creative Commons BY-SA: reuse with credit, share alike) | Legally reusable and shareable. **Fextralife is excluded:** its terms forbid scraping and automated downloading. |
| Answer-writing model | **A small open model (about 1–4 billion parameters)** run through **Ollama** on the owner's laptop | Free, no keys, and small enough to run on the free website's CPUs. The same model is used locally and on the website. |
| Model selection | Candidates from the Qwen, Gemma, and Llama families; the winner is chosen by golden-set score (Section 5) | Measured, not guessed. Prefer the simplest license for public use (for example Apache 2.0); each candidate's license is checked at Level 1. |
| Embeddings | **Local open-source embedding model** | Free, offline; runs on laptop and website CPUs. |
| Vector database | **ChromaDB**, stored as a local folder | The usual beginner choice; no server to run; the folder ships with the website. |
| Interface | Terminal first (Levels 0–7), then a web page (Level 8) | The terminal hides nothing while learning. |
| Publishing | **Both**: GitHub repository + free Hugging Face Space (Level 8) | Downloaders get speed and privacy; casual users just open a link. |
| Spoiler-free mode | Added at **Level 6** | Taught as the metadata-filtering lesson once the core works. |
| Language | Python | Owner is comfortable in Python. |

### Owner's development machine
Intel i7-12650H, 16 GB RAM, NVIDIA RTX 4060 Laptop GPU (8 GB), about 34 GB free disk. The GPU makes local testing fast. Each model takes 2–5 GB of disk, so downloaded models should be limited to the few being compared.

### Rejected ideas (kept for the record)
- **Claude via Claude Pro and the Agent SDK:** a Pro login can't be used to serve other people, and a paid API key breaks the hard rule.
- **Free cloud AI services (for example, Groq's free tier):** about 6,000 tokens per minute shared by all users, roughly 2 questions per minute for everyone combined, and the provider can change the free tier at any time.
- **Spotify-based project:** Spotify's developer terms forbid feeding Spotify content into AI models, and its API is heavily restricted as of February 2026. The personal data export route was dropped because it includes IP addresses and device data.
- **Rulebook Referee:** the owner doesn't play those games, so they couldn't catch wrong answers.

---

## 3. Architecture

### 3.1 The seven parts

Each part has one job and talks to the others only through its inputs and outputs, so any part can be replaced without touching the rest.

| # | Part | Input | Output | Job |
|---|---|---|---|---|
| 1 | **Collector** | List of wiki pages to fetch | Raw page files on disk, plus each page's URL | Download pages slowly and politely; resume after interruption without duplicating pages. |
| 2 | **Cleaner** | Raw page files | Clean text with headings kept | Strip menus, edit links, formatting codes, image captions, and navigation boxes. |
| 3 | **Chunker** | Clean pages | Chunks, each with labels (Section 4.3) | Cut pages into searchable pieces. |
| 4 | **Embedder** | Chunk text, or a question | A vector (list of numbers) | Place text on the "meaning map". The same model is used for chunks and questions. |
| 5 | **Library** | Chunks + vectors + labels | The top 5 closest chunks for a query | Store everything locally in ChromaDB and answer "nearest 5" searches. |
| 6 | **Answerer** | Question + retrieved chunks | Answer text + list of sources | Build the prompt, send it to the local open model, and return the cited answer. |
| 7 | **Interface** | What the user types | Answer, sources, and (in debug mode) the retrieved chunks | Terminal chat for Levels 0–7; web page from Level 8. Debug mode shows every retrieved chunk and its similarity score. |

```
BUILD THE LIBRARY (once, on the laptop):  Collector → Cleaner → Chunker → Embedder → Library
ASK A QUESTION (each):                   Interface → Embedder → Library (top 5) → Answerer → Interface
```

The Library is built once on the owner's laptop and shipped as files with both the GitHub repository and the website, so neither the website nor downloaders need to rebuild it.

### 3.2 The closed-book fence (Answerer rules)

The Answerer must:

1. **Use a model with no tools**: it only reads the prompt and writes text. Open models run through Ollama have no web or file access.
2. **Use a fixed system prompt** stating: answer only from the provided wiki excerpts, cite a source for each fact, and if the excerpts don't contain the answer, reply exactly *"My library doesn't cover that."*
3. **Allow one reply only**, with no multi-step agent behavior.
4. **Quote its evidence:** every sentence of an answer must include an exact quote from a retrieved chunk, tagged with that chunk's number (Layer 2 in Section 3.3).
5. **Be the only part that knows which model is used.** Swapping to a different open model changes no other part.

### 3.3 Anti-memory layers

A model may "know" some Sekiro lore from its training. Small open models know far less than large ones, but answers from memory instead of the library must still be **blocked or detected**. All layers are free.

| Layer | What it does | Where it runs | Level |
|---|---|---|---|
| **1. No evidence, no question** | If no chunk passes the relevance cut-off, the model is never called (Section 4.5). | Everywhere | 4 |
| **2. Quote-first answers** | The model must back every sentence with an exact quote from a numbered chunk. | Everywhere | 1 |
| **3. Quote checker** | Plain code (no AI) confirms each quote appears word for word in the chunk it cites. Any sentence without a matching quote rejects the whole answer, and the user sees *"The answer couldn't be verified against the library."* | Everywhere | 4 |
| **4. Fact-checker pass** | A second model request checks that every claim is supported by the excerpts. Free now that models run locally, but it doubles answer time. | **Test runs on the laptop only**; off on the website | 4 |
| **5. Planted-fact test** | Tests run against a test copy of the library with deliberately changed facts (Section 5.5). An answer matching the changed fact proves it came from the library; an answer matching the real game proves it came from memory. | Test runs on the laptop only | 4 |

Small models follow instructions less reliably than large ones, so Layer 3 may reject more answers. Measuring and reducing that rejection rate is part of Level 4.

---

## 4. Data and chunking

### 4.1 What goes in
- **In:** character pages, lore and story pages, the four endings, key item descriptions (prosthetic tools, memories, key items), and location pages' lore sections.
- **Out for now:** boss strategy guides, walkthroughs, patch notes, and trivia or speculation sections.

### 4.2 How we get it
- **Level 0, step 1:** check whether the Sekiro Fandom wiki offers an official database download. If it does, use it. If not, fetch pages through the wiki's public page-access interface, **no faster than one request per second**, saving each raw page so nothing is downloaded twice.
- **Level 0, step 2:** count pages and words, and write the numbers down. All size decisions come from these measurements, not guesses.

### 4.3 Chunk labels (metadata)
Every chunk carries: `game` (always "Sekiro" until Level 7), `page_title`, `section`, `url`, and `page_type` (character / item / location / lore / ending). `story_progress` is added at Level 6.

### 4.4 Chunking rules
- **Level 1 (the deliberately naive baseline):** fixed-size chunks of about 300 words with about 50 words of overlap, ignoring headings.
- **Level 3 (improved):** split at the wiki's own section headings first; cap chunks at about 400 words; keep about 15% overlap between neighbors; start every chunk with a **context header** (`Page: Isshin Ashina → History`); **one item description = one chunk**.
- The Level 3 rules are adopted only if they score better than Level 1 on the golden set.

### 4.5 Retrieval settings
- Return the **top 5** chunks per question (tunable, and compared on the golden set). Small models may do better with fewer chunks; this is tested at Level 4.
- **Relevance cut-off:** if even the best chunk is too far from the question, reply *"I couldn't find anything about that"* **without calling the model**. The cut-off value is set at Level 4 using the canary tests.

### 4.6 Credit and license (public release)
- The wiki text is licensed **CC BY-SA**. The published Library files carry the same license, with credit to the Sekiro Fandom wiki and its contributors.
- Every answer's citations link to the source wiki page.
- The README and the website show a notice: *"Unofficial fan project. Not affiliated with FromSoftware or Activision. Wiki content from the Sekiro Fandom wiki, CC BY-SA."*
- The project's own code is released under the MIT license.

---

## 5. Testing

Every test runs on the owner's laptop and costs nothing, so tests can be re-run as often as wanted.

### 5.1 Golden set
A file of test questions written by the owner. Each row has: the question, the key facts of the correct answer, and the wiki page(s) that contain it. It starts at **30 questions at Level 2** and grows to **50** by Level 5.

### 5.2 Two separate scores
- **Retrieval score:** the percentage of golden questions where the correct page appears among the 5 retrieved chunks. This tests the Chunker, Embedder, and Library.
- **Answer score:** each answer is graded on three things: *correct* (yes / partly / no), *faithful* (uses only the retrieved text: yes / no), and *cited* (yes / no). This tests the Answerer. The owner grades by hand at first; the Layer 4 fact-checker can assist in test runs.

**Diagnosis rule:** correct chunk missing → fix search or chunking. Correct chunk present but the answer is wrong → fix the Answerer (prompt, chunk count, or model).

### 5.3 Canary tests (added at Level 4)
At least **8 questions deliberately not in the library**, for example *"Who is Ranni?"* (Elden Ring). The only passing answer is *"My library doesn't cover that."* Any canary failure means the fence leaks, and it must be fixed before trusting any other score.

### 5.4 Scorecard
Every level that changes retrieval, answering, or the model is re-scored, and the scores are recorded side by side, so improvements are proven rather than assumed.

### 5.5 Planted-fact tests (added at Level 4)
At least **3 tests**. Each uses a test copy of the library in which one fact is deliberately changed. For example, *"Owl is Wolf's foster father"* becomes *"Hanbei is Wolf's foster father"*, and the question is *"Who is Wolf's foster father?"*
- The answer uses the planted fact ("Hanbei") → it came from the library → **pass**.
- The answer uses the real fact ("Owl") → it came from the model's memory → **fail**: the fence leaks and must be fixed.

The test copy is kept separate and is never shipped or used for normal questions.

---

## 6. Levels (the learning roadmap)

A level is one stage of the same growing project. Each one ends with something that runs, a lesson learned, and (from Level 2 on) a score.

| Level | Build | Lesson | Done when |
|---|---|---|---|
| **0. Get the data** | Collector, Cleaner; measure the data | Real data is messy; look before you build | Clean Sekiro lore pages are on disk and their size is recorded |
| **1. Naive RAG** | Install Ollama and one small open model; naive chunker, local embeddings, ChromaDB, fenced Answerer with quote-first answers, terminal chat with debug mode | The whole pipeline end to end | *"What is Dragonrot?"* returns an answer with quoted evidence, and debug mode shows the 5 chunks |
| **2. Golden set and scorecard** | 30 golden questions; retrieval and answer scores | How RAG quality is measured | Level 1's two scores are recorded |
| **3. Better chunking** | Section-based chunks, context headers, overlap, one chunk per item | Why chunking matters, with proof | Re-scored and compared with Level 1 |
| **4. Grounding and model choice** | Quote checker, relevance cut-off, 8+ canary tests, planted-fact tests, fact-checker for test runs; compare 2–3 small open models, plus one larger model on the laptop's GPU as a reference | Fighting hallucination; choosing a model by measurement | All canaries and planted-fact tests pass; the website model is chosen by score |
| **5. Hybrid search and reranking** | Keyword search alongside meaning search; a reranking step using a **free, local** reranking model | How production systems search | Re-scored on the grown 50-question set; the reranker is kept only if it is worth its extra time on CPU |
| **6. Spoiler-free mode** | `story_progress` labels; filter by *"I've beaten up to …"* | Metadata filtering | Spoiler-mode questions return no chunks beyond the stated progress |
| **7. Second game** | Add Dark Souls (DS1 first) with `game` labels; ask *"Which game?"* when unclear | Multi-source libraries, name collisions (e.g. Patches) | Mixed-game golden questions pass without cross-game mix-ups |
| **8. Go public** | Web page; public GitHub repository with setup instructions for Ollama; free Hugging Face Space (CPU tier) running the same model and Library; credit, license, and fan-project notice; public safeguards (Section 7.2) | Publishing a real AI app for free | The website answers a question when opened in a private browser window with no login; a fresh download from GitHub runs by following the README alone |

After Level 8, each remaining game (Demon's Souls, DS2, DS3, Elden Ring) is added as a small extension of Level 7 and republished.

Hugging Face's free GPU sharing ("ZeroGPU") may speed up the website. It is checked at Level 8 and used only if it is available on a free account with no card.

---

## 7. When things go wrong

### 7.1 Failure handling

| Situation | Behavior |
|---|---|
| No chunk passes the relevance cut-off (from Level 4, when the cut-off is set) | *"I couldn't find anything about that."* The model is not called. |
| Answer fails the quote check (from Level 4) | Answer rejected with *"The answer couldn't be verified against the library."* Debug mode shows which sentence failed. |
| Ollama isn't running, or the model isn't downloaded (download version) | A clear message saying what to start or download, and how. |
| Wiki download interrupted | Next run resumes where it stopped; already-saved pages are skipped. |
| Wiki page fails to download | Logged and skipped; the run continues; failures are listed at the end. |
| Question matches several topics | Answer with all sources shown. |

### 7.2 Public safeguards (website)

| Situation | Behavior |
|---|---|
| Several visitors at once | Questions wait in a queue and are answered one at a time; the visitor sees their place in line. |
| Very long or junk input | Questions longer than 300 characters are refused with a short message. |
| Attempts to override the rules (e.g. *"ignore your instructions"*) | The fence and quote checker still apply; an answer without valid quotes is rejected. |
| Website asleep after 48 hours without visitors | Hugging Face shows a waking-up screen; the first answer is delayed while it starts. |
| Visitor privacy | Questions and answers are not stored or logged. |

---

## 8. Glossary (quick reference)

- **LLM:** a large language model that writes text.
- **Open model:** a model whose files can be downloaded and run for free on your own computer (e.g. Qwen, Gemma, Llama).
- **Ollama:** a free program that downloads and runs open models on a computer.
- **Hugging Face Spaces:** a free hosting service for AI demo websites.
- **Parameters (e.g. "4B"):** a rough measure of model size, in billions. Bigger is usually smarter but slower.
- **RAG:** Retrieval-Augmented Generation: find relevant text first, then have the LLM answer from it (an open-book exam).
- **Chunk:** a small piece of a document, the unit the library searches.
- **Embedding / vector:** a list of numbers that places text on a "meaning map"; similar meanings sit close together.
- **Vector database:** storage that quickly finds the chunks closest to a question.
- **Top-k:** how many chunks are retrieved per question (here, 5).
- **Context window:** how much text an LLM can read at once.
- **Metadata:** labels attached to a chunk (game, page, section) used for filtering and citations.
- **Overlap:** a shared sliver of text between neighboring chunks, so nothing falls into the gap.
- **Context header:** the page and section name placed at the start of a chunk so it makes sense on its own.
- **Grounding / faithfulness:** how strictly an answer sticks to the retrieved text.
- **Golden set:** test questions with known correct answers.
- **Canary test:** a question deliberately not in the library; the correct response is "not covered".
- **Planted-fact test:** a test library with one fact deliberately changed, to prove whether an answer came from the library or from the model's memory.
- **Quote checker:** plain code that confirms every quote in an answer really appears in the chunk it cites.
- **Hybrid search:** combining keyword search and meaning search.
- **Reranking:** a second, pickier step that re-orders retrieved chunks.
- **Hallucination:** an LLM confidently stating something false.
- **CC BY-SA:** a Creative Commons license: reuse is allowed with credit, and shared copies must use the same license.
