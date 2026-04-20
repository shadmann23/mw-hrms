"""
tests/test_ui_selenium.py — Browser UI Tests
Requires: pip install selenium
Run with server running: python manage.py runserver
Then: pytest tests/test_ui_selenium.py -v
"""
import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys

BASE_URL = 'http://127.0.0.1:8000'

# ─────────────────────────────────────────────
#  BROWSER FIXTURE
# ─────────────────────────────────────────────

@pytest.fixture(scope='module')
def browser():
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1280,900')
    driver = webdriver.Chrome(options=options)
    driver.implicitly_wait(8)
    yield driver
    driver.quit()


def wait_for(browser, by, value, timeout=8):
    return WebDriverWait(browser, timeout).until(
        EC.presence_of_element_located((by, value))
    )


# ═══════════════════════════════════════════════
#  LOGIN PAGE TESTS
# ═══════════════════════════════════════════════

class TestLoginPageUI:

    def test_login_page_title(self, browser):
        browser.get(f'{BASE_URL}/accounts/login/')
        assert 'MilkWays' in browser.title or 'Sign In' in browser.page_source

    def test_login_logo_visible(self, browser):
        browser.get(f'{BASE_URL}/accounts/login/')
        logo = browser.find_elements(By.CSS_SELECTOR, '.auth-logo img')
        assert len(logo) > 0
        assert logo[0].is_displayed()

    def test_login_form_fields_visible(self, browser):
        browser.get(f'{BASE_URL}/accounts/login/')
        username = browser.find_element(By.ID, 'admin')
        password = browser.find_element(By.ID, 'admin123')
        assert username.is_displayed()
        assert password.is_displayed()

    def test_login_submit_button_visible(self, browser):
        browser.get(f'{BASE_URL}/accounts/login/')
        btn = browser.find_element(By.CSS_SELECTOR, 'button[type=submit]')
        assert btn.is_displayed()
        assert 'Sign In' in btn.text

    def test_create_account_link_visible(self, browser):
        browser.get(f'{BASE_URL}/accounts/login/')
        link = browser.find_element(By.PARTIAL_LINK_TEXT, 'Create')
        assert link.is_displayed()

    def test_wrong_credentials_shows_error(self, browser):
        browser.get(f'{BASE_URL}/accounts/login/')
        browser.find_element(By.ID, 'id_username').send_keys('wronguser')
        browser.find_element(By.ID, 'id_password').send_keys('wrongpass')
        browser.find_element(By.CSS_SELECTOR, 'button[type=submit]').click()
        # Should stay on login page and show error
        assert '/login/' in browser.current_url or 'Invalid' in browser.page_source or 'auth-err' in browser.page_source

    def test_successful_login_redirects(self, browser):
        """Requires a real user in DB — update credentials below"""
        browser.get(f'{BASE_URL}/accounts/login/')
        browser.find_element(By.ID, 'id_username').clear()
        browser.find_element(By.ID, 'id_username').send_keys('admin')  # change to your admin username
        browser.find_element(By.ID, 'id_password').clear()
        browser.find_element(By.ID, 'id_password').send_keys('Admin@12345')  # change to your password
        browser.find_element(By.CSS_SELECTOR, 'button[type=submit]').click()
        WebDriverWait(browser, 8).until(lambda d: '/login/' not in d.current_url)
        assert '/login/' not in browser.current_url


# ═══════════════════════════════════════════════
#  REGISTER PAGE TESTS
# ═══════════════════════════════════════════════

class TestRegisterPageUI:

    def test_register_page_loads(self, browser):
        browser.get(f'{BASE_URL}/accounts/register/')
        assert 'Create' in browser.page_source or 'Register' in browser.page_source

    def test_register_logo_visible(self, browser):
        browser.get(f'{BASE_URL}/accounts/register/')
        logo = browser.find_elements(By.CSS_SELECTOR, '.auth-logo img')
        assert len(logo) > 0
        assert logo[0].is_displayed()

    def test_register_form_fields_visible(self, browser):
        browser.get(f'{BASE_URL}/accounts/register/')
        fields = ['id_first_name', 'id_last_name', 'id_username', 'id_email']
        for field_id in fields:
            element = browser.find_element(By.ID, field_id)
            assert element.is_displayed(), f'{field_id} not visible'

    def test_register_password_fields_visible(self, browser):
        browser.get(f'{BASE_URL}/accounts/register/')
        p1 = browser.find_element(By.ID, 'id_password1')
        p2 = browser.find_element(By.ID, 'id_password2')
        assert p1.is_displayed()
        assert p2.is_displayed()

    def test_register_left_panel_visible(self, browser):
        browser.get(f'{BASE_URL}/accounts/register/')
        left_panel = browser.find_elements(By.CSS_SELECTOR, '.auth-left')
        assert len(left_panel) > 0

    def test_register_submit_button_text(self, browser):
        browser.get(f'{BASE_URL}/accounts/register/')
        btn = browser.find_element(By.CSS_SELECTOR, 'button[type=submit]')
        assert 'Create' in btn.text or 'Register' in btn.text

    def test_register_sign_in_link(self, browser):
        browser.get(f'{BASE_URL}/accounts/register/')
        link = browser.find_element(By.PARTIAL_LINK_TEXT, 'Sign In')
        assert link.is_displayed()
        assert '/login/' in link.get_attribute('href')

    def test_register_empty_form_shows_errors(self, browser):
        browser.get(f'{BASE_URL}/accounts/register/')
        browser.find_element(By.CSS_SELECTOR, 'button[type=submit]').click()
        # Should stay on register page
        assert '/register/' in browser.current_url


# ═══════════════════════════════════════════════
#  SIDEBAR / DASHBOARD TESTS (after login)
# ═══════════════════════════════════════════════

class TestDashboardUI:
    """These tests require a logged-in session. Run test_successful_login first."""

    def login(self, browser):
        browser.get(f'{BASE_URL}/accounts/login/')
        browser.find_element(By.ID, 'id_username').clear()
        browser.find_element(By.ID, 'id_username').send_keys('admin')  # change to your username
        browser.find_element(By.ID, 'id_password').clear()
        browser.find_element(By.ID, 'id_password').send_keys('Admin@12345')  # change to your password
        browser.find_element(By.CSS_SELECTOR, 'button[type=submit]').click()
        WebDriverWait(browser, 8).until(lambda d: '/login/' not in d.current_url)

    def test_sidebar_logo_visible(self, browser):
        self.login(browser)
        logo = browser.find_elements(By.CSS_SELECTOR, '.sidebar-brand img')
        assert len(logo) > 0
        assert logo[0].is_displayed()

    def test_sidebar_nav_links_visible(self, browser):
        self.login(browser)
        nav_links = browser.find_elements(By.CSS_SELECTOR, '.nav-link')
        assert len(nav_links) > 0

    def test_dashboard_page_loads(self, browser):
        self.login(browser)
        assert browser.find_element(By.CSS_SELECTOR, '.sidebar').is_displayed()

    def test_sidebar_has_dashboard_link(self, browser):
        self.login(browser)
        links = browser.find_elements(By.PARTIAL_LINK_TEXT, 'Dashboard')
        assert len(links) > 0
