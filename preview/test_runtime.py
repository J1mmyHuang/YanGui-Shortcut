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

CONFIG = {'Base URL': 'https://offline.invalid/v1', '模型 ID': 'offline-fixture-model', 'API Key': 'offline-test-value'}


def operation(action='note.create', **changes):
    value = dict(action=action, title='手机按钮灵感', body='保留中文、"引号"和\\路径', query='',
                 start='', end='', due='', all_day=False, include_completed=False)
    value.update(changes)
    return value


def response(*operations):
    return {'choices': [{'index': 0, 'message': {'role': 'assistant', 'content':
            json.dumps({'operations': list(operations)}, ensure_ascii=False)}, 'finish_reason': 'stop'}]}


def targets(runtime):
    return [w for w in runtime.writes if not w.get('title', '').startswith('闪念原话')]


def saved_transcripts(runtime):
    return [w for w in runtime.writes if w.get('title', '').startswith('闪念原话')]


class GeneratedRuntimeTests(unittest.TestCase):
    def runtime(self, responses, *, records=None, config=None, backup=None, answers=None):
        self.assertIsNotNone(OfflineRuntime, '缺少用于执行生成动作流的最小离线解释器')
        document = build()
        if backup is not None:
            for action in document['WFWorkflowActions']:
                p = action['WFWorkflowActionParameters']
                text = p.get('WFTextActionText')
                if isinstance(text, dict) and text['Value']['string'] == '否':
                    text['Value']['string'] = backup
        return OfflineRuntime(document, responses=responses, records=records or {}, answers=answers or {},
                              import_answers=config if config is not None else CONFIG)

    def execute(self, responses, **kwargs):
        return self.runtime(responses, **kwargs).run()

    def test_single_note_uses_import_config_and_reaches_native_note(self):
        rt = self.execute([response(operation())])
        self.assertEqual([(w['kind'], w['title']) for w in targets(rt)], [('note', '手机按钮灵感')])
        self.assertIn('保留中文、"引号"和\\路径', targets(rt)[0]['body'])
        self.assertIn('原话：原始中文口述', targets(rt)[0]['body'])
        self.assertEqual(len(rt.requests), 1)
        request = rt.requests[0]
        self.assertEqual(request['url'], 'https://offline.invalid/v1/chat/completions')
        self.assertEqual(request['headers']['Authorization'], 'Bearer offline-test-value')
        self.assertEqual(request['json']['model'], 'offline-fixture-model')
        self.assertEqual(request['json']['messages'][1]['role'], 'user')
        self.assertEqual(saved_transcripts(rt), [])

    def test_one_dictation_is_split_and_classified_into_all_three_apps(self):
        rt = self.execute([response(
            operation('note.create', title='书的推荐', body='这本书值得推荐给朋友'),
            operation('reminder.create', title='买洗衣液', due='2026-10-23T18:00:00+11:00'),
            operation('calendar.create', title='见导师', start='2026-10-21T15:00:00+11:00',
                      end='2026-10-21T16:00:00+11:00'))])
        self.assertEqual([w['kind'] for w in targets(rt)], ['note', 'reminder', 'calendar'])
        self.assertEqual(len(rt.requests), 1)
        self.assertEqual(rt.displays, [])
        self.assertEqual(len(rt.notifications), 1)
        for text in ['已处理 3 项', '📝 备忘录：书的推荐', '⏰ 提醒：买洗衣液 · 10月23日 18:00', '📅 日历：见导师 · 10月21日 15:00']:
            self.assertIn(text, rt.notifications[0])
        # Multi-item speech: each item keeps its own wording, not the whole transcript.
        self.assertNotIn('原话：', targets(rt)[0]['body'])

    def test_positive_epoch_interval_creates_timed_calendar_event(self):
        rt = self.execute([response(operation('calendar.create', title='导师会议',
            start='2026-10-21T15:00:00+11:00', end='2026-10-21T16:00:00+11:00'))])
        self.assertEqual(len(targets(rt)), 1, rt.displays)
        event = targets(rt)[0]
        self.assertEqual(event['kind'], 'calendar')
        self.assertFalse(event['all_day'])
        self.assertEqual(event['start'].isoformat(), '2026-10-21T15:00:00+11:00')
        self.assertEqual((event['end'] - event['start']).total_seconds(), 3600)

    def test_all_day_event_ends_on_its_last_day(self):
        for end, last_day in [('2026-10-24', '2026-10-23'), ('2026-10-26', '2026-10-25')]:
            with self.subTest(end=end):
                rt = self.execute([response(operation('calendar.create', title='出差', all_day=True,
                                                      start='2026-10-23', end=end))])
                event = targets(rt)[0]
                self.assertTrue(event['all_day'])
                self.assertEqual(event['start'].date().isoformat(), '2026-10-23')
                self.assertEqual(event['end'].date().isoformat(), last_day)
                self.assertIn('10月23日', rt.notifications[0])

    def test_reversed_calendar_interval_falls_back_to_note_and_other_items_still_run(self):
        rt = self.execute([response(
            operation('calendar.create', title='坏日程', start='2026-10-21T16:00:00+11:00', end='2026-10-21T15:00:00+11:00'),
            operation('note.create', title='好笔记'))])
        self.assertEqual([w['kind'] for w in targets(rt)], ['note', 'note'])
        self.assertEqual([w['title'] for w in targets(rt)], ['坏日程', '好笔记'])
        self.assertIn('结束必须晚于开始', targets(rt)[0]['body'])
        self.assertFalse(any(w['kind'] == 'calendar' for w in rt.writes))
        self.assertTrue(any('结束必须晚于开始' in d for d in rt.displays))

    def test_ambiguous_calendar_values_never_create_events(self):
        for change in [dict(start='', end=''), dict(start='周末', end='周日'),
                       dict(start='2026-10-21T15:00:00+11:00', end=''),
                       dict(start='2026-02-30T15:00:00+11:00', end='2026-02-30T16:00:00+11:00'),
                       dict(start='2026-10-21', end='2026-10-22', all_day=False),
                       dict(start='2026-10-21T15:00:00+11:00', end='2026-10-22T15:00:00+11:00', all_day=True)]:
            with self.subTest(change=change):
                rt = self.execute([response(operation('calendar.create', **change))])
                self.assertFalse(any(w['kind'] == 'calendar' for w in rt.writes))
                self.assertEqual([w['kind'] for w in targets(rt)], ['note'])

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

    def test_calendar_search_rejects_oversized_or_missing_ranges_without_reading_records(self):
        for change in [dict(start='2026-10-01', end='2026-12-01'), dict(start='', end='')]:
            rt = self.execute([response(operation('calendar.search', **change))],
                              records={'calendarevents': [{'Title': '秘密', 'Start Date': '2026-10-21T10:00:00+11:00',
                                                           'End Date': '2026-10-21T11:00:00+11:00', 'Is All Day': False}]})
            self.assertEqual(rt.reads, [])
            self.assertNotIn('秘密', '\n'.join(rt.displays))
            self.assertTrue(any('日历查询未执行' in d for d in rt.displays))

    def test_note_search_reads_only_matching_synthetic_candidates(self):
        rt = self.execute([response(operation('note.search', query='按钮'))], records={'notes': [
            {'Name': '设计', 'Body': '手机按钮做灵感入口', 'Last Modified Date': '2026-10-19'},
            {'Name': '早餐', 'Body': '燕麦', 'Last Modified Date': '2026-10-20'},
        ]})
        self.assertIn('手机按钮做灵感入口', '\n'.join(rt.displays))
        self.assertNotIn('燕麦', '\n'.join(rt.displays))
        self.assertEqual(targets(rt), [])

    def test_note_search_without_keyword_reads_nothing(self):
        rt = self.execute([response(operation('note.search', query=''))], records={'notes': [
            {'Name': '设计', 'Body': '内容', 'Last Modified Date': '2026-10-19'}]})
        self.assertEqual(rt.reads, [])
        self.assertTrue(any('备忘录查询未执行' in d for d in rt.displays))

    def test_date_only_reminder_becomes_undated_todo_with_the_date_in_notes(self):
        rt = self.execute([response(operation('reminder.create', title='买书', due='2026-10-23'))])
        reminder = targets(rt)[0]
        self.assertEqual(reminder['kind'], 'reminder')
        self.assertEqual(reminder['alert'], 'No Alert')
        self.assertIsNone(reminder['due'])
        self.assertIn('2026-10-23', reminder['notes'])
        self.assertIn('仅日期', rt.notifications[0])

    def test_timed_and_undated_reminders_use_distinct_native_parameters(self):
        for due, enabled in [('2026-10-23T15:00:00+11:00', 'Alert'), ('', 'No Alert')]:
            with self.subTest(due=due):
                rt = self.execute([response(operation('reminder.create', title='买书', due=due))])
                self.assertEqual(len(targets(rt)), 1, rt.displays)
                self.assertEqual(targets(rt)[0]['kind'], 'reminder')
                self.assertEqual(targets(rt)[0]['alert'], enabled)
                self.assertEqual(targets(rt)[0]['due'], due or None)

    def test_malformed_reminder_due_falls_back_to_note(self):
        for due in ['周五', '2026-02-30', '2026-10-23T25:00:00+11:00']:
            with self.subTest(due=due):
                rt = self.execute([response(operation('reminder.create', title='买书', due=due))])
                self.assertFalse(any(w['kind'] == 'reminder' for w in rt.writes))
                self.assertEqual([w['kind'] for w in targets(rt)], ['note'])

    def test_empty_title_gets_a_timestamp_title(self):
        rt = self.execute([response(operation('note.create', title='', body='只有内容'))])
        self.assertTrue(targets(rt)[0]['title'].startswith('闪念 · 2026-10-20T12:00:00'))

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

    def test_search_and_create_can_share_one_dictation(self):
        rt = self.execute([response(operation('note.create', title='新想法'), operation('note.search', query='按钮'))],
                          records={'notes': [{'Name': '设计', 'Body': '手机按钮', 'Last Modified Date': '2026-10-19'}]})
        self.assertEqual([w['title'] for w in targets(rt)], ['新想法'])
        self.assertEqual(rt.notifications, [])
        self.assertIn('📝 备忘录：新想法', rt.displays[0])
        self.assertIn('手机按钮', rt.displays[0])

    def test_api_error_and_bad_contract_save_only_the_transcript(self):
        bad_boolean = response(operation(all_day='false'))
        malformed = {'choices': [{'message': {'content': '{"operations": ['}}]}
        for value in [{'error': {'message': 'synthetic unauthorized'}}, bad_boolean, malformed,
                      {'choices': []}, {'choices': ['not a dictionary']}, {'choices': [{'message': []}]},
                      response()]:
            with self.subTest(response=value):
                rt = self.execute([value])
                self.assertEqual(targets(rt), [])
                self.assertEqual(len(rt.requests), 1)
                self.assertEqual(len(saved_transcripts(rt)), 1)
                self.assertIn('原始中文口述', saved_transcripts(rt)[0]['body'])
                self.assertTrue(any('原始中文口述' in d for d in rt.displays))

    def test_missing_config_stops_before_dictation_and_network(self):
        for blank in ['Base URL', '模型 ID', 'API Key']:
            with self.subTest(blank=blank):
                rt = self.execute([], config={**CONFIG, blank: ''})
                self.assertEqual(rt.requests, [])
                self.assertEqual(rt.writes, [])
                self.assertIn('快捷指令最上方', rt.displays[0])
                self.assertNotIn('is.workflow.actions.dictatetext', rt.executed)

    def test_bad_base_url_is_rejected_before_dictation(self):
        for url in ['http://offline.invalid/v1', 'https://user@offline.invalid/v1', 'https://offline.invalid/v1?x=1', 'offline.invalid']:
            with self.subTest(url=url):
                rt = self.execute([], config={**CONFIG, 'Base URL': url})
                self.assertEqual(rt.requests, [])
                self.assertNotIn('is.workflow.actions.dictatetext', rt.executed)

    def test_pasted_whitespace_and_trailing_slash_are_cleaned(self):
        rt = self.execute([response(operation())], config={
            'Base URL': ' https://offline.invalid/v1/ \n', '模型 ID': ' offline-fixture-model\n', 'API Key': 'offline-test-value \n'})
        self.assertEqual(rt.requests[0]['url'], 'https://offline.invalid/v1/chat/completions')
        self.assertEqual(rt.requests[0]['headers']['Authorization'], 'Bearer offline-test-value')
        self.assertEqual(rt.requests[0]['json']['model'], 'offline-fixture-model')

    def test_empty_dictation_stops_before_network(self):
        rt = self.execute([], answers={'Dictate Text': '   '})
        self.assertEqual(rt.requests, [])
        self.assertEqual(rt.writes, [])
        self.assertTrue(any('没有听到内容' in d for d in rt.displays))

    def test_backup_switch_saves_transcript_before_network_without_duplicates(self):
        rt = self.execute([response(operation())], backup='是')
        self.assertEqual(len(saved_transcripts(rt)), 1)
        self.assertEqual(rt.writes[0]['title'][:4], '闪念原话')
        self.assertEqual(len(targets(rt)), 1)
        rt = self.execute([{'error': {'message': 'synthetic'}}], backup='是')
        self.assertEqual(len(saved_transcripts(rt)), 1)

    def test_transport_abort_keeps_transcript_only_when_backup_is_on(self):
        for backup, saved in [('是', 1), ('否', 0)]:
            with self.subTest(backup=backup):
                rt = self.runtime([OfflineExternalError('synthetic timeout')], backup=backup)
                with self.assertRaises(OfflineExternalError):
                    rt.run()
                self.assertEqual(targets(rt), [])
                self.assertEqual(len(rt.writes), saved)
                if saved:
                    self.assertIn('原始中文口述', rt.writes[0]['body'])

    def test_failure_in_one_item_does_not_block_the_others(self):
        rt = self.execute([response(
            operation('reminder.create', title='坏提醒', due='周五'),
            operation('reminder.create', title='好提醒', due=''),
            operation('note.create', title='好笔记'))])
        self.assertEqual([(w['kind'], w['title']) for w in targets(rt)],
                         [('note', '坏提醒'), ('reminder', '好提醒'), ('note', '好笔记')])


if __name__ == '__main__':
    unittest.main(verbosity=2)
