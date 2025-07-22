import os
import re

def get_ebooks():
    """Scans the ebooks directory and returns a list of epub files."""
    ebooks = []
    for filename in sorted(os.listdir('ebooks')):
        if filename.endswith('.epub'):
            ebooks.append(filename)
    return ebooks

def format_markdown_list(ebooks):
    """Formats the list of ebooks for README.md."""
    md_list = []
    for i, ebook in enumerate(ebooks):
        title = os.path.splitext(ebook)[0]
        md_list.append(f"{i+1}. **[{title}](./ebooks/{ebook})**")
    return '\n'.join(md_list)

def format_html_list(ebooks):
    """Formats the list of ebooks for index.html."""
    html_list = []
    for ebook in ebooks:
        title = os.path.splitext(ebook)[0]
        html_list.append(
            f"<li>\n" \
            f"    <strong><a href=\"./ebooks/{ebook}\">{title}</a></strong>\n" \
            f"</li>"
        )
    return '\n'.join(html_list)

def update_file(filepath, start_marker, end_marker, content):
    """Updates the content of a file between two markers."""
    with open(filepath, 'r', encoding='utf-8') as f:
        file_content = f.read()

    # A simpler, more robust way to build the regex pattern
    pattern = re.compile(
        re.escape(start_marker) + ".*?" + re.escape(end_marker),
        re.DOTALL
    )

    if pattern.search(file_content):
        new_content = pattern.sub(f"{start_marker}\n{content}\n{end_marker}", file_content)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"Successfully updated {filepath}")
    else:
        print(f"Could not find markers in {filepath}")

def main():
    """Main function to update the documentation files."""
    ebooks = get_ebooks()

    # Update README.md
    md_content = format_markdown_list(ebooks)
    update_file('README.md', '<!-- EBOOK_LIST_START -->', '<!-- EBOOK_LIST_END -->', md_content)

    # Update index.html
    html_content = format_html_list(ebooks)
    update_file('index.html', '<!-- EBOOK_LIST_START -->', '<!-- EBOOK_LIST_END -->', html_content)

if __name__ == '__main__':
    main()