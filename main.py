# main.py - The Final, Stable, and Patient Production Version

import os
import json
import time
import pyotp
import pytz
from datetime import datetime
from urllib.parse import urlparse, parse_qs

from kiteconnect import KiteConnect
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.keys import Keys

# --- Helper Functions (These are correct and unchanged) ---
def get_sheet_service():
    creds_json = json.loads(os.getenv('SERVICE_ACCOUNT_JSON_CONTENT'))
    creds = Credentials.from_service_account_info(creds_json, scopes=['https://www.googleapis.com/auth/spreadsheets'])
    return build('sheets', 'v4', credentials=creds).spreadsheets()

def update_info_cell(sheet_service, key, value):
    spreadsheet_id = os.getenv('SPREADSHEET_ID')
    print(f"Updating sheet: '{key}' = '{value[:30]}...'")
    key = key.lower()
    result = sheet_service.values().get(spreadsheetId=spreadsheet_id, range='Info!A1:A20').execute()
    values = result.get('values', [])
    for i, row in enumerate(values):
        if len(row) >= 1 and row[0].strip().lower() == key:
            range_name = f"Info!B{i+1}"
            sheet_service.values().update(spreadsheetId=spreadsheet_id, range=range_name, valueInputOption='RAW', body={'values': [[value]]}).execute()
            print(f"Successfully updated '{key}' in the sheet.")
            return
    print(f"Warning: Key '{key}' not found in 'Info' sheet Column A.")

# --- The Main Cloud Function (With Human-Like Pauses) ---
def automated_zerodha_login(request):
    # Load all config
    ist = pytz.timezone('Asia/Kolkata')
    ZERODHA_USER_ID = os.getenv('ZERODHA_USER_ID')
    ZERODHA_PASSWORD = os.getenv('ZERODHA_PASSWORD')
    ZERODHA_TOTP_SECRET = os.getenv('ZERODHA_TOTP_SECRET')
    ZERODHA_API_KEY = os.getenv('ZERODHA_API_KEY')
    ZERODHA_API_SECRET = os.getenv('ZERODHA_API_SECRET')
    
    print("Starting automated Zerodha login process...")

    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage') # Critical for stability
    options.add_argument('--disable-gpu')
    options.add_argument("window-size=1920,1080")
    
    driver = webdriver.Chrome(options=options)
    wait = WebDriverWait(driver, 60) # A generous wait time for elements
    
    try:
        # Step 1: Go to page and pause
        kite = KiteConnect(api_key=ZERODHA_API_KEY)
        print("Navigating to login URL...")
        driver.get(kite.login_url())
        time.sleep(2)

        # Step 2: Type User ID, press Enter, and pause
        print("Typing User ID and pressing Enter...")
        wait.until(EC.visibility_of_element_located((By.ID, "userid"))).send_keys(ZERODHA_USER_ID + Keys.RETURN)
        time.sleep(2)
        
        # Step 3: Type Password, press Enter, and pause
        print("Waiting for password field...")
        wait.until(EC.visibility_of_element_located((By.ID, "password"))).send_keys(ZERODHA_PASSWORD + Keys.RETURN)
        print("Password submitted by pressing Enter.")
        time.sleep(2)

        # Step 4: Wait for TOTP page
        print("Waiting for TOTP page...")
        wait.until(EC.visibility_of_element_located((By.ID, "userid")))
        
        # Step 5: Type TOTP (no click/enter) and pause
        totp = pyotp.TOTP(ZERODHA_TOTP_SECRET).now()
        print(f"Generated TOTP: {totp}")
        driver.find_element(By.ID, "userid").send_keys(totp)
        print("TOTP sent. Waiting for automatic redirect.")
        time.sleep(2)
        
        # Step 6: Wait patiently for the result
        print("Waiting for final redirect URL...")
        wait.until(EC.url_contains("request_token"))
        final_url = driver.current_url
        print("Final redirect detected.")
        
        # --- SUCCESS PATH ---
        parsed_url = urlparse(final_url)
        request_token = parse_qs(parsed_url.query).get("request_token", [None])[0]
        driver.quit()
        
        # --- Crucial pause before using the token ---
        print("Pausing before generating session to prevent race condition...")
        time.sleep(2)
        
        session_data = kite.generate_session(request_token, api_secret=ZERODHA_API_SECRET)
        access_token = session_data["access_token"]
        
        sheet_service = get_sheet_service()
        now_ist = datetime.now(ist)
        update_info_cell(sheet_service, "access_token", access_token)
        update_info_cell(sheet_service, "access_token_timestamp", now_ist.strftime("%Y-%m-%d %H:%M:%S"))
        
        print("✅ Zerodha login successful. Access token saved to Google Sheet.")
        return "✅ Zerodha login successful. Access token saved to Google Sheet.", 200

    except Exception as e:
        # --- Simple Error Handling ---
        print(f"❌ An error occurred during the automation: {e}")
        if 'driver' in locals() and driver:
            driver.quit()
        return f"Automation failed: {e}", 500
