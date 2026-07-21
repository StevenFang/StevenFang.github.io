#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import re
import json
import base64
from datetime import datetime
from urllib.parse import urlparse, urlunparse
import requests
import idna
from Crypto.Cipher import AES

LOG_FILE = 'decoder.log'

# 清空日志
with open(LOG_FILE, 'w', encoding='utf-8') as f:
    f.write('')

def log_message(message: str):
    ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(f'[{ts}] {message}\n')

def remove_comments(json_text: str) -> str:
    log_message("Removing comments from JSON")
    json_text = re.sub(r'(?<!:)\/\/.*$', '', json_text, flags=re.MULTILINE)
    json_text = re.sub(r'/\*[\s\S]*?\*/', '', json_text)
    return json_text

def pad_end(key: str) -> bytes:
    log_message(f"Padding key: {key}")
    raw = key.encode('utf-8')
    if len(raw) >= 16:
        return raw[:16]
    return raw + b'0' * (16 - len(raw))

def resolve(url: str, path: str) -> str:
    log_message(f"Resolving path: {path} with URL: {url}")
    return url.rstrip('/') + '/' + path.lstrip('/')

def extract_data(data: str) -> str:
    log_message(f"Extracting data: {data}")
    m = re.search(r'[A-Za-z0-9]{8}\*\*', data)
    if not m:
        return ''
    idx = data.find(m.group(0))
    return data[idx + 10:]

def base64_decode_custom(data: str) -> str:
    log_message(f"Decoding base64 data: {data}")
    extract = extract_data(data)
    if not extract:
        return data
    try:
        decoded = base64.b64decode(extract)
        return decoded.decode('utf-8')
    except Exception as e:
        log_message(f"Base64 decode error: {e}")
        return data

def cbc_decrypt(data: str) -> str:
    log_message(f"Decrypting data with CBC: {data}")
    try:
        decode_bytes = bytes.fromhex(data.lower())
    except Exception as e:
        raise Exception(f'Invalid hex data: {e}')

    decode_str = decode_bytes.decode('latin1', errors='ignore')
    start = decode_str.find('$#')
    end = decode_str.find('#$', start + 2)
    if start == -1 or end == -1:
        raise Exception('Key markers not found in data.')

    key_raw = decode_str[start + 2:end]
    key = pad_end(key_raw)

    iv_raw = decode_str[-13:]
    iv = pad_end(iv_raw)

    pos = data.find('2324')
    if pos == -1:
        raise Exception("Delimiter '2324' not found in hex input.")
    start_hex = pos + 4
    if len(data) <= 26 + start_hex:
        raise Exception('Hex data too short for expected slicing.')
    cipher_hex = data[start_hex: len(data) - 26]
    try:
        cipher_bytes = bytes.fromhex(cipher_hex)
    except Exception as e:
        raise Exception(f'Invalid cipher hex: {e}')

    try:
        cipher = AES.new(key, AES.MODE_CBC, iv)
        decrypted = cipher.decrypt(cipher_bytes)
        pad_len = decrypted[-1]
        if isinstance(pad_len, int) and 1 <= pad_len <= 16:
            decrypted = decrypted[:-pad_len]
        return decrypted.decode('utf-8', errors='ignore')
    except Exception as e:
        raise Exception(f'Decryption failed: {e}')

def replace(url: str, data: str, ext: str) -> str:
    log_message(f"Replacing {ext} in data")
    t = ext.replace("\"./", "\"" + resolve(url, "./"))
    t = t.replace("\"../", "\"" + resolve(url, "../"))
    t = t.replace("./", "__JS1__")
    t = t.replace("../", "__JS2__")
    return data.replace(ext, t)

def fix(url: str, data: str) -> str:
    log_message(f"Fixing data: {data}")
    pattern = r'"(?:\./|\.\./).*?\.js\?.*?"'
    matches = re.findall(pattern, data)
    for m in matches:
        data = replace(url, data, m)
    data = data.replace("../", resolve(url, "../"))
    data = data.replace("./", resolve(url, "./"))
    data = data.replace("__JS1__", "./")
    data = data.replace("__JS2__", "../")
    log_message(f"Fixed data: {data}")
    return data

def verify(url: str, data: str) -> str:
    log_message(f"Verifying data: {data}")
    if not data:
        raise Exception('Data is empty.')
    try:
        _ = json.loads(data)
        return fix(url, data)
    except Exception:
        pass

    if '**' in data:
        data = base64_decode_custom(data)
    if data.startswith('2423'):
        data = cbc_decrypt(data)
    return fix(url, data)

def prompt_url() -> str:
    url = input('请输入 URL: ').strip()
    return url

def main():
    url = prompt_url()
    if not url:
        print('URL parameter is missing.')
        sys.exit(1)

    parsed = urlparse(url)
    if parsed.hostname:
        try:
            ascii_host = idna.encode(parsed.hostname).decode('ascii')
            new_netloc = ascii_host
            if parsed.port:
                new_netloc += f':{parsed.port}'
            parsed = parsed._replace(netloc=new_netloc)
            url = urlunparse(parsed)
        except Exception as e:
            log_message(f"IDN conversion failed: {e}")

    log_message(f"Fetching URL: {url}")

    headers = {'User-Agent': 'okhttp/5.1.0'}
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        response_text = resp.text
    except Exception as e:
        log_message(f'Error fetching the URL: {e}')
        print(f'解密失败: {e}')
        sys.exit(1)

    log_message(f"Fetched response: {response_text}")

    try:
        result = verify(url, response_text)
        result = remove_comments(result)
        log_message(f"Decoded result: {result}")
        try:
            decoded = json.loads(result)
        except Exception as e:
            log_message(f'JSON decode error: {e}')
            print(f'解密失败: {e}')
            sys.exit(1)
        formatted = json.dumps(decoded, ensure_ascii=False, indent=4)

        # 保存为以当前时间命名的 JSON 文件
        filename = datetime.now().strftime('%Y%m%d_%H%M%S') + '.json'
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(formatted)

        print(f'保存为文件: {filename}')
        print(formatted)
    except Exception as e:
        log_message(f'Error processing the data: {e}')
        print(f'Error processing the data: {e}')
        sys.exit(1)

if __name__ == '__main__':
    main()
