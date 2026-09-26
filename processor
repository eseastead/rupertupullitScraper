#gemini basically did all this for me

import sys
import requests
from bs4 import BeautifulSoup
import json
import re
import os
from datetime import datetime # Added for date parsing

# For UI components
from IPython.display import display, HTML
import ipywidgets as widgets
from ipywidgets import Layout, Box, VBox, HBox, Button

# ==================== CONFIGURATION ====================
# Updated URL to the AJAX endpoint
URL = "https://rupertsupullit.com/wp-admin/admin-ajax.php"

# Define the path for the JSON file to store car data
CAR_DATA_FILE = 'car_inventory.json'

# Default filtering is set to None (Prints ALL cars in the yard).
# Un-comment or add string values inside the brackets to restrict results.

# Column 1 Examples: ["Toyota", "Mazda", "Volkswagen", "Lexus", "Honda"]
TARGET_MAKES = None

# Column 2 Examples: ["Sienna", "Mazda6", "Jetta", "Camry", "Civic"]
TARGET_MODELS = None

# Column 3 Examples: Min=2000, Max=2010 (Uses integers for ranges)
MIN_YEAR = None
MAX_YEAR = None

# Column 4 Examples: ["Minivan", "Sedan", "SUV", "Truck", "Coupe"]
TARGET_BODY_STYLES = None

# Column 5 Examples: ["3.3L 6cyl", "2.3L 4cyl", "1.4L 4cyl", "V6"]
TARGET_ENGINES = None

# Column 6 Examples: ["Import 10 K", "Import 10 L", "Import 10 J", "Row 15"]
TARGET_YARD_ROWS = None

# Column 7 Examples: ["09/23/26", "09/24/26"]
TARGET_DATES = None

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
        'nonce': 'eb3bd746d7', # Note: nonce might be dynamic and require dynamic extraction if this fails.
        'view': 'table',
        'length': '1000' # Request a large number of entries to ensure all are fetched if possible
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


def get_unique_values(cars_data, column_name):
    """Extracts unique values for a given column from a list of car dictionaries."""
    return sorted(list(set(car[column_name] for car in cars_data if car.get(column_name))))

def create_car_table_html(cars):
    """Generates an HTML table for a list of car dictionaries, including image display."""
    if not cars:
        return "<p>No cars to display.</p>"

    # Start HTML table
    html_table = """
    <style>
        table { width: 100%; border-collapse: collapse; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; vertical-align: middle; }
        th { background-color: #f2f2f2; }
        img { max-width: 100px; height: auto; display: block; margin: auto; }
    </style>
    <table>
        <thead>
            <tr>
                <th>Thumbnail</th>
                <th>Make</th>
                <th>Model</th>
                <th>Year</th>
                <th>Body Style</th>
                <th>Engine</th>
                <th>Yard Row</th>
                <th>Date Set</th>
            </tr>
        </thead>
        <tbody>
    """

    for car in cars:
        thumbnail_html = f"<img src=\"{car['Thumbnail']}\" alt=\"Thumbnail\">" if car['Thumbnail'] and car['Thumbnail'] != 'N/A' else 'N/A'
        html_table += f"""
            <tr>
                <td>{thumbnail_html}</td>
                <td>{car.get('Make', 'N/A')}</td>
                <td>{car.get('Model', 'N/A')}</td>
                <td>{car.get('Year', 'N/A')}</td>
                <td>{car.get('Body Style', 'N/A')}</td>
                <td>{car.get('Engine', 'N/A')}</td>
                <td>{car.get('Yard Row', 'N/A')}</td>
                <td>{car.get('Date Set', 'N/A')}</td>
            </tr>
        """
    html_table += """
        </tbody>
    </table>
    """
    return html_table

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
    else:
        print(f"\n[*] Loaded {len(previous_cars)} previous car entries.")
        added, removed, modified = compute_car_diff(previous_cars, current_cars)
        diff_report = {
            'added': added,
            'removed': removed,
            'modified': modified
        }

        print("\n--- Inventory Change Report ---")
        if added:
            print(f"[*] {len(added)} new cars added:")
            for car in added:
                print(f"    + {car['Make']} {car['Model']} {car['Year']} ({car['Yard Row']})")
        if removed:
            print(f"[*] {len(removed)} cars removed:")
            for car in removed:
                print(f"    - {car['Make']} {car['Model']} {car['Year']} ({car['Yard Row']})")
        if modified:
            print(f"[*] {len(modified)} cars modified:")
            for change in modified:
                print(f"    ~ {change['current']['Make']} {change['current']['Model']} {change['current']['Year']} ({change['current']['Yard Row']})")
                for field, current_value in change['current'].items():
                    if field not in ['Make', 'Model', 'Year', 'Yard Row', 'Thumbnail'] and change['previous'].get(field) != current_value:
                        print(f"        - {field}: {change['previous'].get(field)}")
                        print(f"        + {field}: {current_value}")
        if not (added or removed or modified):
            print("[*] No changes detected in the inventory.")
        print("-------------------------------")

        # After computing and displaying the diff, save the current data for the next run
        save_cars_to_json(current_cars)
        print("[*] Current car data updated for subsequent diff calculation.")

    # --- UI Setup ---
    all_available_cars = previous_cars + current_cars # Union of all cars ever seen for filter options
    all_available_cars_map = {get_car_unique_key(car): car for car in all_available_cars}
    all_available_cars = list(all_available_cars_map.values())

    # Get unique values for dropdowns from the union of all cars
    makes = ['All'] + get_unique_values(all_available_cars, 'Make')
    models = ['All'] + get_unique_values(all_available_cars, 'Model')
    body_styles = ['All'] + get_unique_values(all_available_cars, 'Body Style')
    engines = ['All'] + get_unique_values(all_available_cars, 'Engine')
    yard_rows = ['All'] + get_unique_values(all_available_cars, 'Yard Row')
    years = ['All'] + get_unique_values(all_available_cars, 'Year')

    # Widgets for filters
    make_dropdown = widgets.Dropdown(options=makes, description='Make:', layout=Layout(width='auto'))
    model_dropdown = widgets.Dropdown(options=models, description='Model:', layout=Layout(width='auto'))
    year_dropdown = widgets.Dropdown(options=years, description='Year:', layout=Layout(width='auto'))
    body_style_dropdown = widgets.Dropdown(options=body_styles, description='Body Style:', layout=Layout(width='auto'))
    engine_dropdown = widgets.Dropdown(options=engines, description='Engine:', layout=Layout(width='auto'))
    yard_row_dropdown = widgets.Dropdown(options=yard_rows, description='Yard Row:', layout=Layout(width='auto'))

    # Output widgets for displaying results and diff
    car_display_output = widgets.Output()
    diff_output = widgets.Output()

    # Function to apply filters and update display
    def update_display(change):
        with car_display_output:
            car_display_output.clear_output()
            filtered_cars = []
            for car in current_cars:
                match_make = (make_dropdown.value == 'All' or car.get('Make') == make_dropdown.value)
                match_model = (model_dropdown.value == 'All' or car.get('Model') == model_dropdown.value)
                match_year = (year_dropdown.value == 'All' or car.get('Year') == year_dropdown.value)
                match_body_style = (body_style_dropdown.value == 'All' or car.get('Body Style') == body_style_dropdown.value)
                match_engine = (engine_dropdown.value == 'All' or car.get('Engine') == engine_dropdown.value)
                match_yard_row = (yard_row_dropdown.value == 'All' or car.get('Yard Row') == yard_row_dropdown.value)

                if all([match_make, match_model, match_year, match_body_style, match_engine, match_yard_row]):
                    filtered_cars.append(car)

            # Sort filtered_cars by 'Date Set' in descending order
            def get_sort_key(car):
                date_str = car.get('Date Set')
                if date_str and date_str != 'N/A':
                    try:
                        # Assuming date format is MM/DD/YY
                        return datetime.strptime(date_str, '%m/%d/%y')
                    except ValueError:
                        return datetime.min # Malformed dates at the end
                return datetime.min # N/A or missing dates at the end

            filtered_cars.sort(key=get_sort_key, reverse=True)
            
            display(HTML(f"<h3>Filtered Cars ({len(filtered_cars)} of {len(current_cars)}):</h3>"))
            display(HTML(create_car_table_html(filtered_cars)))

        with diff_output:
            diff_output.clear_output()
            display(HTML("<h3>Inventory Change Report:</h3>"))
            if diff_report['added'] or diff_report['removed'] or diff_report['modified']:
                if diff_report['added']:
                    display(HTML(f"<h4>Added Cars ({len(diff_report['added'])}):</h4>"))
                    display(HTML(create_car_table_html(diff_report['added'])))
                if diff_report['removed']:
                    display(HTML(f"<h4>Removed Cars ({len(diff_report['removed'])}):</h4>"))
                    display(HTML(create_car_table_html(diff_report['removed'])))
                if diff_report['modified']:
                    display(HTML(f"<h4>Modified Cars ({len(diff_report['modified'])}):</h4>"))
                    modified_html = """
                    <style>
                        .modified-prev { background-color: #ffe0e0; }
                        .modified-current { background-color: #e0ffe0; }
                    </style>
                    """
                    for change in diff_report['modified']:
                        modified_html += f"<p><b>{change['current']['Make']} {change['current']['Model']} {change['current']['Year']} ({change['current']['Yard Row']})</b></p>"
                        modified_html += "<table>"
                        for field, current_value in change['current'].items():
                            previous_value = change['previous'].get(field)
                            if field not in ['Make', 'Model', 'Year', 'Yard Row'] and previous_value != current_value:
                                modified_html += f"<tr><td>{field}:</td><td class='modified-prev'>{previous_value}</td><td class='modified-current'>{current_value}</td></tr>"
                            elif field == 'Thumbnail': # Always show current thumbnail
                                current_thumbnail_html = f"<img src=\"{current_value}\" alt=\"Current Thumbnail\">" if current_value and current_value != 'N/A' else 'N/A'
                                previous_thumbnail_html = f"<img src=\"{previous_value}\" alt=\"Previous Thumbnail\">" if previous_value and previous_value != 'N/A' else 'N/A'
                                if previous_value != current_value:
                                    modified_html += f"<tr><td>{field}:</td><td class='modified-prev'>{previous_thumbnail_html}</td><td class='modified-current'>{current_thumbnail_html}</td></tr>"
                                else:
                                     modified_html += f"<tr><td>{field}:</td><td colspan='2'>{current_thumbnail_html}</td></tr>"
                            else:
                                modified_html += f"<tr><td>{field}:</td><td colspan='2'>{current_value}</td></tr>"
                        modified_html += "</table><br>"
                    display(HTML(modified_html))
            else:
                display(HTML("<p>No changes detected in the inventory.</p>"))

    # Register callbacks
    make_dropdown.observe(update_display, names='value')
    model_dropdown.observe(update_display, names='value')
    year_dropdown.observe(update_display, names='value')
    body_style_dropdown.observe(update_display, names='value')
    engine_dropdown.observe(update_display, names='value')
    yard_row_dropdown.observe(update_display, names='value')

    # Initial display update
    update_display(None)

    # Arrange widgets
    filter_widgets = HBox([make_dropdown, model_dropdown, year_dropdown, body_style_dropdown, engine_dropdown, yard_row_dropdown])
    
    # Use a tabbed interface for car list and diff report
    tab_children = [car_display_output, diff_output]
    tab = widgets.Tab(children=tab_children)
    tab.set_title(0, 'Current Inventory')
    tab.set_title(1, 'Diff Report')

    display(VBox([filter_widgets, tab]))

if __name__ == "__main__":
    main()
