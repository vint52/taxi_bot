"""Taxi service client for scraping trip data."""
from datetime import datetime
import logging
import os
from typing import Any, Dict, List, Optional

import requests
from lxml import html


logger = logging.getLogger(__name__)

# Default directory for saving debug HTML dumps
DEFAULT_DEBUG_HTML_DIR = '/tmp/taxi_debug'


class TaxiAuthenticationError(Exception):
    """Raised when authentication fails."""
    pass


class TaxiScraperError(Exception):
    """Raised when scraping fails."""
    pass


class Taxi:
    """Client for interacting with the taxi service."""
    
    BASE_URL = "http://65050.homeip.net"
    CORP_PATH = "/corp/taxi/corp"
    
    def __init__(self, login: str, password: str, debug_html_dir: Optional[str] = None):
        """
        Initialize the taxi client.
        
        Args:
            login: Username for authentication
            password: Password for authentication
            debug_html_dir: Directory for saving HTML dumps on parse errors
        """
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.9; rv:45.0) '
                         'Gecko/20100101 Firefox/45.0'
        })
        self.debug_html_dir = debug_html_dir or DEFAULT_DEBUG_HTML_DIR
        
        # Store credentials for re-authentication
        self._login_credentials = (login, password)
        
        self._login(login, password)
    
    def get_profile_info(self, _retry: bool = True) -> Dict[str, Any]:
        """
        Get profile information including balance and trips.
        
        Args:
            _retry: Internal flag to prevent infinite retry loops
        
        Returns:
            Dictionary with 'balance' and 'trips' keys
            
        Raises:
            TaxiScraperError: If scraping fails
        """
        try:
            logger.debug(f"Requesting profile info from {self._make_url(self.CORP_PATH)}")
            response = self.session.get(self._make_url(self.CORP_PATH), timeout=10)
            response.raise_for_status()
            logger.debug(f"Received response with status {response.status_code}, content length: {len(response.text)}")
            
            tree = html.fromstring(response.text)
            
            # Check if session expired (redirected to login page) - CHECK FIRST!
            if self._is_login_page(tree):
                if _retry:
                    logger.warning("Session expired detected, re-authenticating...")
                    try:
                        self._reauth()
                        logger.info("Re-authentication successful, retrying...")
                        return self.get_profile_info(_retry=False)
                    except Exception as e:
                        logger.error(f"Re-authentication failed: {e}")
                        self._save_debug_html(response.text, "reauth_failed")
                        raise TaxiScraperError(f"Session expired and re-authentication failed: {e}")
                else:
                    logger.error("Session expired and re-authentication already attempted")
                    self._save_debug_html(response.text, "session_expired")
                    raise TaxiScraperError("Session expired and re-authentication failed")
            
            # Parse balance
            try:
                balance = self._parse_balance(tree, page_html=response.text)
                logger.debug(f"Parsed balance: {balance}")
            except TaxiScraperError as e:
                # If balance parsing fails, check if it's because we're on login page
                if self._is_login_page(tree):
                    if _retry:
                        logger.warning("Balance parsing failed - detected login page, re-authenticating...")
                        try:
                            self._reauth()
                            return self.get_profile_info(_retry=False)
                        except Exception as reauth_error:
                            logger.error(f"Re-authentication failed: {reauth_error}")
                            raise TaxiScraperError(f"Session expired: {e}")
                    else:
                        raise TaxiScraperError(f"Session expired: {e}")
                else:
                    logger.error(f"Failed to parse balance: {e}")
                    raise
            
            # Parse trips
            try:
                trips = self._parse_trips(tree)
                logger.debug(f"Parsed {len(trips)} trips")
            except TaxiScraperError as e:
                logger.error(f"Failed to parse trips: {e}")
                # If trips parsing fails, continue with empty trips list
                trips = []
            
            return {
                "balance": balance,
                "trips": trips
            }
            
        except TaxiScraperError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error getting profile info: {e}", exc_info=True)
            raise TaxiScraperError(f"Failed to get profile info: {e}") from e
    
    def _is_login_page(self, tree) -> bool:
        """Check if the current page is the login page (session expired)."""
        # Check for login form
        login_form = tree.xpath('//form[@id="taxi-client-form"]')
        if len(login_form) > 0:
            return True
        
        # Check page title for login page indicators
        page_title = tree.xpath('//title/text()')
        if page_title:
            title_text = ' '.join(page_title).lower()
            if 'вход' in title_text or 'login' in title_text:
                logger.warning(f"Login page detected by title: {page_title}")
                return True
        
        # Check if balance element is missing (indicates not logged in)
        balance_div = tree.xpath('//div[@id="balance"]')
        if not balance_div:
            # Additional check: if we're missing balance AND have login form, definitely login page
            login_form = tree.xpath('//form[@id="taxi-client-form"]')
            if len(login_form) > 0:
                return True
        
        return False
    
    def _reauth(self) -> None:
        """Re-authenticate using stored credentials."""
        logger.warning("=== RE-AUTHENTICATION STARTED ===")
        login, password = self._login_credentials
        
        # Clear existing session cookies to start fresh
        logger.debug("Clearing existing session cookies...")
        self.session.cookies.clear()
        
        try:
            logger.debug(f"Attempting login with username: {login}")
            self._login(login, password)
            logger.info("=== RE-AUTHENTICATION SUCCESSFUL ===")
        except TaxiAuthenticationError as e:
            logger.error(f"=== RE-AUTHENTICATION FAILED: Authentication error ===")
            logger.error(f"Error: {e}")
            raise
        except Exception as e:
            logger.error(f"=== RE-AUTHENTICATION FAILED: Unexpected error ===")
            logger.error(f"Error: {e}", exc_info=True)
            raise TaxiAuthenticationError(f"Re-authentication failed: {e}") from e
    
    def _parse_balance(self, tree, page_html: Optional[str] = None) -> int:
        """Parse balance from HTML tree."""
        try:
            balance_elements = tree.xpath('//div[@id="balance"]/div/p/strong/text()')
            if not balance_elements:
                self._log_parsing_failure(tree, page_html, "balance")
                raise TaxiScraperError(
                    "Balance element not found on page - page structure may have changed. "
                    "Check logs for debug HTML dump path."
                )
            
            balance_str = balance_elements[0]
            return int(balance_str)
        except TaxiScraperError:
            raise
        except (IndexError, ValueError) as e:
            logger.error(f"Failed to parse balance value: {e}")
            raise TaxiScraperError(f"Failed to parse balance: {e}") from e
    
    def _log_parsing_failure(
        self, tree, page_html: Optional[str], element_name: str
    ) -> None:
        """Log detailed debugging info when parsing fails."""
        logger.error(f"=== PARSING FAILURE: {element_name} ===")
        
        # Check for common page elements to understand page state
        page_title = tree.xpath('//title/text()')
        logger.error(f"Page title: {page_title}")
        
        # Check if we're on login page (not authenticated)
        login_form = tree.xpath('//form[@id="taxi-client-form"]')
        if login_form:
            logger.error("DETECTED: Login form present - session may have expired!")
        
        # Check for error messages on page
        error_messages = tree.xpath('//div[contains(@class, "error")]//text()')
        if error_messages:
            logger.error(f"Error messages on page: {error_messages}")
        
        # Log balance div structure specifically
        balance_div = tree.xpath('//div[@id="balance"]')
        if balance_div:
            balance_html = html.tostring(balance_div[0], encoding='unicode')
            logger.error(f"Balance div HTML: {balance_html[:500]}")
        else:
            logger.error("Balance div (#balance) NOT FOUND on page")
            # Try to find any div that might contain balance
            all_divs_with_balance = tree.xpath('//*[contains(text(), "баланс") or contains(text(), "Баланс")]')
            if all_divs_with_balance:
                logger.error(f"Found {len(all_divs_with_balance)} elements containing 'баланс'")
        
        # Log body structure overview
        body = tree.xpath('//body')
        if body:
            body_classes = body[0].get('class', 'no-class')
            body_id = body[0].get('id', 'no-id')
            logger.error(f"Body attributes: class='{body_classes}', id='{body_id}'")
        
        # Save full HTML to file for debugging
        if page_html:
            self._save_debug_html(page_html, element_name)
    
    def _save_debug_html(self, page_html: str, element_name: str) -> None:
        """Save HTML content to file for debugging."""
        try:
            os.makedirs(self.debug_html_dir, exist_ok=True)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{self.debug_html_dir}/parse_error_{element_name}_{timestamp}.html"
            
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(page_html)
            
            logger.error(f"Debug HTML saved to: {filename}")
        except Exception as e:
            logger.error(f"Failed to save debug HTML: {e}")
    
    def _parse_trips(self, tree) -> List[Dict]:
        """Parse trips from HTML tree."""
        try:
            table_rows = tree.xpath('//table[@id="sortTable"]/tbody/tr')
            trips = []
            
            for row in table_rows:
                try:
                    trip = self._parse_trip_row(row)
                    trips.append(trip)
                except Exception as e:
                    logger.warning(f"Failed to parse trip row: {e}")
                    continue
            
            return trips
            
        except Exception as e:
            raise TaxiScraperError(f"Failed to parse trips: {e}") from e
    
    def _parse_trip_row(self, row) -> Dict[str, Any]:
        """Parse a single trip row."""
        time_str = row.xpath(".//td[2]/text()")[0]
        timestamp = int(datetime.timestamp(
            datetime.strptime(time_str, '%Y-%m-%d %H:%M')
        ))
        
        return {
            "time": timestamp,
            "phone": row.xpath(".//td[3]/text()")[0],
            "name": row.xpath(".//td[4]/text()")[0],
            "from": row.xpath(".//td[5]/a/text()")[0],
            "to": row.xpath(".//td[6]/a/text()")[0],
            "distance": float(row.xpath(".//td[7]/text()")[0]),
            "waiting": float(row.xpath(".//td[8]/text()")[0]),
            "price": int(row.xpath(".//td[9]/text()")[0])
        }
    
    def _login(self, login: str, password: str) -> None:
        """
        Authenticate with the taxi service.
        
        Args:
            login: Username
            password: Password
            
        Raises:
            TaxiAuthenticationError: If authentication fails
        """
        try:
            logger.debug(f"Starting authentication process for user: {login}")
            
            # Get the login form
            logger.debug(f"Fetching login page from {self._make_url(self.CORP_PATH)}")
            response = self.session.get(self._make_url(self.CORP_PATH), timeout=10)
            response.raise_for_status()
            logger.debug(f"Login page response status: {response.status_code}")
            
            if response.cookies:
                self.session.cookies.update(response.cookies)
                logger.debug(f"Updated session cookies: {len(response.cookies)} cookies")
            
            # Parse form data
            tree = html.fromstring(response.text)
            form = tree.xpath('//form[@id="taxi-client-form"]')
            
            if not form:
                logger.error("Login form not found on page")
                raise TaxiAuthenticationError("Login form not found - page structure may have changed")
            
            form = form[0]
            form_build_id = form.xpath('.//input[@name="form_build_id"]/@value')
            form_id = form.xpath('.//input[@name="form_id"]/@value')
            
            if not form_build_id or not form_id:
                logger.error("Form IDs not found")
                raise TaxiAuthenticationError("Form IDs not found - page structure may have changed")
            
            form_build_id = form_build_id[0]
            form_id = form_id[0]
            logger.debug(f"Found form IDs: form_id={form_id}, form_build_id={form_build_id[:20]}...")
            
            # Submit login form
            logger.debug("Submitting login form...")
            response = self.session.post(
                self._make_url(self.CORP_PATH),
                data={
                    "mail": login,
                    "pass": password,
                    "form_build_id": form_build_id,
                    "form_id": form_id,
                    "op": "Войти"
                },
                timeout=10,
            )
            response.raise_for_status()
            logger.debug(f"Login POST response status: {response.status_code}")
            
            # Check for error messages
            tree = html.fromstring(response.text)
            error_message = tree.xpath('//div[@class="messages error"]')
            if error_message:
                error_text = ' '.join(error_message[0].xpath('.//text()'))
                logger.error(f"Authentication error message: {error_text}")
                raise TaxiAuthenticationError("Invalid credentials")
            
            # Verify we're logged in by checking for balance element
            balance_div = tree.xpath('//div[@id="balance"]')
            if not balance_div:
                logger.warning("Balance element not found after login - may not be authenticated")
                # Check if we're still on login page
                login_form = tree.xpath('//form[@id="taxi-client-form"]')
                if login_form:
                    logger.error("Still on login page after authentication attempt")
                    raise TaxiAuthenticationError("Authentication failed - still on login page")
            
            logger.info("Successfully authenticated with taxi service")
            
        except TaxiAuthenticationError:
            raise
        except Exception as e:
            logger.error(f"Login error: {e}", exc_info=True)
            raise TaxiAuthenticationError(f"Authentication failed: {e}") from e
    
    def _make_url(self, path: str) -> str:
        """Create full URL from path."""
        return self.BASE_URL + path
