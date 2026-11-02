"""Upgrade the interface without rebuilding or discarding embedded research data."""
import json
from pathlib import Path
import re


def refresh_page(directory, write):
    root = Path(directory)
    page, template = root / 'index.html', root / 'template/template.html'
    if not page.exists() or not template.exists():
        return False
    current, shell = page.read_text(encoding='utf-8'), template.read_text(encoding='utf-8')
    marker = '/*DATA*/null'
    if shell.count(marker) != 1:
        raise ValueError('The installed interface template is invalid. Reinstall Claim Viewer.')
    match = re.search(r'\bconst\s+DATA\s*=\s*', current)
    if not match:
        raise ValueError('The existing page data could not be found. The page was left unchanged.')
    start = match.end()
    _, length = json.JSONDecoder().raw_decode(current[start:])
    updated = shell.replace(marker, current[start:start + length])
    if updated == current:
        return False
    write(str(root / 'index.html.previous'), current)
    write(str(page), updated)
    return True
