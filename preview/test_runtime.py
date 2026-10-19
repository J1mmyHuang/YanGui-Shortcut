"""Execute generated action routes using synthetic data; never Apple runtime tests."""
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).parent))
from build_shannian import build

try:
    from offline_runtime import OfflineRuntime, OfflineExternalError
except ImportError:
    OfflineRuntime = None
    OfflineExternalError = RuntimeError


def operation(action='note.create', **changes):
    value = dict(action=action, title='手机按钮灵感', body='保留中文、"引号"和\\路径', query='',
                 start='', end='', due='', all_day=False, include_completed=False, question='')
    value.update(changes)
    return value


def response(*operations):
    return {'choices': [{'index': 0, 'message': {'role': 'assistant', 'content':
            json.dumps({'operations': list(operations)}, ensure_ascii=False)}, 'finish_reason': 'stop'}]}


def targets(runtime):
    return [w for w in runtime.writes if not w.get('title', '').startswith('闪念原话')]


class GeneratedRuntimeTests(unittest.TestCase):
    def execute(self, responses, *, records=None, answers=None, menus=None):
        self.assertIsNotNone(OfflineRuntime, '缺少用于执行生成动作流的最小离线解释器')
        rt = OfflineRuntime(build(), responses=responses, records=records or {},
                            answers=answers or {}, menus=menus or ['文字输入'])
        return rt.run()

    def test_dictionary_choice_item_reaches_confirmed_note_write(self):
        # A List-type assumption for choices=[Dictionary] wrongly prevents this route.
        rt = self.execute([response(operation())])
        self.assertEqual([(w['kind'], w['title']) for w in targets(rt)], [('note', '手机按钮灵感')])
        self.assertIn('保留中文、"引号"和\\路径', targets(rt)[0]['body'])
        self.assertEqual(len(rt.requests), 1)
        self.assertEqual(rt.requests[0]['json']['messages'][1]['role'], 'user')

    def test_positive_epoch_interval_creates_timed_calendar_event(self):
        # Reversing First/Second Date yields negative epoch and rejects a valid interval.
        rt = self.execute([response(operation('calendar.create', title='导师会议',
            start='2026-10-21T15:00:00+11:00', end='2026-10-21T16:00:00+11:00'))])
        self.assertEqual(len(targets(rt)), 1, rt.displays)
        event = targets(rt)[0]
        self.assertEqual(event['kind'], 'calendar')
        self.assertEqual(event['start'].isoformat(), '2026-10-21T15:00:00+11:00')
        self.assertEqual((event['end'] - event['start']).total_seconds(), 3600)

    def test_reversed_calendar_interval_performs_no_target_write(self):
        rt = self.execute([response(operation('calendar.create',
            start='2026-10-21T16:00:00+11:00', end='2026-10-21T15:00:00+11:00'))])
        self.assertEqual(targets(rt), [])
        self.assertTrue(any('结束必须晚于开始' in d for d in rt.displays))

    def test_calendar_search_enforces_keyword_and_overlap_boundaries(self):
        rt = self.execute([response(operation('calendar.search', query='导师',
            start='2026-10-21', end='2026-10-22'))], records={'calendarevents': [
                {'Title': '导师跨日会议', 'Start Date': '2026-10-20T23:30:00+11:00',
                 'End Date': '2026-10-21T00:30:00+11:00', 'Is All Day': False},
                {'Title': '买菜', 'Start Date': '2026-10-21T15:00:00+11:00',
                 'End Date': '2026-10-21T16:00:00+11:00', 'Is All Day': False},
                {'Title': '导师下日会议', 'Start Date': '2026-10-22T00:00:00+11:00',
                 'End Date': '2026-10-22T01:00:00+11:00', 'Is All Day': False},
                {'Title': '导师已结束会议', 'Start Date': '2026-10-20T23:00:00+11:00',
                 'End Date': '2026-10-21T00:00:00+11:00', 'Is All Day': False},
            ]})
        output = '\n'.join(rt.displays)
        self.assertIn('导师跨日会议', output)
        self.assertNotIn('买菜', output)
        self.assertNotIn('导师下日会议', output)
        self.assertNotIn('导师已结束会议', output)
        self.assertEqual(targets(rt), [])

    def test_note_search_reads_only_matching_synthetic_candidates(self):
        rt = self.execute([response(operation('note.search', query='按钮'))], records={'notes': [
            {'Name': '设计', 'Body': '手机按钮做灵感入口', 'Last Modified Date': '2026-10-19'},
            {'Name': '早餐', 'Body': '燕麦', 'Last Modified Date': '2026-10-20'},
        ]})
        self.assertIn('手机按钮做灵感入口', '\n'.join(rt.displays))
        self.assertNotIn('燕麦', '\n'.join(rt.displays))
        self.assertEqual(targets(rt), [])

    def test_date_only_reminder_fails_closed_without_invented_time(self):
        rt = self.execute([response(operation('reminder.create', title='买书', due='2026-10-23'))])
        self.assertEqual(targets(rt), [], rt.displays)

    def test_timed_and_undated_reminders_use_distinct_native_parameters(self):
        for due, enabled in [('2026-10-23T15:00:00+11:00', 'Alert'), ('', 'No Alert')]:
            with self.subTest(due=due):
                rt = self.execute([response(operation('reminder.create', title='买书', due=due))])
                self.assertEqual(len(targets(rt)), 1, rt.displays)
                self.assertEqual(targets(rt)[0]['kind'], 'reminder')
                self.assertEqual(targets(rt)[0]['alert'], enabled)
                self.assertEqual(targets(rt)[0]['due'], due or None)

    def test_reminder_search_defaults_to_incomplete_and_filters_title(self):
        rt = self.execute([response(operation('reminder.search', query='买'))], records={'reminders': [
            {'Title': '买洗衣液', 'Due Date': None, 'Is Completed': False, 'List': '提醒事项'},
            {'Title': '买书已完成', 'Due Date': None, 'Is Completed': True, 'List': '提醒事项'},
            {'Title': '写论文', 'Due Date': None, 'Is Completed': False, 'List': '提醒事项'},
        ]})
        output = '\n'.join(rt.displays)
        self.assertIn('买洗衣液', output)
        self.assertNotIn('买书已完成', output)
        self.assertNotIn('写论文', output)
        self.assertEqual(targets(rt), [])

    def test_reminder_search_range_excludes_upper_boundary_and_missing_due(self):
        rt = self.execute([response(operation('reminder.search', start='2026-10-21', end='2026-10-22'))],
            records={'reminders': [
                {'Title': '当日买书', 'Due Date': '2026-10-21T00:00:00+11:00', 'Is Completed': False, 'List': '提醒事项'},
                {'Title': '次日买书', 'Due Date': '2026-10-22T00:00:00+11:00', 'Is Completed': False, 'List': '提醒事项'},
                {'Title': '无期买书', 'Due Date': None, 'Is Completed': False, 'List': '提醒事项'},
            ]})
        output = '\n'.join(rt.displays)
        self.assertIn('当日买书', output)
        self.assertNotIn('次日买书', output)
        self.assertNotIn('无期买书', output)

    def test_multiple_operations_are_all_rejected_before_target_writes(self):
        rt = self.execute([response(operation(), operation('reminder.create'))])
        self.assertEqual(targets(rt), [])
        self.assertTrue(any('多个操作' in d for d in rt.displays))

    def test_api_error_and_bad_contract_do_not_reach_target_writes(self):
        bad_boolean = response(operation(all_day='false'))
        malformed = {'choices': [{'message': {'content': '{"operations": ['}}]}
        for value in [{'error': {'message': 'synthetic unauthorized'}}, bad_boolean, malformed,
                      {'choices': []}, {'choices': ['not a dictionary']}, {'choices': [{'message': []}]}]:
            with self.subTest(response=value):
                rt = self.execute([value])
                self.assertEqual(targets(rt), [])
                self.assertEqual(len(rt.requests), 1)

    def test_clarification_reuses_context_and_executes_exactly_once(self):
        rt = self.execute([
            response(operation('clarify', question='具体几点？')),
            response(operation('note.create', title='澄清后的灵感')),
        ], answers={'具体几点？': '下午三点'})
        self.assertEqual(len(rt.requests), 2)
        self.assertIn('下午三点', rt.requests[1]['json']['messages'][1]['content'])
        self.assertEqual([w['title'] for w in targets(rt)], ['澄清后的灵感'])

    def test_clarification_limit_stops_without_target_writes(self):
        rt = self.execute([response(operation('clarify', question='请补充？'))] * 3,
                          answers={'请补充？': '仍不明确'})
        self.assertEqual(len(rt.requests), 3)
        self.assertEqual(targets(rt), [])
        self.assertTrue(any('三轮' in d for d in rt.displays))

    def test_declining_backup_stops_before_network_and_any_write(self):
        rt = self.execute([], menus=['文字输入', '取消'])
        self.assertEqual(rt.requests, [])
        self.assertEqual(rt.writes, [])

    def test_transport_abort_has_only_preconfirmed_recovery_note(self):
        self.assertIsNotNone(OfflineRuntime, '缺少最小离线解释器')
        rt = OfflineRuntime(build(), responses=[OfflineExternalError('synthetic timeout')], menus=['文字输入'])
        with self.assertRaises(OfflineExternalError):
            rt.run()
        self.assertEqual(targets(rt), [])
        self.assertEqual(len(rt.writes), 1)
        self.assertIn('原始中文口述', rt.writes[0]['body'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
