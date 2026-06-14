import requests
import re
import os
from datetime import datetime

def filter_vless_reality_configs():
    url = "https://raw.githubusercontent.com/barry-far/V2ray-config/main/Splitted-By-Protocol/vless.txt"
    
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        lines = response.text.splitlines()
        
        filtered_lines = []
        for line in lines:
            line = line.strip()
            if line.startswith('#') or not line:
                continue
            
            if 'vless://' in line:
                # بررسی security=reality و پورت 443
                if re.search(r'security=reality', line, re.IGNORECASE) and re.search(r':443[?&/]', line):
                    filtered_lines.append(line)
        
        # ذخیره با زمان به‌روزرسانی
        output_filename = "vless_reality.txt"
        with open(output_filename, "w", encoding="utf-8") as f:
            f.write(f"# Last Update: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}\n")
            f.write(f"# Total Configs: {len(filtered_lines)}\n")
            f.write("#" + "="*60 + "\n\n")
            f.write("\n".join(filtered_lines))
        
        print(f"✅ Updated: {len(filtered_lines)} VLESS Reality configs (Port 443)")
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    filter_vless_reality_configs()
