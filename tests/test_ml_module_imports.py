def test_train_explain_imports():
    # make sure the file at least imports (this catches syntax errors)
    import backend.train_explain  # noqa: F401
