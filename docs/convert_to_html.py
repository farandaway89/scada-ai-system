#!/usr/bin/env python
"""
Markdown to HTML converter with beautiful styling
"""
import os
import re
from pathlib import Path

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: 'Segoe UI', 'Malgun Gothic', sans-serif;
            line-height: 1.8;
            color: #333;
            max-width: 1200px;
            margin: 0 auto;
            padding: 40px 20px;
            background: #f5f5f5;
        }}
        .container {{
            background: white;
            padding: 60px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            border-radius: 8px;
        }}
        h1 {{
            color: #2c3e50;
            border-bottom: 4px solid #3498db;
            padding-bottom: 15px;
            margin-bottom: 30px;
            font-size: 2.5em;
        }}
        h2 {{
            color: #34495e;
            margin-top: 40px;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 2px solid #ecf0f1;
            font-size: 2em;
        }}
        h3 {{
            color: #555;
            margin-top: 30px;
            margin-bottom: 15px;
            font-size: 1.5em;
        }}
        h4 {{
            color: #666;
            margin-top: 20px;
            margin-bottom: 10px;
            font-size: 1.2em;
        }}
        p {{
            margin-bottom: 15px;
            text-align: justify;
        }}
        ul, ol {{
            margin-left: 30px;
            margin-bottom: 15px;
        }}
        li {{
            margin-bottom: 8px;
        }}
        code {{
            background: #f4f4f4;
            padding: 2px 6px;
            border-radius: 3px;
            font-family: 'Consolas', 'Monaco', monospace;
            font-size: 0.9em;
            color: #e74c3c;
        }}
        pre {{
            background: #2c3e50;
            color: #ecf0f1;
            padding: 20px;
            border-radius: 5px;
            overflow-x: auto;
            margin: 20px 0;
            font-family: 'Consolas', 'Monaco', monospace;
            line-height: 1.5;
        }}
        pre code {{
            background: none;
            color: #ecf0f1;
            padding: 0;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }}
        th {{
            background: #3498db;
            color: white;
            padding: 12px;
            text-align: left;
            font-weight: 600;
        }}
        td {{
            padding: 12px;
            border-bottom: 1px solid #ecf0f1;
        }}
        tr:nth-child(even) {{
            background: #f9f9f9;
        }}
        tr:hover {{
            background: #f0f0f0;
        }}
        blockquote {{
            border-left: 4px solid #3498db;
            padding-left: 20px;
            margin: 20px 0;
            color: #555;
            font-style: italic;
            background: #f8f9fa;
            padding: 15px 20px;
            border-radius: 0 5px 5px 0;
        }}
        .toc {{
            background: #ecf0f1;
            padding: 20px;
            border-radius: 5px;
            margin-bottom: 30px;
        }}
        .toc h2 {{
            margin-top: 0;
            border-bottom: none;
        }}
        .toc ul {{
            list-style: none;
            margin-left: 0;
        }}
        .toc a {{
            color: #3498db;
            text-decoration: none;
        }}
        .toc a:hover {{
            text-decoration: underline;
        }}
        hr {{
            border: none;
            border-top: 2px solid #ecf0f1;
            margin: 40px 0;
        }}
        @media print {{
            body {{
                background: white;
                padding: 0;
            }}
            .container {{
                box-shadow: none;
                padding: 20px;
            }}
            pre {{
                page-break-inside: avoid;
            }}
            table {{
                page-break-inside: avoid;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        {content}
    </div>
</body>
</html>
"""

def md_to_html(md_text):
    """Convert Markdown to HTML (simple version)"""
    html = md_text

    # Code blocks
    html = re.sub(r'```(\w+)?\n(.*?)```', r'<pre><code>\2</code></pre>', html, flags=re.DOTALL)

    # Headers
    html = re.sub(r'^# (.*?)$', r'<h1>\1</h1>', html, flags=re.MULTILINE)
    html = re.sub(r'^## (.*?)$', r'<h2>\1</h2>', html, flags=re.MULTILINE)
    html = re.sub(r'^### (.*?)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)
    html = re.sub(r'^#### (.*?)$', r'<h4>\1</h4>', html, flags=re.MULTILINE)

    # Bold and italic
    html = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', html)
    html = re.sub(r'\*(.*?)\*', r'<em>\1</em>', html)

    # Inline code
    html = re.sub(r'`([^`]+)`', r'<code>\1</code>', html)

    # Links
    html = re.sub(r'\[(.*?)\]\((.*?)\)', r'<a href="\2">\1</a>', html)

    # Tables
    lines = html.split('\n')
    in_table = False
    result = []

    for i, line in enumerate(lines):
        if '|' in line and line.strip().startswith('|'):
            if not in_table:
                result.append('<table>')
                in_table = True
                # Header row
                cells = [c.strip() for c in line.split('|')[1:-1]]
                result.append('<thead><tr>')
                for cell in cells:
                    result.append(f'<th>{cell}</th>')
                result.append('</tr></thead>')
                result.append('<tbody>')
            elif '---' not in line:
                # Data row
                cells = [c.strip() for c in line.split('|')[1:-1]]
                result.append('<tr>')
                for cell in cells:
                    result.append(f'<td>{cell}</td>')
                result.append('</tr>')
        else:
            if in_table:
                result.append('</tbody></table>')
                in_table = False
            result.append(line)

    if in_table:
        result.append('</tbody></table>')

    html = '\n'.join(result)

    # Horizontal rules
    html = re.sub(r'^---$', '<hr>', html, flags=re.MULTILINE)

    # Paragraphs
    html = re.sub(r'\n\n', '</p><p>', html)
    html = '<p>' + html + '</p>'

    # Clean up
    html = html.replace('<p><h', '<h')
    html = html.replace('</h1></p>', '</h1>')
    html = html.replace('</h2></p>', '</h2>')
    html = html.replace('</h3></p>', '</h3>')
    html = html.replace('</h4></p>', '</h4>')
    html = html.replace('<p><pre>', '<pre>')
    html = html.replace('</pre></p>', '</pre>')
    html = html.replace('<p><table>', '<table>')
    html = html.replace('</table></p>', '</table>')
    html = html.replace('<p><hr></p>', '<hr>')
    html = html.replace('<p></p>', '')

    return html

def convert_md_file(md_path, output_dir):
    """Convert a single MD file to HTML"""
    with open(md_path, 'r', encoding='utf-8') as f:
        md_content = f.read()

    html_content = md_to_html(md_content)

    title = Path(md_path).stem
    html = HTML_TEMPLATE.format(title=title, content=html_content)

    output_path = Path(output_dir) / f"{title}.html"
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f"[OK] Converted: {md_path} -> {output_path}")
    return output_path

def main():
    docs_dir = Path(__file__).parent
    html_dir = docs_dir / 'html_output'
    html_dir.mkdir(exist_ok=True)

    md_files = [
        '01_프로젝트_개요.md',
        '02_개발계획서.md',
        '03_기술개발일지.md',
        '05_사용자_가이드.md',
        '06_향후_개선계획.md',
    ]

    report_files = [
        '04_완료보고서/01_전체_요약.md',
        '04_완료보고서/03_고도화버전_분석.md',
        '04_완료보고서/04_비교분석표.md',
        '04_완료보고서/05_파일구조_분석.md',
        '04_완료보고서/06_코드_상세분석.md',
        '04_완료보고서/07_문제해결_과정.md',
    ]

    print("=" * 60)
    print("Markdown to HTML Converter")
    print("=" * 60)
    print()

    print("Converting main documents...")
    for md_file in md_files:
        md_path = docs_dir / md_file
        if md_path.exists():
            convert_md_file(md_path, html_dir)

    print("\nConverting report documents...")
    for md_file in report_files:
        md_path = docs_dir / md_file
        if md_path.exists():
            convert_md_file(md_path, html_dir)

    print("\n" + "=" * 60)
    print(f"[OK] All files converted to: {html_dir}")
    print("=" * 60)
    print("\n다음 단계:")
    print("1. html_output 폴더의 HTML 파일을 브라우저로 열기")
    print("2. Ctrl+P 누르기")
    print("3. '대상: PDF로 저장' 선택")
    print("4. 저장하기")
    print("\n또는:")
    print(f"start {html_dir}")

if __name__ == '__main__':
    main()
