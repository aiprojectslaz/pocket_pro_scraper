from lxml import etree


def scrape_xml(filepath: str, section_id: str | None = None) -> str:
    tree = etree.parse(filepath)
    root = tree.getroot()

    if section_id:
        # Use local-name() to handle XML namespaces safely
        matches = root.xpath(
            f".//*[local-name()='section' and @id='{section_id}']"
        )
        if not matches:
            # Also try case variations (Section, SECTION)
            matches = root.xpath(
                f".//*[translate(local-name(),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz')='section' and @id='{section_id}']"
            )
        if not matches:
            raise ValueError(f"Section id '{section_id}' not found in {filepath}")
        node = matches[0]
    else:
        node = root

    text = " ".join(node.itertext()).strip()
    # Normalise whitespace
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    text = "\n".join(lines)

    if not text:
        raise ValueError(f"No text extracted from XML: {filepath}")

    return text
