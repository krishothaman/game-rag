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
