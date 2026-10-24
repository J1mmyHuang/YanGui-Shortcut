#!/usr/bin/env python3
"""用二分法找出测试版快捷指令里报错的那一个动作。

用法：bisect_mac_test.py 快捷指令名 dist/YanGui-Test.xml "原话" [模型回复JSON]
测试版在每个普通动作后插了检查点：输入 `阶段|||原话` 时，在第一个编号不小于阶段的检查点停下，输出「停在动作 N」。
先不带阶段完整运行；报错时在 1..动作总数 之间二分，找到能停下的最大阶段，下一个动作就是出错的动作。
需要在沙箱外运行。测试版的配置是占位值：给定回复 JSON 时不发请求，所以要带上回复 JSON。
"""
from pathlib import Path
import json
import plistlib
import re
import subprocess
import sys
import tempfile


def run(name, text, timeout=150):
    with tempfile.TemporaryDirectory() as tmp:
        source, target = Path(tmp) / 'in.txt', Path(tmp) / 'out.txt'
        source.write_text(text, encoding='utf-8')
        try:
            r = subprocess.run(['shortcuts', 'run', name, '--input-path', str(source), '--output-path', str(target),
                                '--output-type', 'public.plain-text'], capture_output=True, text=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            return None, '超时'
        out = target.read_text(encoding='utf-8') if target.exists() else ''
        return r.returncode, (out or r.stderr).strip()


def main():
    if len(sys.argv) not in (4, 5):
        raise SystemExit(__doc__)
    name, xml, utterance = sys.argv[1], sys.argv[2], sys.argv[3]
    reply = sys.argv[4] if len(sys.argv) == 5 else None
    actions = plistlib.loads(Path(xml).read_bytes())['WFWorkflowActions']

    def payload(stage):
        head = [] if stage is None else [str(stage)]
        if reply is not None:
            head = head or ['999999']
            head.append(reply)
        return '|||'.join(head + [utterance])

    code, out = run(name, payload(None))
    if code == 0:
        print('完整运行没有报错。输出：\n' + out)
        return
    print('完整运行报错：', out)
    lo, hi = 1, len(actions) + 1  # lo: 已知能停下，hi: 已知报错
    code, out = run(name, payload(lo))
    if not (code == 0 and out.startswith('停在动作')):
        print('阶段 1 就报错：错误发生在第一个检查点之前。', out)
        return
    while hi - lo > 1:
        mid = (lo + hi) // 2
        code, out = run(name, payload(mid))
        ok = code == 0 and out.startswith('停在动作')
        print(f'阶段 {mid}: {"能停下 → " + out if ok else "报错"}')
        lo, hi = (mid, hi) if ok else (lo, mid)
    code, out = run(name, payload(lo))
    match = re.search(r'停在动作 (\d+)( 之前)?：', out)
    stopped, before = int(match.group(1)), bool(match.group(2))

    def is_checkpoint(index):
        action = actions[index]
        params = action['WFWorkflowActionParameters']
        ident = action['WFWorkflowActionIdentifier']
        if ident.endswith('.output'):
            return str(params.get('WFOutput', {}).get('Value', {}).get('string', '')).startswith('停在动作')
        if ident.endswith('.conditional'):
            inp = params.get('WFInput', {})
            return isinstance(inp, dict) and inp.get('Variable', {}).get('Value', {}).get('VariableName') == 'Stage Number' \
                or (params.get('WFControlFlowMode') == 2 and is_checkpoint_end(index))
        return False

    def is_checkpoint_end(index):
        return index >= 2 and actions[index - 1]['WFWorkflowActionIdentifier'].endswith('.output') and is_checkpoint(index - 1)

    print(f'\n最后一个正常的检查点：{"动作 %d 之前" % stopped if before else "动作 %d（%s）" % (stopped, actions[stopped]["WFWorkflowActionIdentifier"])}')
    index = stopped if before else stopped + 1
    shown = 0
    print('出错的是它之后的动作：')
    while index < len(actions) and shown < 3:
        if not is_checkpoint(index) and actions[index]['WFWorkflowActionIdentifier'] != 'is.workflow.actions.comment':
            action = actions[index]
            params = {k: v for k, v in action['WFWorkflowActionParameters'].items() if k != 'UUID'}
            print(f'  [{index}] {action["WFWorkflowActionIdentifier"]}  {json.dumps(params, ensure_ascii=False, default=str)[:700]}')
            shown += 1
        index += 1


if __name__ == '__main__':
    main()
