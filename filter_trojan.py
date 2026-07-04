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
        
        filtered_lines = []
        for line in lines:
            line = line.strip()
            if line.startswith('#') or not line:
                continue
            
            if 'trojan://' in line:
                # فقط بررسی پورت 443
                if re.search(r'trojan://[^@]+@([^:?]+):443(?:[?/]|$)', line):
                    filtered_lines.append(line)
        
        # ذخیره فایل نهایی
        output_filename = "trojan_port443.txt"
        with open(output_filename, "w", encoding="utf-8") as f:
            f.write(f"# Last Update: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}\n")
            f.write(f"# Total Configs: {len(filtered_lines)}\n")
            f.write(f"# Filter: Port 443 only\n")
            f.write("#" + "="*60 + "\n\n")
            f.write("\n".join(filtered_lines))
        
        print(f"✅ Updated: {len(filtered_lines)} configs (Port 443 only)")
        print(f"📁 File saved: {output_filename}")
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    filter_trojan_configs()
