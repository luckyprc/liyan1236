import base64
import re
import urllib.request
import os

SUB_URL = os.environ.get('SUB_URL', '').strip()
if not SUB_URL:
    raise ValueError("SUB_URL not set")

req = urllib.request.Request(
    SUB_URL,
    headers={'User-Agent': 'v2rayN/4.0'}
)

resp = urllib.request.urlopen(req, timeout=30)
print(f"HTTP Status: {resp.status}")
print(f"Content-Type: {resp.headers.get('Content-Type', 'unknown')}")

data = resp.read().decode('utf-8', errors='ignore').strip()
print(f"Raw length: {len(data)}")
print(f"Raw preview: {data[:500]}")

# 自动检测 Base64 并解码
lines = []
if any(data.startswith(p) for p in ('vless://', 'vmess://', 'trojan://', 'ss://', 'ssr://', 'http://', 'https://')):
    lines = [l.strip() for l in data.splitlines() if l.strip()]
else:
    # 尝试 Base64 解码
    try:
        # 补全 padding
        pad = 4 - len(data) % 4
        if pad != 4:
            data += '=' * pad
        decoded = base64.b64decode(data).decode('utf-8', errors='ignore')
        print(f"Base64 decoded length: {len(decoded)}")
        print(f"Decoded preview: {decoded[:500]}")
        lines = [l.strip() for l in decoded.splitlines() if l.strip()]
    except Exception as e:
        print(f"Base64 decode failed: {e}")
        lines = [l.strip() for l in data.splitlines() if l.strip()]

# 过滤代理节点
proxy_lines = [l for l in lines if l.startswith(('vless://', 'vmess://', 'trojan://', 'ss://', 'ssr://'))]
print(f"Total proxy lines: {len(proxy_lines)}")

# 保底优选IP
CF_IPS = {
    'mobile':  ['104.16.32.100', '104.18.1.100', '172.64.95.2'],
    'unicom':  ['104.18.21.50', '162.159.62.8', '104.19.45.6'],
    'telecom': ['172.65.230.14', '104.21.0.100', '172.67.0.100']
}

def get_host_port(url):
    m = re.search(r'@([^:]+):(\d+)', url)
    return (m.group(1), int(m.group(2))) if m else ('', 0)

def replace_host(url, new_host):
    return re.sub(r'@([^:]+):', f'@{new_host}:', url, count=1)

def is_cf(host):
    if host.startswith(('104.16.', '104.17.', '104.18.', '104.19.', '104.20.', '104.21.', '104.24.',
                        '172.64.', '162.159.', '108.162.', '2606:4700')):
        return True
    if 'cloudflare' in host.lower() or '.cf.' in host.lower():
        return True
    return False

direct_nodes = []
cf_nodes = []

for line in proxy_lines:
    host, port = get_host_port(line)
    if not host:
        continue
    if '[' in host:  # 跳过 IPv6
        continue
    if port == 443:
        direct_nodes.append(line)
    elif is_cf(host):
        cf_nodes.append(line)

print(f"Direct 443 nodes: {len(direct_nodes)}")
print(f"CF nodes optimized: {len(cf_nodes)}")

os.makedirs('dist', exist_ok=True)

for carrier in ['mobile', 'unicom', 'telecom', 'mixed']:
    nodes = list(direct_nodes)
    
    if carrier == 'mixed':
        for node in cf_nodes:
            for c in ['mobile', 'unicom', 'telecom']:
                nodes.append(replace_host(node, CF_IPS[c][0]))
    else:
        for node in cf_nodes:
            for ip in CF_IPS[carrier]:
                nodes.append(replace_host(node, ip))
    
    text = '\n'.join(nodes) + '\n'
    with open(f'dist/sub_{carrier}.txt', 'w', encoding='utf-8') as f:
        f.write(text)
    with open(f'dist/sub_{carrier}_base64.txt', 'w', encoding='utf-8') as f:
        f.write(base64.b64encode(text.encode()).decode() + '\n')

readme_lines = [
    "# 蜂窝网络订阅",
    "- 443落地节点：{} 个（直接连，最稳）".format(len(direct_nodes)),
    "- CF优化节点：{} 个（已替换优选IP）".format(len(cf_nodes)),
    "- 更新时间：见提交记录",
    "- 推荐订阅（自动选最优）：sub_mixed_base64.txt"
]
with open('dist/README.md', 'w', encoding='utf-8') as f:
    f.write('\n'.join(readme_lines) + '\n')
