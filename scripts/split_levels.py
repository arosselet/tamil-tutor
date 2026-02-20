import json
import os

def split_levels():
    source_file = "curriculum/levels.json"
    output_dir = "curriculum/levels"
    index_file = "curriculum/index.json"

    if not os.path.exists(source_file):
        print(f"Error: {source_file} not found")
        return

    try:
        with open(source_file, "r") as f:
            levels = json.load(f)
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON: {e}")
        return

    index_data = {}

    for level_key, level_data in levels.items():
        # Ensure level key is numeric for sorting, but handle string keys in JSON
        try:
            level_num = int(level_key)
        except ValueError:
            print(f"Skipping invalid key: {level_key}")
            continue

        filename = f"level_{level_num:02d}.json"
        file_path = os.path.join(output_dir, filename)

        # Write individual level file
        with open(file_path, "w") as f:
            json.dump(level_data, f, indent=2, ensure_ascii=False)
        
        print(f"Created {file_path}")

        # Add to index (minimal data)
        index_data[level_key] = {
            "title": level_data.get("title", "Unknown"),
            "tier": level_data.get("tier", 1),
            "description": level_data.get("description", ""),
            "file": filename
        }

    # Write index file
    with open(index_file, "w") as f:
        json.dump(index_data, f, indent=2, ensure_ascii=False)
    
    print(f"Created {index_file} with {len(index_data)} entries")

if __name__ == "__main__":
    split_levels()
