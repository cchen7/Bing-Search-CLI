from bing_search_cli.storage import append_history, load_history


def test_append_and_load_history(tmp_path, monkeypatch):
    monkeypatch.setenv("BSC_CONFIG_DIR", str(tmp_path))
    append_history({"timestamp": "t1", "query": "q1", "answer": "a1"})
    append_history({"timestamp": "t2", "query": "q2", "answer": "a2"})

    entries = load_history(limit=10)
    assert len(entries) == 2
    assert entries[0]["query"] == "q1"
    assert entries[1]["query"] == "q2"
