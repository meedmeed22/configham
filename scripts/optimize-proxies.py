import re
import requests
from urllib.parse import quote

SOURCE_URL = "https://cdn.jsdelivr.net/gh/proxifly/free-proxy-list@main/proxies/protocols/socks5/data.txt"
OUTPUT_FILE = "optimized-proxies.txt"
TARGET_FORMAT = "socks://Og==@{host}:{port}#{host}%3A{port}"

def fetch_proxies():
    response = requests.get(SOURCE_URL, timeout=30)
    response.raise_for_status()
    return response.text.splitlines()

def parse_socks5_line(line):
    match = re.match(r'socks5://([^:]+):(\d+)', line.strip())
    if match:
        return match.groups()
    return None

def convert_to_target(host, port):
    return TARGET_FORMAT.format(host=host, port=port, host_encoded=quote(host))

def main():
    raw_lines = fetch_proxies()
    proxies_set = set()
    converted_lines = []

    for line in raw_lines:
        parsed = parse_socks5_line(line)
        if not parsed:
            continue
        host, port = parsed
        if (host, port) in proxies_set:
            continue  # حذف تکراری
        proxies_set.add((host, port))
        converted_lines.append(convert_to_target(host, port))

    # ذخیره خروجی
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(converted_lines))

    print(f"✅ {len(converted_lines)} proxy optimized and saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
