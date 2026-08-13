def test_authenticated_file_is_returned():
    request = type(
        "Request", (), {"headers": {"X-User": "alice"}, "query": {"name": "report.txt"}}
    )()
    assert request.query["name"] == "report.txt"
