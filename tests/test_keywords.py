from game_rag.keywords import KeywordIndex, fuse, words


def test_words_lowercases_and_drops_punctuation_and_tiny_words():
    assert words("Who trained Wolf, as a kid?") == ["who", "trained", "wolf", "as", "kid"]


def test_rare_word_beats_a_word_every_doc_has():
    docs = [
        "sekiro wolf shinobi",
        "sekiro lady butterfly trained wolf",
        "sekiro sekiro sekiro sekiro",
    ]
    index = KeywordIndex(docs)
    assert index.top("sekiro butterfly", 3)[0] == 1


def test_docs_without_any_query_word_are_left_out():
    index = KeywordIndex(["emma doctor", "owl shinobi"])
    assert index.top("owl", 5) == [1]


def test_fuse_rewards_docs_both_lists_agree_on():
    meaning = ["a", "b", "c"]
    keywords = ["c", "d", "a"]
    assert fuse([meaning, keywords])[:2] == ["a", "c"]
