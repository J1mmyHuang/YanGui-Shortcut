"""Execute generated action routes using synthetic data; never Apple runtime tests."""
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).parent))
from build_yangui import build

try:
    from offline_runtime import OfflineRuntime, OfflineExternalError
except ImportError:
    OfflineRuntime = None
    OfflineExternalError = RuntimeError

CONFIG = {'选择 API 协议': 'openai', 'Base URL': 'https://offline.invalid/v1',
          '模型 ID': 'offline-fixture-model', 'API Key': 'offline-test-value'}
ANTHROPIC = {**CONFIG, '选择 API 协议': 'anthropic', 'Base URL': 'https://offline.invalid/anthropic'}
KEY = CONFIG['API Key']


def operation(action='note.create', **changes):
    value = dict(action=action, title='手机按钮灵感', body='保留中文、"引号"和\\路径', query='',
                 start='', end='', due='', all_day=False, include_completed=False, checklist=False)
    value.update(changes)
    return value


def response(*operations):
    return {'choices': [{'index': 0, 'message': {'role': 'assistant', 'content':
            json.dumps({'operations': list(operations)}, ensure_ascii=False)}, 'finish_reason': 'stop'}]}


def anthropic_response(*operations, thinking=False, fenced=False, prose=False):
    text = json.dumps({'operations': list(operations)}, ensure_ascii=False)
    if fenced:
        text = '```json\n' + text + '\n```'
    if prose:
        text = '好的，结果如下：\n' + text + '\n以上。'
    blocks = [{'type': 'text', 'text': text}]
    if thinking:
        blocks.insert(0, {'type': 'thinking', 'thinking': '先想一想', 'signature': 'x'})
    return {'id': 'msg_1', 'type': 'message', 'role': 'assistant', 'content': blocks, 'stop_reason': 'end_turn'}


def models(*ids, key='data'):
    return {'object': 'list', key: [{'id': i, 'object': 'model'} for i in ids]}


def targets(runtime):
    return [w for w in runtime.writes if not w.get('title', '').startswith('YanGui 原话')]


def saved_transcripts(runtime):
    return [w for w in runtime.writes if w.get('title', '').startswith('YanGui 原话')]


class RuntimeCase(unittest.TestCase):
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



class GeneratedRuntimeTests(RuntimeCase):
    def test_single_note_uses_import_config_and_reaches_native_note(self):
        rt = self.execute([response(operation())])
        self.assertEqual([(w['kind'], w['title']) for w in targets(rt)], [('note', '手机按钮灵感')])
        self.assertIn('保留中文、"引号"和\\路径', targets(rt)[0]['body'])
        self.assertIn('原话：原始中文口述', targets(rt)[0]['body'])
        self.assertEqual(len(rt.requests), 1)
        request = rt.requests[0]
        self.assertEqual(request['url'], 'https://offline.invalid/v1/chat/completions')
        self.assertEqual(request['method'], 'POST')
        self.assertIs(request['advanced'], True)
        self.assertEqual(request['headers']['Authorization'], 'Bearer offline-test-value')
        self.assertEqual(request['json']['model'], 'offline-fixture-model')
        self.assertEqual([m['role'] for m in request['json']['messages']], ['system', 'user'])
        self.assertIn('原始中文口述', request['json']['messages'][1]['content'])
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

    def test_unrecognised_or_vague_reminder_deadlines_still_create_an_undated_reminder(self):
        for due in ['周五', '一会儿', '待会儿', '2026-02-30', '2026-10-23T25:00:00+11:00']:
            with self.subTest(due=due):
                rt = self.execute([response(operation('reminder.create', title='交作业', due=due))])
                self.assertEqual([w['kind'] for w in rt.writes], ['reminder'], rt.displays)
                reminder = rt.writes[0]
                self.assertEqual((reminder['alert'], reminder['due']), ('No Alert', None))
                self.assertIn(due, reminder['notes'])
                self.assertIn('未设提醒时间', rt.notifications[0])
                self.assertEqual(rt.displays, [])

    def test_empty_deadline_is_a_plain_todo_without_a_time_phrase(self):
        rt = self.execute([response(operation('reminder.create', title='交作业', due=''))])
        self.assertEqual((rt.writes[0]['alert'], rt.writes[0]['due']), ('No Alert', None))
        self.assertNotIn('时间说法', rt.writes[0]['notes'])

    def test_empty_title_gets_a_timestamp_title(self):
        rt = self.execute([response(operation('note.create', title='', body='只有内容'))])
        self.assertTrue(targets(rt)[0]['title'].startswith('YanGui · 2026-10-20T12:00:00'))

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
        for blank in ['Base URL', 'API Key']:
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
            '选择 API 协议': ' OpenAI\n', 'Base URL': ' https://offline.invalid/v1/ \n', '模型 ID': ' offline-fixture-model\n', 'API Key': 'offline-test-value \n'})
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
        self.assertTrue(rt.writes[0]['title'].startswith('YanGui 原话'))
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
            operation('calendar.create', title='坏日程', start='2026-10-21T16:00:00+11:00', end='2026-10-21T15:00:00+11:00'),
            operation('reminder.create', title='好提醒', due=''),
            operation('note.create', title='好笔记'))])
        self.assertEqual([(w['kind'], w['title']) for w in targets(rt)],
                         [('note', '坏日程'), ('reminder', '好提醒'), ('note', '好笔记')])


class LocalTimeAndListTests(RuntimeCase):
    """Times written as device-local wall-clock text, classification fallbacks and checklist lines."""

    def test_local_times_without_offset_create_events_in_the_device_zone(self):
        rt = self.execute([response(operation('calendar.create', title='会议',
            start='2026-10-20T15:00:00', end='2026-10-20T16:00:00'))])
        event = targets(rt)[0]
        self.assertEqual(event['start'].isoformat(), '2026-10-20T15:00:00+11:00')
        self.assertEqual(event['end'].isoformat(), '2026-10-20T16:00:00+11:00')
        self.assertIn('10月20日 15:00', rt.notifications[0])

    def test_local_time_reminder_is_set_at_that_wall_clock_time(self):
        rt = self.execute([response(operation('reminder.create', title='开会', due='2026-10-20T15:00:00'))])
        reminder = targets(rt)[0]
        self.assertEqual((reminder['kind'], reminder['alert']), ('reminder', 'Alert'))
        self.assertEqual(reminder['due'], '2026-10-20T15:00:00+11:00')

    def test_sloppy_but_unambiguous_time_spellings_are_normalised(self):
        for value in ['2026-10-20 15:00', '2026-10-20T15:00', '2026-10-20 15:00:00', '2026-10-20T15:00:00']:
            with self.subTest(value=value):
                rt = self.execute([response(operation('reminder.create', title='开会', due=value))])
                self.assertEqual(targets(rt)[0]['due'], '2026-10-20T15:00:00+11:00')
        rt = self.execute([response(operation('calendar.create', title='会议', start='2026-10-20 15:00', end='2026-10-20 16:00'))])
        self.assertEqual(targets(rt)[0]['kind'], 'calendar')

    def test_explicit_offsets_still_mean_that_instant(self):
        rt = self.execute([response(operation('reminder.create', title='开会', due='2026-10-20T04:00:00Z'))])
        from datetime import datetime
        self.assertEqual(datetime.fromisoformat(targets(rt)[0]['due']), datetime.fromisoformat('2026-10-20T15:00:00+11:00'))

    def test_unparseable_calendar_time_falls_back_to_a_note_that_shows_what_was_received(self):
        rt = self.execute([response(operation('calendar.create', title='开会', start='今天下午3点', end='今天下午4点'))])
        self.assertFalse(any(w['kind'] == 'calendar' for w in rt.writes))
        self.assertEqual([w['kind'] for w in targets(rt)], ['note'])
        self.assertIn('收到：今天下午3点', targets(rt)[0]['body'] + '\n'.join(rt.displays))
        self.assertTrue(any('今天下午3点' in d for d in rt.displays))

    def test_checklist_items_become_real_checklist_entries_on_one_note(self):
        rt = self.execute([response(operation('note.create', title='购物清单', body='水果\n蔬菜\n可乐', checklist=True))])
        self.assertEqual(len(rt.writes), 1)
        note = rt.writes[0]
        self.assertEqual((note['title'], note['body']), ('购物清单', ''))
        self.assertEqual(note['checklist'], ['水果', '蔬菜', '可乐'])
        self.assertIn('📝 清单：购物清单（3 项）', rt.notifications[0])
        self.assertNotIn('☐', json.dumps(rt.writes, ensure_ascii=False))

    def test_leading_symbols_blank_lines_and_spaces_are_cleaned_from_checklist_lines(self):
        body = '- 水果\n\n  • 蔬菜  \n☐ 可乐\n○ 牛奶\n   \n'
        rt = self.execute([response(operation('note.create', title='购物清单', body=body, checklist=True))])
        self.assertEqual(rt.writes[0]['checklist'], ['水果', '蔬菜', '可乐', '牛奶'])

    def test_checklist_note_carries_no_transcript_and_empty_body_still_creates_the_note(self):
        rt = self.execute([response(operation('note.create', title='空清单', body='', checklist=True))])
        self.assertEqual((rt.writes[0]['title'], rt.writes[0]['checklist']), ('空清单', []))
        self.assertNotIn('原始中文口述', json.dumps(rt.writes, ensure_ascii=False))

    def test_plain_notes_are_unchanged_when_checklist_is_false(self):
        rt = self.execute([response(operation('note.create', title='想法', body='一条\n两行', checklist=False))])
        self.assertEqual(rt.writes[0]['checklist'], [])
        self.assertIn('一条\n两行', rt.writes[0]['body'])

    def test_checklist_shares_one_dictation_with_other_destinations(self):
        rt = self.execute([response(
            operation('note.create', title='购物清单', body='水果\n蔬菜', checklist=True),
            operation('calendar.create', title='会议', start='2026-10-20T15:00:00', end='2026-10-20T16:00:00'),
            operation('note.create', title='想法', body='普通笔记'))])
        self.assertEqual([w['kind'] for w in rt.writes], ['note', 'calendar', 'note'])
        self.assertEqual(rt.writes[0]['checklist'], ['水果', '蔬菜'])
        self.assertEqual(rt.writes[2]['checklist'], [])

    def test_notes_intents_without_the_iphone_descriptor_are_rejected_by_the_interpreter(self):
        document = build()
        for action in document['WFWorkflowActions']:
            if action['WFWorkflowActionIdentifier'] == 'com.apple.mobilenotes.CreateChecklistItemLinkAction':
                del action['WFWorkflowActionParameters']['AppIntentDescriptor']
        rt = OfflineRuntime(document, responses=[response(operation('note.create', title='清单', body='水果', checklist=True))],
                            import_answers=CONFIG)
        with self.assertRaises(ValueError):
            rt.run()


class MacTestVariantTests(RuntimeCase):
    def run_variant(self, responses, utterance='测试：今天下午两点有个会', **kwargs):
        rt = OfflineRuntime(build(test=True), responses=responses,
                            shortcut_input=utterance, **kwargs)
        return rt.run()

    def test_input_text_is_processed_and_the_report_is_returned_as_output(self):
        rt = self.run_variant([response(operation('calendar.create', title='测试会议',
                                                  start='2026-10-20T14:00:00', end='2026-10-20T15:00:00'))])
        self.assertEqual([w['kind'] for w in rt.writes], ['calendar'])
        self.assertIn('📅 日历：测试会议 · 10月20日 14:00', rt.output)
        self.assertIn('测试：今天下午两点有个会', rt.requests[0]['json']['messages'][1]['content'])
        self.assertEqual((rt.notifications, rt.displays), ([], []))

    def test_notes_are_text_only_and_checklist_items_are_listed(self):
        rt = self.run_variant([response(operation('note.create', title='购物清单', body='水果\n蔬菜', checklist=True),
                                        operation('note.create', title='想法', body='内容'))])
        self.assertEqual(rt.writes, [])
        for text in ['📝 清单：购物清单（2 项）', '☑ 水果', '☑ 蔬菜', '📝 备忘录：想法']:
            self.assertIn(text, rt.output)

    def test_real_notes_switch_writes_notes_and_checklist_items(self):
        rt = OfflineRuntime(build(test=True, real_notes=True), shortcut_input='测试：买菜清单',
                            responses=[response(operation('note.create', title='买菜清单', body='西红柿\n- 鸡蛋', checklist=True),
                                                operation('note.create', title='想法', body='内容'))])
        rt.run()
        self.assertEqual([(w['kind'], w['title'], w.get('checklist')) for w in rt.writes],
                         [('note', '买菜清单', ['西红柿', '鸡蛋']), ('note', '想法', [])])
        self.assertIn('📝 清单：买菜清单（2 项）', rt.output)

    def test_a_config_line_supplies_the_api_settings_for_one_run(self):
        config = json.dumps({'protocol': 'openai', 'base_url': 'https://api.example.test/v1/', 'key': 'k-local', 'model': 'm-local'})
        rt = self.run_variant([response(operation('reminder.create', title='买牛奶'))],
                              utterance=f'config={config}\n999999|||测试：提醒我买牛奶')
        self.assertEqual(rt.requests[0]['url'], 'https://api.example.test/v1/chat/completions')
        self.assertEqual(rt.requests[0]['headers']['Authorization'], 'Bearer k-local')
        self.assertEqual(rt.requests[0]['json']['model'], 'm-local')
        self.assertIn('测试：提醒我买牛奶', rt.requests[0]['json']['messages'][1]['content'])
        self.assertNotIn('config=', rt.requests[0]['json']['messages'][1]['content'])
        self.assertNotIn('k-local', rt.output)
        self.assertEqual([w['title'] for w in rt.writes], ['买牛奶'])

    def test_failures_are_returned_as_output_not_dialogs(self):
        rt = self.run_variant([{'error': {'message': 'synthetic quota'}}])
        self.assertIn('synthetic quota', rt.output)
        self.assertEqual(rt.writes, [])


class MacTestVariantDebugTests(RuntimeCase):
    """Stages and reply override of the Mac test variant (never part of the shipped shortcut)."""
    CAL = dict(title='测试会议', start='2026-10-20T14:00:00', end='2026-10-20T15:00:00')

    def run_variant(self, shortcut_input, responses=None):
        rt = OfflineRuntime(build(test=True), responses=responses if responses is not None else [response(operation('calendar.create', **self.CAL))],
                            shortcut_input=shortcut_input)
        return rt.run()

    def test_plain_input_runs_everything_and_lists_the_raw_fields(self):
        rt = self.run_variant('测试：今天下午两点有个会')
        self.assertEqual([w['kind'] for w in rt.writes], ['calendar'])
        self.assertIn('🧪 动作=calendar.create | 开始=2026-10-20T14:00:00 | 结束=2026-10-20T15:00:00', rt.output)

    def test_stage_stops_at_the_first_checkpoint_at_or_after_the_stage(self):
        stops = []
        for stage in [1, 50, 400, 800, 1200, 1500]:
            rt = self.run_variant(f'{stage}|||测试：今天下午两点有个会')
            self.assertTrue(rt.output.startswith('停在动作 '), rt.output)
            index = int(rt.output.split('停在动作 ')[1].split('：')[0].split(' ')[0])
            self.assertGreaterEqual(index, stage)
            stops.append(index)
            self.assertFalse(any(w['kind'] == 'calendar' for w in rt.writes) and stage < 1200)
        self.assertEqual(stops, sorted(stops))  # a later stage never stops earlier

    def test_a_stage_past_the_last_action_runs_to_the_end(self):
        rt = self.run_variant('999999|||测试：今天下午两点有个会')
        self.assertEqual([w['kind'] for w in rt.writes], ['calendar'])
        self.assertIn('📅 日历：', rt.output)

    def test_every_plain_action_is_followed_by_one_checkpoint(self):
        doc = build(test=True)['WFWorkflowActions']
        checkpoints = [a for a in doc if a['WFWorkflowActionIdentifier'] == 'is.workflow.actions.output'
                       and 'WFOutput' in a['WFWorkflowActionParameters']
                       and a['WFWorkflowActionParameters']['WFOutput']['Value']['string'].startswith('停在动作')]
        self.assertGreater(len(checkpoints), 300)

    def test_reply_override_replaces_the_model_text(self):
        reply = json.dumps({'operations': [operation('reminder.create', title='来自覆盖', due='')]}, ensure_ascii=False)
        rt = self.run_variant(f'999999|||{reply}|||测试：覆盖')
        self.assertEqual([(w['kind'], w['title']) for w in rt.writes], [('reminder', '来自覆盖')])
        self.assertEqual(rt.requests, [])  # a given reply replaces the request itself


class ChecklistAndSearchGuardTests(RuntimeCase):
    def test_empty_checklist_text_never_reaches_split_text(self):
        # Split Text with an empty text parameter shows up on a real iPhone as an unset parameter.
        for body in ['', '- ', '☐']:
            with self.subTest(body=body):
                rt = self.execute([response(operation('note.create', title='空清单', body=body, checklist=True))])
                self.assertEqual((rt.writes[0]['title'], rt.writes[0]['checklist']), ('空清单', []))
                self.assertFalse('is.workflow.actions.text.split' in rt.executed)

    def test_literal_backslash_n_in_a_checklist_still_splits_into_items(self):
        # Seen from a real model: the list came back as "可乐\\n橙汁\\n卷纸", a backslash and n instead of a line break.
        rt = self.execute([response(operation('note.create', title='超市购物清单', body='可乐\\n橙汁\\r\\n卷纸', checklist=True))])
        self.assertEqual(rt.writes[0]['checklist'], ['可乐', '橙汁', '卷纸'])

    def test_whitespace_or_symbol_only_lines_create_no_items(self):
        for body in ['   ', '☐\n☐', '\n\n']:
            with self.subTest(body=body):
                rt = self.execute([response(operation('note.create', title='空清单', body=body, checklist=True))])
                self.assertEqual(rt.writes[0]['checklist'], [])

    def test_time_comparisons_use_the_dates_themselves(self):
        rt = self.execute([response(operation('calendar.create', title='会议',
            start='2026-10-20T14:00:00', end='2026-10-20T15:00:00'))])
        self.assertEqual(rt.writes[0]['start'].isoformat(), '2026-10-20T14:00:00+11:00')
        rt = self.execute([response(operation('calendar.create', title='会议',
            start='2026-10-20T15:00:00', end='2026-10-20T14:00:00'))])
        self.assertFalse(any(w['kind'] == 'calendar' for w in rt.writes))
        rt = self.execute([response(operation('calendar.create', title='会议',
            start='2026-10-20T15:00:00', end='2026-10-20T15:00:00'))])
        self.assertFalse(any(w['kind'] == 'calendar' for w in rt.writes))


class ProtocolAndModelTests(RuntimeCase):
    """Protocol choice, /models selection and visible error reasons."""

    def run_one(self, responses, **kwargs):
        return self.execute(responses, **kwargs)

    def test_interpreter_rejects_item_types_that_real_shortcuts_would_mangle(self):
        # The old request tagged dictionary messages as item type 3 (number); the real engine
        # then sends broken messages and the provider answers with an error.
        document = build()
        for action in document['WFWorkflowActions']:
            fields = action['WFWorkflowActionParameters'].get('WFJSONValues')
            if fields:
                for item in fields['Value']['WFDictionaryFieldValueItems']:
                    if item['WFItemType'] == 2:
                        item['WFValue']['Value'][0]['WFItemType'] = 3
        rt = OfflineRuntime(document, responses=[response(operation())], import_answers=CONFIG)
        with self.assertRaises(ValueError):
            rt.run()

    def test_anthropic_protocol_request_shape(self):
        rt = self.run_one([anthropic_response(operation())], config=ANTHROPIC)
        self.assertEqual([w['title'] for w in targets(rt)], ['手机按钮灵感'])
        request = rt.requests[0]
        self.assertEqual(request['url'], 'https://offline.invalid/anthropic/v1/messages')
        self.assertEqual(request['method'], 'POST')
        self.assertEqual(request['headers'], {'x-api-key': KEY, 'anthropic-version': '2023-06-01',
                                              'Content-Type': 'application/json'})
        body = request['json']
        self.assertEqual(sorted(body), ['max_tokens', 'messages', 'model', 'system'])
        self.assertEqual(body['model'], 'offline-fixture-model')
        self.assertEqual(body['max_tokens'], '4096')
        self.assertIn('智能', body['system'] + '智能')
        self.assertEqual([m['role'] for m in body['messages']], ['user'])
        self.assertIn('原始中文口述', body['messages'][0]['content'])

    def test_anthropic_base_url_forms_resolve_to_one_messages_endpoint(self):
        for base in ['https://api.anthropic.com', 'https://api.anthropic.com/', 'https://api.anthropic.com/v1',
                     'https://api.anthropic.com/v1/', 'https://api.anthropic.com/v1/messages']:
            with self.subTest(base=base):
                rt = self.run_one([anthropic_response(operation())], config={**ANTHROPIC, 'Base URL': base})
                self.assertEqual(rt.requests[0]['url'], 'https://api.anthropic.com/v1/messages')
        rt = self.run_one([anthropic_response(operation())], config={**ANTHROPIC, 'Base URL': 'https://gw.example.com/api/anthropic/'})
        self.assertEqual(rt.requests[0]['url'], 'https://gw.example.com/api/anthropic/v1/messages')

    def test_openai_base_url_forms_resolve_to_one_completions_endpoint(self):
        for base in ['https://offline.invalid/v1', 'https://offline.invalid/v1/', 'https://offline.invalid/v1/chat/completions']:
            with self.subTest(base=base):
                rt = self.run_one([response(operation())], config={**CONFIG, 'Base URL': base})
                self.assertEqual(rt.requests[0]['url'], 'https://offline.invalid/v1/chat/completions')

    def test_anthropic_reply_skips_thinking_blocks_and_fences(self):
        for kwargs in [dict(thinking=True), dict(fenced=True), dict(prose=True), dict(thinking=True, fenced=True)]:
            with self.subTest(kwargs=kwargs):
                rt = self.run_one([anthropic_response(operation(), operation('reminder.create', title='买书'), **kwargs)],
                                  config=ANTHROPIC)
                self.assertEqual([w['kind'] for w in targets(rt)], ['note', 'reminder'])

    def test_openai_reply_with_code_fence_is_accepted(self):
        fenced = {'choices': [{'message': {'content': '```json\n' + json.dumps({'operations': [operation()]}, ensure_ascii=False) + '\n```'}}]}
        rt = self.run_one([fenced])
        self.assertEqual(len(targets(rt)), 1)

    def test_anthropic_failures_keep_transcript_and_show_reason(self):
        for value in [{'type': 'error', 'error': {'type': 'authentication_error', 'message': 'invalid x-api-key'}},
                      {'content': []}, {'id': 'msg'}, {'content': [{'type': 'thinking', 'thinking': 'x'}]},
                      {'content': [{'type': 'text', 'text': '没有 JSON'}]},
                      {'content': [{'type': 'text', 'text': '{"operations": ['}]}]:
            with self.subTest(value=value):
                rt = self.run_one([value], config=ANTHROPIC)
                self.assertEqual(targets(rt), [])
                self.assertEqual(len(saved_transcripts(rt)), 1)
        rt = self.run_one([{'type': 'error', 'error': {'type': 'authentication_error', 'message': 'invalid x-api-key'}}], config=ANTHROPIC)
        self.assertIn('invalid x-api-key', rt.displays[0])

    def test_protocol_must_be_openai_or_anthropic(self):
        for bad in ['gemini', '', 'openai anthropic']:
            with self.subTest(bad=bad):
                rt = self.run_one([], config={**CONFIG, '选择 API 协议': bad})
                self.assertEqual(rt.requests, [])
                self.assertNotIn('is.workflow.actions.dictatetext', rt.executed)
        rt = self.run_one([anthropic_response(operation())], config={**ANTHROPIC, '选择 API 协议': 'Anthropic'})
        self.assertEqual(len(targets(rt)), 1)

    def test_provider_error_text_is_shown_without_leaking_the_key(self):
        for protocol_config, value in [(CONFIG, {'error': {'message': 'The model `nope` does not exist', 'type': 'invalid_request_error'}}),
                                       (CONFIG, {'error': 'quota exceeded for this plan'})]:
            rt = self.run_one([value], config=protocol_config)
            shown = '\n'.join(rt.displays)
            self.assertTrue('does not exist' in shown or 'quota exceeded' in shown, shown)
            self.assertIn('https://offline.invalid/v1/chat/completions', shown)
            self.assertIn('offline-fixture-model', shown)
            self.assertIn('openai', shown)
            self.assertNotIn(KEY, shown)
            self.assertEqual(len(saved_transcripts(rt)), 1)

    def test_unexpected_reply_shows_the_start_of_the_response(self):
        rt = self.run_one([{'code': 40001, 'msg': 'balance too low'}])
        self.assertIn('缺少 choices', rt.displays[0])
        self.assertIn('balance too low', rt.displays[0])
        self.assertNotIn(KEY, rt.displays[0])

    def test_blank_model_lists_openai_models_and_uses_the_choice(self):
        rt = self.run_one([models('model-a', 'model-b', 'model-c'), response(operation())],
                          config={**CONFIG, '模型 ID': ''}, answers={'Choose From List': 'model-b'})
        listing, chat = rt.requests
        self.assertEqual((listing['method'], listing['url']), ('GET', 'https://offline.invalid/v1/models'))
        self.assertEqual(listing['headers'], {'Authorization': 'Bearer offline-test-value'})
        self.assertIsNone(listing['json'])
        self.assertEqual(rt.choices, [['model-a', 'model-b', 'model-c']])
        self.assertEqual(chat['json']['model'], 'model-b')
        self.assertEqual(len(targets(rt)), 1)
        self.assertIn('本次使用模型：model-b', rt.notifications[0])
        self.assertEqual(rt.executed.index('is.workflow.actions.choosefromlist') < rt.executed.index('is.workflow.actions.dictatetext'), True)

    def test_blank_model_lists_anthropic_models_with_anthropic_headers(self):
        rt = self.run_one([models('claude-x', 'claude-y'), anthropic_response(operation())],
                          config={**ANTHROPIC, '模型 ID': ''})
        listing, chat = rt.requests
        self.assertEqual(listing['url'], 'https://offline.invalid/anthropic/v1/models?limit=1000')
        self.assertEqual(listing['headers'], {'x-api-key': KEY, 'anthropic-version': '2023-06-01'})
        self.assertEqual(chat['json']['model'], 'claude-x')

    def test_filled_model_never_calls_models(self):
        rt = self.run_one([response(operation())])
        self.assertEqual(len(rt.requests), 1)
        self.assertEqual(rt.choices, [])
        self.assertNotIn('本次使用模型', ' '.join(rt.notifications))

    def test_models_failures_stop_before_dictation_and_writes(self):
        cases = [({'error': {'message': 'invalid api key'}}, 'invalid api key'),
                 ({'object': 'list'}, '没有返回可用的模型列表'), ({'data': []}, '没有返回可用的模型列表'),
                 ({'models': [{'id': 'x'}]}, '没有返回可用的模型列表')]
        for value, expected in cases:
            with self.subTest(value=value):
                rt = self.run_one([value], config={**CONFIG, '模型 ID': ''})
                self.assertEqual(rt.writes, [])
                self.assertNotIn('is.workflow.actions.dictatetext', rt.executed)
                self.assertIn(expected, rt.displays[0])
                self.assertIn('手动填写模型 ID', rt.displays[0])
                self.assertNotIn(KEY, rt.displays[0])


if __name__ == '__main__':
    unittest.main(verbosity=2)
