import re

def clean_name(name):
    if not name:
        return "UNKNOWN"
    # Remove common prefixes
    name = re.sub(r'^(CHECKCARD|PURCHASE|POS PURCHASE|DEBIT CARD PURCHASE)\s*\d*\s*', '', name, flags=re.IGNORECASE)
    # Remove dates (MM/DD, MM-DD)
    name = re.sub(r'\b\d{1,2}[/-]\d{1,2}\b', '', name)
    # Remove large number sequences (IDs)
    name = re.sub(r'\b\d{4,}\b', '', name)
    # Remove special chars
    name = re.sub(r'[^\w\s]', ' ', name)
    return ' '.join(name.split()).upper()
