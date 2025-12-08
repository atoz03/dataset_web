import os
import argparse
from collections import defaultdict

def count_images(root_dir):
    """
    Recursively counts the number of files in each subdirectory of a given directory.

    Args:
        root_dir (str): The path to the root directory to scan.

    Returns:
        defaultdict: A dictionary mapping class (subdirectory) to its file count.
    """
    class_counts = defaultdict(int)
    print(f"Scanning directory: {root_dir}")
    if not os.path.isdir(root_dir):
        print(f"Error: Directory not found at {root_dir}")
        return class_counts

    for class_name in sorted(os.listdir(root_dir)):
        class_path = os.path.join(root_dir, class_name)
        if os.path.isdir(class_path):
            # Walk through the directory and count files
            file_count = 0
            for _, _, files in os.walk(class_path):
                # Filter out hidden files like .DS_Store
                file_count += len([f for f in files if not f.startswith('.')])
            class_counts[class_name] = file_count
    return class_counts

def print_report(title, class_counts):
    """
    Prints a formatted report of class counts.

    Args:
        title (str): The title for the report section.
        class_counts (defaultdict): The dictionary of class counts.
    """
    print("\n" + "="*50)
    print(f"{title.upper()} IMAGE COUNT REPORT")
    print("="*50)
    if not class_counts:
        print("No subdirectories found or directory is empty.")
        return

    # Sort by count, ascending
    sorted_counts = sorted(class_counts.items(), key=lambda item: item[1])

    for class_name, count in sorted_counts:
        print(f"- {class_name}: {count}")
    print("="*50)
    print(f"Total classes: {len(class_counts)}")
    print(f"Total images: {sum(class_counts.values())}")
    print("="*50 + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Count images in each class (subdirectory) for specified root directories."
    )
    parser.add_argument(
        "--roots",
        nargs='+',
        required=True,
        help="One or more root directories to scan (e.g., datasets/crops datasets/pests)."
    )

    args = parser.parse_args()

    for root in args.roots:
        counts = count_images(root)
        print_report(f"'{root}'", counts)