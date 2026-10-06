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
    sys.stderr.write(f"[*] Attempting GET request to: {main_site_url} to retrieve nonce.\n")
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
            sys.stderr.write(f"[*] Successfully extracted dynamic nonce: {dynamic_nonce}\n")
            return dynamic_nonce
        else:
            sys.stderr.write("[-] Could not find the dynamic nonce on the page.\n")
            return None
    except requests.RequestException as e:
        sys.stderr.write(f"[-] Network connection error while fetching nonce: {e}\n")
        return None

def fetch_inventory_html(dynamic_nonce):
    """Fetches the live inventory webpage using a POST request with form parameters."""
    sys.stderr.write(f"[*] Attempting POST request to: {AJAX_URL} with dynamic nonce.\n")

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
        sys.stderr.write(f"[-] Network connection error: {e}\n")
        return None

def scan_and_extract_inventory(html):
    """Parses the inventory table and extracts all car details into a list of dictionaries."""
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
                    elif cells:
                        sys.stderr.write(f"[!] Warning: Insufficient data columns for a row: {[cell.get_text(strip=True) for cell in cells]}\n")
                        pass
                sys.stderr.write(f"[_] Successfully extracted {len(all_cars_data)} car entries.\n")
            else:
                sys.stderr.write("[-] No <tr> elements found within the <tbody> of the inventory table.\n")
                pass
        else:
            sys.stderr.write("[-] No <tbody> found within the inventory table.\n")
            pass
    else:
        sys.stderr.write("[-] Could not find the inventory table with class 'yardconnect-vehicles-table'.\n")
        pass
    return all_cars_data

def sort_cars_by_date_set(cars):
    """Sorts a list of car dictionaries chronologically by 'Date Set'."""
    def get_sort_key(car):
        date_str = car.get("Date Set", "")
        try:
            # Try parsing with 2-digit year first, e.g., '09/25/26' -> %y
            return datetime.strptime(date_str, "%m/%d/%y")
        except ValueError:
            try:
                # Fallback for 4-digit year format '09/25/2026' -> %Y
                return datetime.strptime(date_str, "%m/%d/%Y")
            except ValueError:
                try:
                    # Fallback for alternative hyphenated 4-digit year format
                    return datetime.strptime(date_str, "%Y-%m-%d")
                except ValueError:
                    try:
                        # Fallback for alternative hyphenated 2-digit year format
                        return datetime.strptime(date_str, "%y-%m-%d")
                    except ValueError:
                        # Fallback if unparseable, return epoch start
                        return datetime.min

    return sorted(cars, key=get_sort_key)

def save_cars_to_json(cars_data, filename=CAR_DATA_FILE):
    """Saves a list of car dictionaries to a JSON file, sorted by Date Set."""
    sorted_data = sort_cars_by_date_set(cars_data)
    try:
        with open(filename, 'w') as f:
            json.dump(sorted_data, f, indent=4)
        sys.stderr.write(f"[_] Car data saved to {filename}\n")
    except IOError as e:
        sys.stderr.write(f"[-] Error saving car data to JSON: {e}\n")
        pass

def load_cars_from_json(filename=CAR_DATA_FILE):
    """Loads car data from a JSON file."""
    if os.path.exists(filename):
        try:
            with open(filename, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            sys.stderr.write(f"[-] Error decoding JSON from {filename}: {e}\n")
            pass
        except IOError as e:
            sys.stderr.write(f"[-] Error loading car data from JSON: {e}\n")
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
    """Generates a plain-text diff report string suitable for external formatting."""
    report_lines = []
    report_lines.append(f"REPORT_HEADER: Inventory Change Report ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')})")

    if added_cars:
        report_lines.append(f"ADDED_COUNT: {len(added_cars)}")
        for car in sort_cars_by_date_set(added_cars):
            report_lines.append(f"ADDED_ITEM: {car['Make']} {car['Model']} {car['Year']} | Date Set: {car['Date Set']}")

    if removed_cars:
        report_lines.append(f"REMOVED_COUNT: {len(removed_cars)}")
        for car in sort_cars_by_date_set(removed_cars):
            report_lines.append(f"REMOVED_ITEM: {car['Make']} {car['Model']} {car['Year']} | Date Set: {car['Date Set']}")

    if modified_cars:
        report_lines.append(f"MODIFIED_COUNT: {len(modified_cars)}")
        # Sort modified cars using the current vehicle's Date Set
        sorted_modified = sorted(modified_cars, key=lambda x: sort_cars_by_date_set([x['current']])[0].get('Date Set', ''))
        for change in sorted_modified:
            report_lines.append(f"MODIFIED_ITEM: {change['current']['Make']} {change['current']['Model']} {change['current']['Year']} | Date Set: {change['current']['Date Set']}")
            for field, current_value in change['current'].items():
                if field not in ['Make', 'Model', 'Year', 'Yard Row', 'Thumbnail', 'Date Set'] and change['previous'].get(field) != current_value:
                    report_lines.append(f"MODIFIED_DETAIL:   {field}: {change['previous'].get(field)} -> {current_value}")

    if not (added_cars or removed_cars or modified_cars):
        report_lines.append("NO_CHANGES: No changes detected in the inventory.")

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
            sys.stderr.write(f"[_] Loaded {len(previous_cars)} previous car entries from file: {previous_cars_filepath}.\n")
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
    current_cars = sort_cars_by_date_set(current_cars)

    if not previous_cars:
        diff_report_str = f"INITIAL_LOAD: No previous car data provided. Saving current {len(current_cars)} entries as initial dataset."
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
    sys.stderr.write("Script finished execution.\n")
