def test_package_imports():
    import services.api

    assert services.api.__version__
