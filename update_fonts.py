"""
Font Updater Script.

This script iterates through HTML templates in a specific directory
and replaces instances of 'Inter' font configurations with standard
'sans-serif'. It also removes external Google Fonts links.
"""

import os


def update_fonts_in_templates(templates_dir: str) -> None:
    """
    Update font configurations in all HTML files within the given directory.

    Args:
        templates_dir (str): The absolute or relative path to the directory
                             containing HTML template files.
    """
    for filename in os.listdir(templates_dir):
        if filename.endswith(".html"):
            filepath: str = os.path.join(templates_dir, filename)
            with open(filepath, "r", encoding="utf-8") as f:
                content: str = f.read()

            # Replace font-family
            new_content: str = content.replace(
                "font-family: 'Inter', sans-serif;", "font-family: sans-serif;"
            )
            new_content = new_content.replace(
                'font-family: "Inter", sans-serif;', "font-family: sans-serif;"
            )

            # Remove Google Fonts link
            link_str: str = (
                '<link href="https://fonts.googleapis.com/css2?'
                'family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">'
            )
            new_content = new_content.replace(link_str, "")

            if content != new_content:
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(new_content)
                print(f"Updated {filename}")


if __name__ == "__main__":
    TEMPLATES_DIR: str = r"d:\ACADS\Main project UI\fresh start\UI_NSVIF\templates"
    update_fonts_in_templates(TEMPLATES_DIR)
