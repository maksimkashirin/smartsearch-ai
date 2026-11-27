import csv
import json
import xml.etree.ElementTree as ET
from pathlib import Path
from decimal import Decimal

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
XML_FILE = DATA_DIR / "Mindbox.yml.gz.xml"

category_count = 0
product_count = 0
available_count = 0


def text(element, tag):
    return (element.findtext(tag) or "").strip()


def price(element, tag):
    value = text(element, tag)
    if not value:
        return None

    number = Decimal(value)
    return number if number > 0 else None


with (
    open(DATA_DIR / "categories.csv", "w",
         encoding="utf-8", newline="") as categories_file,
    open(DATA_DIR / "products.csv", "w",
         encoding="utf-8", newline="") as products_file
):
    categories = csv.writer(categories_file)
    products = csv.writer(products_file)

    stack = []

    for event, elem in ET.iterparse(
        XML_FILE, events=("start", "end")
    ):
        if event == "start":
            stack.append(elem)
            continue

        if elem.tag == "category":
            categories.writerow([
                elem.get("id"),
                elem.get("parentId"),
                (elem.text or "").strip()
            ])

            category_count += 1
            stack[-2].remove(elem)

        elif elem.tag == "offer":
            attributes = {}

            for param in elem.findall("param"):
                key = param.get("name", "").strip()
                value = (param.text or "").strip()

                if key and value:
                    attributes.setdefault(key, []).append(value)

            available = elem.get("available") == "true"

            products.writerow([
                elem.get("id"),
                elem.get("group_id") or text(elem, "group_id"),
                text(elem, "name"),
                text(elem, "vendor"),
                text(elem, "vendorCode"),
                text(elem, "categoryId"),
                text(elem, "description"),
                price(elem, "price"),
                price(elem, "oldprice"),
                text(elem, "currencyId"),
                available,
                text(elem, "url"),
                text(elem, "picture"),
                text(elem, "vendorUrl"),
                text(elem, "sales_notes"),
                json.dumps(attributes, ensure_ascii=False)
            ])

            product_count += 1
            available_count += int(available)

            if product_count % 10000 == 0:
                print(
                    f"Processed: {product_count}",
                    flush=True
                )

            stack[-2].remove(elem)

        stack.pop()

print(f"Categories: {category_count}")
print(f"Products: {product_count}")
print(f"Available: {available_count}")
print("Catalog processing completed.")
