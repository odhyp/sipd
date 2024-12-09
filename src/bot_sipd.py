"""
A module for automating interactions with SIPD-RI Kemendagri Website.
"""

import json
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from src.utils import get_month_name, get_current_date, PathHelper


class SIPDBot:
    """
    A bot for automating interactions with the SIPD-RI

    To-do List:
    # TODO: add refresh page method, using locator for reusability
    # TODO: add reload page method, using locator for reusability
    """

    _URL_LOGIN = "https://sipd.kemendagri.go.id/penatausahaan/login"
    _URL_PENATAUSAHAAN = "https://sipd.kemendagri.go.id/penatausahaan"
    _URL_PENATAUSAHAAN_REALISASI = (
        f"{_URL_PENATAUSAHAAN}/penatausahaan/pengeluaran/laporan/realisasi"
    )
    _URL_AKLAP = "https://sipd.kemendagri.go.id/penatausahaan/aklap"

    def __init__(self):
        self.browser = None
        self.context = None
        self.page = None

    def _initialize_browser(self):
        """
        Initializes the Playwright browser instance for automation.

        Attributes:
            self.browser (Browser): The Playwright browser instance.
            self.context (BrowserContext): The context for managing browser settings and cookies.
            self.page (Page): The active page within the browser context for navigation and interaction.

        Notes:
            - The browser is launched in non-headless mode (`headless=False`) to allow visual debugging.
            - The `--start-maximized` argument ensures the browser opens in maximized mode.
            - A universal viewport is disabled using `no_viewport=True`.
        """
        playwright = sync_playwright().start()
        self.browser = playwright.chromium.launch(
            headless=False, args=["--start-maximized"]
        )
        self.context = self.browser.new_context(no_viewport=True)
        self.page = self.context.new_page()

    def login_manual(self):
        """
        Log in to SIPD-RI manually.

        This method navigates to the login page and the user s
        """
        if not self.page:
            self._initialize_browser()

        self.page.goto(self._URL_LOGIN, timeout=120_000)
        self.page.bring_to_front()

        print("Please fill the login and CAPTCHA form")
        print("Only continue after successfully logged in!")
        input("\nPress Enter to continue...")

        menu_link = self.page.locator('a:has-text("Akuntansi")').first
        menu_link.wait_for(timeout=120_000)

    def login_with_env(self, username, password):
        """
        Log in to SIPD-RI using the provided credentials in the `.env` file

        This method navigates to the login page, enters the username and password,
        selects the appropriate account, and handles CAPTCHA verification. The user
        must manually complete the CAPTCHA before proceeding.

        Args:
            username (str): The username to log in with.
            password (str): The password for the specified username.

        Raises:
            PlaywrightTimeoutError: If any page elements fail to load within the timeout period.

        Notes:
            - The CAPTCHA must be completed manually. Automation pauses to allow the user to handle it.
            - A delay may be introduced for bad connections using a fail-safe.
        """
        if not self.page:
            self._initialize_browser()

        # TODO: add fail-safe for bad connection
        self.page.goto(self._URL_LOGIN, timeout=120_000)

        # Login Form
        input_username = self.page.locator("#ed_username")
        input_username.wait_for(state="visible")
        input_username.focus()
        input_username.type(username)
        input_password = self.page.locator("#ed_password")
        input_password.wait_for()
        input_password.type(password)
        input_password.press("Enter")

        # Account card
        card_account = self.page.locator(
            "div.account-select-card:has-text('Bendahara Umum Daerah')"
        )
        btn_account = card_account.locator("button:has-text('Pilih Akun ini')")
        card_account.wait_for()
        btn_account.click()

        # CAPTCHA form
        self.page.bring_to_front()
        input("Press Enter after successful login...")

        # Sidebar - Akuntansi
        menu_link = self.page.locator('a:has-text("Akuntansi")').first
        menu_link.wait_for(timeout=120_000)

    def login_with_cookies(self):
        """
        Log in to SIPD-RI using the previously saved session cookies. It will load
        cookie file named `cookie.json`.

        Raises:
            FileNotFoundError: If the `cookies.json` file does not exist.
            json.JSONDecodeError: If the `cookies.json` file contains invalid JSON.

        Notes:
            - The method assumes that the `cookies.json` file exists and contains valid cookies.
            - If the cookies are expired or invalid, the session will not be authenticated successfully.

        """
        if not self.page:
            self._initialize_browser()

        try:
            with open("cookies.json", "r", encoding="utf-8") as f:
                cookies = json.load(f)
                self.context.add_cookies(cookies)

            self.page.goto(self._URL_LOGIN)

        except FileNotFoundError:
            print("Error: cookies.json file not found. Please save cookies first.")
        except json.JSONDecodeError:
            print("Error: Invalid JSON format. Please re-save cookies!")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")

    def close_browser(self):
        """
        Safely closes the Playwright browser and its associated context.
        """
        if self.context:
            self.context.close()
        if self.browser:
            self.browser.close()

    def download_realisasi(self, start_month=1, end_month=1):
        """
        Downloads realisasi reports for specified months from the SIPD system.

        Args:
            start_month (int): The starting month (1-12).
            end_month (int): The ending month (1-12).

        Notes:
            - Handles potential errors during navigation, element interaction, and downloads.
            - Downloads reports for each month between `start_month` and `end_month`, inclusive.
            - Ensures robust handling of unexpected issues, such as timeouts or invalid months.

        Raises:
            Exception: If a critical error occurs during the process.

        To-do:
            - [ ] add output_path parameter
        """
        try:
            self.page.goto(self._URL_PENATAUSAHAAN_REALISASI)
            menu_title = self.page.locator('h1:has-text("Laporan Realisasi")')
            menu_title.wait_for()

            # Download form - SKPD
            submenu_skpd = self.page.locator("div.css-j93siq input").first
            submenu_skpd.wait_for()
            submenu_skpd.click()
            submenu_skpd.type("Unduh Semua SKPD")
            submenu_skpd.press("Enter")

            for i in range(start_month, end_month + 1):
                print(f"({i}/{end_month}) --- Downloading file...")

                try:
                    # Download form - Bulan
                    submenu_bulan = self.page.locator("div.css-j93siq input").nth(1)
                    submenu_bulan.wait_for(timeout=60_000)
                    submenu_bulan.click()
                    submenu_bulan.type(get_month_name(i))
                    submenu_bulan.press("Enter")

                    try:
                        with self.page.expect_download(
                            timeout=120_000
                        ) as download_info:
                            btn_download = self.page.locator(
                                'button:has-text("Download")'
                            )
                            btn_download.click()

                        current_date = get_current_date()
                        download_dir = f"Laporan Realisasi {current_date}"
                        download_name = f"2024-{i:02}-Laporan Realisasi.xlsx"
                        download_path = PathHelper.get_output_path(
                            output_dir=download_dir, file_name=download_name
                        )

                        download_file = download_info.value
                        download_file.save_as(download_path)

                        print(
                            f"({i}/{end_month}) --- Download success! File saved as {download_name}"
                        )

                    except PlaywrightTimeoutError as e:
                        print(f"({i}/{end_month}) --- Download failed: {e}")
                        print("Retrying...")
                        # TODO: Retry logic for failed downloads.

                except IndexError:  # Catching month values > 12
                    print(
                        f"({i}/{end_month}) --- Invalid month! There are only 12 months."
                    )

                except Exception as e:
                    print(f"({i}/{end_month}) --- Unexpected error: {e}")
                    print("Skipping to the next month.")

        except PlaywrightTimeoutError as e:
            print(f"Page load timed out: {e}")

        except Exception as e:
            print(f"Critical error occurred: {e}")
