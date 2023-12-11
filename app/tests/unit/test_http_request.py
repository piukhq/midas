from app.http_request import urljoin


def test_url_join():
    url_joined = urljoin("https://my.sample.com", "no_slash_path")
    assert url_joined == "https://my.sample.com/no_slash_path"
