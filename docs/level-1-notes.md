# Level 1 notes

## Library
- Chunks: 531 (230 clean pages, 300 words each, 50 word overlap)
- Time to build: 25s (`qwen3-embedding:0.6b` on the RTX 4060 laptop)
- Tests: 63 passing

## Before RAG vs after RAG
Question: In Sekiro, what is Dragonrot and how is it cured? Who is the Sculptor really?

**Before (qwen3.5:4b alone)**
- Thinking on, "what is dragonrot?": went in circles through Elder Scrolls, Elden Ring, Path of Exile, WoW, Cyberpunk, Monster Hunter... shouted "BINGO!" at wrong games, never mentioned Sekiro, never answered.
- Thinking off: confident and almost all wrong. A disease of "Mount Heian", caught by killing infected rats, cured with medicine bottles or by getting your "blood pressure below 10".
- Asked again: now a "Demon King" spreads it at the end of every chapter and it can't be cured. Different wrong answer every time.

**After**
- Playground (3 hand-picked Rot Essence chunks): correct cause (Wolf dying drains other people) and correct cure (Blood Sample to Emma, Dragon's Blood Droplet at a Sculptor's Idol), cited [1]-[3], but no exact quotes. "Who is Radahn?" got "My library doesn't cover that."
- Full RAG with `--debug`: top 5 were 2 Sculptor chunks, 2 Rot Essence chunks and Recovery Charm (similarity 0.73 to 0.63). The Dragonrot part was right, with real quotes. The Sculptor part was weak, it only said he has Dragonrot. Asked on its own, it gave the Orangutan backstory correctly.
- Every quote I checked by hand exists in the clean data.

## Questions I tried
| Question | Right chunks found? | Answer right? | Quoted properly? |
|---|---|---|---|
| Dragonrot + Sculptor (the before-RAG question) | Yes | Dragonrot yes, Sculptor partly | Yes, real quotes |
| Who is the Sculptor? (alone) | Yes (Sculptor > Description) | Yes | Cited, but paraphrased |
| Who is Emma? | Yes (Emma > Description) | Yes | Copied the chunk, including junk at the start |
| Does Emma die in a game ending? | No, Ending 1: Shura never showed up | No, garbled | Real quotes, mixed up |
| Is Emma killed by Wolf? | No | No, said she survives | Real quotes glued into a fake conclusion |
| Does Emma die by Wolf in the Shura ending? | No | No, said the opposite | No quotes |
| Who is Radahn? (not in Sekiro) | Nothing relevant (0.41-0.43, all bunched) | Yes, refused properly | - |
| Are there monkeys in Sekiro? | Yes (Folding Screen Monkeys, Illusory Hall Monk) | Yes | Cited, but paraphrased |

## What I noticed
1. RAG fixed the worst problem. Same 4B model, but answers went from made up (rats, Demon King) to real wiki facts with sources.
2. The model mostly ignores the "exact quote in every sentence" rule and paraphrases with [n] instead. When it does quote, the quotes are real, but real quotes can still be glued into a false conclusion (the Emma answers).
3. Search is the weak spot. The Emma answer is in the library: Ending 1: Shura says "Defeat Emma, the Gentle Blade and Isshin Ashina" and the Isshin Ashina page says Wolf kills Emma in the Shura Ending. Neither made the top 5 in 3 tries. The question says "die"/"killed" but the page says "Defeat", and one sentence gets drowned out inside a 300 word chunk about other stuff.
4. When the 5 chunks don't answer the question, the model guesses instead of saying "My library doesn't cover that." It only refused when the chunks were clearly unrelated (Radahn).
5. Two-part questions split the 5 slots between topics, so the second part gets a weak answer.
6. Similarity: the off-topic question topped out at 0.43 with no gap, good matches were 0.6-0.73. A cut-off around 0.5 might work, to be measured at Level 4.
7. Cleaner leftovers showed up in search results: boss strategy under "Part 1"/"Part 2" headings (Isshin Ashina (Shura), Isshin the Sword Saint) and a stray "Emma Isshin Ashina Wolf Kuro Genichiro" row at the start of Emma > Description.

## Questions for Level 2
- First golden question: "Does Emma die in the Shura ending?" Key facts: yes, Wolf fights and kills Emma, the Gentle Blade, then Isshin. Pages: Ending 1: Shura, Isshin Ashina.
- When the answer is on two pages, does finding either one count as a retrieval hit?
- Should two-part questions go in the golden set, or be split into two questions?
