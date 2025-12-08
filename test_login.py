#!/usr/bin/env python3
"""
Simple test script to verify MeroShare login functionality
"""
import sys
from pathlib import Path
import logging

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from src.config import Config
from src.meroshare.browser import BrowserManager
from src.meroshare.login import MeroShareLogin

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def test_login():
    print("=" * 50)
    print("MeroShare Login Test")
    print("=" * 50)
    
    # Load config
    config = Config()
    meroshare_config = config.get_meroshare()
    
    # Check if credentials are set
    if not meroshare_config.get('username'):
        print("❌ ERROR: Username not found in config.yaml")
        print("Please add your credentials to config/config.yaml")
        return False
    
    print(f"✓ Username: {meroshare_config.get('username')}")
    print(f"✓ DP-ID: {meroshare_config.get('dp_id', 'Not set')}")
    client_id = meroshare_config.get('client_id') or meroshare_config.get('clientId')
    if client_id:
        print(f"✓ Client ID: {client_id}")
    print(f"✓ Password: {'*' * len(meroshare_config.get('password', ''))}")
    print()
    
    # Ask user if they want to proceed
    response = input("Do you want to proceed with login test? (y/n): ")
    if response.lower() != 'y':
        print("Test cancelled.")
        return False
    
    print("\nStarting browser (headless=False so you can see what's happening)...")
    print("Note: If CAPTCHA appears, you'll have 60 seconds to complete it manually.\n")
    
    try:
        # Run browser in non-headless mode so user can see
        with BrowserManager(headless=False) as browser:
            login = MeroShareLogin(browser, config)
            
            print("Attempting login...")
            success = login.login()
            
            if success:
                print("\n" + "=" * 50)
                print("✅ LOGIN SUCCESSFUL!")
                print("=" * 50)
                print("\nBrowser will stay open for 10 seconds so you can verify...")
                import time
                time.sleep(10)
                return True
            else:
                print("\n" + "=" * 50)
                print("❌ LOGIN FAILED")
                print("=" * 50)
                print("\nCheck the browser window and logs above for details.")
                print("Browser will stay open for 10 seconds...")
                import time
                time.sleep(10)
                return False
                
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user.")
        return False
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        logger.exception("Login test failed")
        return False

if __name__ == "__main__":
    success = test_login()
    sys.exit(0 if success else 1)

