# Level 0 notes

## Numbers (from data/stats.json)
- Pages: 230 (plus 88 redirects merged into other pages, and 1 empty page: Shoukichi)
- Sections: 870
- Total words: 104,501
- Average / median words per page: 454 / 160
- Largest page: Emma (5,984 words)

## Where the data came from
- 319 unique page titles from 12 wiki categories, downloaded through the public API at about 1 page a second. 0 failures.
- Categories: Lore, Characters, Bosses, Mini-Bosses, Endings, Key Items, Prosthetic Tools, Memories, Locations, Chapters, Dialogue, Dialogues.
- Special:Statistics (where a database download would be) is behind a bot check, so no database dump. API only.

## What changed from the plan
- **Added the Bosses and Mini-Bosses categories (43 pages).** Big lore characters like Lady Butterfly, Guardian Ape, Corrupted Monk, Divine Dragon and Isshin the Sword Saint only live there.
- **Menus are now spotted by how much of a block is links (50% or more)**, anywhere on the page. The first version kept only paragraphs before the first heading, and that deleted all 4 endings and the big dialogue pages.
- **Table title rows ("Dialogue", "Loot", ending names) count as headings.** This keeps boss dialogue even when the strategy section above it gets dropped.
- **Tables inside tables are read once.** Before, the inner rows showed up twice (36 pages affected).
- **More sections dropped:** availability, loot, wares, trophy, cut content, cut dialogue, fight, new game plus. Also any heading containing tactic, moveset, equipment, phase, preparation, stealth route or strateg, because the wiki names boss strategy sections a lot of different ways.

## What I noticed when reading pages
1. Redirects are how the wiki bundles things. 88 titles (castle sub-areas, item variants like the ten Prayer Necklaces) all point to just 19 pages.
2. Most pages are short and a few are huge. The median is 160 words but Emma is almost 6,000, so chunking has to handle both.
3. Dialogue pages are walls of `Event | Speaker: line` rows. The tab labels that say *where* a conversation happens (like "Dilapidated Temple") get deleted as junk, so dialogue loses that context.
4. 28 pages still have lines that repeat, but they repeat on the wiki too (NPCs saying the same thing in different conversations). Not a cleaner bug.
5. 32 boss pages start with a section called "Introduction", which on its own says nothing. The page title needs to go along with every chunk (Level 3 context headers).

## Questions for Level 1
- What chunk size works when the median page is 160 words but some pages are about 6,000?
- Should tab labels (where a conversation happens) become headings instead of being deleted?
- Are "Location" sections (where an NPC stands during a questline) lore or gameplay?
- Which small open model to try first?
