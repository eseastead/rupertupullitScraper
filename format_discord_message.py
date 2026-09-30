import sys
import os
import re
import json # Import json for json.dumps

def format_discord_message(diff_report_raw):
    formatted_lines = []
    changes_detected = False

    # Process header
    header = ''
    for line in diff_report_raw.splitlines():
        if line.startswith('REPORT_HEADER:'):
            header = line.replace('REPORT_HEADER: ', '', 1)
            formatted_lines.append(f"### {header}")
            break

    added_items = []
    removed_items = []
    modified_items = []
    modified_details = {}

    added_count = 0
    removed_count = 0
    modified_count = 0
    no_changes_msg = ""
    initial_load_msg = ""

    current_modified_item_key = None

    for line in diff_report_raw.splitlines():
        if line.startswith('ADDED_COUNT:'):
            added_count = int(line.replace('ADDED_COUNT: ', '', 1))
        elif line.startswith('ADDED_ITEM:'):
            added_items.append(line.replace('ADDED_ITEM: ', '', 1))
        elif line.startswith('REMOVED_COUNT:'):
            removed_count = int(line.replace('REMOVED_COUNT: ', '', 1))
        elif line.startswith('REMOVED_ITEM:'):
            removed_items.append(line.replace('REMOVED_ITEM: ', '', 1))
        elif line.startswith('MODIFIED_COUNT:'):
            modified_count = int(line.replace('MODIFIED_COUNT: ', '', 1))
        elif line.startswith('MODIFIED_ITEM:'):
            item_key = line.replace('MODIFIED_ITEM: ', '', 1)
            modified_items.append(item_key)
            modified_details[item_key] = []
            current_modified_item_key = item_key # Set current item for details
        elif line.startswith('MODIFIED_DETAIL:'):
            if current_modified_item_key:
                detail_line = line.replace('MODIFIED_DETAIL:   ', '', 1)
                match = re.match(r'([^:]+): (.+) -> (.+)', detail_line)
                if match:
                    field, old_val, new_val = match.groups()
                    modified_details[current_modified_item_key].append(f"  - *{field}*: Changed from `{old_val}` to `{new_val}`")
                else:
                    modified_details[current_modified_item_key].append(f"  - {detail_line}") # Fallback
        elif line.startswith('NO_CHANGES:'):
            no_changes_msg = line.replace('NO_CHANGES: ', '', 1)
        elif line.startswith('INITIAL_LOAD:'):
            initial_load_msg = line.replace('INITIAL_LOAD: ', '', 1)

    if added_count > 0:
        formatted_lines.append("")
        formatted_lines.append(f"**New Cars Added: {added_count}**")
        changes_detected = True
        for item in added_items:
            formatted_lines.append(f"- **+** {item}")

    if removed_count > 0:
        formatted_lines.append("")
        formatted_lines.append(f"**Cars Removed: {removed_count}**")
        changes_detected = True
        for item in removed_items:
            formatted_lines.append(f"- **-** {item}")

    if modified_count > 0:
        formatted_lines.append("")
        formatted_lines.append(f"**Cars Modified: {modified_count}**")
        changes_detected = True
        for item_key in modified_items:
            formatted_lines.append(f"- **~** {item_key}")
            for detail in modified_details.get(item_key, []):
                formatted_lines.append(detail)

    if no_changes_msg:
        formatted_lines.append("")
        formatted_lines.append(f"*{no_changes_msg}*")

    if initial_load_msg:
        formatted_lines.append("")
        formatted_lines.append("### Initial Inventory Load")
        formatted_lines.append(f"* {initial_load_msg}")

    discord_message_content = "\n".join(formatted_lines)

    # JSON-escape the message content for safe passing through GITHUB_OUTPUT
    json_safe_discord_message_content = json.dumps(discord_message_content)

    # Output as a single line to GITHUB_OUTPUT
    print(f"discord_message_content={json_safe_discord_message_content}")
    print(f"changes_detected={'true' if changes_detected else 'false'}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.stderr.write("Usage: python format_discord_message.py <diff_report_filepath>\n")
        sys.exit(1)

    diff_report_filepath = sys.argv[1]
    if not os.path.exists(diff_report_filepath):
        sys.stderr.write(f"Error: Diff report file not found at {diff_report_filepath}\n")
        sys.exit(1)

    with open(diff_report_filepath, 'r') as f:
        diff_report_content = f.read()

    format_discord_message(diff_report_content)
