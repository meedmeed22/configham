import requests
import re
from datetime import datetime
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

def filter_trojan_configs():
    url = "https://raw.githubusercontent.com/barry-far/V2ray-config/main/Splitted-By-Protocol/trojan.txt"

    try:
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
                # بررسی پورت 443
                if re.search(r'trojan://[^@]+@([^:?]+):443(?:[?/]|$)', line):
                    # بررسی و تغییر address برای type=xhttp
                    modified_line = modify_address_for_xhttp(line)
                    filtered_lines.append(modified_line)

        # ذخیره فایل نهایی
        output_filename = "trojan_port443.txt"
        with open(output_filename, "w", encoding="utf-8") as f:
            f.write(f"# Last Update: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}\n")
            f.write(f"# Total Configs: {len(filtered_lines)}\n")
            f.write(f"# Filter: Port 443 only\n")
            f.write(f"# Note: Configs with type=xhttp have address changed to www.hcaptcha.com\n")
            f.write("#" + "="*60 + "\n\n")
            f.write("\n".join(filtered_lines))

        print(f"✅ Updated: {len(filtered_lines)} configs (Port 443 only)")
        print(f"📁 File saved: {output_filename}")
        return True

    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def modify_address_for_xhttp(config_line):
    """
    اگر type=xhttp باشد، address را به www.hcaptcha.com تغییر می‌دهد
    """
    try:
        if 'trojan://' not in config_line:
            return config_line
        
        # جدا کردن پروتکل از بقیه
        prefix = 'trojan://'
        rest = config_line[len(prefix):]
        
        # پیدا کردن موقعیت @ برای جدا کردن credentials از بقیه
        at_index = rest.find('@')
        if at_index == -1:
            return config_line
        
        credentials = rest[:at_index]
        after_at = rest[at_index + 1:]
        
        # جدا کردن host:port از query string
        question_index = after_at.find('?')
        if question_index == -1:
            return config_line
        
        host_port = after_at[:question_index]
        query_string = after_at[question_index + 1:]
        
        # جدا کردن host و port
        host_port_parts = host_port.split(':')
        if len(host_port_parts) < 2:
            return config_line
        
        # بررسی query parameters
        params = parse_qs(query_string)
        
        # اگر type=xhttp وجود داشت، address را تغییر بده
        if 'type' in params and params['type'][0] == 'xhttp':
            # تغییر host به www.hcaptcha.com
            host = 'www.hcaptcha.com'
            # حفظ port
            port = host_port_parts[1]
            new_host_port = f"{host}:{port}"
            
            # بازسازی URL
            new_url = f"{prefix}{credentials}@{new_host_port}?{query_string}"
            return new_url
        
        return config_line
        
    except Exception as e:
        # در صورت بروز خطا، config اصلی را برگردان
        return config_line

if __name__ == "__main__":
    filter_trojan_configs()