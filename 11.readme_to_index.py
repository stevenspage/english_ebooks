#!/usr/bin/env python
"""Convert README.md to README.html and embed all CSS from styles/.

Usage: python md_to_html.py [input_md] [output_html]
Defaults: README.md -> README.html
Features:
 - convert local Markdown to HTML using a template matching the live site
 - embed local styles from styles/*.css into the head
 - option --use-live to fetch the live rendered HTML instead
"""
from pathlib import Path
import sys
import markdown
import argparse
import urllib.request
import urllib.error
import re


def collect_css(styles_dir: Path) -> str:
    css_texts = []
    if not styles_dir.exists():
        return ""
    for p in sorted(styles_dir.glob('**/*.css')):
        try:
            css_texts.append(p.read_text(encoding='utf-8'))
        except Exception:
            try:
                css_texts.append(p.read_text(encoding='latin-1'))
            except Exception:
                pass
    return "\n\n".join(css_texts)


# A template matching the live example site (head + basic styles).
# The converted markdown HTML will be inserted into the `{content}` placeholder.
TEMPLATE = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>英文电子书合集</title>
    <link rel="icon" type="image/png" href="favicon.png">
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif, "Apple Color Emoji", "Segoe UI Emoji";
            line-height: 1.6;
            color: #24292e;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f6f8;
        }
        h1, h2 {
            border-bottom: 1px solid #eaecef;
            padding-bottom: .3em;
        }
        a {
            color: #0366d6;
            text-decoration: none;
        }
        a:hover {
            text-decoration: underline;
        }
        blockquote {
            color: #6a737d;
            border-left: .25em solid #dfe2e5;
            padding: 0 1em;
            margin-left: 0;
        }
        ol {
            padding-left: 2em;
        }
        li {
            margin-bottom: 1.5em;
        }
        .center-div {
            text-align: center;
        }
        .badge-link {
            display: inline-block;
            text-decoration: none;
        }
        .badge {
            display: inline-block;
            padding: 0.5em 1em;
            font-size: .85em;
            font-weight: 600;
            line-height: 1;
            color: #fff;
            background-color: #0366d6;
            border-radius: 2em;
        }
        /* book review blockquote style */
        .book-review {
            color: #6a737d;
            border-left: .25em solid #dfe2e5;
            padding: 0 1em;
            margin-left: 0;
            background: rgba(255,255,255,0.6);
        }
    </style>
    {extra_styles}
</head>
<body>

{content}

</body>
</html>
'''


def convert(md_path: Path, out_path: Path, styles_dir: Path):
    md_text = md_path.read_text(encoding='utf-8')

    # Fix: lines like '    > quote' are treated as code blocks by some markdown parsers.
    # Unindent a single level of 4 spaces when it precedes a blockquote marker so the parser
    # will emit a real <blockquote> element.
    md_text = re.sub(r'(?m)^[ \t]{4}(>\s?)', r'\1', md_text)

    # Convert markdown to HTML using common extensions
    html_body = markdown.markdown(md_text, extensions=[
        'extra', 'admonition', 'codehilite', 'toc', 'tables'
    ], output_format='html5')

    # Post-process: add class to blockquotes for book-review styling
    # Convert <blockquote>...</blockquote> to <blockquote class="book-review">...</blockquote>
    html_body = re.sub(r'<blockquote(\s*)>', r'<blockquote class="book-review">', html_body)
    
    # Fix: Move standalone author bio blockquotes back into their parent list items
    # This handles the case where the second blockquote (author bio) gets parsed as a separate element
    def fix_author_bio_placement(html):
        # Pattern to match: </li></ol><blockquote class="book-review">...作者简介...
        pattern = r'</li>\s*</ol>\s*<blockquote class="book-review">\s*<p><strong>作者简介</strong>:(.*?)</p>\s*</blockquote>'
        
        def replace_func(match):
            author_bio = match.group(1).strip()
            return f'<blockquote class="book-review">\n<p><strong>作者简介</strong>:{author_bio}</p>\n</blockquote>\n</li>\n</ol>'
        
        return re.sub(pattern, replace_func, html, flags=re.DOTALL)
    
    html_body = fix_author_bio_placement(html_body)

    # 修改第一个链接的文本和图标为“🏛️ My Library”，并将链接指向 reader_index.html
    # 匹配第一个指向 stevenspage.github.io/english_ebooks/ 的链接
    first_link_pattern = r'(<a[^>]+href="https?://stevenspage\.github\.io/english_ebooks/"[^>]*>)([\s\S]*?)(</a>)'
    def replace_first_link(match):
        return match.group(1) + '🏛️ My Library' + match.group(3)
    html_body, n = re.subn(first_link_pattern, replace_first_link, html_body, count=1)
    # 将第一个链接的 href 指向 reader_index.html
    html_body = re.sub(r'(href="https?://stevenspage\.github\.io/english_ebooks/)"', r'\1reader_index.html"', html_body, count=1)
    
    # Normalize ebook links: convert absolute links pointing at the live repo
    # (https://stevenspage.github.io/english_ebooks/...) to relative paths
    # so the generated HTML works locally (e.g. reader.html?book=...)
    html_body = re.sub(
        r'href="https?://stevenspage\.github\.io/english_ebooks/([^"]*)"',
        r'href="\1"',
        html_body,
    )

    # Do not inject CSS from styles/ (these CSS files are not intended for this page)
    extra_styles = ''

    final = TEMPLATE.replace('{extra_styles}', extra_styles).replace('{content}', html_body)

    out_path.write_text(final, encoding='utf-8')
    print(f'Wrote: {out_path.resolve()}')


def main():
    parser = argparse.ArgumentParser(description='Convert README.md to README.html or fetch live example.')
    parser.add_argument('input', nargs='?', help='input markdown file (default README.md)')
    parser.add_argument('output', nargs='?', help='output html file (default README.html)')
    parser.add_argument('--use-live', '-l', dest='live_url', help='Fetch rendered HTML from a live URL and save it instead of converting markdown')

    args = parser.parse_args()

    cwd = Path(__file__).parent
    in_md = Path(args.input) if args.input else cwd / 'README.md'
    out_html = Path(args.output) if args.output else cwd / 'index.html'
    styles_dir = cwd / 'styles'

    if args.live_url:
        # Fetch live HTML and write it directly
        try:
            with urllib.request.urlopen(args.live_url) as resp:
                content = resp.read()
            # Attempt to decode using utf-8, fallback to latin-1
            try:
                html_text = content.decode('utf-8')
            except Exception:
                html_text = content.decode('latin-1')
            out_html.write_text(html_text, encoding='utf-8')
            print(f'Fetched and wrote live page to: {out_html.resolve()}')
            return
        except urllib.error.URLError as e:
            print(f'Failed to fetch {args.live_url}: {e}')
            sys.exit(3)

    if not in_md.exists():
        print(f'Input file not found: {in_md}')
        sys.exit(2)

    convert(in_md, out_html, styles_dir)


if __name__ == '__main__':
    main()
