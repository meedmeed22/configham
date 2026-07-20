import requests
import re
from datetime import datetime
from urllib.parse import parse_qs

def filter_trojan_configs():
    url = "https://raw.githubusercontent.com/barry-far/V2ray-config/main/Splitted-By-Protocol/trojan.txt"

    try:
        print("🔄 Fetching Trojan configs...")
        response = requests.get(url, timeout=30)
        response.raise_for_status()

        lines = response.text.splitlines()

        # لیست‌های جداگانه برای دو نوع config
        xhttp_configs = []
        normal_configs = []

        for line in lines:
            line = line.strip()
            if line.startswith('#') or not line:
                continue

            if 'trojan://' in line:
                # بررسی پورت 443
                if re.search(r'trojan://[^@]+@([^:?]+):443(?:[?/]|$)', line):
                    # بررسی type=xhttp
                    if is_xhttp_config(line):
                        # تغییر address برای xhttp
                        modified_line = modify_address_for_xhttp(line)
                        xhttp_configs.append(modified_line)
                    else:
                        normal_configs.append(line)

        # ذخیره فایل اول: configهای معمولی (port 443)
        output_filename1 = "trojan_port443.txt"
        with open(output_filename1, "w", encoding="utf-8") as f:
            f.write(f"# Last Update: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}\n")
            f.write(f"# Total Configs: {len(normal_configs)}\n")
            f.write(f"# Filter: Port 443 only (non-xhttp)\n")
            f.write("#" + "="*60 + "\n\n")
            f.write("\n".join(normal_configs))

        # ذخیره فایل دوم: configهای xhttp (port 443 با address تغییر یافته)
        output_filename2 = "trojan_port443_xhttp.txt"
        with open(output_filename2, "w", encoding="utf-8") as f:
            f.write(f"# Last Update: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}\n")
            f.write(f"# Total Configs: {len(xhttp_configs)}\n")
            f.write(f"# Filter: Port 443 only (type=xhttp)\n")
            f.write(f"# Note: Address changed to www.hcaptcha.com\n")
            f.write("#" + "="*60 + "\n\n")
            f.write("\n".join(xhttp_configs))

        print(f"✅ Updated:")
        print(f"   - Normal configs (non-xhttp): {len(normal_configs)} configs → {output_filename1}")
        print(f"   - XHTTP configs (address changed): {len(xhttp_configs)} configs → {output_filename2}")
        print(f"📁 Files saved successfully")
        return True

    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def is_xhttp_config(config_line):
    """
    بررسی می‌کند که آیا config دارای type=xhttp است یا خیر
    """
    try:
        if 'trojan://' not in config_line:
            return False
        
        # پیدا کردن بخش query string
        question_index = config_line.find('?')
        if question_index == -1:
            return False
        
        query_string = config_line[question_index + 1:]
        # جدا کردن پارامترها
        params = parse_qs(query_string)
        
        # بررسی وجود type=xhttp
        return 'type' in params and params['type'][0] == 'xhttp'
        
    except Exception:
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
        
        # تغییر host به www.hcaptcha.com
        host = 'www.hcaptcha.com'
        port = host_port_parts[1]
        new_host_port = f"{host}:{port}"
        
        # بازسازی URL
        new_url = f"{prefix}{credentials}@{new_host_port}?{query_string}"
        return new_url
        
    except Exception as e:
        # در صورت بروز خطا، config اصلی را برگردان
        return config_line

if __name__ == "__main__":
    filter_trojan_configs()