#!/usr/bin/env python3
"""在 Mac 上运行已导入的「YanGui 测试」快捷指令：把原话作为快捷指令输入，打印它的输出和系统报错。

用法：run_mac_test.py [--config 配置文件] 快捷指令名 "原话" [超时秒数]
--config：本次运行用的接口配置，文件格式为四组两行（API Protocol / API Base URL / API Key / API Model，下一行是值）。
它作为输入第一行 config={...} 传给测试版，只经过本机临时文件，不写进签名文件，也不打印。
测试版由 `python3 preview/build_yangui.py --test` 生成（dist/YanGui-Test.xml），签名后双击导入（无导入问题）；加 `--real-notes` 生成时备忘录真实写入。
原话格式：`阶段|||回复JSON|||原话` 用给定回复、不发请求；`probeN|||原话` 只运行第 N 个格式探针。
需要在沙箱外运行；日历、提醒事项的写入是真实写入，测试原话建议带「测试」二字，便于事后清理。
"""
from pathlib import Path
import json
import subprocess
import sys
import tempfile


def read_config(path):
    lines = [line.strip() for line in Path(path).read_text(encoding='utf-8').splitlines() if line.strip()]
    pairs = dict(zip(lines[0::2], lines[1::2]))
    return json.dumps({'protocol': pairs['API Protocol'], 'base_url': pairs['API Base URL'],
                       'key': pairs['API Key'], 'model': pairs['API Model']}, ensure_ascii=False)


def main():
    args = sys.argv[1:]
    config = None
    if args[:1] == ['--config'] and len(args) >= 2:
        config, args = read_config(args[1]), args[2:]
    if len(args) not in (2, 3):
        raise SystemExit(__doc__)
    name, utterance = args[0], args[1]
    if config:
        utterance = f'config={config}\n{utterance}'
    timeout = int(args[2]) if len(args) == 3 else 120
    with tempfile.TemporaryDirectory() as tmp:
        source, target = Path(tmp) / 'input.txt', Path(tmp) / 'output.txt'
        source.write_text(utterance, encoding='utf-8')
        try:
            run = subprocess.run(['shortcuts', 'run', name, '--input-path', str(source), '--output-path', str(target),
                                  '--output-type', 'public.plain-text'],
                                 capture_output=True, text=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            raise SystemExit(f'超过 {timeout} 秒没有结束：快捷指令可能在等待权限弹窗或界面操作。')
        print('退出码:', run.returncode)
        if run.stdout.strip():
            print('标准输出:', run.stdout.strip())
        if run.stderr.strip():
            print('报错:', run.stderr.strip())
        if target.exists():
            print('快捷指令输出:')
            print(target.read_text(encoding='utf-8'))


if __name__ == '__main__':
    main()
