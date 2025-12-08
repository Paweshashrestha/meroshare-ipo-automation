from src.meroshare.browser import BrowserManager
from src.config import Config
import logging
import time
import json
import re

logger = logging.getLogger(__name__)


class MeroShareLogin:
    def __init__(self, browser: BrowserManager, config: Config):
        self.browser = browser
        self.config = config
        self.meroshare_config = config.get_meroshare()
    
    def _setup_request_interception(self, client_id: str):
        """Set up request/response interception for login endpoints."""
        login_responses = []
        
        def handle_response(response):
            url = response.url.lower()
            if any(pattern in url for pattern in ['/login', '/auth', 'meroshare']):
                try:
                    status = response.status
                    if status != 200:
                        logger.warning(f"Login response status: {status} - {response.url}")
                        try:
                            body = response.body()
                            if body:
                                response_json = json.loads(body)
                                logger.info(f"Response: {json.dumps(response_json, indent=2)}")
                        except:
                            pass
                except Exception as e:
                    logger.debug(f"Error processing response: {e}")
        
        self.browser.page.on("response", handle_response)
        
        def handle_route(route):
            request = route.request
            url = request.url.lower()
            method = request.method.upper()
            
            is_login_request = (
                method == 'POST' and 
                any(pattern in url for pattern in ['/login', '/auth', 'meroshare'])
            )
            
            if is_login_request and request.post_data:
                try:
                    post_data = request.post_data
                    data = json.loads(post_data) if isinstance(post_data, str) else post_data
                    
                    old_client_id = data.get('clientId', 'not set')
                    data['clientId'] = int(client_id)
                    
                    logger.info(f"Injecting clientId: {client_id} (was: {old_client_id})")
                    
                    route.continue_(
                        post_data=json.dumps(data),
                        headers=dict(request.headers)
                    )
                    return
                except Exception as e:
                    logger.error(f"Error modifying request: {e}")
            
            route.continue_()
        
        patterns = [
            '**/api/**/login**',
            '**/auth/**/login**',
            '**/*login*',
            '**/api/**/auth**',
            '**/meroShare/**/auth**',
            '**/meroshare/**/auth**'
        ]
        
        for pattern in patterns:
            self.browser.page.route(pattern, handle_route)
    
    def _find_field(self, selectors: list, field_type: str = "field"):
        """Find a form field using multiple selectors."""
        for selector in selectors:
            try:
                element = self.browser.page.query_selector(selector)
                if element:
                    logger.debug(f"Found {field_type} with selector: {selector}")
                    return element
            except:
                continue
        return None
    
    def _find_dp_field(self):
        """Find the DP (Depository Participant) dropdown field."""
        selectors = [
            'select[name*="dp" i]',
            'select[id*="dp" i]',
            'select',
            'input[placeholder*="dp" i]',
            'input[name*="depository" i]'
        ]
        
        dp_field = self._find_field(selectors, "DP field")
        
        if not dp_field:
            all_inputs = self.browser.page.query_selector_all('input[type="text"], select')
            for inp in all_inputs:
                try:
                    tag_name = inp.evaluate('el => el.tagName').lower()
                    if tag_name == 'select':
                        options = inp.query_selector_all('option')
                        if options and any('bank' in opt.inner_text().lower() or 'limited' in opt.inner_text().lower() 
                                         for opt in options[:3]):
                            dp_field = inp
                            break
                except:
                    continue
        
        return dp_field
    
    def _select_dp_option(self, dp_field, dp_id: str = None, client_id: str = None):
        """Select DP option from dropdown and extract clientId."""
        options = dp_field.query_selector_all('option')
        if not options:
            return None, None
        
        selected_value = None
        extracted_client_id = client_id
        
        if client_id:
            for option in options:
                option_value = option.get_attribute('value')
                option_data_id = option.get_attribute('data-id') or option.get_attribute('data-client-id')
                
                if (option_value and str(option_value) == str(client_id)) or \
                   (option_data_id and str(option_data_id) == str(client_id)):
                    selected_value = option_value
                    extracted_client_id = client_id
                    break
        
        if not selected_value and dp_id:
            dp_id_upper = dp_id.upper()
            for option in options:
                option_text = option.inner_text().strip().upper()
                option_value = option.get_attribute('value')
                
                if dp_id_upper in option_text or option_text in dp_id_upper:
                    selected_value = option_value
                    
                    option_data_id = option.get_attribute('data-id') or option.get_attribute('data-client-id')
                    if option_data_id:
                        extracted_client_id = option_data_id
                    elif option_value and option_value.isdigit():
                        extracted_client_id = option_value
                    break
        
        if not selected_value:
            for option in options:
                option_text = option.inner_text().strip()
                option_value = option.get_attribute('value')
                
                if dp_id and (dp_id.lower() in option_text.lower() or option_text.lower() in dp_id.lower()):
                    selected_value = option_value
                    option_data_id = option.get_attribute('data-id') or option.get_attribute('data-client-id')
                    if option_data_id:
                        extracted_client_id = option_data_id
                    elif option_value and option_value.isdigit():
                        extracted_client_id = option_value
                    break
        
        if selected_value:
            try:
                dp_field.select_option(value=selected_value, force=True)
                time.sleep(1)
                
                if not extracted_client_id:
                    selected_option = dp_field.query_selector(f'option[value="{selected_value}"]')
                    if selected_option:
                        option_data_id = selected_option.get_attribute('data-id') or selected_option.get_attribute('data-client-id')
                        if option_data_id:
                            extracted_client_id = option_data_id
                        elif selected_value.isdigit():
                            extracted_client_id = selected_value
            except Exception as e:
                logger.warning(f"Error selecting DP option: {e}")
                return None, None
        
        return selected_value, extracted_client_id
    
    def _set_client_id_in_angular(self, client_id: str):
        """Set clientId in Angular scope and form fields."""
        self.browser.page.evaluate(f"""
            (function() {{
                var clientIdValue = {client_id};
                var select = document.querySelector('select');
                
                if (select) {{
                    if (!select.name) {{
                        select.name = 'clientId';
                        select.id = 'clientId';
                    }}
                    
                    select.dispatchEvent(new Event('change', {{ bubbles: true }}));
                    select.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    
                    if (typeof angular !== 'undefined') {{
                        try {{
                            var element = angular.element(select);
                            var scope = element.scope();
                            if (scope) {{
                                if (scope.loginData) scope.loginData.clientId = clientIdValue;
                                if (scope.login) scope.login.clientId = clientIdValue;
                                if (scope.$apply) scope.$apply();
                            }}
                        }} catch(e) {{
                            console.log('Angular update error:', e);
                        }}
                    }}
                }}
                
                var form = document.querySelector('form');
                if (form) {{
                    var existing = form.querySelector('[name="clientId"]:not(select)');
                    if (existing) existing.remove();
                    
                    var hiddenInput = document.createElement('input');
                    hiddenInput.type = 'hidden';
                    hiddenInput.name = 'clientId';
                    hiddenInput.value = clientIdValue;
                    form.appendChild(hiddenInput);
                }}
                
                var clientIdInputs = document.querySelectorAll('input[name*="clientId" i]');
                clientIdInputs.forEach(function(inp) {{
                    inp.value = clientIdValue;
                    inp.dispatchEvent(new Event('change', {{ bubbles: true }}));
                }});
                
                window.clientId = clientIdValue;
            }})();
        """)
    
    def _setup_ajax_interceptors(self, client_id: str):
        """Set up AJAX interceptors to inject clientId."""
        self.browser.page.evaluate(f"""
            (function() {{
                var clientIdValue = {client_id};
                
                var originalFetch = window.fetch;
                window.fetch = function(...args) {{
                    var url = args[0];
                    var options = args[1] || {{}};
                    
                    if (url && typeof url === 'string' && 
                        (url.includes('/login') || url.includes('/auth') || url.includes('meroshare')) &&
                        options.method && options.method.toUpperCase() === 'POST') {{
                        if (options.body) {{
                            try {{
                                var body = typeof options.body === 'string' ? JSON.parse(options.body) : options.body;
                                body.clientId = clientIdValue;
                                options.body = JSON.stringify(body);
                            }} catch(e) {{
                                console.log('Could not parse fetch body:', e);
                            }}
                        }}
                    }}
                    return originalFetch.apply(this, [url, options]);
                }};
                
                var originalXHROpen = XMLHttpRequest.prototype.open;
                var originalXHRSend = XMLHttpRequest.prototype.send;
                
                XMLHttpRequest.prototype.open = function(method, url, ...rest) {{
                    this._method = method;
                    this._url = url;
                    return originalXHROpen.apply(this, [method, url, ...rest]);
                }};
                
                XMLHttpRequest.prototype.send = function(data) {{
                    if (this._url && (this._url.includes('/login') || this._url.includes('/auth') || this._url.includes('meroshare')) &&
                        this._method && this._method.toUpperCase() === 'POST') {{
                        if (data && typeof data === 'string') {{
                            try {{
                                var body = JSON.parse(data);
                                body.clientId = clientIdValue;
                                data = JSON.stringify(body);
                            }} catch(e) {{
                                console.log('Could not parse XHR body:', e);
                            }}
                        }}
                    }}
                    return originalXHRSend.apply(this, [data]);
                }};
            }})();
        """)
    
    def _extract_client_id_from_angular(self):
        """Extract clientId from Angular scope after DP selection."""
        try:
            client_id = self.browser.page.evaluate("""
                (function() {
                    if (typeof angular !== 'undefined') {
                        try {
                            var select = document.querySelector('select');
                            if (select) {
                                var element = angular.element(select);
                                var scope = element.scope();
                                if (scope) {
                                    if (scope.loginData && scope.loginData.clientId) {
                                        return scope.loginData.clientId;
                                    }
                                    if (scope.login && scope.login.clientId) {
                                        return scope.login.clientId;
                                    }
                                }
                            }
                        } catch(e) {
                            return null;
                        }
                    }
                    return null;
                })();
            """)
            return str(client_id) if client_id else None
        except:
            return None
    
    def login(self) -> bool:
        """Perform login to MeroShare."""
        try:
            logger.info("Navigating to MeroShare login page...")
            self.browser.navigate("https://meroshare.cdsc.com.np/#/login")
            time.sleep(2)
            
            if self.browser.wait_for_captcha():
                logger.warning("CAPTCHA detected. Please complete manually.")
                return False
            
            username = self.meroshare_config.get('username')
            password = self.meroshare_config.get('password')
            dp_id = self.meroshare_config.get('dp_id')
            client_id = self.meroshare_config.get('client_id') or self.meroshare_config.get('clientId')
            boid = self.meroshare_config.get('boid')
            
            if not username or not password:
                logger.error("Missing username or password in config")
                return False
            
            if not dp_id and not client_id:
                logger.error("Missing dp_id or client_id in config")
                return False
            
            if client_id:
                self._setup_request_interception(client_id)
            
            logger.info("Filling login credentials...")
            
            username_field = self._find_field([
                'input[placeholder*="username" i]',
                'input[name*="username" i]',
                'input[id*="username" i]',
                'input[type="text"]'
            ], "username")
            
            if not username_field:
                logger.error("Username field not found")
                return False
            
            self.browser.page.fill('input[type="text"]:first-of-type', username)
            time.sleep(0.5)
            
            password_field = self._find_field(['input[type="password"]'], "password")
            if not password_field:
                logger.error("Password field not found")
                return False
            
            self.browser.page.fill('input[type="password"]', password)
            time.sleep(0.5)
            
            if boid and boid != "YOUR_BOID" and boid.strip():
                boid_field = self._find_field([
                    'input[name*="boid" i]',
                    'input[id*="boid" i]',
                    'input[placeholder*="boid" i]'
                ], "BOID")
                if boid_field:
                    self.browser.page.fill(boid_field, boid)
                    time.sleep(0.5)
            
            dp_field = self._find_dp_field()
            if not dp_field:
                logger.error("DP field not found")
                return False
            
            tag_name = dp_field.evaluate('el => el.tagName').lower()
            
            if tag_name == 'input':
                dp_field.click()
                time.sleep(0.5)
                dp_field.fill('')
                dp_field.type(dp_id or '', delay=100)
                time.sleep(1)
                dp_field.press('Enter')
                time.sleep(1)
            elif tag_name == 'select':
                selected_value, extracted_client_id = self._select_dp_option(dp_field, dp_id, client_id)
                
                if not selected_value:
                    logger.error("Could not select DP option")
                    return False
                
                if extracted_client_id:
                    client_id = str(extracted_client_id)
                else:
                    angular_client_id = self._extract_client_id_from_angular()
                    if angular_client_id:
                        client_id = angular_client_id
                
                if client_id:
                    self._set_client_id_in_angular(client_id)
                    time.sleep(1)
            else:
                logger.error(f"Unknown DP field type: {tag_name}")
                return False
            
            if not client_id or client_id == '0':
                logger.error("clientId not found or invalid")
                return False
            
            if client_id:
                self._setup_ajax_interceptors(client_id)
                self._set_client_id_in_angular(client_id)
            
            time.sleep(1)
            
            login_button = self.browser.page.query_selector(
                'button[type="submit"], button:has-text("Login"), button:has-text("LOGIN")'
            )
            
            if not login_button:
                logger.error("Login button not found")
                return False
            
            logger.info("Clicking login button...")
            login_button.click()
            time.sleep(5)
            
            current_url = self.browser.page.url.lower()
            page_text = self.browser.page.inner_text('body').lower()
            
            error_indicators = ['incorrect', 'invalid', 'wrong', 'error', 'failed', 'unauthorized']
            success_indicators = ['dashboard', 'home', 'portfolio', 'asba']
            
            for error in error_indicators:
                if error in page_text:
                    error_elements = self.browser.page.query_selector_all(
                        '.error, .alert-danger, [class*="error"], [class*="danger"]'
                    )
                    for elem in error_elements:
                        if any(err in elem.inner_text().lower() for err in error_indicators):
                            logger.error(f"Login failed: {elem.inner_text()[:100]}")
                            return False
            
            if 'login' not in current_url:
                if any(indicator in current_url or indicator in page_text for indicator in success_indicators):
                    logger.info("Login successful!")
                    return True
            
            if 'login' in current_url:
                error_visible = self.browser.page.query_selector('.error, .alert-danger, [class*="error"]')
                if error_visible:
                    logger.error(f"Login failed: {error_visible.inner_text()}")
                    return False
                
                time.sleep(2)
                page_text_after = self.browser.page.inner_text('body').lower()
                if any(err in page_text_after for err in error_indicators):
                    logger.error("Login failed: Error detected after waiting")
                    return False
                elif any(success in page_text_after for success in success_indicators):
                    logger.info("Login successful!")
                    return True
            
            logger.warning("Login status unclear")
            return False
            
        except Exception as e:
            logger.error(f"Login error: {e}", exc_info=True)
            return False
