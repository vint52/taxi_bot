"""Client for the corporate taxi web cabinet."""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

import requests
from lxml import html
from lxml.html import HtmlElement

from models import ProfileInfo, Trip

logger = logging.getLogger(__name__)

BASE_URL = "http://65050.homeip.net"
CORP_PATH = "/corp/taxi/corp"
REQUEST_TIMEOUT = 10
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.9; rv:45.0) Gecko/20100101 Firefox/45.0"
TRIP_TIME_FORMAT = "%Y-%m-%d %H:%M"

LOGIN_FORM_XPATH = '//form[@id="taxi-client-form"]'
BALANCE_XPATH = '//div[@id="balance"]/div/p/strong/text()'
TRIP_ROWS_XPATH = '//table[@id="sortTable"]/tbody/tr'
LOGIN_ERROR_XPATH = '//div[@class="messages error"]//text()'


class TaxiError(Exception):
    """Base class for taxi cabinet failures."""


class TaxiAuthenticationError(TaxiError):
    """Credentials were rejected or the login form could not be submitted."""


class TaxiScraperError(TaxiError):
    """The cabinet page could not be fetched or parsed."""


def is_login_page(tree: HtmlElement) -> bool:
    """Return True when the page shows the login form instead of the cabinet."""
    return bool(tree.xpath(LOGIN_FORM_XPATH))


def parse_login_form(tree: HtmlElement) -> tuple[str, str]:
    """Extract the Drupal ``form_build_id`` and ``form_id`` from the login form."""
    forms = tree.xpath(LOGIN_FORM_XPATH)
    if not forms:
        raise TaxiAuthenticationError("Login form not found - page structure may have changed")
    form = forms[0]
    build_ids = form.xpath('.//input[@name="form_build_id"]/@value')
    form_ids = form.xpath('.//input[@name="form_id"]/@value')
    if not build_ids or not form_ids:
        raise TaxiAuthenticationError("Login form is missing its hidden identifiers")
    return build_ids[0], form_ids[0]


def parse_balance(tree: HtmlElement) -> int:
    """Read the account balance from the cabinet page."""
    values = tree.xpath(BALANCE_XPATH)
    if not values:
        raise TaxiScraperError("Balance element not found - page structure may have changed")
    try:
        return int(values[0])
    except ValueError as exc:
        raise TaxiScraperError(f"Unexpected balance value: {values[0]!r}") from exc


def parse_trips(tree: HtmlElement) -> list[Trip]:
    """Read the rides table. Rows that cannot be parsed are skipped with a warning."""
    trips: list[Trip] = []
    for row in tree.xpath(TRIP_ROWS_XPATH):
        try:
            trips.append(parse_trip_row(row))
        except (IndexError, ValueError) as exc:
            logger.warning("Skipping unparsable trip row: %s", exc)
    return trips


def parse_trip_row(row: HtmlElement) -> Trip:
    """Convert one ``<tr>`` of the rides table into a :class:`Trip`."""

    def cell(index: int, path: str = "text()") -> str:
        return row.xpath(f".//td[{index}]/{path}")[0]

    ride_time = datetime.strptime(cell(2), TRIP_TIME_FORMAT)
    return Trip(
        time=int(ride_time.timestamp()),
        phone=cell(3),
        name=cell(4),
        from_address=cell(5, "a/text()"),
        to_address=cell(6, "a/text()"),
        distance=float(cell(7)),
        waiting=float(cell(8)),
        price=int(cell(9)),
    )


class TaxiClient:
    """Fetches balance and rides from the cabinet, logging in on demand.

    All methods are blocking; call them from a worker thread in async code.
    """

    def __init__(
        self,
        username: str,
        password: str,
        debug_html_dir: str | Path,
        base_url: str = BASE_URL,
    ) -> None:
        self._username = username
        self._password = password
        self._debug_html_dir = Path(debug_html_dir)
        self._url = base_url + CORP_PATH
        self.session = requests.Session()
        self.session.headers["User-Agent"] = USER_AGENT

    def get_profile_info(self) -> ProfileInfo:
        """Return the current balance and rides, re-authenticating if the session expired."""
        try:
            tree, page = self._load_page()
            if is_login_page(tree):
                logger.info("Cabinet session is not active, logging in")
                self.login()
                tree, page = self._load_page()
                if is_login_page(tree):
                    self._save_debug_html(page, "session_expired")
                    raise TaxiScraperError("Login page returned right after authentication")

            try:
                balance = parse_balance(tree)
            except TaxiScraperError:
                self._save_debug_html(page, "balance")
                raise
            return ProfileInfo(balance=balance, trips=parse_trips(tree))
        except requests.RequestException as exc:
            raise TaxiScraperError(f"Request to taxi cabinet failed: {exc}") from exc

    def login(self) -> None:
        """Submit the login form with the stored credentials."""
        self.session.cookies.clear()
        tree, _ = self._load_page()
        form_build_id, form_id = parse_login_form(tree)

        response = self.session.post(
            self._url,
            data={
                "mail": self._username,
                "pass": self._password,
                "form_build_id": form_build_id,
                "form_id": form_id,
                "op": "Войти",
            },
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        tree = html.fromstring(response.text)

        errors = " ".join(text.strip() for text in tree.xpath(LOGIN_ERROR_XPATH)).strip()
        if errors:
            logger.error("Taxi cabinet rejected credentials: %s", errors)
            raise TaxiAuthenticationError("Invalid credentials")
        if is_login_page(tree):
            raise TaxiAuthenticationError("Still on the login page after submitting credentials")
        logger.info("Authenticated with taxi cabinet as %s", self._username)

    def _load_page(self) -> tuple[HtmlElement, str]:
        response = self.session.get(self._url, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        return html.fromstring(response.text), response.text

    def _save_debug_html(self, page: str, reason: str) -> None:
        """Dump the page to disk so parsing failures can be investigated later."""
        try:
            self._debug_html_dir.mkdir(parents=True, exist_ok=True)
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            path = self._debug_html_dir / f"parse_error_{reason}_{stamp}.html"
            path.write_text(page, encoding="utf-8")
            logger.error("Debug HTML saved to %s", path)
        except OSError as exc:
            logger.error("Failed to save debug HTML: %s", exc)
