from game_rag.cleaner import CleanPage, Section, clean_html, clean_page

# copied the layout of the real "Rot Essence" page, cut down a lot
ITEM_HTML = """
<div class="mw-content-ltr mw-parser-output">
<table class="article-table mw-collapsible"><tbody>
<tr><th colspan="4"><a href="/wiki/Items">Items</a></th></tr>
<tr><td><figure><img alt="Memory"/></figure><center><a href="/wiki/Memories">Memories</a></center></td></tr>
</tbody></table>
<h2><span class="mw-headline" id="In-Game_Description">In-Game Description</span><span class="mw-editsection"><span class="mw-editsection-bracket">[</span><a>Sign in to edit</a><span class="mw-editsection-bracket">]</span></span></h2>
<p>The more one with the power of the Dragon's Heritage dies,<br>the more the sickness spreads.</p>
<h2><span class="mw-headline" id="Overview">Overview</span></h2>
<p><b>Dragonrot</b> is the name of the illness that has gripped <a href="/wiki/Ashina">Ashina</a>.</p>
<ul><li>It spreads after <a href="/wiki/Wolf">Wolf</a> dies.</li><li>It does <b>NOT</b> kill any NPC.</li></ul>
<table class="article-table mw-collapsible mw-collapsed"><tbody>
<tr><th>Event</th><th>Dialogue</th></tr>
<tr><td>Talking after first resurrection</td><td><u><b>Emma</b></u>: Hmm... Notice anything different?<br><u><b>Wolf</b></u>: ... Yes.</td></tr>
</tbody></table>
<h2><span class="mw-headline" id="Trivia">Trivia</span></h2>
<p>A trivia fact that should be dropped.</p>
<h3><span class="mw-headline" id="More">More trivia</span></h3>
<p>Also dropped.</p>
<h2><span class="mw-headline" id="Notes">Notes</span></h2>
<p>A note that should be kept.</p>
</div>
"""

# same idea but based on the "Owl" page, plus the newer heading style and a tab box
CHARACTER_HTML = """
<div class="mw-parser-output">
<table><tr><td><b>Owl</b></td><td>•</td><td><a>Owl (Father)</a></td></tr></table>
<div class="fluid hidden"><figure><img alt="Spacer"/></figure></div>
<p>Owl is a great shinobi.</p>
<div class="mw-heading mw-heading2"><h2 id="Description">Description</h2></div>
<aside class="portable-infobox"><h2 class="pi-title">Owl</h2><div>Voice actor: someone</div></aside>
<p>He raised Wolf.</p>
<div class="wikia-gallery"><div class="wikia-gallery-caption">Owl artwork</div></div>
<div class="tabber wds-tabber"><div class="wds-tabs__wrapper"><ul><li>Tab label</li></ul></div>
<div class="wds-tab__content"><p>Inside the tab.</p></div></div>
</div>
"""


def sections_by_heading(html):
    return {s.heading: s for s in clean_html(html)}


def test_keeps_only_real_sections_in_order():
    assert [s.heading for s in clean_html(ITEM_HTML)] == ["In-Game Description", "Overview", "Notes"]


def test_line_breaks_become_new_lines():
    text = sections_by_heading(ITEM_HTML)["In-Game Description"].text
    assert text == "The more one with the power of the Dragon's Heritage dies,\nthe more the sickness spreads."


def test_links_and_bold_become_plain_text():
    text = sections_by_heading(ITEM_HTML)["Overview"].text
    assert "Dragonrot is the name of the illness that has gripped Ashina." in text


def test_lists_become_dash_lines():
    text = sections_by_heading(ITEM_HTML)["Overview"].text
    assert "- It spreads after Wolf dies.\n- It does NOT kill any NPC." in text


def test_tables_become_rows():
    text = sections_by_heading(ITEM_HTML)["Overview"].text
    assert "Event | Dialogue" in text
    assert "Talking after first resurrection | Emma: Hmm... Notice anything different?\nWolf: ... Yes." in text


def test_dropped_sections_and_their_subsections_are_skipped():
    all_text = "\n".join(s.text for s in clean_html(ITEM_HTML))
    assert "trivia" not in all_text.lower()
    assert "Also dropped." not in all_text
    assert sections_by_heading(ITEM_HTML)["Notes"].text == "A note that should be kept."


def test_intro_paragraph_kept_and_navigation_dropped():
    first = clean_html(CHARACTER_HTML)[0]
    assert first == Section(heading="Introduction", level=1, text="Owl is a great shinobi.")


def test_new_style_heading_wrapper_is_recognised():
    second = clean_html(CHARACTER_HTML)[1]
    assert (second.heading, second.level) == ("Description", 2)


def test_infobox_gallery_and_tab_labels_are_removed():
    text = clean_html(CHARACTER_HTML)[1].text
    assert text == "He raised Wolf.\nInside the tab."


def test_strategy_sections_are_dropped():
    html = "<h2>Strategy</h2><p>Dodge left.</p><h2>Lore</h2><p>An old tale.</p>"
    assert clean_html(html) == [Section(heading="Lore", level=2, text="An old tale.")]


def test_clean_page_keeps_title_url_and_categories():
    raw = {
        "requested_title": "Dragonrot",
        "title": "Rot Essence",
        "url": "https://sekiro-shadows-die-twice.fandom.com/wiki/Rot_Essence",
        "html": "<h2>Overview</h2><p>Dragonrot spreads.</p>",
        "categories": ["Key Items"],
    }
    assert clean_page(raw) == CleanPage(
        title="Rot Essence",
        url="https://sekiro-shadows-die-twice.fandom.com/wiki/Rot_Essence",
        categories=["Key Items"],
        sections=[Section(heading="Overview", level=2, text="Dragonrot spreads.")],
    )


# the real ending pages have no headings at all, just a menu and one big table
def test_page_without_headings_keeps_its_content_table():
    html = """
    <table><tr><th colspan="2"><a>Items</a></th></tr><tr><td><a>Memories</a></td><td><a>Prayer Bead</a></td></tr></table>
    <table class="article-table mw-collapsible">
    <tr><td colspan="2">Ending 1: Shura</td></tr>
    <tr><td>Requirements</td><td>Side with Owl and turn against Kuro.</td></tr>
    <tr><td>Story</td><td>Wolf abandons his lord and becomes a demon of carnage.</td></tr>
    </table>
    """
    assert clean_html(html) == [Section(
        heading="Ending 1: Shura",
        level=2,
        text="Requirements | Side with Owl and turn against Kuro.\n"
             "Story | Wolf abandons his lord and becomes a demon of carnage.",
    )]


# emma's dialogue page is one giant tab box before any heading
def test_tab_box_before_first_heading_is_kept():
    html = """
    <div class="tabber wds-tabber"><div class="wds-tabs__wrapper"><ul><li>Dilapidated Temple</li></ul></div>
    <div class="wds-tab__content"><table><tr><th>Event</th><th>Dialogue</th></tr>
    <tr><td>Talking</td><td>Emma: Hello.</td></tr></table></div></div>
    """
    assert clean_html(html) == [Section(heading="Introduction", level=1, text="Event | Dialogue\nTalking | Emma: Hello.")]


# boss pages: strategy gets dropped but the dialogue table after it is lore, keep it
def test_table_title_row_starts_its_own_section():
    html = """
    <h2>Behaviour and Tactics</h2><p>Dodge left.</p>
    <table><tr><th colspan="2">Loot</th></tr><tr><td>Memory: Great Shinobi</td><td>1</td></tr></table>
    <table><tr><th colspan="2">Dialogue</th></tr><tr><td>Approaching</td><td>Wolf: Father...</td></tr></table>
    """
    assert clean_html(html) == [Section(heading="Dialogue", level=2, text="Approaching | Wolf: Father...")]


def test_link_heavy_menu_after_headings_is_dropped():
    links = " • ".join(f"<a>{name}</a>" for name in ["Ako", "Ashina", "Centipedes", "Divine Realm", "Dragon", "Kuro", "Owl", "Wolf"])
    html = f"<h2>Overview</h2><p>Real text.</p><table><tr><td>Lore Contents</td></tr><tr><td>{links}</td></tr></table>"
    assert clean_html(html) == [Section(heading="Overview", level=2, text="Real text.")]


def test_long_one_cell_row_is_a_quote_not_a_title():
    html = "<h2>Lore</h2><table><tr><td>Where you find the departed, you'll find the Memorial Mob.</td></tr></table>"
    assert clean_html(html) == [Section(heading="Lore", level=2, text="Where you find the departed, you'll find the Memorial Mob.")]


# ending pages have a table inside a table, the inner rows were showing up twice
def test_nested_table_rows_are_not_read_twice():
    html = """
    <h2>Ending</h2>
    <table>
    <tr><td>Overview</td><td><table><tr><td>Wolf becomes Shura.</td></tr></table></td></tr>
    </table>
    """
    assert clean_html(html) == [Section(heading="Ending", level=2, text="Overview | Wolf becomes Shura.")]


def test_named_cut_dialogue_sections_are_dropped_too():
    html = "<h2>Notes</h2><p>Kept.</p><h2>Emma's Cut Dialogue</h2><p>Never used in the game.</p>"
    assert clean_html(html) == [Section(heading="Notes", level=2, text="Kept.")]


# the wiki names boss strategy sections a million ways, so match on words inside the heading
def test_strategy_headings_are_dropped_whatever_they_are_called():
    html = """
    <h2>Behaviors and Tactics</h2><p>a</p>
    <h2>Moveset</h2><p>b</p>
    <h2>Phase 1 &amp; 2</h2><p>c</p>
    <h2>Suggested Equipment</h2><p>d</p>
    <h2>Preparation</h2><p>e</p>
    <h2>Stealth Route (Hirata Estate)</h2><p>f</p>
    <h2>Fight</h2><p>g</p>
    <h2>Lore</h2><p>Trained in the forest of mist.</p>
    """
    assert clean_html(html) == [Section(heading="Lore", level=2, text="Trained in the forest of mist.")]


def test_stray_gallery_label_is_dropped():
    html = "<h2>Notes</h2><p>Kept.</p><div>Gallery</div><p>A caption.</p>"
    assert clean_html(html) == [Section(heading="Notes", level=2, text="Kept.")]


STRAY_HTML = """
<div class="mw-parser-output">
<h2><span class="mw-headline" id="Description">Description</span></h2>
<b>Emma</b>
<a href="/wiki/Isshin">Isshin Ashina</a>
<p>Emma is a doctor who served Isshin.</p>
</div>
"""

BOSS_HTML = """
<div class="mw-parser-output">
<h2><span class="mw-headline" id="Introduction">Introduction</span></h2>
<p>The Guardian Ape guards the Lotus of the Palace.</p>
<h2><span class="mw-headline" id="Phase_1">Phase 1</span></h2>
<p>Dodge the sweep.</p>
<h2><span class="mw-headline" id="Phase_2">Phase 2</span></h2>
<p>It picks up its head.</p>
</div>
"""


def test_stray_link_and_bold_names_are_dropped():
    assert sections_by_heading(STRAY_HTML)["Description"].text == "Emma is a doctor who served Isshin."


def test_boss_phases_are_counted_even_though_the_moves_are_dropped():
    sections = sections_by_heading(BOSS_HTML)
    assert "Phase 1" not in sections
    assert sections["Phases"].text == "This boss fight has 2 phases: Phase 1, Phase 2."
