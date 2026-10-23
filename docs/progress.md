# Progress so far

A running log of what changed and what it did to the scores. The per-level details are in `level-0-notes.md`, `level-1-notes.md` and `level-3-notes.md`.

## Scoreboard

Dev set = the golden questions we tune against (15 at first, 25 since Level 5). Held-out = 10 locked questions we only check at the end of a step.

| Step | Retrieval (dev) | Answers (dev) | Answers (held-out) |
|---|---|---|---|
| Level 1, first working RAG | 9/11 | 9/15 | not built yet |
| Level 3, chunking + cleaning | 10/11 | 10/15 | 9/10 |
| Level 4.1, stricter prompt | 10/11 | 11/15 | 8/10 |
| Level 5.1, hybrid search (still 4B) | 11/11 | 12/15 | 7/10 |
| Level 4.2, 9B model + hybrid search | 11/11 | 13/15 | 9/10 |
| Level 4.2 again, dev grown to 25 | 19/19 | 22/25 | 9/10 |
| **Level 5.2, + reranker** | **18/19** | **23/25** | **8/10** |

An answer only counts if it's right **and** has no false claim in it. "Right fact plus one made-up extra" is a fail.

## Level 0: the data
- Pulled 319 Sekiro pages from the Fandom wiki API (CC BY-SA, about one request a second).
- Cleaner turns the HTML into text sections and throws away strategy, trivia, loot and cut content.
- 88 redirects and 1 empty page skipped, 230 clean pages left.

## Level 1: the first working RAG
- Chunk the pages, embed them with `qwen3-embedding:0.6b`, store them in ChromaDB, take the top 5 for a question, and have `qwen3.5:4b` answer only from those, quoting and citing `[n]`.
- Commands: `index`, `ask`, `chat`.
- It worked, but the Emma/Shura question showed it can glue real quotes into a false answer.

## Level 2: measuring it
- **Golden set** (`data/golden/sekiro.jsonl`): 15 questions with the facts and the pages that hold the answer. 4 of them are traps the wiki can't answer, so the right reply is a refusal.
- **`score`** checks whether a right page reached the top 5. **`score --answers`** also answers each one and asks you y/n.
- **Verdict memory**: y/n calls are saved per exact answer text, so a rerun only asks about answers that changed.
- **Held-out set** (`data/golden/holdout.jsonl`, `score --holdout`): 10 locked questions, written the way a player would ask, so we can tell real improvement from tuning to the test.

## Level 3: chunking and cleaning
- Every chunk is embedded with `Page > Section` in front. This fixed the ending pages, which search couldn't find before.
- Chunks follow section boundaries instead of cutting every 300 words. 531 chunks became 597, median 197 words.
- Cleaner drops stray `<b>Name</b>` / `<a>Name</a>` tags. They were leaking "Emma Isshin Ashina Wolf Kuro Genichiro" into answers.
- Boss pages keep a one-line phase count, so "how many phases" is answerable.

## Level 4: the answerer
**4.1 Stricter prompt.** Three new rules: keep who-did-what-to-whom exactly as the excerpt has it, never say something didn't happen unless an excerpt says so, add nothing the excerpts don't state. Fixed Genichiro and Return, but #1, #3 and #11 still flip who did what, and a held-out answer got worse. Prompt rules can't fully fix a small model.

**Canary tests** (`playground/canary.py`): we plant made-up facts ("Emma's favourite food is roasted chestnuts") and questions with no answer. The 4B model passed 5/5, and it even repeated a deliberately false fact ("Owl fought Kuro"). So it does trust the excerpts over its own memory. The mistakes come from reading long excerpts that name lots of characters, not from ignoring the wiki.

**4.2 Bigger model.** Swapped `qwen3.5:4b` for `qwen3.5:9b` (6.6 GB download, free). It fits fully on an 8 GB GPU, also passes 5/5 canaries, and scored 13/15 on dev and 9/10 on held-out, the best so far on both. It's about twice as slow (64s vs 34s for 15 answers) but reads crowded excerpts much better: it finally says Emma *does* die in the Shura ending. It's now the default, and `--model qwen3.5:4b` still works for smaller GPUs.

Still wrong with 9B: #11 claims Kuro "does not die in the traditional sense", and held-out #104 stitches Owl's defeat line onto the wrong scene.

## Level 5: smarter search
**5.1 Hybrid search.** Search now runs two ways and merges them:
- **Meaning** (the embeddings we had): good at "who trained Wolf as a kid?" even when the wiki says it in other words.
- **Keywords (BM25)**: a scored index lookup. Words found on every page (like "Sekiro") count for almost nothing, rare ones (like "Butterfly") count a lot. Written in `src/game_rag/keywords.py`, about 40 lines, no new library.
- **Reciprocal rank fusion** merges the two lists using only the positions, so the two kinds of score never need comparing.

Dev retrieval went 10/11 → 11/11 ("how many endings" found an ending page again), and on #9 and #12 the ending page jumped to first place. Held-out retrieval stayed 7/8. With the 4B model, answers went +1 on dev and -1 on held-out, because the extra loosely-related chunks tempted it into adding false extras. With 9B that problem mostly went away.

Held-out #101 (Lady Butterfly) still misses. A word stemmer would probably fix it ("trained" vs "training"), but we spotted that by looking at a held-out question, so we're not allowed to tune for it. Fixes have to come from dev failures.

**Growing the dev set.** Added 10 more dev questions (25 in total, 19 with an answer in the wiki). The 9B model scored 22/25 on it before any Level 5.2 change.

**5.2 Reranker.** Search now picks 20 candidates and a small **cross-encoder** reads each one *together with* the question and gives it a score. We keep the 5 best.
- Model: `cross-encoder/ms-marco-MiniLM-L6-v2`, 91 MB, free, runs on the CPU through `onnxruntime` (`src/game_rag/reranker.py`, about 30 lines). It downloads once from Hugging Face, then loads from disk with no account or token.
- Why not rerank all 597 chunks? Search vectors are made ahead of time, but the reranker has to read question and chunk together, so it can only start once you ask. 20 chunks take ~0.4s; 597 would take ~15s.
- Retrieval: dev 19/19 → 18/19 (lost #2 "how many endings", the counting question), held-out 7/8 → **8/8** (Lady Butterfly #101 found without tuning for it).
- Answers: dev 22/25 → **23/25**. #1 (Emma in Shura) and #11 (Kuro in Immortal Severance) are fixed: the ending pages moved to the top, so the model stopped inventing how the scenes play out. #6 got worse (now implies one prayer bead is enough instead of four).
- Held-out answers 9/10 → 8/10. #104 no longer invents a scene but gives a garbled reason. #107 (Dragonrot) quotes the wiki correctly but was marked n because we doubt the wiki's "four deaths" claim.
- Cost: about 0.4s more per question on the CPU, small next to the answer itself. Kept.

## Things learned along the way
- **Found ≠ right.** A right page in the top 5 doesn't mean the right chunk, and the right chunk doesn't mean a right answer.
- **Every fix breaks something.** Chunk headers fixed the endings and broke the Sculptor question. Section chunking fixed the Sculptor and broke "how many endings". Only the score catches this.
- **Counting questions** ("how many endings / bosses") don't work in simple RAG, because the answer is spread over many pages. Left alone on purpose.
- **Your laptop is fine.** GPU peaked at 100% at 60°C on the 4B, 73°C on the 9B (throttling starts around 85°C). Crashes were RAM, from a 22 GB model once and from After Effects and Unreal another time.
- **Bigger model beat more prompt rules.** Three extra prompt rules got +1; the 9B model got +1 on dev and +2 on held-out on top of that.
- **Same pages, better order, better answer.** The reranker barely changed *which* pages were found, but putting the most on-topic chunk first fixed two answers. Small models lean hardest on the first excerpt.
- **Search first, then answer.** Doing all the searches before all the answers stops the GPU swapping models, and took 10 answers from minutes to 21 seconds.

## Still broken and where it gets fixed
| Problem | Questions | Fix |
|---|---|---|
| Model garbles who did what | held-out #104 | open |
| Answer drops a key detail (4 beads) | #6 | open |
| Counting across pages | #2, #7 | later, maybe never in plain RAG |
