# Level 3: chunking and cleaning

Three changes, measured against the 15 dev questions after every one.

## Scores

| | before | after |
|---|---|---|
| retrieval (dev) | 9/11 | 10/11 |
| answers (dev) | 9/15 | 10/15 |
| retrieval (held-out) | not run | 7/8 |
| answers (held-out) | not run | 9/10 |

Chunks went from 531 to 597, median 300 words to 197.

## What changed

**1. Page title in front of every chunk.** Only the first chunk of a long page used to say what page it came from, so the later chunks of the ending pages looked like any Kuro or Emma text. Chunks are now embedded as `Page > Section\ntext`. The stored text is untouched, so only search sees it.

**2. Chunks follow sections.** A chunk used to start in Description and end halfway through Dialogue. Now whole sections get packed together up to 300 words, and only a section bigger than that gets split with overlap.

**3. Cleaner fixes.**
- Stray `<b>Name</b>` and `<a>Name</a>` tags between paragraphs are dropped. They were leaking page furniture like "Emma Isshin Ashina Wolf Kuro Genichiro" into the start of answers. 219 words in the whole corpus, all junk.
- Boss pages get a `Phases` line ("This boss fight has 2 phases: Phase 1, Phase 2."). The movesets are still dropped as strategy, but the phase count is lore.

## What it fixed
- #9 Shura bosses, #12 Return, #13 Gourd Seed and #14 Sculptor now answer correctly.
- #4 Guardian Ape answers "2 phases" instead of dodging.
- Both ending pages that search used to miss (#11, #12) now reach the top 5.

## What broke
- #2 "how many endings" was found before and is missed now: every chunk of the page called "Sekiro" starts with the word Sekiro, so those chunks win. Left alone on purpose, it's a counting question and simple RAG can't answer it.
- #14 broke after change 1 and came back after change 2.

## Still broken, and whose fault it is
- **Answerer (Level 4):** #1 says Emma doesn't die, #3 and #8 flip who did what to whom ("Emma saved the Sculptor", "Genichiro adopted a peasant boy"), #11 says Kuro doesn't die permanently.
- **Search (Level 5):** held-out #101 missed the Lady Butterfly page.
- **Nobody's fault yet:** #2 and #7 need counting across pages.

## Held-out set
`data/golden/holdout.jsonl`, 10 locked questions scored once at the end of the level and never tuned against. It scored 9/10 on answers, better than the dev set's 10/15, because the dev set is full of questions we picked *because* they fail.
