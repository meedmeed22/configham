import requests
import re
from datetime import datetime

def filter_trojan_configs():
    url = "https://raw.githubusercontent.com/barry-far/V2ray-config/main/Splitted-By-Protocol/trojan.txt"

    try:
        print("🔄 Fetching Trojan configs...")
        response = requests.get(url, timeout=30)
        response.raise_for_status()

        lines = response.text.splitlines()

        # لیست‌های جداگانه برای دو نوع خروجی
        original_configs = []  # کانفیگ‌های اصلی بدون تغییر
        modified_configs = []  # کانفیگ‌های با آدرس تغییر یافته

        for line in lines:
            line = line.strip()
            if line.startswith('#') or not line:
                continue

            if 'trojan://' in line:
                # بررسی پورت 443
                if not re.search(r'trojan://[^@]+@([^:?]+):443(?:[?/]|$)', line):
                    # اضافه کردن به لیست اصلی (بدون تغییر)
                    original_configs.append(line)
                    # تغییر آدرس به www.hcaptcha.com و اضافه به لیست دوم
                    modified_line = change_address_to_hcaptcha(line)
                    modified_configs.append(modified_line)

        # ذخیره فایل اول: کانفیگ‌های اصلی (بدون تغییر)
        output_filename1 = "trojan_port443.txt"
        with open(output_filename1, "w", encoding="utf-8") as f:
            f.write(f"# Last Update: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}\n")
            f.write(f"# Total Configs: {len(original_configs)}\n")
            f.write(f"# Filter: Port 443 only (Original addresses)\n")
            f.write("#" + "="*60 + "\n\n")
            f.write("\n".join(original_configs))

        # ذخیره فایل دوم: کانفیگ‌های با آدرس تغییر یافته
        output_filename2 = "trojan_port443_hcaptcha.txt"
        with open(output_filename2, "w", encoding="utf-8") as f:
            f.write(f"# Last Update: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}\n")
            f.write(f"# Total Configs: {len(modified_configs)}\n")
            f.write(f"# Filter: Port 443 only (Address changed to www.hcaptcha.com)\n")
            f.write(f"# Note: All addresses have been changed to www.hcaptcha.com\n")
            f.write("#" + "="*60 + "\n\n")
            f.write("\n".join(modified_configs))

        print(f"✅ Updated:")
        print(f"   - Original configs (unchanged): {len(original_configs)} configs → {output_filename1}")
        print(f"   - Modified configs (address changed to www.hcaptcha.com): {len(modified_configs)} configs → {output_filename2}")
        print(f"📁 Files saved successfully")
        return True

    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def change_address_to_hcaptcha(config_line):
    """
    آدرس (host) را در تمام کانفیگ‌ها به www.hcaptcha.com تغییر می‌دهد
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
        port = host_port_parts[1]  # حفظ پورت اصلی (443)
        new_host_port = f"{host}:{port}"
        
        # بازسازی URL
        new_url = f"{prefix}{credentials}@{new_host_port}?{query_string}"
        return new_url
        
    except Exception as e:
        # در صورت بروز خطا، config اصلی را برگردان
        return config_line

if __name__ == "__main__":
    filter_trojan_configs()
