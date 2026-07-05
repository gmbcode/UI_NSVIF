import os

templates_dir = r"d:\ACADS\Main project UI\fresh start\UI_NSVIF\templates"
for filename in os.listdir(templates_dir):
    if filename.endswith(".html"):
        filepath = os.path.join(templates_dir, filename)
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Replace font-family
        new_content = content.replace("font-family: 'Inter', sans-serif;", "font-family: sans-serif;")
        new_content = new_content.replace('font-family: "Inter", sans-serif;', "font-family: sans-serif;")
        
        # Remove Google Fonts link
        link_str = '<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">'
        new_content = new_content.replace(link_str, "")
        
        if content != new_content:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(new_content)
            print(f"Updated {filename}")
