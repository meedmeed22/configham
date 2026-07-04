import requests
import re
import os
from datetime import datetime
import ipaddress
import socket

def get_turkey_ip_ranges():
    """دریافت محدوده آیپی های ترکیه از منابع معتبر"""
    turkey_ranges = []
    
    try:
        # استفاده از API ipinfo.io برای دریافت محدوده آیپی ترکیه
        response = requests.get("https://ipinfo.io/countries/TR", timeout=10)
        if response.status_code == 200:
            data = response.json()
            if 'prefixes' in data:
                for prefix in data['prefixes']:
                    if 'prefix' in prefix:
                        turkey_ranges.append(prefix['prefix'])
        
        # منابع جایگزین در صورت عدم موفقیت
        if not turkey_ranges:
            # استفاده از لیست ثابت برخی از محدوده‌های معروف ترکیه
            turkey_ranges = [
                "88.240.0.0/12",
                "78.160.0.0/11",
                "212.174.0.0/15",
                "212.175.0.0/16",
                "85.96.0.0/12",
                "88.228.0.0/14",
                "95.0.0.0/12",
                "5.176.0.0/13",
                "31.200.0.0/14",
                "46.1.0.0/16",
                "46.2.0.0/15",
                "81.213.0.0/16",
                "82.145.0.0/16",
                "85.96.0.0/12",
                "88.228.0.0/14",
                "94.54.0.0/15",
                "95.0.0.0/12",
                "144.122.0.0/16",
                "176.40.0.0/14",
                "195.142.0.0/16"
            ]
            
    except Exception as e:
        print(f"⚠️ Warning: Could not fetch Turkey IP ranges: {e}")
        # استفاده از لیست ثابت در صورت خطا
        turkey_ranges = [
            "88.240.0.0/12",
            "78.160.0.0/11",
            "212.174.0.0/15",
            "85.96.0.0/12",
            "95.0.0.0/12"
        ]
    
    return turkey_ranges

def is_ip_in_turkey(ip_address, turkey_ranges):
    """بررسی اینکه آیا آیپی در محدوده ترکیه قرار دارد"""
    try:
        ip = ipaddress.ip_address(ip_address)
        for cidr in turkey_ranges:
            if ip in ipaddress.ip_network(cidr, strict=False):
                return True
        return False
    except Exception:
        return False

def extract_ip_from_config(config):
    """استخراج آیپی از کانفیگ تروجان"""
    match = re.search(r'trojan://[^@]+@([^:?]+)', config)
    if match:
        return match.group(1)
    return None

def filter_trojan_configs():
    url = "https://raw.githubusercontent.com/barry-far/V2ray-config/main/Splitted-By-Protocol/trojan.txt"
    
    try:
        # دریافت محدوده آیپی های ترکیه
        print("🔄 Fetching Turkey IP ranges...")
        turkey_ranges = get_turkey_ip_ranges()
        print(f"✅ Loaded {len(turkey_ranges)} Turkey IP ranges")
        
        # دریافت کانفیگ‌ها
        print("🔄 Fetching Trojan configs...")
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        lines = response.text.splitlines()
        
        filtered_lines = []
        
        for line in lines:
            line = line.strip()
            if line.startswith('#') or not line:
                continue
            
            if 'trojan://' in line:
                # استخراج آیپی و بررسی ترکیه بودن (بدون محدودیت پورت)
                ip = extract_ip_from_config(line)
                if ip and is_ip_in_turkey(ip, turkey_ranges):
                    filtered_lines.append(line)
        
        # ذخیره فایل نهایی (همه تروجان‌های ترکیه)
        output_filename = "trojan_turkey.txt"
        with open(output_filename, "w", encoding="utf-8") as f:
            f.write(f"# Last Update: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}\n")
            f.write(f"# Total Configs: {len(filtered_lines)}\n")
            f.write(f"# Filter: All Trojan configs with Turkey IPs\n")
            f.write("#" + "="*60 + "\n\n")
            f.write("\n".join(filtered_lines))
        
        print(f"✅ Updated: {len(filtered_lines)} configs (All Trojan + Turkey IPs)")
        print(f"📁 File saved: {output_filename}")
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    filter_trojan_configs()
