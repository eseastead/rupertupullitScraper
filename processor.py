import sys
import requests
from bs4 import BeautifulSoup
import json
import re
import os
from datetime import datetime

# ==================== CONFIGURATION ====================
MAIN_SITE_URL = "https://rupertsupullit.com/"
AJAX_URL = "https://rupertsupullit.com/wp-admin/admin-ajax.php"
CAR_DATA_FILE = 'car_inventory.json'

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}
# =======================================================

def get_dynamic_nonce(main_site_url, headers):
    """Fetches the main page and extracts the dynamic nonce."""
    sys.stderr.write(f"[*] Attempting GET request to: {main_site_url} to retrieve nonce.\n")
    try:
        response = requests.get(main_site_url, headers=headers, timeout=15)
        response.raise_for_status()
        full_html = response.text
        nonce_pattern = re.compile(r'"nonce":"([a-f0-9]+)"')
        match = nonce_pattern.search(full_html)
        if match:
            dynamic_nonce = match.group(1)
            sys.stderr.write(f"[*] Successfully extracted dynamic nonce: {dynamic_nonce}\n")
            return dynamic_nonce
        else:
            sys.stderr.write("[-] Could not find the dynamic nonce on the page.\n")
            return None
    except requests.RequestException as e:
        sys.stderr.write(f"[-] Network connection error while fetching nonce: {e}\n")
        return None

def fetch_inventory_html(dynamic_nonce):
    """Fetches the live inventory webpage."""
    sys.stderr.write(f"[*] Attempting POST request to: {AJAX_URL} with dynamic nonce.\n")
    form_data = {
        'make': '',
        'model': '',
        'year_start': '1963',
        'year_end': '2026',
        'action': 'yardconnect_search_vehicles',
        'nonce': dynamic_nonce,
        'view': 'table',
        'length': '1000'
    }
    try:
        response = requests.post(AJAX_URL, headers=HEADERS, data=form_data, timeout=15)
        response.raise_for_status()
        return response.text
    except requests.RequestException as e:
        sys.stderr.write(f"[-] Network connection error: {e}\n")
        return None

def scan_and_extract_inventory(html):
    """Parses the inventory table and extracts all car details."""
    soup = BeautifulSoup(html, "html.parser")
    all_cars_data = []
    inventory_table = soup.find("table", class_="yardconnect-vehicles-table")

    if inventory_table:
        sys.stderr.write("[_] Found the inventory table. Extracting all car data...\n")
        tbody = inventory_table.find("tbody")
        if tbody:
            rows = tbody.find_all("tr")
            if rows:
                sys.stderr.write(f"[_] Found {len(rows)} car entries in total.\n")
                for row in rows:
                    cells = row.find_all("td")
                    if cells and len(cells) >= 8:
                        car_data = {
                            "Thumbnail": cells[0].find("img")['src'] if cells[0].find("img") else "N/A",
                            "Make": cells[1].get_text(strip=True),
                            "Model": cells[2].get_text(strip=True),
                            "Year": cells[3].get_text(strip=True),
                            "Body Style": cells[4].get_text(strip=True),
                            "Engine": cells[5].get_text(strip=True),
                            "Yard Row": cells[6].get_text(strip=True),
                            "Date Set": cells[7].get_text(strip=True)
                        }
                        all_cars_data.append(car_data)
    return all_cars_data

def get_car_unique_key(car):
    return f"{car['Make']}-{car['Model']}-{car['Year']}-{car['Yard Row']}"

def compute_car_diff_struct(previous_cars, current_cars):
    """Compares lists and returns a structured dictionary of changes instead of flat text."""
    previous_map = {get_car_unique_key(car): car for car in previous_cars}
    current_map = {get_car_unique_key(car): car for car in current_cars}

    added_cars = []
    removed_cars = []
    modified_cars = []

    for key, current_car in current_map.items():
        if key not in previous_map:
            added_cars.append(current_car)
        else:
            previous_car = previous_map[key]
            diff_fields = {}
            for field, value in current_car.items():
                if field not in ['Make', 'Model', 'Year', 'Yard Row', 'Thumbnail'] and previous_car.get(field) != value:
                    diff_fields[field] = {"from": previous_car.get(field), "to": value}
            if diff_fields:
                modified_cars.append({"car": current_car, "changes": diff_fields})

    for key, previous_car in previous_map.items():
        if key not in current_map:
            removed_cars.append(previous_car)

    return {
        "added": added_cars,
        "removed": removed_cars,
        "modified": modified_cars
    }

def build_discord_messages(diff_struct):
    """Formats structured changes into a list of messages under 2000 characters."""
    messages = []
    current_message = f"**Inventory Change Report ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')})**\n"
    
    def add_line(line):
        nonlocal current_message, messages
        if len(current_message) + len(line) + 1 > 1950:
            messages.append(current_message)
            current_message = ""
        current_message += line + "\n"

    if diff_struct["added"]:
        add_line(f"\n**[+] Added Cars ({len(diff_struct['added'])}):**")
        for car in diff_struct["added"]:
            add_line(f"• {car['Make']} {car['Model']} {car['Year']} (Row: {car['Yard Row']}, Set: {car['Date Set']})")

    if diff_struct["removed"]:
        add_line(f"\n**[-] Removed Cars ({len(diff_struct['removed'])}):**")
        for car in diff_struct["removed"]:
            add_line(f"• {car['Make']} {car['Model']} {car['Year']} (Row: {car['Yard Row']}, Set: {car['Date Set']})")

    if diff_struct["modified"]:
        add_line(f"\n**[*] Modified Cars ({len(diff_struct['modified'])}):**")
        for item in diff_struct["modified"]:
            car = item["car"]
            add_line(f"• {car['Make']} {car['Model']} {car['Year']}:")
            for field, change in item["changes"].items():
                add_line(f"  - {field}: {change['from']} -> {change['to']}")

    if not (diff_struct["added"] or diff_struct["removed"] or diff_struct["modified"]):
        add_line("No changes detected in the inventory.")

    if current_message.strip():
        messages.append(current_message)

    return messages

if __name__ == "__main__":
    previous_cars_filepath = None
    if len(sys.argv) > 1:
        previous_cars_filepath = sys.argv[1]

    previous_cars = []
    if previous_cars_filepath and os.path.exists(previous_cars_filepath):
        try:
            with open(previous_cars_filepath, 'r') as f:
                previous_cars = json.load(f)
        except Exception as e:
            sys.stderr.write(f"[-] Error loading previous inventory: {e}\n")

    dynamic_nonce_value = get_dynamic_nonce(MAIN_SITE_URL, HEADERS)
    if not dynamic_nonce_value:
        sys.exit("[-] Error: Failed to retrieve dynamic nonce.")

    html = fetch_inventory_html(dynamic_nonce_value)
    if not html:
        sys.exit("[-] Error: Failed to fetch inventory HTML.")

    current_cars_data = scan_and_extract_inventory(html)
    
    diff_structure = compute_car_diff_struct(previous_cars, current_cars_data)
    discord_chunks = build_discord_messages(diff_structure)

    output = {
        "current_inventory": current_cars_data,
        "diff_report_chunks": discord_chunks
    }
    print(json.dumps(output))
