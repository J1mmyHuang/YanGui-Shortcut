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
             start='', end='', due='', all_day=False, include_completed=False, checklist=False)
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
        for change in [dict(all_day='false'),dict(include_completed=1),dict(checklist='true'),dict(checklist=None),dict(title=[]),
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
        for needle in ['calendar.create','reminder.create','note.create','拆成互相独立的事项','一律用 note.create',
                       '提醒我下午3点有会议','会议本身也归日历','日期按今天','不要带时区偏移','checklist=true','只写条目文字','下一个整点','当天 09:00']:
            self.assertIn(needle,prompt)
        for needle in ['判定顺序','必须用 calendar.create 并填好 start 和 end','不单独成项','我今天下午两点有一个会',
                       '两样及以上','只买或只带一样东西时用 reminder.create','超市购物清单']:
            self.assertIn(needle,prompt)
        examples=[line for line in prompt.splitlines() if line.startswith('{"operations"')]
        self.assertEqual(len(examples),5)  # the format line and four examples
        for line in examples:
            self.assertTrue(self.matches(line),line)
        self.assertNotIn('☐',prompt)
        self.assertNotIn('clarify',prompt)
        self.assertNotIn('question',prompt)

    def chat_requests(self):
        doc=MOD.build()
        return [a['WFWorkflowActionParameters'] for a in doc['WFWorkflowActions']
                if a['WFWorkflowActionIdentifier']=='is.workflow.actions.downloadurl'
                and a['WFWorkflowActionParameters']['WFHTTPMethod']=='POST']

    @staticmethod
    def items(p):
        return {x['WFKey']['Value']['string']:x for x in p['WFJSONValues']['Value']['WFDictionaryFieldValueItems']}

    @staticmethod
    def header_names(p):
        return [x['WFKey']['Value']['string'] for x in p['WFHTTPHeaders']['Value']['WFDictionaryFieldValueItems']]

    def test_native_requests_match_the_real_export_format(self):
        requests=self.chat_requests()
        self.assertEqual(len(requests),2)  # one per protocol
        for p in requests:
            self.assertEqual(p['WFHTTPBodyType'],'JSON')
            self.assertIs(p['Advanced'],True)
            self.assertIs(p['ShowHeaders'],True)
            messages=self.items(p)['messages']
            self.assertEqual(messages['WFItemType'],2)
            self.assertEqual(messages['WFValue']['WFSerializationType'],'WFArrayParameterState')
            for element in messages['WFValue']['Value']:
                # Dictionary elements are item type 1 and wrapped twice, as in real exports.
                self.assertEqual(element['WFItemType'],1)
                self.assertNotIn('WFKey',element)
                self.assertEqual(element['WFValue']['WFSerializationType'],'WFDictionaryFieldValue')
                self.assertEqual(element['WFValue']['Value']['WFSerializationType'],'WFDictionaryFieldValue')
                self.assertIn('WFDictionaryFieldValueItems',element['WFValue']['Value']['Value'])

    def test_protocol_specific_headers_and_bodies(self):
        requests=self.chat_requests()
        anthropic=next(r for r in requests if 'x-api-key' in self.header_names(r))
        openai=next(r for r in requests if 'Authorization' in self.header_names(r))
        self.assertEqual(self.header_names(openai),['Authorization','Content-Type'])
        self.assertEqual(sorted(self.items(openai)),['messages','model'])
        self.assertEqual(len(self.items(openai)['messages']['WFValue']['Value']),2)
        self.assertEqual(self.header_names(anthropic),['x-api-key','anthropic-version','Content-Type'])
        fields=self.items(anthropic)
        self.assertEqual(sorted(fields),['max_tokens','messages','model','system'])
        self.assertEqual(fields['max_tokens']['WFItemType'],3)
        self.assertEqual(fields['max_tokens']['WFValue']['Value']['string'],str(MOD.ANTHROPIC_MAX_TOKENS))
        self.assertEqual(len(fields['messages']['WFValue']['Value']),1)
        version=anthropic['WFHTTPHeaders']['Value']['WFDictionaryFieldValueItems'][1]['WFValue']['Value']['string']
        self.assertEqual(version,MOD.ANTHROPIC_VERSION)

    def test_dictionary_item_types_match_value_kinds_everywhere(self):
        def walk(o):
            if isinstance(o,dict):
                if 'WFItemType' in o and 'WFValue' in o:
                    value,code=o['WFValue'],o['WFItemType']
                    kind=value.get('WFSerializationType')
                    if kind=='WFDictionaryFieldValue':self.assertEqual(code,1)
                    elif kind=='WFArrayParameterState':self.assertEqual(code,2)
                    elif kind=='WFNumberSubstitutableState':self.assertEqual(code,4)
                    else:self.assertIn(code,(0,3))
                    if code==3:self.assertRegex(value['Value']['string'],r'\A-?[0-9.]+\Z')
                for x in o.values():walk(x)
            elif isinstance(o,list):
                for x in o:walk(x)
        walk(MOD.build())

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
        # The Action Button cannot stop Dictate Text (its only choices are After Pause, After Short Pause and On Tap),
        # so dictation ends by itself after a pause.
        self.assertEqual(dictate[0]['WFDictateTextStopListening'],'After Pause')
        posts=[n for n,a in enumerate(MOD.build()['WFWorkflowActions'])
               if a['WFWorkflowActionIdentifier']=='is.workflow.actions.downloadurl'
               and a['WFWorkflowActionParameters']['WFHTTPMethod']=='POST']
        self.assertLess(ids.index('is.workflow.actions.dictatetext'),posts[0])

    def test_config_is_at_the_front_and_asked_at_import(self):
        doc=MOD.build(); acts=doc['WFWorkflowActions']
        self.assertTrue(acts[0]['WFWorkflowActionParameters']['WFCommentActionText'].startswith('这是一个免费的开源软件'))
        questions=doc['WFWorkflowImportQuestions']
        self.assertEqual(len(questions),4)
        first_request=identifiers(doc).index('is.workflow.actions.downloadurl')
        dictate=identifiers(doc).index('is.workflow.actions.dictatetext')
        for q in questions:
            action=acts[q['ActionIndex']]
            self.assertEqual(action['WFWorkflowActionIdentifier'],'is.workflow.actions.gettext')
            self.assertEqual(action['WFWorkflowActionParameters']['WFTextActionText'],q['DefaultValue'])
            self.assertEqual(q['ParameterKey'],'WFTextActionText')
            self.assertEqual(q['Category'],'Parameter')
            self.assertLess(q['ActionIndex'],14)
            self.assertLess(q['ActionIndex'],min(dictate,first_request))
        texts=[q['Text'] for q in questions]
        self.assertIn('协议',texts[0]);self.assertIn('Base URL',texts[1])
        self.assertIn('API Key',texts[2]);self.assertIn('模型',texts[3]);self.assertIn('/models',texts[3])
        self.assertEqual([q['DefaultValue'] for q in questions],['openai','','',''])
        for number,label in enumerate(['API 协议','Base URL','API Key','模型 ID'],1):
            self.assertTrue(texts[number-1].startswith('【%d/4 %s】'%(number,label)),texts[number-1])

    def test_runtime_key_is_blank_and_not_baked_into_source(self):
        doc=MOD.build()
        text=json.dumps(doc,ensure_ascii=False)
        self.assertNotRegex(text,r'sk-(?:proj-)?[A-Za-z0-9_-]{25,}')
        for q in doc['WFWorkflowImportQuestions'][1:]:
            self.assertEqual(q['DefaultValue'],'')
        base=doc['WFWorkflowActions'][doc['WFWorkflowImportQuestions'][1]['ActionIndex']]
        self.assertEqual(base['WFWorkflowActionParameters']['WFTextActionText'],'')

    def test_time_difference_compares_the_two_real_dates_without_a_reference_date(self):
        b=MOD.Builder(); end=b.named('End Date Value'); start=b.named('Start Date Value'); b.seconds_between(end,start)
        p=b.actions[-1]['WFWorkflowActionParameters']
        self.assertEqual(p['WFInput'],MOD.T(end))
        self.assertEqual(p['WFTimeUntilFromDate'],MOD.T(start))
        self.assertEqual(p['WFTimeUntilUnit'],'Seconds')
        self.assertNotIn('Epoch Date',json.dumps(MOD.build()))

    def test_iso_contract_checks_real_calendar_dates_and_offset_limits(self):
        pattern=MOD.ISO_REGEX.replace(r'\z',r'\Z')
        timed=MOD.TIMED
        for value in ['2026-10-20T15:00:00','2026-10-20T15:00:00+11:00','2026-10-20T04:00:00Z']:
            self.assertRegex(value,'\\A'+timed+'\\Z')
        for value in ['2026-10-20T15:00','2026-10-20 15:00:00','2026-10-20T25:00:00','2026-10-20T15:00:00+14:01']:
            self.assertNotRegex(value,'\\A'+timed+'\\Z')
        for value in ['2024-02-29','2000-02-29','2026-10-20T23:30:00Z','2026-10-20T10:00:00+14:00','2026-10-20T15:00:00']:
            self.assertRegex(value,pattern)
        for value in ['2026-02-29','2026-02-30','2026-04-31','2026-10-20T10:00:00+14:01']:
            self.assertNotRegex(value,pattern)

    def test_no_item_type_list_sentinel_and_calendar_keyword_is_native_filter(self):
        doc=MOD.build(); self.assertFalse('List Type' in json.dumps(doc))
        calendar=[a['WFWorkflowActionParameters'] for a in doc['WFWorkflowActions']
                  if a['WFWorkflowActionIdentifier']=='is.workflow.actions.filter.calendarevents']
        self.assertTrue(any(any(r['Property']=='Title' for r in p['WFContentItemFilter']['Value']['WFActionParameterFilterTemplates']) for p in calendar))

    def test_notes_actions_carry_the_descriptor_and_entity_link_of_a_real_iphone_export(self):
        doc=MOD.build(); acts=doc['WFWorkflowActions']
        creates=[a for a in acts if a['WFWorkflowActionIdentifier']=='com.apple.mobilenotes.SharingExtension']
        appends=[a for a in acts if a['WFWorkflowActionIdentifier']=='com.apple.mobilenotes.CreateChecklistItemLinkAction']
        self.assertTrue(creates);self.assertEqual(len(appends),1)
        for a in creates:
            p=a['WFWorkflowActionParameters']
            self.assertEqual(p['AppIntentDescriptor'],{'AppIntentIdentifier':'CreateNoteLinkAction','BundleIdentifier':'com.apple.mobilenotes','Name':'备忘录','TeamIdentifier':'0000000000'})
            self.assertIn('WFCreateNoteInput',p)
        p=appends[0]['WFWorkflowActionParameters']
        self.assertEqual(p['AppIntentDescriptor'],{'AppIntentIdentifier':'CreateChecklistItemLinkAction','BundleIdentifier':'com.apple.mobilenotes','Name':'备忘录','TeamIdentifier':'0000000000'})
        entity=p['noteEntity']
        self.assertEqual(entity['WFSerializationType'],'WFTextTokenAttachment')
        self.assertEqual(entity['Value']['Type'],'ActionOutput')
        # the entity points at the Create Note action that precedes it
        index=acts.index(appends[0])
        sources=[a for a in acts[:index] if a['WFWorkflowActionIdentifier']=='com.apple.mobilenotes.SharingExtension'
                 and a['WFWorkflowActionParameters']['UUID']==entity['Value']['OutputUUID']]
        self.assertEqual(len(sources),1)

    def test_numeric_parameters_use_the_encodings_of_real_exports(self):
        # A text operand, text number or token-string split input shows up on a real iPhone as
        # "Please choose a value for each parameter in this action."
        acts=MOD.build()['WFWorkflowActions']
        for a in acts:
            ident=a['WFWorkflowActionIdentifier'];p=a['WFWorkflowActionParameters']
            if ident=='is.workflow.actions.math':
                operand=p['WFMathOperand']
                self.assertTrue(isinstance(operand,(float,str)) and not isinstance(operand,dict) or operand.get('WFSerializationType')=='WFTextTokenAttachment',operand)
                self.assertIn(p.get('WFMathOperation'),(None,'-'))  # addition leaves the key out
            if ident=='is.workflow.actions.conditional' and p.get('WFControlFlowMode')==0 and p['WFCondition'] in (0,1,2,3):
                self.assertIsInstance(p['WFNumberValue'],float)
            if ident=='is.workflow.actions.text.split':
                self.assertEqual(p['text']['WFSerializationType'],'WFTextTokenAttachment')

    def test_mac_test_variant_reads_shortcut_input_and_returns_its_result(self):
        doc=MOD.build(test=True); ids=identifiers(doc)
        for absent in ['is.workflow.actions.dictatetext','is.workflow.actions.showresult','is.workflow.actions.notification',
                       'com.apple.mobilenotes.SharingExtension','com.apple.mobilenotes.CreateChecklistItemLinkAction']:
            self.assertNotIn(absent,ids)
        self.assertEqual(ids[-1],'is.workflow.actions.output')
        self.assertEqual(doc['WFWorkflowInputContentItemClasses'],['WFStringContentItem'])
        self.assertIs(doc['WFWorkflowHasShortcutInputVariables'],True)
        self.assertIn('ExtensionInput',json.dumps(doc))
        # imported without questions; placeholders only, so the signed test file never carries a key
        self.assertEqual(doc['WFWorkflowImportQuestions'],[])
        self.assertIn('https://example.invalid/v1',json.dumps(doc))
        # the shipped build is untouched by the variant
        shipped=MOD.build()
        self.assertEqual(len(shipped['WFWorkflowImportQuestions']),4)
        for debug in ['example.invalid','test-key','probe1']:
            self.assertNotIn(debug,json.dumps(shipped))
        self.assertEqual(shipped['WFWorkflowInputContentItemClasses'],[])
        self.assertIn('is.workflow.actions.dictatetext',identifiers(shipped))
        self.assertNotIn('ExtensionInput',json.dumps(shipped))
        for debug in ['Stage Number','Override Reply','Has Override','🧪','停在动作']:
            self.assertNotIn(debug,json.dumps(shipped,ensure_ascii=False))
        self.assertNotIn('WFWorkflowHasShortcutInputVariables',shipped)

    def test_real_notes_test_variant_uses_the_shipped_notes_actions(self):
        def notes(doc):
            return [(a['WFWorkflowActionIdentifier'],a['WFWorkflowActionParameters']['AppIntentDescriptor'],
                     sorted(k for k in a['WFWorkflowActionParameters'] if k!='UUID'))
                    for a in doc['WFWorkflowActions'] if a['WFWorkflowActionIdentifier'].startswith('com.apple.mobilenotes.')]
        shipped=notes(MOD.build());variant=notes(MOD.build(test=True,real_notes=True))
        self.assertEqual(sorted(map(str,shipped)),sorted(map(str,variant)))
        self.assertGreater(len(shipped),10)

    def test_boolean_flags_are_compared_as_text_never_as_numbers(self):
        # A JSON boolean in a numeric If raised "choose a value for each parameter" on a real Mac engine.
        acts=MOD.build()['WFWorkflowActions']
        flags={'All Day Flag','Checklist Flag','Include Completed Flag'}
        seen=0
        for a in acts:
            p=a['WFWorkflowActionParameters']
            if a['WFWorkflowActionIdentifier']=='is.workflow.actions.conditional' and p.get('WFControlFlowMode')==0:
                name=p['WFInput']['Variable']['Value'].get('VariableName')
                if name in flags:
                    seen+=1
                    self.assertIn(p['WFCondition'],(4,5),name)
        self.assertGreaterEqual(seen,4)
        text=json.dumps(acts,ensure_ascii=False)
        self.assertIn('all_day|include_completed|checklist',text)

    @staticmethod
    def producers(acts):
        """Map a parameter value to the identifiers of the actions whose output it carries, through named variables."""
        by_uuid={a['WFWorkflowActionParameters'].get('UUID'):a for a in acts}
        setters={}
        for a in acts:
            p=a['WFWorkflowActionParameters']
            if a['WFWorkflowActionIdentifier'] in ('is.workflow.actions.setvariable','is.workflow.actions.appendvariable'):
                setters.setdefault(p['WFVariableName'],[]).append(p['WFInput'])
        def refs(value):
            if isinstance(value,dict):
                if value.get('Type')=='Variable' and 'Variable' in value:yield from refs(value['Variable']);return
                if value.get('WFSerializationType') in ('WFTextTokenAttachment','WFTextTokenString'):
                    inner=value['Value'];yield from (inner.get('attachmentsByRange',{}).values() if 'string' in inner else [inner]);return
        def resolve(value,seen=()):
            out=set()
            for ref in refs(value):
                if ref.get('Type')=='ActionOutput':out.add(by_uuid[ref['OutputUUID']]['WFWorkflowActionIdentifier'].removeprefix('is.workflow.actions.'))
                elif ref.get('Type')=='Variable':
                    name=ref['VariableName']
                    if name.startswith('Repeat Item'):out.add('repeat item')
                    elif name not in seen:
                        for source in setters.get(name,[]):out|=resolve(source,seen+(name,))
                else:out.add(ref.get('Type'))
            return out
        return resolve

    def test_value_sources_follow_what_the_mac_engine_accepts(self):
        # Measured on the Mac Shortcuts engine (probes 1-8 and the scenario runs on 2026-10-20):
        # an If comparing a value taken straight from Get Dictionary Value raises "choose a value for each
        # parameter"; an empty text still "has any value"; Format Date with WFDateFormat='Custom' plus
        # WFDateFormatString returns empty text, while the pattern placed in WFDateFormat works.
        for doc in (MOD.build(),MOD.build(test=True)):
            acts=doc['WFWorkflowActions'];resolve=self.producers(acts)
            for n,a in enumerate(acts):
                p=a['WFWorkflowActionParameters'];ident=a['WFWorkflowActionIdentifier']
                probe=any('格式探针' in str(x['WFWorkflowActionParameters'].get('WFCommentActionText','')) for x in acts[max(0,n-12):n])
                if ident=='is.workflow.actions.conditional' and 'WFCondition' in p and not probe:
                    sources=resolve(p['WFInput'])
                    if p['WFCondition'] in (100,101):
                        self.assertFalse(sources&{'gettext','text.replace','text.match'},(p,sources))
                    else:
                        self.assertFalse(sources&{'getvalueforkey','getitemfromlist','detect.dictionary','repeat item'},(p,sources))
                if ident=='is.workflow.actions.format.date' and not probe:
                    self.assertNotIn('WFDateFormatString',p)
                    self.assertNotEqual(p['WFDateFormat'],'Custom')
                for key in ('WFDate','WFCalendarItemStartDate','WFCalendarItemEndDate','WFAlertCustomTime'):
                    if key in p and not probe:
                        self.assertNotIn('getitemfromlist',resolve(p[key]),(ident,key))

    def test_nested_loops_name_the_inner_item(self):
        text=json.dumps(MOD.build()['WFWorkflowActions'],ensure_ascii=False)
        self.assertIn('"Repeat Item 2"',text)
        self.assertNotIn('"Repeat Item 3"',text)

    def test_backup_switch_defaults_to_off(self):
        doc=MOD.build(); acts=doc['WFWorkflowActions']
        i=next(n for n,a in enumerate(acts) if a['WFWorkflowActionParameters'].get('WFVariableName')=='Backup Transcript')
        self.assertEqual(acts[i-1]['WFWorkflowActionParameters']['WFTextActionText']['Value']['string'],'否')


if __name__=='__main__':
    unittest.main(verbosity=2)
