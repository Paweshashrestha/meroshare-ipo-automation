import sys
from pathlib import Path
import logging
import re
import requests
from typing import Optional, Dict, Any, Tuple, List

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.config import Config
from src.meroshare.browser import BrowserManager
from src.meroshare.login import MeroShareLogin

MEROSHARE_LOGIN_URL = "https://meroshare.cdsc.com.np/#/login"
ASBA_LINK_SELECTOR = 'a[href="#/asba"]'
TELEGRAM_REQUEST_TIMEOUT = 10
ASBA_NAVIGATE_TIMEOUT_MS = 15000

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


def account_display_name(account_config: Dict[str, Any]) -> str:
    return account_config.get("account_name") or account_config.get("username") or "N/A"


def send_telegram_notification(config: Config, message: str) -> bool:
    """Send Telegram notification."""
    try:
        telegram_config = config.get_telegram()
        bot_token = telegram_config.get("bot_token")
        chat_id = telegram_config.get("chat_id")
        
        if not bot_token or not chat_id or bot_token == "YOUR_BOT_TOKEN" or chat_id == "YOUR_CHAT_ID":
            return False
        
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "HTML"
        }
        
        response = requests.post(url, json=payload, timeout=TELEGRAM_REQUEST_TIMEOUT)
        if response.status_code == 200:
            logger.info("Telegram notification sent")
            return True
        else:
            logger.warning("Failed to send Telegram notification: %s", response.status_code)
            return False
    except Exception as e:
        logger.warning("Error sending Telegram notification: %s", e)
        return False


def navigate_to_asba(browser: BrowserManager) -> bool:
    """Navigate to ASBA section. Returns True on success."""
    try:
        page = browser.page
        if not page:
            return False
        page.wait_for_timeout(3000)
        asba_link = page.wait_for_selector(ASBA_LINK_SELECTOR, timeout=ASBA_NAVIGATE_TIMEOUT_MS)
        if not asba_link:
            return False
        asba_link.click()
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(2000)
        logger.info("Navigated to ASBA section")
        return True
    except Exception as e:
        logger.error("Failed to navigate to ASBA: %s", e)
        return False


def check_for_available_ipos(browser: BrowserManager) -> Tuple[bool, List]:
    """Check if IPOs are available and return list of IPO rows."""
    try:
        if not browser.page:
            return False, []
        
        browser.page.wait_for_load_state("networkidle")
        browser.page.wait_for_timeout(3000)
        try:
            browser.page.wait_for_selector("table tbody tr, tbody tr, app-no-records-found", timeout=15000)
        except Exception:
            pass
        browser.page.wait_for_timeout(2000)
        
        no_records = browser.page.query_selector("app-no-records-found .fallback-title-message, .no-records, [class*='no-record']")
        if no_records:
            text = no_records.inner_text().strip()
            if "No Record" in text or "no record" in text.lower():
                logger.info("No IPO available currently")
                return False, []
        
        # Try multiple selectors to find IPO rows
        ipo_rows = []
        
        # Try table rows first
        ipo_rows = browser.page.query_selector_all("table tbody tr")
        logger.debug(f"Found {len(ipo_rows)} rows using 'table tbody tr' selector")
        
        # If no table rows, try other selectors
        if not ipo_rows:
            ipo_rows = browser.page.query_selector_all("tbody tr")
            logger.debug(f"Found {len(ipo_rows)} rows using 'tbody tr' selector")
        
        if not ipo_rows:
            ipo_rows = browser.page.query_selector_all("tr[role='row']")
            logger.debug(f"Found {len(ipo_rows)} rows using 'tr[role=row]' selector")
        
        if not ipo_rows:
            # Try finding any clickable rows that might contain IPO info
            all_rows = browser.page.query_selector_all("tr, .card, [role='row'], .row")
            # Filter rows that might be IPO entries (have buttons or links)
            for row in all_rows:
                row_text = row.inner_text().lower() if row else ""
                if any(keyword in row_text for keyword in ['apply', 'ipo', 'issue', 'share']):
                    ipo_rows.append(row)
            logger.debug(f"Found {len(ipo_rows)} rows using filtered approach")
        
        # Filter out header rows
        if ipo_rows:
            filtered_rows = []
            for row in ipo_rows:
                row_text = row.inner_text().lower() if row else ""
                # Skip header rows
                if not any(header in row_text for header in ['company', 'issue', 'type', 'price', 'action']):
                    if any(keyword in row_text for keyword in ['apply', 'view', 'details']) or len(row_text) > 20:
                        filtered_rows.append(row)
            ipo_rows = filtered_rows if filtered_rows else ipo_rows
        
        if not ipo_rows:
            logger.warning("No IPO rows found with any selector")
            page_html = browser.page.content()
            if "apply" in page_html.lower() or "ipo" in page_html.lower():
                logger.warning("Page has 'apply'/'ipo' text but no rows - table may still be loading or structure changed")
            return False, []
        
        logger.info(f"Found {len(ipo_rows)} IPO row(s) on ASBA page")
        return True, ipo_rows
    except Exception as e:
        logger.error(f"Error checking for IPOs: {e}", exc_info=True)
        return False, []


def extract_ipo_details_from_form(browser: BrowserManager) -> Optional[Dict[str, Any]]:
    """Extract IPO details from the application form page."""
    try:
        if not browser.page:
            return None
        page_html = browser.page.content()
        
        share_type_elem = browser.page.query_selector('span.share-of-type')
        share_type = share_type_elem.inner_text().strip() if share_type_elem else None
        
        share_group_elem = browser.page.query_selector('span.isin[tooltip="Share Group"]')
        if share_group_elem:
            share_group = share_group_elem.inner_text().strip()
        else:
            page_text = browser.page.inner_text("body")
            share_group_match = re.search(r'Ordinary Shares|Preference Shares', page_text, re.IGNORECASE)
            share_group = share_group_match.group(0) if share_group_match else None
        
        price = None
        price_match = re.search(r'Price per Share[^>]*>([^<]+)<', page_html, re.IGNORECASE | re.DOTALL)
        if price_match:
            try:
                price = int(price_match.group(1).strip())
            except ValueError:
                pass
        
        if price is None:
            page_text = browser.page.inner_text("body")
            price_match = re.search(r'Price per Share[^\n]*\n[^\n]*?(\d+)', page_text, re.IGNORECASE)
            if price_match:
                try:
                    price = int(price_match.group(1).strip())
                except ValueError:
                    pass
        
        return {
            "share_type": share_type,
            "share_group": share_group,
            "price": price
        }
    except Exception as e:
        logger.error(f"Error extracting IPO details: {e}")
        return None


def check_ipo_conditions(ipo_details: Dict[str, Any]) -> bool:
    """Check if IPO meets the required conditions."""
    if not ipo_details:
        return False
    
    share_type = ipo_details.get("share_type", "").strip().upper()
    share_group = ipo_details.get("share_group", "").strip().upper()
    price = ipo_details.get("price")
    
    if share_type != "IPO":
        return False
    if share_group != "ORDINARY SHARES":
        return False
    if price != 100:
        return False
    
    logger.info("IPO conditions met!")
    return True


def find_and_click_apply_button(browser: BrowserManager, ipo_row) -> bool:
    """Find and click the Apply button for an IPO."""
    try:
        if not browser.page:
            return False
        buttons = ipo_row.query_selector_all('button, a, [role="button"], td button, td a')
        apply_button = None
        
        for btn in buttons:
            try:
                btn_text = btn.inner_text().lower().strip()
                if 'apply' in btn_text:
                    apply_button = btn
                    break
            except Exception:
                continue
        
        if not apply_button:
            row_text = ipo_row.inner_text().lower()
            if 'apply' in row_text:
                try:
                    ipo_row.evaluate('el => el.click()')
                    browser.page.wait_for_load_state("networkidle")
                    browser.page.wait_for_timeout(2000)
                    if browser.page.query_selector('app-issue, form, #appliedKitta'):
                        browser.page.evaluate('window.scrollTo(0, 0)')
                        browser.page.wait_for_timeout(500)
                        return True
                except Exception:
                    pass
        
        if apply_button:
            apply_button.click()
            browser.page.wait_for_load_state("networkidle")
            browser.page.wait_for_timeout(2000)
            if browser.page.query_selector('app-issue, form, #appliedKitta'):
                browser.page.evaluate('window.scrollTo(0, 0)')
                browser.page.wait_for_timeout(500)
                return True
        return False
    except Exception as e:
        logger.error(f"Error clicking Apply button: {e}")
        return False


def fill_ipo_form(browser: BrowserManager, account_config: Dict[str, Any]) -> bool:
    """Fill the IPO application form with account details."""
    try:
        if not browser.page:
            return False
        logger.info("Filling IPO application form...")
        browser.page.evaluate('window.scrollTo(0, 0)')
        browser.page.wait_for_timeout(500)
        
        crn = account_config.get("crn")
        bank_name = account_config.get("bank_name")
        applied_kitta = account_config.get("applied_kitta", "10")
        
        if not crn or not bank_name:
            logger.error("Missing required config: crn or bank_name")
            return False
        
        kitta_input = browser.page.query_selector('#appliedKitta, input[name="appliedKitta"]')
        if kitta_input:
            kitta_input.scroll_into_view_if_needed()
            browser.page.wait_for_timeout(300)
            kitta_input.fill(applied_kitta)
            browser.page.wait_for_timeout(500)
        
        bank_select = browser.page.query_selector('#selectBank, select[name="selectBank"]')
        if bank_select:
            bank_select.scroll_into_view_if_needed()
            browser.page.wait_for_timeout(300)
            options = bank_select.query_selector_all("option:not([value=''])")
            for option in options:
                option_text = option.inner_text().strip()
                bank_name_clean = bank_name.upper().replace("LIMITED", "").replace("LTD", "").strip()
                option_text_clean = option_text.upper().replace("LIMITED", "").replace("LTD", "").strip()
                if (bank_name.upper() in option_text.upper() or 
                    bank_name_clean in option_text_clean or
                    option_text_clean in bank_name_clean):
                    bank_select.select_option(value=option.get_attribute("value"))
                    bank_select.evaluate('el => el.dispatchEvent(new Event("change", { bubbles: true }))')
                    browser.page.wait_for_timeout(2000)
                    break
            
            account_select = browser.page.query_selector('select[name*="account" i], select[id*="account" i]')
            if account_select:
                account_select.scroll_into_view_if_needed()
                browser.page.wait_for_timeout(300)
                browser.page.wait_for_timeout(1000)
                account_options = account_select.query_selector_all('option:not([value=""]):not([value="0"])')
                if account_options:
                    first_account_value = account_options[0].get_attribute("value")
                    account_select.select_option(value=first_account_value)
                    browser.page.wait_for_timeout(500)
        
        crn_input = browser.page.query_selector('#crnNumber, input[name="crnNumber"]')
        if crn_input:
            crn_input.scroll_into_view_if_needed()
            browser.page.wait_for_timeout(300)
            crn_input.fill(crn)
            browser.page.wait_for_timeout(500)
        
        disclaimer_checkbox = browser.page.query_selector('#disclaimer, input[name="disclaimer"]')
        if disclaimer_checkbox and not disclaimer_checkbox.is_checked():
            disclaimer_checkbox.scroll_into_view_if_needed()
            browser.page.wait_for_timeout(300)
            disclaimer_checkbox.check()
            browser.page.wait_for_timeout(500)
        
        return True
    except Exception as e:
        logger.error(f"Error filling IPO form: {e}", exc_info=True)
        return False


def submit_ipo_form(browser: BrowserManager, account_config: Dict[str, Any]) -> bool:
    """Submit the IPO application form."""
    try:
        if not browser.page:
            return False
        browser.page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
        browser.page.wait_for_timeout(500)
        
        logger.info("Looking for Proceed button...")
        proceed_button = browser.page.query_selector(
            'button[type="submit"]:not([disabled]), button:has-text("Proceed"):not([disabled])'
        )
        if not proceed_button:
            logger.warning("Proceed button not found - may already be on transaction PIN page")
            # Continue to check for transaction PIN input
        else:
            logger.info("Found Proceed button, clicking...")
            # Scroll page first, then try to click
            browser.page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
            browser.page.wait_for_timeout(500)
            
            # Try regular click first
            try:
                proceed_button.scroll_into_view_if_needed(timeout=5000)
                browser.page.wait_for_timeout(300)
                proceed_button.click()
            except Exception as e:
                logger.warning(f"Regular click failed: {e}, using JavaScript click...")
                # Use JavaScript click as fallback
                browser.page.evaluate('''
                    () => {
                        const btn = document.querySelector('button[type="submit"]:not([disabled]), button:has-text("Proceed"):not([disabled])');
                        if (btn) {
                            btn.click();
                        }
                    }
                ''')
            
            browser.page.wait_for_load_state("networkidle")
            browser.page.wait_for_timeout(3000)  # Wait longer for page to load
        
        logger.info("Looking for Transaction PIN input...")
        # Wait for transaction PIN input to appear
        try:
            transaction_pin_input = browser.page.wait_for_selector(
                '#transactionPIN, input[name="transactionPIN"], input[id*="transaction"], input[name*="transaction"]',
                timeout=10000
            )
            logger.info("Transaction PIN input found")
        except Exception as e:
            logger.warning(f"Transaction PIN input not found: {e}")
            transaction_pin_input = browser.page.query_selector('#transactionPIN, input[name="transactionPIN"]')
        
        if transaction_pin_input:
            logger.info("Found Transaction PIN input")
            transaction_pin = account_config.get("transaction_pin")
            if not transaction_pin:
                logger.error("Transaction PIN not found in account config")
                return False
            
            # Scroll to input and fill it
            browser.page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
            browser.page.wait_for_timeout(500)
            
            try:
                transaction_pin_input.scroll_into_view_if_needed(timeout=5000)
            except Exception:
                logger.warning("Could not scroll to transaction PIN input, trying anyway...")
            
            browser.page.wait_for_timeout(500)
            
            # Clear any existing value and fill
            transaction_pin_input.click()
            browser.page.wait_for_timeout(200)
            transaction_pin_input.fill("")  # Clear first
            browser.page.wait_for_timeout(200)
            transaction_pin_input.fill(transaction_pin)
            browser.page.wait_for_timeout(500)
            
            # Verify it was filled
            filled_value = transaction_pin_input.input_value()
            if filled_value == transaction_pin:
                logger.info(f"Transaction PIN filled successfully: {filled_value}")
            else:
                logger.warning(f"Transaction PIN may not have been filled correctly. Expected: {transaction_pin}, Got: {filled_value}")
            
            logger.info("Waiting for Apply button to enable...")
            browser.page.wait_for_timeout(2000)  # Wait longer for button to enable
            
            # Try multiple approaches to find and click the Apply button
            logger.info("Looking for Apply button...")
            apply_button = None
            
            # Wait for button to become enabled (Angular might need time)
            try:
                logger.info("Waiting for Apply button to become enabled...")
                browser.page.wait_for_function(
                    '() => { const btn = document.querySelector("button.btn-primary[type=\\"submit\\"]"); return btn && !btn.disabled && btn.offsetParent !== null; }',
                    timeout=15000
                )
                logger.info("Button is now enabled and visible")
            except Exception as e:
                logger.warning(f"Button may not be enabled yet: {e}")
            
            # Try multiple selectors based on the HTML structure
            selectors = [
                'button.btn-primary[type="submit"]:not([disabled])',
                'button[type="submit"].btn-primary:not([disabled])',
                'button.btn-gap.btn-primary[type="submit"]:not([disabled])',
                'button.btn-primary[type="submit"]',
                'button[type="submit"]:not([disabled])',
                'button:has-text("Apply"):not([disabled])',
                'button[type="submit"]'
            ]
            
            for selector in selectors:
                try:
                    buttons = browser.page.query_selector_all(selector)
                    for btn in buttons:
                        try:
                            # Check if button is visible and not disabled
                            is_disabled = btn.get_attribute("disabled")
                            is_visible = browser.page.evaluate('(btn) => btn.offsetParent !== null', btn)
                            
                            if not is_disabled and is_visible:
                                apply_button = btn
                                logger.info(f"Found Apply button using selector: {selector}")
                                break
                        except Exception:
                            continue
                    if apply_button:
                        break
                except Exception:
                    continue
            
            # Final fallback: get any submit button
            if not apply_button:
                logger.warning("No enabled button found, trying to get any submit button...")
                apply_button = browser.page.query_selector('button[type="submit"]')
            
            if apply_button:
                logger.info("Found Apply button, clicking...")
                browser.page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                browser.page.wait_for_timeout(500)
                
                # Try scrolling into view
                try:
                    apply_button.scroll_into_view_if_needed(timeout=5000)
                except Exception:
                    pass
                
                browser.page.wait_for_timeout(500)
                
                # Try clicking with JavaScript as fallback
                try:
                    apply_button.click()
                    logger.info("Clicked Apply button successfully")
                except Exception as e:
                    logger.warning(f"Regular click failed: {e}, trying JavaScript click...")
                    # Use JavaScript click if regular click fails - use the specific selector
                    browser.page.evaluate('''
                        () => {
                            const btn = document.querySelector('button.btn-primary[type="submit"]:not([disabled])') || 
                                        document.querySelector('button.btn-gap.btn-primary[type="submit"]:not([disabled])') ||
                                        document.querySelector('button[type="submit"]:not([disabled])');
                            if (btn) {
                                btn.click();
                            }
                        }
                    ''')
                    logger.info("JavaScript click executed")
                
                logger.info("Waiting for page to load after submission...")
                browser.page.wait_for_load_state("networkidle", timeout=15000)
                browser.page.wait_for_timeout(3000)
                
                error_indicators = browser.page.query_selector_all('.error, .alert-danger, [class*="error"]')
                for indicator in error_indicators:
                    text = indicator.inner_text().lower()
                    if any(word in text for word in ["error", "failed", "invalid"]):
                        logger.error(f"Error: {indicator.inner_text()[:200]}")
                        return False
                
                page_text = browser.page.inner_text("body").lower()
                if any(word in page_text for word in ["error occurred", "failed", "invalid"]):
                    return False
                
                transaction_pin_still_present = browser.page.query_selector('#transactionPIN')
                if transaction_pin_still_present:
                    return False
                
                success_indicators = browser.page.query_selector_all('.success, .alert-success, [class*="success"]')
                for indicator in success_indicators:
                    text = indicator.inner_text().lower()
                    if any(word in text for word in ["success", "submitted", "applied"]):
                        logger.info("IPO application submitted successfully!")
                        return True
                
                if "success" in page_text or "submitted" in page_text:
                    logger.info("IPO application submitted successfully!")
                    return True
                
                logger.info("No explicit success message, but transaction PIN is gone - assuming success")
                return True
            else:
                logger.error("Apply button not found or not clickable")
                return False
        else:
            logger.info("No Transaction PIN input found - form may have been submitted already or different flow")
            return True
    except Exception as e:
        logger.error(f"Error submitting IPO form: {e}", exc_info=True)
        return False


def get_ipo_company_name(browser: BrowserManager) -> str:
    """Extract company name from IPO form."""
    try:
        if not browser.page:
            return "Unknown Company"
        company_elem = browser.page.query_selector('.company-name span, [tooltip="Company Name"]')
        if company_elem:
            name = company_elem.inner_text().strip()
            return name if name else "Unknown Company"
        return "Unknown Company"
    except Exception:
        return "Unknown Company"


def process_ipo_for_account(browser: BrowserManager, account_config: Dict[str, Any], ipo_rows: List, config: Config) -> bool:
    """Process IPOs and apply for matching ones for a single account."""
    if not browser.page:
        return False
    for idx, row in enumerate(ipo_rows):
        try:
            logger.info(f"Processing IPO {idx + 1}...")
            
            if not find_and_click_apply_button(browser, row):
                continue
            
            ipo_details = extract_ipo_details_from_form(browser)
            if not ipo_details:
                if browser.page:
                    browser.page.go_back()
                    browser.page.wait_for_load_state("networkidle")
                continue
            
            if not check_ipo_conditions(ipo_details):
                if browser.page:
                    browser.page.go_back()
                    browser.page.wait_for_load_state("networkidle")
                continue
            
            company_name = get_ipo_company_name(browser)
            
            if fill_ipo_form(browser, account_config):
                if submit_ipo_form(browser, account_config):
                    logger.info(f"Successfully applied for IPO {idx + 1}")
                    
                    # Send Telegram notification
                    message = f"""
✅ <b>IPO Application Successful!</b>

📊 <b>Company:</b> {company_name}
👤 <b>Account:</b> {account_display_name(account_config)}
📦 <b>Kitta:</b> {account_config.get('applied_kitta', '10')}
💰 <b>Price:</b> Rs. 100 per share
📈 <b>Type:</b> IPO - Ordinary Shares

Application submitted successfully!
"""
                    send_telegram_notification(config, message)
                    return True
            
            if browser.page:
                browser.page.wait_for_timeout(2000)
            navigate_to_asba(browser)
            
        except Exception as e:
            logger.error(f"Error processing IPO {idx + 1}: {e}", exc_info=True)
            try:
                if browser.page:
                    browser.page.go_back()
                    browser.page.wait_for_load_state("networkidle")
            except Exception:
                navigate_to_asba(browser)
            continue
    
    return False


def find_matching_ipo(browser: BrowserManager, ipo_rows: List) -> Optional[Dict[str, Any]]:
    """Find a matching IPO and return its details."""
    if not browser.page:
        return None
    for idx, row in enumerate(ipo_rows):
        try:
            logger.info(f"Checking IPO {idx + 1}...")
            
            if not find_and_click_apply_button(browser, row):
                continue
            
            ipo_details = extract_ipo_details_from_form(browser)
            if not ipo_details:
                browser.page.go_back()
                browser.page.wait_for_load_state("networkidle")
                continue
            
            if check_ipo_conditions(ipo_details):
                company_name = get_ipo_company_name(browser)
                ipo_details['company_name'] = company_name
                ipo_details['row_index'] = idx
                return ipo_details
            
            browser.page.go_back()
            browser.page.wait_for_load_state("networkidle")
        except Exception as e:
            logger.error(f"Error checking IPO {idx + 1}: {e}")
            try:
                if browser.page:
                    browser.page.go_back()
                    browser.page.wait_for_load_state("networkidle")
            except Exception:
                navigate_to_asba(browser)
            continue
    logger.info(f"Checked {len(ipo_rows)} IPO(s), none matched (Price=100, Type=IPO, Ordinary Shares)")
    return None


def apply_for_ipo_with_account(browser: BrowserManager, account_config: Dict[str, Any], config: Config, ipo_index: int, company_name: Optional[str] = None) -> bool:
    """Apply for IPO with a specific account."""
    try:
        if not browser.page:
            return False
        
        # Navigate to ASBA and wait for page to load
        navigate_to_asba(browser)
        browser.page.wait_for_load_state("networkidle")
        browser.page.wait_for_timeout(3000)
        
        # Use the same IPO detection logic that worked in check_for_available_ipos
        has_ipos, ipo_rows = check_for_available_ipos(browser)
        
        if not has_ipos or not ipo_rows:
            logger.error("No IPOs found on page - may have already been applied")
            return False
        
        logger.info(f"Found {len(ipo_rows)} IPO row(s) on page")
        
        # Try to find the IPO by company name first (most reliable)
        row = None
        if company_name:
            for r in ipo_rows:
                try:
                    row_text = r.inner_text()
                    if company_name.lower() in row_text.lower():
                        row = r
                        logger.info(f"Found IPO by company name: {company_name}")
                        break
                except Exception as e:
                    logger.debug("Row inner_text failed: %s", e)
                    continue
        
        # Fall back to index if name search didn't work
        if not row:
            if ipo_index < len(ipo_rows):
                row = ipo_rows[ipo_index]
                logger.info(f"Using IPO at index {ipo_index}")
            else:
                logger.warning(f"IPO index {ipo_index} out of range, using first available IPO")
                row = ipo_rows[0] if ipo_rows else None
        
        if not row:
            logger.error("Could not find IPO row")
            return False
        
        if not find_and_click_apply_button(browser, row):
            return False
        
        ipo_details = extract_ipo_details_from_form(browser)
        if not ipo_details or not check_ipo_conditions(ipo_details):
            return False
        
        company_name = get_ipo_company_name(browser)
        
        fill_result = fill_ipo_form(browser, account_config)
        if not fill_result:
            logger.error(f"Failed to fill IPO form for account: {account_display_name(account_config)}")
            return False
        
        logger.info("Form filled successfully, now submitting...")
        submit_result = submit_ipo_form(browser, account_config)
        if not submit_result:
            logger.error(f"Failed to submit IPO form for account: {account_display_name(account_config)}")
            return False
        
        logger.info(f"Successfully applied for IPO with account: {account_display_name(account_config)}")
        
        message = f"""
✅ <b>IPO Application Successful!</b>

📊 <b>Company:</b> {company_name}
👤 <b>Account:</b> {account_display_name(account_config)}
📦 <b>Kitta:</b> {account_config.get('applied_kitta', '10')}
💰 <b>Price:</b> Rs. 100 per share
📈 <b>Type:</b> IPO - Ordinary Shares

Application submitted successfully!
"""
        send_telegram_notification(config, message)
        return True
    except Exception as e:
        logger.error(f"Error applying for IPO with account {account_display_name(account_config)}: {e}", exc_info=True)
        return False


def main():
    """Main function: Check with first account, if IPO found, apply with all accounts."""
    try:
        config = Config()
        
        meroshare_config = config.get_meroshare()
        accounts = meroshare_config.get("accounts")
        
        if not accounts:
            accounts = [meroshare_config]
        elif not isinstance(accounts, list):
            accounts = [accounts]
        
        if len(accounts) == 0:
            logger.error("No accounts configured")
            return False
        
        # Use first account to check for IPOs
        check_account = accounts[0]
        other_accounts = accounts[1:] if len(accounts) > 1 else []
        
        logger.info(f"Checking IPOs with account: {account_display_name(check_account)}")
        if other_accounts:
            logger.info(f"Will apply with {len(other_accounts)} additional account(s) if IPO found")
        
        send_telegram_notification(config, f"🚀 IPO Check Started\n\nChecking with: {account_display_name(check_account)}\nOther accounts: {len(other_accounts)}")
        
        if not all([check_account.get("username"), check_account.get("password"), 
                   check_account.get("crn"), check_account.get("bank_name")]):
            logger.error("Missing required config in check account")
            send_telegram_notification(config, "❌ Error: Missing required config")
            return False
        
        headless = config.get("headless", True)
        with BrowserManager(headless=headless) as browser:
            if not browser.page:
                logger.error("Browser page not initialized")
                return False
            
            # Step 1: Login with first account and check for IPOs
            temp_config = Config()
            temp_config.config['meroshare'] = check_account
            login = MeroShareLogin(browser, temp_config)
            
            logger.info("Logging in with check account...")
            if not login.login():
                reason = getattr(login, "last_error", "") or "Login failed"
                logger.error(f"Login failed: {reason}")
                send_telegram_notification(config, f"❌ Login failed for check account {account_display_name(check_account)}: {reason}")
                return False
            
            if not navigate_to_asba(browser):
                return False
            
            has_ipos, ipo_rows = check_for_available_ipos(browser)
            logger.info(f"IPO check result: has_ipos={has_ipos}, rows_found={len(ipo_rows) if ipo_rows else 0}")

            matching_ipo = None
            if has_ipos and ipo_rows:
                logger.info(f"Searching for matching IPO among {len(ipo_rows)} IPO(s)...")
                matching_ipo = find_matching_ipo(browser, ipo_rows)
            elif not has_ipos and other_accounts:
                logger.info("Account 1: No IPOs on page (may already have applied). Will try other accounts.")
                send_telegram_notification(config, "ℹ️ Account 1: No IPOs (may already applied). Checking accounts 2 & 3...")
            elif not has_ipos:
                send_telegram_notification(config, "🔍 No IPOs available currently")
                return True
            applied_count = 0
            ipo_index = 0
            company_name = "Unknown"

            if matching_ipo:
                company_name = matching_ipo.get('company_name', 'Unknown')
                ipo_index = matching_ipo.get('row_index', 0)
                logger.info(f"Found matching IPO: {company_name}")
                send_telegram_notification(config, f"✅ Found matching IPO!\n\n📊 Company: {company_name}\n💰 Price: Rs. 100\n📈 Type: IPO - Ordinary Shares\n\nApplying with all accounts...")
                logger.info(f"Applying with check account: {account_display_name(check_account)}")
                if apply_for_ipo_with_account(browser, check_account, config, ipo_index, company_name):
                    applied_count += 1
                    if browser.page:
                        browser.page.wait_for_timeout(3000)
                else:
                    send_telegram_notification(config, f"❌ Account 1 ({account_display_name(check_account)}): Apply failed (may already have applied)")
            else:
                if has_ipos:
                    logger.info("Account 1: No matching IPO (may already have applied). Trying other accounts...")
                    send_telegram_notification(config, "ℹ️ Account 1: No matching IPO (may already applied). Checking accounts 2 & 3...")

            # Step 3: Apply with all other accounts (2 and 3)
            for account_idx, account_config in enumerate(other_accounts, 2):
                try:
                    logger.info(f"\n{'='*50}")
                    logger.info(f"Applying with Account {account_idx}/{len(accounts)}: {account_display_name(account_config)}")
                    logger.info(f"{'='*50}")
                    
                    if not all([account_config.get("username"), account_config.get("password"), 
                               account_config.get("crn"), account_config.get("bank_name")]):
                        logger.error(f"Account {account_idx}: Missing required config")
                        continue
                    
                    if not browser.page or not browser.context:
                        continue
                    try:
                        browser.context.clear_cookies()
                        if browser.page:
                            browser.page.close()
                        browser.page = browser.context.new_page()
                        browser.navigate(MEROSHARE_LOGIN_URL)
                        browser.page.wait_for_timeout(5000)
                    except Exception as nav_err:
                        logger.warning(f"New page / navigate failed: {nav_err}")
                    temp_config = Config()
                    temp_config.config['meroshare'] = account_config

                    def do_login():
                        login_obj = MeroShareLogin(browser, temp_config)
                        return login_obj.login(), getattr(login_obj, "last_error", "") or "Login failed"

                    logger.info("Logging in...")
                    ok, reason = do_login()
                    if not ok:
                        logger.warning("Login failed, retrying with fresh page...")
                        try:
                            browser.context.clear_cookies()
                            if browser.page:
                                browser.page.close()
                            browser.page = browser.context.new_page()
                            browser.navigate(MEROSHARE_LOGIN_URL)
                            browser.page.wait_for_timeout(5000)
                            ok, reason = do_login()
                        except Exception as retry_err:
                            logger.warning(f"Retry failed: {retry_err}")
                    if not ok:
                        logger.error(f"Login failed: {reason}")
                        send_telegram_notification(config, f"❌ Account {account_idx} ({account_display_name(account_config)}): {reason}")
                        continue

                    acc_ipo_index = ipo_index
                    acc_company_name = company_name
                    if not matching_ipo:
                        if not navigate_to_asba(browser):
                            continue
                        has_acc_ipos, acc_ipo_rows = check_for_available_ipos(browser)
                        if not has_acc_ipos or not acc_ipo_rows:
                            logger.info(f"Account {account_idx}: No IPOs on their ASBA page")
                            continue
                        acc_matching = find_matching_ipo(browser, acc_ipo_rows)
                        if not acc_matching:
                            logger.info(f"Account {account_idx}: No matching IPO for them")
                            continue
                        acc_ipo_index = acc_matching.get('row_index', 0)
                        acc_company_name = acc_matching.get('company_name', 'Unknown')
                        logger.info(f"Account {account_idx}: Found matching IPO: {acc_company_name}")

                    if apply_for_ipo_with_account(browser, account_config, config, acc_ipo_index, acc_company_name):
                        applied_count += 1
                        if browser.page:
                            browser.page.wait_for_timeout(3000)
                    
                except Exception as e:
                    logger.error(f"Error processing account {account_idx}: {e}", exc_info=True)
                    send_telegram_notification(config, f"❌ Account {account_idx}: Error - {str(e)[:200]}")
                    continue
            
            logger.info(f"Completed: Applied with {applied_count}/{len(accounts)} account(s)")
            send_telegram_notification(config, f"✅ IPO Application Completed\n\nApplied with {applied_count}/{len(accounts)} account(s)")
            return True
        
    except Exception as e:
        logger.error(f"Failed: {e}", exc_info=True)
        send_telegram_notification(config, f"❌ Error: {str(e)[:200]}")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
