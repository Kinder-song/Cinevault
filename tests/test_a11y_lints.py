"""Static checks for common a11y issues in templates."""
import re
from pathlib import Path

import pytest

TEMPLATE_DIR = Path(__file__).parent.parent / "templates"


def test_no_inline_onclick_in_templates():
    """Inline onclick is a11y blocker; should be replaced with addEventListener."""
    offenders = []
    for path in TEMPLATE_DIR.glob("*.html"):
        content = path.read_text()
        for match in re.finditer(r'\son\w+="[^"]*"', content):
            offenders.append(f"{path.name}: {match.group(0)}")
    assert not offenders, "Inline event handlers found:\n" + "\n".join(offenders)


def test_all_inputs_have_labels():
    """Every <input>/<textarea>/<select> must have a <label> or aria-label."""
    offenders = []
    for path in TEMPLATE_DIR.glob("*.html"):
        content = path.read_text()
        for match in re.finditer(
            r'<(input|textarea|select)\b[^>]*>', content
        ):
            tag = match.group(0)
            if "aria-label" in tag or 'type="hidden"' in tag or 'type="submit"' in tag:
                continue
            # Check if a label is associated
            if 'id="' in tag:
                input_id = re.search(r'id="([^"]+)"', tag).group(1)
                if f'for="{input_id}"' in content:
                    continue
            offenders.append(f"{path.name}: {tag[:100]}")
    assert not offenders, "Unlabeled inputs:\n" + "\n".join(offenders[:10])


def test_images_have_alt_text():
    offenders = []
    for path in TEMPLATE_DIR.glob("*.html"):
        content = path.read_text()
        for match in re.finditer(r'<img\b[^>]*>', content):
            tag = match.group(0)
            if "alt=" not in tag:
                offenders.append(f"{path.name}: {tag[:100]}")
    assert not offenders, "Images without alt:\n" + "\n".join(offenders[:10])
