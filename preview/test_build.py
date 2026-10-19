"""Offline artifact/contract regression checks; these are NOT iPhone tests."""
import importlib.util
import json
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).parent
SPEC = importlib.util.spec_from_file_location('build_shannian', ROOT / 'build_shannian.py')
MOD = None
if (ROOT / 'build_shannian.py').exists():
    MOD = importlib.util.module_from_spec(SPEC)
    SPEC.loader.exec_module(MOD)


def operation(action='note.create', **changes):
    d = dict(action=action, title='标题', body='原话："你好"\n下一行\\路径', query='',
             start='', end='', due='', all_day=False, include_completed=False, question='')
    d.update(changes)
    return d


class BuildContractTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(MOD, '尚未实现可重建的快捷指令生成器')

    def matches(self, value):
        return bool(re.fullmatch(MOD.CONTRACT_REGEX.replace(r'\z', r'\Z'), value))

    def test_all_six_actions_and_clarification_accept_real_json_strings(self):
        for action in ['note.create','note.search','calendar.create','calendar.search',
                       'reminder.create','reminder.search','clarify']:
            for ascii_mode in (True, False):
                s = json.dumps({'operations':[operation(action, title='中文🌟')]}, ensure_ascii=ascii_mode)
                self.assertTrue(self.matches(s), (action, ascii_mode))

    def test_boolean_type_confusion_and_nonallowlisted_actions_fail(self):
        for change in [dict(all_day='false'),dict(include_completed=1),dict(title=[]),
                       dict(action='reminder.delete'),dict(action='note.update')]:
            self.assertFalse(self.matches(json.dumps({'operations':[operation(**change)]})))

    def test_missing_duplicate_extra_or_reordered_fields_fail_closed(self):
        base=json.dumps({'operations':[operation()]}, ensure_ascii=False)
        self.assertFalse(self.matches(base.replace('"title": "标题", ','')))
        self.assertFalse(self.matches(base.replace('"title": "标题"','"title":"标题","title":"第二个"')))
        self.assertFalse(self.matches(base.replace('"question": ""','"question":"", "url":"https://other.invalid"')))
        self.assertFalse(self.matches(base.replace('"action": "note.create", "title": "标题"',
                                                    '"title": "标题", "action": "note.create"')))

    def test_malformed_json_unescaped_controls_and_surrogates_fail(self):
        valid=json.dumps({'operations':[operation()]})
        for bad in [valid[:-1], valid+',', '```json\n'+valid+'\n```',
                    valid.replace('"title": "\\u6807\\u9898"','"title":"bad\nline"'),
                    valid.replace('"title": "\\u6807\\u9898"',r'"title":"\uD800"')]:
            self.assertFalse(self.matches(bad), bad)

    def test_composite_operations_remain_visible_for_explicit_split_guard(self):
        s=json.dumps({'operations':[operation(),operation('reminder.create')]})
        self.assertTrue(self.matches(s))
        source=(ROOT/'ShanNian.xml').read_text()
        self.assertIn('一次只执行一件事',source)
        self.assertIn('多个操作',source)

    def test_native_request_roundtrip_has_no_text_json_interpolation(self):
        doc=MOD.build()
        requests=[a['WFWorkflowActionParameters'] for a in doc['WFWorkflowActions']
                  if a['WFWorkflowActionIdentifier']=='is.workflow.actions.downloadurl']
        self.assertEqual(len(requests),1)
        p=requests[0]
        self.assertEqual(p['WFHTTPBodyType'],'JSON')
        fields=p['WFJSONValues']['Value']['WFDictionaryFieldValueItems']
        messages=next(x for x in fields if x['WFKey']['Value']['string']=='messages')
        self.assertEqual(messages['WFItemType'],2)
        self.assertEqual(messages['WFValue']['WFSerializationType'],'WFArrayParameterState')
        values=messages['WFValue']['Value']
        self.assertEqual(len(values),2)
        self.assertTrue(all(x['WFItemType']==3 and 'WFKey' not in x for x in values))
        self.assertEqual(p['ShowHeaders'],False)

    def test_only_allowed_app_actions_bounded_searches_and_confirmed_backup(self):
        acts=MOD.build()['WFWorkflowActions']
        ids=[a['WFWorkflowActionIdentifier'] for a in acts]
        for aid in ids:
            self.assertFalse(any(x in aid.lower() for x in ['delete','setters.','updatereminder','runscript','runjavascrip','sendmessage','clipboard']))
        for a in acts:
            if a['WFWorkflowActionIdentifier'].startswith('is.workflow.actions.filter.'):
                p=a['WFWorkflowActionParameters']
                self.assertTrue(p['WFContentItemLimitEnabled'])
                self.assertEqual(p['WFContentItemLimitNumber'],10)
        first_note=ids.index('com.apple.mobilenotes.SharingExtension')
        first_request=ids.index('is.workflow.actions.downloadurl')
        self.assertLess(first_note, first_request)
        self.assertIn('is.workflow.actions.choosefrommenu',ids[:first_note])

    def test_runtime_key_is_asked_and_not_baked_into_source(self):
        doc=MOD.build()
        text=json.dumps(doc,ensure_ascii=False)
        self.assertNotRegex(text,r'sk-(?:proj-)?[A-Za-z0-9_-]{25,}')
        asks=[a['WFWorkflowActionParameters'] for a in doc['WFWorkflowActions']
              if a['WFWorkflowActionIdentifier']=='is.workflow.actions.ask']
        key_asks=[a for a in asks if 'API Key' in str(a.get('WFAskActionPrompt',''))]
        self.assertEqual(len(key_asks),1)
        self.assertNotIn('WFAskActionDefaultAnswer',key_asks[0])

    def test_epoch_action_uses_candidate_as_end_date(self):
        b=MOD.Builder(); candidate=b.named('Candidate Date'); b.epoch(candidate)
        p=b.actions[-1]['WFWorkflowActionParameters']
        self.assertEqual(p['WFInput'],MOD.T(candidate))
        self.assertEqual(p['WFTimeUntilFromDate'],MOD.T(b.named('Epoch Date')))

    def test_iso_contract_checks_real_calendar_dates_and_offset_limits(self):
        pattern=MOD.ISO_REGEX.replace(r'\z',r'\Z')
        for value in ['2024-02-29','2000-02-29','2026-10-20T23:30:00Z','2026-10-20T10:00:00+14:00']:
            self.assertRegex(value,pattern)
        for value in ['2026-02-29','2026-02-30','2026-04-31','2026-10-20T10:00:00+14:01']:
            self.assertNotRegex(value,pattern)

    def test_no_item_type_list_sentinel_and_calendar_keyword_is_native_filter(self):
        doc=MOD.build(); self.assertFalse('List Type' in json.dumps(doc))
        calendar=[a['WFWorkflowActionParameters'] for a in doc['WFWorkflowActions']
                  if a['WFWorkflowActionIdentifier']=='is.workflow.actions.filter.calendarevents']
        self.assertTrue(any(any(r['Property']=='Title' for r in p['WFContentItemFilter']['Value']['WFActionParameterFilterTemplates']) for p in calendar))


if __name__=='__main__':
    unittest.main(verbosity=2)
