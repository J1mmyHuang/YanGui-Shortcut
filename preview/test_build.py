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
             start='', end='', due='', all_day=False, include_completed=False)
    d.update(changes)
    return d


def identifiers(doc):
    return [a['WFWorkflowActionIdentifier'] for a in doc['WFWorkflowActions']]


class BuildContractTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(MOD, '尚未实现可重建的快捷指令生成器')

    def matches(self, value):
        return bool(re.fullmatch(MOD.CONTRACT_REGEX.replace(r'\z', r'\Z'), value))

    def test_all_six_actions_accept_real_json_strings(self):
        for action in ['note.create','note.search','calendar.create','calendar.search',
                       'reminder.create','reminder.search']:
            for ascii_mode in (True, False):
                s = json.dumps({'operations':[operation(action, title='中文🌟')]}, ensure_ascii=ascii_mode)
                self.assertTrue(self.matches(s), (action, ascii_mode))

    def test_boolean_type_confusion_and_nonallowlisted_actions_fail(self):
        for change in [dict(all_day='false'),dict(include_completed=1),dict(title=[]),
                       dict(action='reminder.delete'),dict(action='note.update'),dict(action='clarify')]:
            self.assertFalse(self.matches(json.dumps({'operations':[operation(**change)]})))

    def test_missing_duplicate_extra_or_reordered_fields_fail_closed(self):
        base=json.dumps({'operations':[operation()]}, ensure_ascii=False)
        self.assertFalse(self.matches(base.replace('"title": "标题", ','')))
        self.assertFalse(self.matches(base.replace('"title": "标题"','"title":"标题","title":"第二个"')))
        self.assertFalse(self.matches(base.replace('"include_completed": false','"include_completed": false, "url":"https://other.invalid"')))
        self.assertFalse(self.matches(base.replace('"action": "note.create", "title": "标题"',
                                                    '"title": "标题", "action": "note.create"')))

    def test_malformed_json_unescaped_controls_and_surrogates_fail(self):
        valid=json.dumps({'operations':[operation()]})
        for bad in [valid[:-1], valid+',', '```json\n'+valid+'\n```',
                    valid.replace('"title": "\\u6807\\u9898"','"title":"bad\nline"'),
                    valid.replace('"title": "\\u6807\\u9898"',r'"title":"\uD800"')]:
            self.assertFalse(self.matches(bad), bad)

    def test_multiple_operations_pass_the_contract_and_are_processed_in_a_loop(self):
        s=json.dumps({'operations':[operation(),operation('reminder.create'),operation('calendar.create')]})
        self.assertTrue(self.matches(s))
        self.assertTrue(self.matches(json.dumps({'operations':[]})))
        ids=identifiers(MOD.build())
        self.assertIn('is.workflow.actions.repeat.each',ids)

    def test_prompt_classifies_into_three_apps_and_splits_items(self):
        prompt=MOD.SYSTEM_PROMPT
        for needle in ['calendar.create','reminder.create','note.create','拆成互相独立的事项','一律用 note.create']:
            self.assertIn(needle,prompt)
        self.assertNotIn('clarify',prompt)
        self.assertNotIn('question',prompt)

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

    def test_only_allowed_app_actions_and_bounded_searches(self):
        acts=MOD.build()['WFWorkflowActions']
        for aid in identifiers(MOD.build()):
            self.assertFalse(any(x in aid.lower() for x in ['delete','setters.','updatereminder','runscript','runjavascrip','sendmessage','clipboard']))
        for a in acts:
            if a['WFWorkflowActionIdentifier'].startswith('is.workflow.actions.filter.'):
                p=a['WFWorkflowActionParameters']
                self.assertTrue(p['WFContentItemLimitEnabled'])
                self.assertEqual(p['WFContentItemLimitNumber'],10)

    def test_button_press_starts_dictation_directly(self):
        ids=identifiers(MOD.build())
        for banned in ['is.workflow.actions.ask','is.workflow.actions.choosefrommenu']:
            self.assertNotIn(banned,ids)
        dictate=[a['WFWorkflowActionParameters'] for a in MOD.build()['WFWorkflowActions']
                 if a['WFWorkflowActionIdentifier']=='is.workflow.actions.dictatetext']
        self.assertEqual(len(dictate),1)
        self.assertEqual(dictate[0]['WFSpeechLanguage'],'zh-CN')
        self.assertEqual(dictate[0]['WFDictateTextStopListening'],'On Tap')
        self.assertLess(ids.index('is.workflow.actions.dictatetext'),ids.index('is.workflow.actions.downloadurl'))

    def test_config_is_at_the_front_and_asked_at_import(self):
        doc=MOD.build(); acts=doc['WFWorkflowActions']
        self.assertTrue(acts[0]['WFWorkflowActionParameters']['WFCommentActionText'].startswith('这是一个免费的开源软件'))
        questions=doc['WFWorkflowImportQuestions']
        self.assertEqual(len(questions),3)
        dictate=identifiers(doc).index('is.workflow.actions.dictatetext')
        for q in questions:
            action=acts[q['ActionIndex']]
            self.assertEqual(action['WFWorkflowActionIdentifier'],'is.workflow.actions.gettext')
            self.assertEqual(action['WFWorkflowActionParameters']['WFTextActionText'],'')
            self.assertEqual(q['ParameterKey'],'WFTextActionText')
            self.assertEqual(q['Category'],'Parameter')
            self.assertLess(q['ActionIndex'],12)
            self.assertLess(q['ActionIndex'],dictate)
        self.assertEqual([q['Text'].count('Base URL') > 0 for q in questions],[True,False,False])
        self.assertIn('API Key',questions[2]['Text'])
        self.assertIn('模型',questions[1]['Text'])

    def test_runtime_key_is_blank_and_not_baked_into_source(self):
        doc=MOD.build()
        text=json.dumps(doc,ensure_ascii=False)
        self.assertNotRegex(text,r'sk-(?:proj-)?[A-Za-z0-9_-]{25,}')
        for q in doc['WFWorkflowImportQuestions']:
            self.assertEqual(q['DefaultValue'],'')
        self.assertNotIn('https://api.openai.com',text)

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

    def test_backup_switch_defaults_to_off(self):
        doc=MOD.build(); acts=doc['WFWorkflowActions']
        i=next(n for n,a in enumerate(acts) if a['WFWorkflowActionParameters'].get('WFVariableName')=='Backup Transcript')
        self.assertEqual(acts[i-1]['WFWorkflowActionParameters']['WFTextActionText']['Value']['string'],'否')


if __name__=='__main__':
    unittest.main(verbosity=2)
