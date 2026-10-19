#!/usr/bin/env python3
"""读取已签名的 .shortcut（AEA1 封装），输出其中的 plist（XML）。仅限 macOS：依赖系统的 aea、aa、openssl。

用法：read_signed_shortcut.py 输入.shortcut [输出.xml]
未给输出路径时，把动作数和动作标识摘要打印到终端。
"""
from pathlib import Path
import plistlib
import struct
import subprocess
import sys
import tempfile


def read_signed(path):
    data = Path(path).read_bytes()
    if data[:4] != b'AEA1':
        # 未签名的 plist 直接读取
        return plistlib.loads(data)
    auth_length = struct.unpack('<I', data[8:12])[0]
    auth = plistlib.loads(data[12:12 + auth_length])
    leaf = auth['SigningCertificateChain'][0]
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        (tmp / 'leaf.der').write_bytes(leaf)
        pem = subprocess.run(['openssl', 'x509', '-inform', 'der', '-in', str(tmp / 'leaf.der'), '-pubkey', '-noout'],
                             check=True, capture_output=True, text=True).stdout
        (tmp / 'sign.pem').write_text(pem)
        subprocess.run(['aea', 'decrypt', '-i', str(path), '-o', str(tmp / 'payload.aar'),
                        '-sign-pub', str(tmp / 'sign.pem')], check=True, capture_output=True)
        (tmp / 'out').mkdir()
        subprocess.run(['aa', 'extract', '-i', str(tmp / 'payload.aar'), '-d', str(tmp / 'out')],
                       check=True, capture_output=True)
        return plistlib.loads((tmp / 'out' / 'Shortcut.wflow').read_bytes())


def main():
    if len(sys.argv) not in (2, 3):
        raise SystemExit(__doc__)
    document = read_signed(sys.argv[1])
    if len(sys.argv) == 3:
        Path(sys.argv[2]).write_bytes(plistlib.dumps(document, fmt=plistlib.FMT_XML, sort_keys=False))
        print(f'已写入 {sys.argv[2]}：{len(document["WFWorkflowActions"])} 个动作')
        return
    actions = document['WFWorkflowActions']
    print(f'{len(actions)} 个动作')
    for index, action in enumerate(actions):
        print(index, action['WFWorkflowActionIdentifier'])


if __name__ == '__main__':
    main()
