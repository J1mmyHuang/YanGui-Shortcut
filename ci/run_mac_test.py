#!/usr/bin/env python3
"""在 Mac 上运行已导入的「闪念测试」快捷指令：把原话作为快捷指令输入，打印它的输出和系统报错。

用法：run_mac_test.py 快捷指令名 "原话" [超时秒数]
测试版由 `python3 preview/build_shannian.py --test` 生成（dist/ShanNian-Test.xml），签名后双击导入（无导入问题）。
原话格式：`阶段|||回复JSON|||原话` 用给定回复、不发请求；`probeN|||原话` 只运行第 N 个格式探针。
需要在沙箱外运行；日历、提醒事项的写入是真实写入，测试原话建议带「测试」二字，便于事后清理。
"""
from pathlib import Path
import subprocess
import sys
import tempfile


def main():
    if len(sys.argv) not in (3, 4):
        raise SystemExit(__doc__)
    name, utterance = sys.argv[1], sys.argv[2]
    timeout = int(sys.argv[3]) if len(sys.argv) == 4 else 120
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
