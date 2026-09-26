import sys
import requests
from bs4 import BeautifulSoup
import json
import re
import os
from datetime import datetime

# ==================== CONFIGURATION ====================
# Updated URL to the AJAX endpoint
URL = "https://rupertsupullit.com/wp-admin/admin-ajax.php"

# Define the path for the JSON file to store car data
CAR_DATA_FILE = 'car_inventory.json'

# Define the path for the diff report output file
DIFF_OUTPUT_FILE = 'diff_report.txt'

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}
# =======================================================

def fetch_inventory_html():
    """Fetches the live inventory webpage using a POST request with form parameters."""
    print(f"[*] Attempting POST request to: {URL}") # For debugging

    # Form data provided by the user
    form_data = {
        'make': '',
        'model': '',
        'year_start': '1963',
        'year_end': '2026',
        'action': 'yardconnect_search_vehicles',
        'nonce': 'eb3bd746d7', # Note: nonce might be dynamic and require dynamic extraction if this fails in the future.
        'view': 'table',
        'length': '1000' # Request a large number of entries to ensure all are fetched
    }

    try:
        # Use a POST request with the form data
        response = requests.post(URL, headers=HEADERS, data=form_data, timeout=15)
        response.raise_for_status()
        return response.text
    except requests.RequestException as e:
        print(f"[-] Network connection error: {e}")
        return None

def scan_and_extract_inventory(html):
    """Parses the inventory table and extracts all car details into a list of dictionaries."""
    soup = BeautifulSoup(html, "html.parser")
    all_cars_data = []

    inventory_table = soup.find("table", class_="yardconnect-vehicles-table")

    if inventory_table:
        print("[*] Found the inventory table. Extracting all car data...")
        tbody = inventory_table.find("tbody")
        if tbody:
            rows = tbody.find_all("tr")
            if rows:
                print(f"[*] Found {len(rows)} car entries in total.")
                for row in rows:
                    cells = row.find_all("td")
                    if cells and len(cells) >= 8: # Ensure enough cells are present
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
                    elif cells:
                        print(f"[!] Warning: Insufficient data columns for a row: {[cell.get_text(strip=True) for cell in cells]}")
                print(f"[*] Successfully extracted {len(all_cars_data)} car entries.")
            else:
                print("[-] No <tr> elements found within the <tbody> of the inventory table.")
        else:
            print("[-] No <tbody> found within the inventory table.")
    else:
        print("[-] Could not find the inventory table with class 'yardconnect-vehicles-table'.")
        print("[*] This might indicate a change in the website structure. Printing full HTML response for inspection (truncated):")
        print("-" * 75)
        print(html[:1000]) # Print first 1000 chars for inspection
        print("-" * 75)
    return all_cars_data

def save_cars_to_json(cars_data, filename=CAR_DATA_FILE):
    """Saves a list of car dictionaries to a JSON file."""
    try:
        with open(filename, 'w') as f:
            json.dump(cars_data, f, indent=4)
        print(f"[*] Car data saved to {filename}")
    except IOError as e:
        print(f"[-] Error saving car data to JSON: {e}")

def load_cars_from_json(filename=CAR_DATA_FILE):
    """Loads car data from a JSON file."""
    if os.path.exists(filename):
        try:
            with open(filename, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            print(f"[-] Error decoding JSON from {filename}: {e}")
        except IOError as e:
            print(f"[-] Error loading car data from JSON: {e}")
    return []

def get_car_unique_key(car):
    """Generates a unique key for a car based on stable attributes."""
    return f"{car['Make']}-{car['Model']}-{car['Year']}-{car['Yard Row']}"

def compute_car_diff(previous_cars, current_cars):
    """Compares two lists of car dictionaries and returns added, removed, and modified cars."""
    previous_map = {get_car_unique_key(car): car for car in previous_cars}
    current_map = {get_car_unique_key(car): car for car in current_cars}

    added_cars = []
    removed_cars = []
    modified_cars = []

    # Check for added and modified cars
    for key, current_car in current_map.items():
        if key not in previous_map:
            added_cars.append(current_car)
        else:
            previous_car = previous_map[key]
            # Compare relevant fields to detect modifications
            diff_found = False
            for field, value in current_car.items():
                # Exclude thumbnail from diff comparison as its URL might change for same car
                if field not in ['Make', 'Model', 'Year', 'Yard Row', 'Thumbnail'] and previous_car.get(field) != value:
                    diff_found = True
                    break
            if diff_found:
                modified_cars.append({'previous': previous_car, 'current': current_car})

    # Check for removed cars
    for key, previous_car in previous_map.items():
        if key not in current_map:
            removed_cars.append(previous_car)

    return added_cars, removed_cars, modified_cars

def generate_diff_report(added_cars, removed_cars, modified_cars):
    """Generates a human-readable diff report string."""
    report_lines = []
    report_lines.append(f"--- Inventory Change Report ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')}) ---")

    if added_cars:
        report_lines.append(f"\n[*] {len(added_cars)} new cars added:")
        for car in added_cars:
            report_lines.append(f"    + {car['Make']} {car['Model']} {car['Year']} ({car['Yard Row']})")
    
    if removed_cars:
        report_lines.append(f"\n[*] {len(removed_cars)} cars removed:")
        for car in removed_cars:
            report_lines.append(f"    - {car['Make']} {car['Model']} {car['Year']} ({car['Yard Row']})")
            
    if modified_cars:
        report_lines.append(f"\n[*] {len(modified_cars)} cars modified:")
        for change in modified_cars:
            report_lines.append(f"    ~ {change['current']['Make']} {change['current']['Model']} {change['current']['Year']} ({change['current']['Yard Row']})")
            for field, current_value in change['current'].items():
                if field not in ['Make', 'Model', 'Year', 'Yard Row', 'Thumbnail'] and change['previous'].get(field) != current_value:
                    report_lines.append(f"        - {field}: {change['previous'].get(field)}")
                    report_lines.append(f"        + {field}: {current_value}")
                elif field == 'Thumbnail' and change['previous'].get(field) != current_value:
                    report_lines.append(f"        ~ Thumbnail URL changed from {change['previous'].get(field)} to {current_value}")

    if not (added_cars or removed_cars or modified_cars):
        report_lines.append("\n[*] No changes detected in the inventory.")
    
    report_lines.append("------------------------------------------")
    return "\n".join(report_lines)

def save_diff_report(report_content, filename=DIFF_OUTPUT_FILE):
    """Saves the diff report content to a text file."""
    try:
        with open(filename, 'w') as f:
            f.write(report_content)
        print(f"[*] Diff report saved to {filename}")
    except IOError as e:
        print(f"[-] Error saving diff report: {e}")

def main():
    html = fetch_inventory_html()
    if not html:
        sys.exit(1)

    current_cars = scan_and_extract_inventory(html)

    # Load previous data to compare
    previous_cars = load_cars_from_json()

    diff_report = {
        'added': [],
        'removed': [],
        'modified': []
    }

    if not previous_cars:
        print(f"\n[*] No previous car data found. Saving current {len(current_cars)} entries as initial dataset.")
        save_cars_to_json(current_cars)
        # No diff report to generate on the first run
        with open(DIFF_OUTPUT_FILE, 'w') as f:
            f.write("Initial inventory saved. No diff to report.")
        print(f"[*] Initial diff report (no changes) saved to {DIFF_OUTPUT_FILE}")
    else:
        print(f"\n[*] Loaded {len(previous_cars)} previous car entries.")
        added, removed, modified = compute_car_diff(previous_cars, current_cars)
        diff_report = {
            'added': added,
            'removed': removed,
            'modified': modified
        }

        # Generate and save the diff report to a file
        report_content = generate_diff_report(added, removed, modified)
        print(report_content)
        save_diff_report(report_content)

        # After computing and displaying the diff, save the current data for the next run
        save_cars_to_json(current_cars)
        print("[*] Current car data updated for subsequent diff calculation.")

if __name__ == "__main__":
    main()
