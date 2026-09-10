from datetime import datetime

import pytest
import requests
from lxml import html

from taxi import (
    TaxiAuthenticationError,
    TaxiClient,
    TaxiScraperError,
    is_login_page,
    parse_balance,
    parse_login_form,
    parse_trips,
)

LOGIN_PAGE = """
<html><head><title>Вход</title></head><body>
<form id="taxi-client-form" method="post">
  <input name="mail"><input name="pass">
  <input type="hidden" name="form_build_id" value="form-abc">
  <input type="hidden" name="form_id" value="taxi_client_form">
</form></body></html>
"""

CABINET_PAGE = """
<html><head><title>Кабинет</title></head><body>
<div id="balance"><div><p>Баланс: <strong>1234</strong></p></div></div>
<table id="sortTable"><thead><tr><th>#</th></tr></thead><tbody>
<tr><td>1</td><td>2024-03-01 10:30</td><td>+79990000001</td><td>Иван</td>
    <td><a href="#">ул. Ленина, 1</a></td><td><a href="#">пр. Мира, 5</a></td>
    <td>12.5</td><td>3.0</td><td>350</td></tr>
<tr><td>2</td><td>2024-03-02 18:05</td><td>+79990000002</td><td>Мария</td>
    <td><a href="#">ул. Садовая, 7</a></td><td><a href="#">пл. Победы, 1</a></td>
    <td>4</td><td>0</td><td>200</td></tr>
<tr><td>3</td><td>broken</td><td></td><td></td><td></td><td></td><td></td><td></td><td></td></tr>
</tbody></table></body></html>
"""

LOGIN_FAILED_PAGE = """
<html><body><div class="messages error">Неверный пароль</div>
<form id="taxi-client-form"></form></body></html>
"""


def test_is_login_page():
    assert is_login_page(html.fromstring(LOGIN_PAGE))
    assert not is_login_page(html.fromstring(CABINET_PAGE))


def test_parse_login_form():
    assert parse_login_form(html.fromstring(LOGIN_PAGE)) == ("form-abc", "taxi_client_form")
    with pytest.raises(TaxiAuthenticationError):
        parse_login_form(html.fromstring(CABINET_PAGE))


def test_parse_balance():
    assert parse_balance(html.fromstring(CABINET_PAGE)) == 1234
    with pytest.raises(TaxiScraperError):
        parse_balance(html.fromstring(LOGIN_PAGE))


def test_parse_trips_skips_broken_rows():
    trips = parse_trips(html.fromstring(CABINET_PAGE))
    assert len(trips) == 2
    first = trips[0]
    assert first.time == int(datetime(2024, 3, 1, 10, 30).timestamp())
    assert first.phone == "+79990000001"
    assert first.name == "Иван"
    assert first.from_address == "ул. Ленина, 1"
    assert first.to_address == "пр. Мира, 5"
    assert first.distance == 12.5
    assert first.waiting == 3.0
    assert first.price == 350
    assert trips[1].price == 200


class FakeResponse:
    def __init__(self, text: str, status: int = 200):
        self.text = text
        self.status_code = status

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"status {self.status_code}")


class FakeSession:
    """Serves pages from a script: each GET pops the next page, POSTs are recorded."""

    def __init__(self, pages: list[str], post_page: str = CABINET_PAGE):
        self.pages = list(pages)
        self.post_page = post_page
        self.posts: list[dict] = []
        self.headers: dict = {}
        self.cookies = requests.cookies.RequestsCookieJar()

    def get(self, url, timeout):
        return FakeResponse(self.pages.pop(0))

    def post(self, url, data, timeout):
        self.posts.append(data)
        return FakeResponse(self.post_page)


@pytest.fixture
def client(tmp_path):
    return TaxiClient("user", "pass", tmp_path / "debug")


def test_profile_info_when_logged_in(client):
    client.session = FakeSession([CABINET_PAGE])
    info = client.get_profile_info()
    assert info.balance == 1234
    assert len(info.trips) == 2
    assert client.session.posts == []


def test_profile_info_logs_in_on_login_page(client):
    client.session = FakeSession([LOGIN_PAGE, LOGIN_PAGE, CABINET_PAGE])
    info = client.get_profile_info()
    assert info.balance == 1234
    (post,) = client.session.posts
    assert post["mail"] == "user"
    assert post["pass"] == "pass"
    assert post["form_build_id"] == "form-abc"
    assert post["form_id"] == "taxi_client_form"


def test_login_rejected(client):
    client.session = FakeSession([LOGIN_PAGE, LOGIN_PAGE], post_page=LOGIN_FAILED_PAGE)
    with pytest.raises(TaxiAuthenticationError, match="Invalid credentials"):
        client.get_profile_info()


def test_balance_missing_saves_debug_dump(client, tmp_path):
    client.session = FakeSession(["<html><body>nothing here</body></html>"])
    with pytest.raises(TaxiScraperError):
        client.get_profile_info()
    dumps = list((tmp_path / "debug").glob("parse_error_balance_*.html"))
    assert len(dumps) == 1


def test_http_error_becomes_scraper_error(client):
    class FailingSession(FakeSession):
        def get(self, url, timeout):
            raise requests.ConnectionError("boom")

    client.session = FailingSession([])
    with pytest.raises(TaxiScraperError, match="boom"):
        client.get_profile_info()
