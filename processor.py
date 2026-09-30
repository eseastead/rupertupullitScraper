import sys
import requests
from bs4 import BeautifulSoup
import json
import re
import os
from datetime import datetime

# ==================== CONFIGURATION ====================
# Updated URLs for dynamic nonce retrieval and AJAX endpoint
MAIN_SITE_URL = "https://rupertsupullit.com/"
AJAX_URL = "https://rupertsupullit.com/wp-admin/admin-ajax.php"

# Define the path for the JSON file to store car data
CAR_DATA_FILE = 'car_inventory.json'

# Define the path for the diff report output file
DIFF_OUTPUT_FILE = 'diff_report.txt'

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}
# =======================================================

def get_dynamic_nonce(main_site_url, headers):
    """Fetches the main page and extracts the dynamic nonce using a robust search."""
    # print(f"[*] Attempting GET request to: {main_site_url} to retrieve nonce.")
    try:
        response = requests.get(main_site_url, headers=headers, timeout=15)
        response.raise_for_status()
        full_html = response.text

        # Use regex to find the nonce value, which was previously found in group 3 of the regex.
        # This pattern looks for '"nonce":"([a-f0-9]+)"' common in JS objects or AJAX data structures.
        nonce_pattern = re.compile(r'"nonce":"([a-f0-9]+)"')
        match = nonce_pattern.search(full_html)
        if match:
            dynamic_nonce = match.group(1)
            # print(f"[*] Successfully extracted dynamic nonce: {dynamic_nonce}")
            return dynamic_nonce
        else:
            # print("[-] Could not find the dynamic nonce on the page.")
            return None
    except requests.RequestException as e:
        # print(f"[-] Network connection error while fetching nonce: {e}")
        return None

def fetch_inventory_html(dynamic_nonce):
    """Fetches the live inventory webpage using a POST request with form parameters."""
    # print(f"[*] Attempting POST request to: {AJAX_URL} with dynamic nonce.")

    # Form data provided by the user
    form_data = {
        'make': '',
        'model': '',
        'year_start': '1963',
        'year_end': '2026',
        'action': 'yardconnect_search_vehicles',
        'nonce': dynamic_nonce, # Use the dynamically fetched nonce
        'view': 'table',
        'length': '1000' # Request a large number of entries to ensure all are fetched
    }

    try:
        # Use a POST request with the form data
        response = requests.post(AJAX_URL, headers=HEADERS, data=form_data, timeout=15)
        response.raise_for_status()
        return response.text
    except requests.RequestException as e:
        # print(f"[-] Network connection error: {e}")
        return None

def scan_and_extract_inventory(html):
    """Parses the inventory table and extracts all car details into a list of dictionaries."""
    soup = BeautifulSoup(html, "html.parser")
    all_cars_data = []

    inventory_table = soup.find("table", class_="yardconnect-vehicles-table")

    if inventory_table:
        # print("[*] Found the inventory table. Extracting all car data...")
        tbody = inventory_table.find("tbody")
        if tbody:
            rows = tbody.find_all("tr")
            if rows:
                # print(f"[*] Found {len(rows)} car entries in total.")
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
                    elif cells:
                        # print(f"[!] Warning: Insufficient data columns for a row: {[cell.get_text(strip=True) for cell in cells]}")
                        pass
                # print(f"[*] Successfully extracted {len(all_cars_data)} car entries.")
            else:
                # print("[-] No <tr> elements found within the <tbody> of the inventory table.")
                pass
        else:
            # print("[-] No <tbody> found within the inventory table.")
            pass
    else:
        # print("[-] Could not find the inventory table with class 'yardconnect-vehicles-table'.")
        pass
    return all_cars_data

def save_cars_to_json(cars_data, filename=CAR_DATA_FILE):
    """Saves a list of car dictionaries to a JSON file."""
    try:
        with open(filename, 'w') as f:
            json.dump(cars_data, f, indent=4)
        # print(f"[*] Car data saved to {filename}")
    except IOError as e:
        # print(f"[-] Error saving car data to JSON: {e}")
        pass

def load_cars_from_json(filename=CAR_DATA_FILE):
    """Loads car data from a JSON file."""
    if os.path.exists(filename):
        try:
            with open(filename, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            # print(f"[-] Error decoding JSON from {filename}: {e}")
            pass
        except IOError as e:
            # print(f"[-] Error loading car data from JSON: {e}")
            pass
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
            report_lines.append(f"    + {car['Make']} {car['Model']} {car['Year']} (Date Set: {car['Date Set']})") # Include Date Set for better identification

    if removed_cars:
        report_lines.append(f"\n[*] {len(removed_cars)} cars removed:")
        for car in removed_cars:
            report_lines.append(f"    - {car['Make']} {car['Model']} {car['Year']} (Date Set: {car['Date Set']})") # Include Date Set

    if modified_cars:
        report_lines.append(f"\n[*] {len(modified_cars)} cars modified:")
        for change in modified_cars:
            report_lines.append(f"    ~ {change['current']['Make']} {change['current']['Model']} {change['current']['Year']} (Date Set: {change['current']['Date Set']})") # Include Date Set
            for field, current_value in change['current'].items():
                if field not in ['Make', 'Model', 'Year', 'Yard Row', 'Thumbnail', 'Date Set'] and change['previous'].get(field) != current_value:
                    report_lines.append(f"        - {field}: {change['previous'].get(field)}")
                    report_lines.append(f"        + {field}: {current_value}")

    if not (added_cars or removed_cars or modified_cars):
        report_lines.append("\n[*] No changes detected in the inventory.")

    report_lines.append("------------------------------------------")
    return "\n".join(report_lines)

def process_inventory_update(previous_cars_filepath=None):
    """
    Fetches current car inventory, compares it with previous inventory,
    and returns the current inventory (list of dicts) and a diff report string.

    Args:
        previous_cars_filepath (str, optional): A file path to a JSON file representing the
                                                 previous car inventory. Defaults to None.

    Returns:
        tuple: A tuple containing:
               - current_cars (list): List of dictionaries for the current car inventory.
               - diff_report_str (str): A human-readable string summarizing the changes.
    """
    previous_cars = []
    if previous_cars_filepath and os.path.exists(previous_cars_filepath):
        try:
            with open(previous_cars_filepath, 'r') as f:
                previous_cars = json.load(f)
            # print(f"[*] Loaded {len(previous_cars)} previous car entries from file: {previous_cars_filepath}.")
        except (json.JSONDecodeError, IOError) as e:
            sys.stderr.write(f"[-] Error loading or decoding previous car data from {previous_cars_filepath}: {e}. Proceeding without previous data.\n")
    elif previous_cars_filepath: # Path was provided but file does not exist
        sys.stderr.write(f"[-] Previous inventory file not found at {previous_cars_filepath}. Proceeding without previous data.\n")

    dynamic_nonce_value = get_dynamic_nonce(MAIN_SITE_URL, HEADERS)
    if not dynamic_nonce_value:
        sys.stderr.write("[-] Error: Failed to retrieve dynamic nonce. Cannot fetch current inventory.\n")
        return previous_cars, "Error: Failed to retrieve dynamic nonce. Cannot fetch current inventory."

    html = fetch_inventory_html(dynamic_nonce_value)
    if not html:
        sys.stderr.write("[-] Error: Failed to fetch inventory HTML.\n")
        return previous_cars, "Error: Failed to fetch inventory HTML."

    current_cars = scan_and_extract_inventory(html)

    if not previous_cars:
        diff_report_str = f"[*] No previous car data provided. Saving current {len(current_cars)} entries as initial dataset."
    else:
        added, removed, modified = compute_car_diff(previous_cars, current_cars)
        diff_report_str = generate_diff_report(added, removed, modified)

    return current_cars, diff_report_str

# --- Command-line execution for GitHub Actions ---
if __name__ == "__main__":
    previous_cars_filepath_input = None
    # Check if a filepath for previous_cars is passed as a command-line argument
    if len(sys.argv) > 1:
        previous_cars_filepath_input = sys.argv[1]

    current_cars_data, diff_report_output = process_inventory_update(previous_cars_filepath_input)

    # Prepare output as a JSON object for easy parsing by GitHub Actions
    # This JSON object will be printed to stdout.
    output = {
        "current_inventory": current_cars_data,
        "diff_report": diff_report_output
    }
    print(json.dumps(output))
