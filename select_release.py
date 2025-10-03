import os
import sys
import datetime
from collections import defaultdict

def parse_date(date_str):
    """Parse a date string in the format YYYY-MM-DD."""
    return datetime.datetime.strptime(date_str, "%Y-%m-%d")

def select_releases_nearest_6_months(release_file):
    """Select the nearest release every 6 months from the most recent date, working backward."""
    releases = []

    # Read the release file
    with open(release_file, "r") as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) != 2:
                continue
            release_id, release_date = parts
            release_date_parsed = parse_date(release_date)

            # Filter releases from 2017-09 to the current date
            if release_date_parsed >= parse_date("2017-09-01"):
                releases.append((release_id, release_date_parsed))


    # Select releases every 6 months
    selected_releases = []
    last_selected_date = None

    for release_id, release_date in releases:
        if last_selected_date is None or (last_selected_date - release_date).days >= 180:
            selected_releases.append((release_id, release_date))
            last_selected_date = release_date


    return selected_releases

def main():
    release_folder = "releases"
    output_folder = "selected_releases"
    os.makedirs(output_folder, exist_ok=True)
    # Optional first argument: a single project name to process
    project_arg = sys.argv[1] if len(sys.argv) > 1 else None

    if project_arg:
        file_name = f"{project_arg}.txt"
        release_file = os.path.join(release_folder, file_name)
        if not os.path.isfile(release_file):
            print(f"⚠️  Release file not found for project '{project_arg}': {release_file}")
            return

        output_file = os.path.join(output_folder, f"select_{project_arg}.txt")
        selected_releases = select_releases_nearest_6_months(release_file)
        with open(output_file, "w") as f:
            for release_id, release_date in selected_releases:
                f.write(f"{release_id} {release_date.strftime('%Y-%m-%d')}\n")
        print(f"Selected releases saved to {output_file}")
        return

    # Process each release file
    for file_name in os.listdir(release_folder):
        if not file_name.endswith(".txt"):
            continue

        project_name = file_name.split(".")[0]
        release_file = os.path.join(release_folder, file_name)
        output_file = os.path.join(output_folder, f"select_{project_name}.txt")

        selected_releases = select_releases_nearest_6_months(release_file)

        # Write the selected releases to the output file
        with open(output_file, "w") as f:
            for release_id, release_date in selected_releases:
                f.write(f"{release_id} {release_date.strftime('%Y-%m-%d')}\n")

        print(f"Selected releases saved to {output_file}")

if __name__ == "__main__":
    main()
