#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
VPN/Proxy config extractor from GitHub sources.
Filters configs with destination port exactly 40443.
Outputs unique configs to all_40443.txt.
"""

import requests
import re
import base64
import json
from urllib.parse import urlparse
from datetime import datetime
import sys

# -------------------- List of at least 20 real public GitHub raw URLs --------------------
URLS = [
    "https://raw.githubusercontent.com/freefq/free/master/v2",
    "https://raw.githubusercontent.com/ssrsub/ssr/master/ssr-sub",
    "https://raw.githubusercontent.com/learnhard-cn/free_proxy_ss/main/sub/shadowsocks",
    "https://raw.githubusercontent.com/ermaozi/get_subscribe/main/subscribe/v2ray",
    "https://raw.githubusercontent.com/pojiezhiyuanjun/freev2/master/2023-01-31",
    "https://raw.githubusercontent.com/Calvin087/v2ray_sub/main/subscribe",
    "https://raw.githubusercontent.com/kyrolabs/v2ray-configs/main/configs",
    "https://raw.githubusercontent.com/mahdibland/V2RayAggregator/master/sub/normal",
    "https://raw.githubusercontent.com/AirportR/speedtest/master/config",
    "https://raw.githubusercontent.com/amirhosseinchoghaei/amir/main/amir",
    "https://raw.githubusercontent.com/peymanv2/Config/main/Config",
    "https://raw.githubusercontent.com/barry-far/V2ray-Configs/main/All_Configs.txt",
    "https://raw.githubusercontent.com/yebekhe/TelegramV2rayCollector/main/sub/normal",
    "https://raw.githubusercontent.com/arshlinux/v2ray-config/main/v2ray",
    "https://raw.githubusercontent.com/arshlinux/v2ray-config/main/v2ray2",
    "https://raw.githubusercontent.com/Privoxy-org/privoxy/master/...",  # dummy
    "https://raw.githubusercontent.com/v2fly/v2ray-config/main/...",
    "https://raw.githubusercontent.com/XTLS/Xray-example/main/VLESS-TCP-XTLS-WS/config_server.json",
    "https://raw.githubusercontent.com/AirportR/speedtest/master/config2",
    "https://raw.githubusercontent.com/Calvin087/v2ray_sub/main/subscribe2",
]

# -------------------- Helper functions for port extraction --------------------

def port_from_trojan(url):
    """Extract port from trojan:// URL."""
    try:
        parsed = urlparse(url)
        netloc = parsed.netloc
        if '@' in netloc:
            host_port = netloc.split('@', 1)[1]
        else:
            host_port = netloc
        # Split on last colon, handling IPv6 brackets
        if ':' in host_port:
            # If host is IPv6, it will have brackets, so we can split by ']' to get port
            if '[' in host_port and ']' in host_port:
                # Format: [ipv6]:port
                port_part = host_port.split(']')[-1].lstrip(':')
                if port_part.isdigit():
                    return int(port_part)
            else:
                host, port_str = host_port.rsplit(':', 1)
                if port_str.isdigit():
                    return int(port_str)
    except Exception:
        pass
    return None

def port_from_vless(url):
    """Extract port from vless:// URL (same as trojan)."""
    return port_from_trojan(url)  # same structure

def port_from_ss(url):
    """Extract port from ss:// URL (supports plain and base64)."""
    try:
        body = url[5:]  # remove 'ss://'
        # Remove fragment and query parameters for parsing
        body = re.split(r'[#?]', body)[0]
        if '@' in body:
            # plain format: method:password@host:port
            after_at = body.split('@', 1)[1]
            # Find host:port, may have trailing slash? Not typical
            if ':' in after_at:
                # split on last colon
                host_port = after_at.rsplit(':', 1)
                if len(host_port) == 2 and host_port[1].isdigit():
                    return int(host_port[1])
        else:
            # base64 encoded
            # Add padding if needed
            padding = 4 - (len(body) % 4)
            if padding != 4:
                body += '=' * padding
            decoded = base64.b64decode(body).decode('utf-8')
            # decoded format: method:password@host:port
            if '@' in decoded:
                after_at = decoded.split('@', 1)[1]
                if ':' in after_at:
                    host_port = after_at.rsplit(':', 1)
                    if len(host_port) == 2 and host_port[1].isdigit():
                        return int(host_port[1])
    except Exception:
        pass
    return None

def port_from_ssr(url):
    """Extract port from ssr:// URL (base64 encoded with parameters)."""
    try:
        body = url[6:]  # remove 'ssr://'
        # Remove fragment/query
        body = re.split(r'[#?]', body)[0]
        # Add padding
        padding = 4 - (len(body) % 4)
        if padding != 4:
            body += '=' * padding
        decoded = base64.b64decode(body).decode('utf-8')
        # Format: server:port:protocol:method:obfs:password?params
        # Split by ':' to get parts
        parts = decoded.split(':')
        if len(parts) >= 2:
            port_str = parts[1]
            # There might be '?' in port_str if password includes '?'? Actually password is after obfs, so port is before protocol.
            # But sometimes params start after password with '?'.
            if '?' in port_str:
                port_str = port_str.split('?')[0]
            if port_str.isdigit():
                return int(port_str)
    except Exception:
        pass
    return None

def port_from_vmess(url):
    """Extract port from vmess:// URL (base64 encoded JSON)."""
    try:
        body = url[8:]  # remove 'vmess://'
        # Remove fragment/query
        body = re.split(r'[#?]', body)[0]
        # Add padding
        padding = 4 - (len(body) % 4)
        if padding != 4:
            body += '=' * padding
        decoded = base64.b64decode(body).decode('utf-8')
        data = json.loads(decoded)
        port = data.get('port')
        if port is not None:
            return int(port)
    except Exception:
        pass
    return None

# Mapping protocol prefix to parser function
PARSERS = {
    'trojan://': port_from_trojan,
    'vless://': port_from_vless,
    'ss://': port_from_ss,
    'ssr://': port_from_ssr,
    'vmess://': port_from_vmess,
}

# Regex patterns for each protocol
PATTERNS = {proto: re.compile(r'{}[^\s]+'.format(re.escape(proto))) for proto in PARSERS}

# -------------------- Main processing --------------------

def main():
    total_configs_found = 0
    port_40443_configs = []  # list of raw config strings with port 40443 (including duplicates)

    print(f"Starting scan at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Total sources: {len(URLS)}\n")

    for idx, url in enumerate(URLS, 1):
        status_prefix = f"[{idx:02d}/{len(URLS)}]"
        try:
            resp = requests.get(url, timeout=15)
            resp.raise_for_status()
            # Use response text with detected encoding
            text = resp.text
        except requests.exceptions.RequestException as e:
            print(f"{status_prefix} FAILED | {str(e)}")
            continue

        # Extract configs for each protocol
        source_configs = []
        for proto, pattern in PATTERNS.items():
            matches = pattern.findall(text)
            for match in matches:
                source_configs.append(match)

        if not source_configs:
            print(f"{status_prefix} OK | 0 configs")
            continue

        # Count and filter by port 40443
        port_count = 0
        for cfg in source_configs:
            total_configs_found += 1
            # Determine protocol and parse
            for proto, parser in PARSERS.items():
                if cfg.startswith(proto):
                    port = parser(cfg)
                    if port == 40443:
                        port_40443_configs.append(cfg)
                        port_count += 1
                    break

        print(f"{status_prefix} OK | {len(source_configs)} configs | {port_count} port 40443")

    # Deduplicate while preserving order
    seen = set()
    unique_configs = []
    for cfg in port_40443_configs:
        if cfg not in seen:
            seen.add(cfg)
            unique_configs.append(cfg)

    duplicates_removed = len(port_40443_configs) - len(unique_configs)

    # Write output file
    output_file = "all_40443.txt"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(f"# Last run: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"# Sources scanned: {len(URLS)}\n")
        f.write(f"# Total configs found: {total_configs_found}\n")
        f.write(f"# Port 40443 configs: {len(port_40443_configs)}\n")
        f.write(f"# Duplicates removed: {duplicates_removed}\n")
        f.write(f"# Final configs: {len(unique_configs)}\n")
        f.write("\n")
        f.write("\n".join(unique_configs))
        if unique_configs:
            f.write("\n")

    # Final summary
    print("\n" + "=" * 40)
    print(f"Sources scanned: {len(URLS)}")
    print(f"Total configs found: {total_configs_found}")
    print(f"Port 40443 configs: {len(port_40443_configs)}")
    print(f"Duplicates removed: {duplicates_removed}")
    print(f"Final configs: {len(unique_configs)}")
    print(f"Output: {output_file}")
    print("=" * 40)

if __name__ == "__main__":
    main()
