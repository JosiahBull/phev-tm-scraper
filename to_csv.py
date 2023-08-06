import os
import json
import csv


def parse_json_file(json_file):
    with open(json_file, 'r') as file:
        data = json.load(file)

    def replace_unknown(value):
        return 'Unknown' if value == -1 else value

    title = data["listing"]["title"]
    id = data["listing"]["id"]
    description = data["scraped_listing"]["description"]
    make = data["scraped_listing"]["make"]
    model = data["scraped_listing"]["model"]
    year = replace_unknown(data["scraped_listing"]["year"])
    kilometers = replace_unknown(data["scraped_listing"]["kilometers"])
    import_history = replace_unknown(data["scraped_listing"]["import_history"])
    litres_per_100_km = replace_unknown(data["scraped_listing"]["litres_per_100_km"])

    return id, title, description, make, model, year, kilometers, import_history, litres_per_100_km


def save_to_csv(output_file, data):
    with open(output_file, 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(["Id", "Title", "Description", "Make", "Model", "Year", "Kilometers", "Import History", "Litres per 100km"])
        writer.writerows(data)


def find_and_parse_json_files(input_dir):
    data_list = []
    for root, _, files in os.walk(input_dir):
        for file in files:
            if file.endswith(".json"):
                json_file_path = os.path.join(root, file)
                data_list.append(parse_json_file(json_file_path))
    return data_list


if __name__ == "__main__":
    input_directory = "./listings"
    output_csv_file = "output.csv"

    parsed_data = find_and_parse_json_files(input_directory)
    save_to_csv(output_csv_file, parsed_data)
    print("CSV file saved successfully.")
