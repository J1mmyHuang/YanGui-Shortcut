"""Small, fail-closed interpreter for this generator's offline regression tests.

This is an explicit semantic model, NOT Apple's Shortcuts runtime. It never
uses the network, Shortcuts CLI, or a real Notes/Calendar/Reminders database.
External results and UI answers must come from synthetic fixtures. Native
permissions, content coercions, picker serialization and ICU behavior still
require device testing. Unsupported actions raise instead of silently passing.
"""
from collections import deque
from copy import deepcopy
from datetime import datetime, timedelta
import json
import re
from zoneinfo import ZoneInfo


class OfflineExternalError(RuntimeError):
    """A supplied external failure, deliberately not caught as a returned value."""


class _Stop(Exception):
    pass


class OfflineRuntime:
    def __init__(self, document, *, responses=(), records=None, answers=None,
                 menus=(), now=None, timezone='Australia/Melbourne'):
        self.actions = document['WFWorkflowActions']
        self.responses = deque(deepcopy(list(responses)))
        self.records = deepcopy(records or {})
        self.answers = dict(answers or {})
        self.menus = deque(menus)
        self.zone = ZoneInfo(timezone)
        self.now = now or datetime(2026, 10, 20, 12, tzinfo=self.zone)
        self.variables = {}
        self.outputs = {}
        self.displays = []
        self.notifications = []
        self.requests = []
        self.writes = []
        self.reads = []
        self.executed = []
        self.blocks = self._blocks()

    def _blocks(self):
        stack, blocks = [], {}
        for index, action in enumerate(self.actions):
            p = action['WFWorkflowActionParameters']
            if 'WFControlFlowMode' not in p:
                continue
            mode, group = p['WFControlFlowMode'], p['GroupingIdentifier']
            if mode == 0:
                stack.append((index, group, []))
            elif not stack or stack[-1][1] != group:
                raise ValueError(f'Malformed control flow at action {index}')
            elif mode == 1:
                stack[-1][2].append(index)
            elif mode == 2:
                start, _, middles = stack.pop()
                blocks[start] = (index, middles)
        if stack:
            raise ValueError('Unclosed control flow')
        return blocks

    def run(self):
        try:
            self._execute(0, len(self.actions))
        except _Stop:
            pass
        return self

    def _execute(self, start, end):
        index = start
        while index < end:
            action = self.actions[index]
            p = action['WFWorkflowActionParameters']
            ident = action['WFWorkflowActionIdentifier']
            self.executed.append(ident)
            if p.get('WFControlFlowMode') == 0:
                close, middles = self.blocks[index]
                if ident.endswith('.conditional'):
                    split = middles[0] if middles else close
                    if self._condition(p):
                        self._execute(index + 1, split)
                    elif middles:
                        self._execute(split + 1, close)
                elif ident.endswith('.choosefrommenu'):
                    choices = p['WFMenuItems']
                    selected = self.menus.popleft() if self.menus else choices[0]
                    if selected not in choices:
                        raise ValueError(f'Synthetic menu answer {selected!r} not in {choices!r}')
                    case = middles[choices.index(selected)]
                    next_case = middles[choices.index(selected) + 1] if choices.index(selected) + 1 < len(middles) else close
                    self._execute(case + 1, next_case)
                elif ident.endswith(('.repeat.count', '.repeat.each')):
                    items = (range(1, int(self._value(p['WFRepeatCount'])) + 1)
                             if ident.endswith('.repeat.count') else self._items(self._value(p['WFInput'])))
                    old = {k: self.variables.get(k) for k in ('Repeat Item', 'Repeat Index')}
                    present = {k for k in old if k in self.variables}
                    for n, item in enumerate(items, 1):
                        self.variables['Repeat Index'] = n
                        if ident.endswith('.repeat.each'):
                            self.variables['Repeat Item'] = item
                            self.outputs[p['UUID']] = item
                        self._execute(index + 1, close)
                    for key in old:
                        if key in present:
                            self.variables[key] = old[key]
                        else:
                            self.variables.pop(key, None)
                else:
                    raise NotImplementedError(ident)
                index = close + 1
                continue
            self.outputs[p['UUID']] = self._action(ident, p)
            index += 1

    @staticmethod
    def _items(value):
        return value if isinstance(value, list) else ([] if value is None or value == '' else [value])

    @staticmethod
    def _has(value):
        return value is not None and value != '' and value != []

    def _reference(self, value):
        kind = value['Type']
        if kind == 'Variable':
            name = value['VariableName']
            if name not in self.variables:
                raise ValueError(f'Uninitialized variable {name!r}')
            result = self.variables[name]
        elif kind == 'ActionOutput':
            uid = value['OutputUUID']
            if uid not in self.outputs:
                raise ValueError(f'Unavailable action output {uid}')
            result = self.outputs[uid]
        elif kind == 'CurrentDate':
            result = self.now
        else:
            raise NotImplementedError(f'Unsupported variable type {kind}')
        for modifier in value.get('Aggrandizements', []):
            if modifier['Type'] == 'WFPropertyVariableAggrandizement':
                result = self._property(result, modifier['PropertyName'])
            elif modifier['Type'] == 'WFDictionaryValueVariableAggrandizement':
                result = self._key(result, modifier['DictionaryKey'])
            else:
                raise NotImplementedError(modifier['Type'])
        return result

    def _value(self, value):
        if not isinstance(value, dict):
            return value
        serialization = value.get('WFSerializationType')
        if serialization == 'WFTextTokenAttachment':
            return self._reference(value['Value'])
        if serialization == 'WFTextTokenString':
            data = value['Value']
            encoded = data['string'].encode('utf-16-le')
            cursor, result = 0, ''
            for token_range, ref in sorted(data.get('attachmentsByRange', {}).items(),
                                           key=lambda item: int(item[0].split(',')[0][1:])):
                position = int(token_range.split(',')[0][1:]) * 2
                if encoded[position:position + 2] != '\ufffc'.encode('utf-16-le'):
                    raise ValueError(f'Token range does not point at placeholder: {token_range}')
                result += encoded[cursor:position].decode('utf-16-le') + self._text(self._reference(ref))
                cursor = position + 2
            return result + encoded[cursor:].decode('utf-16-le')
        if serialization == 'WFDictionaryFieldValue':
            return {self._value(item['WFKey']): self._value(item['WFValue'])
                    for item in value['Value']['WFDictionaryFieldValueItems']}
        if serialization == 'WFArrayParameterState':
            return [self._value(item['WFValue']) for item in value['Value']]
        if serialization == 'WFNumberSubstitutableState':
            return value['Value']
        if value.get('Type') == 'Variable' and 'Variable' in value:
            return self._value(value['Variable'])
        if value.get('Type') in ('ActionOutput', 'Variable', 'CurrentDate'):
            return self._reference(value)
        return {key: self._value(item) for key, item in value.items()}

    def _text(self, value):
        if value is None:
            return ''
        if isinstance(value, list):
            return '\n'.join(self._text(item) for item in value)
        if isinstance(value, dict):
            return json.dumps(value, ensure_ascii=False, default=self._text)
        if isinstance(value, bool):
            return '1' if value else '0'
        if isinstance(value, datetime):
            return value.isoformat()
        return str(value)

    @staticmethod
    def _type(value):
        # Get Type operates on content items; a list has one result per item.
        if isinstance(value, list):
            return [OfflineRuntime._type(item) for item in value]
        if isinstance(value, dict):
            return 'Dictionary'
        if isinstance(value, (int, float)):
            return 'Number'
        if isinstance(value, datetime):
            return 'Date'
        if isinstance(value, str):
            return 'Text'
        return None

    def _date(self, value):
        if isinstance(value, datetime):
            return value
        result = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
        return result.replace(tzinfo=self.zone) if result.tzinfo is None else result

    def _property(self, item, key):
        result = item.get(key)
        if key.endswith('Date') and result:
            return self._date(result)
        return result

    def _key(self, value, path):
        for component in path.split('.'):
            if isinstance(value, dict):
                value = value.get(component)
            elif isinstance(value, list) and component.isdigit():
                offset = int(component) - 1
                value = value[offset] if 0 <= offset < len(value) else None
            else:
                return None
        return value

    def _condition(self, p):
        value, code = self._value(p['WFInput']), p['WFCondition']
        if code in (100, 101):
            return self._has(value) if code == 100 else not self._has(value)
        if code in (0, 1, 2, 3):
            left, right = float(value), float(self._value(p['WFNumberValue']))
            return {0: left < right, 1: left <= right, 2: left > right, 3: left >= right}[code]
        left, right = self._text(value), self._text(self._value(p['WFConditionalActionString']))
        if code == 4:
            return left == right
        if code == 5:
            return left != right
        if code in (99, 999):
            return (right in left) if code == 99 else (right not in left)
        raise NotImplementedError(f'Conditional code {code}')

    def _filter(self, app, p):
        rows = p.get('WFContentItemFilter', {}).get('Value', {})
        predicates = rows.get('WFActionParameterFilterTemplates', [])
        prefix = rows.get('WFActionParameterFilterPrefix', 1)

        def matches(record, predicate):
            actual = self._property(record, predicate['Property'])
            values, code = predicate.get('Values', {}), predicate['Operator']
            if code in (100, 101):
                return self._has(actual) if code == 100 else not self._has(actual)
            if code == 2:
                return bool(actual) and self._date(actual) > self._date(self._value(values['Date']))
            expected = self._value(values.get('String', values.get('Bool')))
            if code == 99:
                return str(expected).casefold() in str(actual or '').casefold()
            if code == 4:
                return actual == expected
            raise NotImplementedError(f'Filter operator {code}')

        records = [r for r in self.records.get(app, [])
                   if not predicates or (all if prefix else any)(matches(r, predicate) for predicate in predicates)]
        prop = p.get('WFContentItemSortProperty')
        if prop:
            def sort_key(item):
                value = self._property(item, prop)
                return (value is None, value or '')
            records.sort(key=sort_key, reverse=p.get('WFContentItemSortOrder') == 'Latest First')
        if p.get('WFContentItemLimitEnabled'):
            records = records[:int(p['WFContentItemLimitNumber'])]
        self.reads.append({'app': app, 'count': len(records)})
        return records

    def _action(self, ident, p):
        name = ident.removeprefix('is.workflow.actions.')
        if name in ('comment', 'nothing'):
            return None
        if name == 'exit':
            raise _Stop()
        if name == 'gettext':
            return self._value(p['WFTextActionText'])
        if name == 'number':
            return float(self._value(p['WFNumberActionNumber']))
        if name == 'setvariable':
            value = self._value(p['WFInput'])
            self.variables[p['WFVariableName']] = value
            return value
        if name == 'ask':
            prompt = self._text(self._value(p['WFAskActionPrompt']))
            if prompt in self.answers:
                return self.answers[prompt]
            if 'API Base URL' in prompt:
                return 'https://offline.invalid/v1'
            if 'API Model' in prompt:
                return 'offline-fixture-model'
            if 'API Key' in prompt:
                return 'offline-test-value'
            if '请输入' in prompt:
                return '原始中文口述'
            raise ValueError(f'No synthetic answer for prompt {prompt!r}')
        if name == 'dictatetext':
            return self.answers.get('Dictate Text', '原始中文口述')
        if name == 'date':
            return self.now
        if name == 'format.date':
            date, pattern = self._date(self._value(p['WFDate'])), p['WFDateFormatString']
            if pattern == 'VV':
                return self.zone.key
            if pattern == 'yyyy-MM-dd':
                return date.astimezone(self.zone).strftime('%Y-%m-%d')
            if pattern == "yyyy-MM-dd'T'HH:mm:ssXXXXX":
                return date.astimezone(self.zone).isoformat(timespec='seconds')
            raise NotImplementedError(f'Date pattern {pattern}')
        if name == 'dictionary':
            return self._value(p['WFItems'])
        if name == 'list':
            return [self._value(item) for item in p['WFItems']]
        if name == 'getitemtype':
            return self._type(self._value(p['WFInput']))
        if name == 'getitemfromlist':
            items = self._items(self._value(p['WFInput']))
            if p['WFItemSpecifier'] != 'First Item':
                raise NotImplementedError(p['WFItemSpecifier'])
            return items[0] if items else None
        if name == 'getvalueforkey':
            source = self._value(p['WFInput'])
            if p.get('WFGetDictionaryValueType') == 'All Keys':
                return list(source)
            return self._key(source, self._text(self._value(p['WFDictionaryKey'])))
        if name == 'count':
            return len(self._items(self._value(p.get('Input', p.get('WFInput')))))
        if name == 'text.match':
            pattern = self._text(self._value(p['WFMatchTextPattern'])).replace(r'\z', r'\Z')
            return [m.group(0) for m in re.finditer(pattern, self._text(self._value(p['text'])))]
        if name == 'text.replace':
            source = self._text(self._value(p['WFInput']))
            old, new = p['WFReplaceTextFind'], p['WFReplaceTextReplace']
            return re.sub(old, new, source) if p.get('WFReplaceTextRegularExpression') else source.replace(old, new)
        if name == 'detect.dictionary':
            value = self._value(p['WFInput'])
            return json.loads(value) if isinstance(value, str) else value
        if name == 'detect.date':
            try:
                return [self._date(self._value(p['WFInput']))]
            except (ValueError, TypeError):
                return []
        if name == 'gettimebetweendates':
            # Bundled catalog: WFTimeUntilFromDate is First Date; WFInput is Second Date.
            first = self._date(self._value(p['WFTimeUntilFromDate']))
            second = self._date(self._value(p['WFInput']))
            if p.get('WFTimeUntilUnit') != 'Seconds':
                raise NotImplementedError(p.get('WFTimeUntilUnit'))
            return second.timestamp() - first.timestamp()
        if name == 'math':
            left, right = float(self._value(p['WFInput'])), float(self._value(p['WFMathOperand']))
            operation = p.get('WFMathOperation', '+')
            if operation == '+':
                return left + right
            if operation == '-':
                return left - right
            raise NotImplementedError(operation)
        if name == 'adjustdate':
            date, quantity = self._date(self._value(p['WFDate'])), p['WFDuration']['Value']
            if quantity['Unit'] != 'sec':
                raise NotImplementedError(quantity['Unit'])
            seconds = float(self._value(quantity['Magnitude']))
            return date + timedelta(seconds=(-seconds if p['WFAdjustOperation'] == 'Subtract' else seconds))
        if name == 'showresult':
            self.displays.append(self._text(self._value(p['Text'])))
            return None
        if name == 'notification':
            self.notifications.append(self._text(self._value(p['WFNotificationActionBody'])))
            return None
        if name == 'downloadurl':
            self.requests.append({'url': self._value(p['WFURL']), 'method': p['WFHTTPMethod'],
                                  'json': self._value(p['WFJSONValues'])})
            if not self.responses:
                raise ValueError('No synthetic response remains; no real request was attempted')
            response = self.responses.popleft()
            if isinstance(response, Exception):
                raise response
            return response
        if ident == 'com.apple.mobilenotes.SharingExtension':
            content = self._text(self._value(p['WFCreateNoteInput']))
            title, _, body = content.partition('\n')
            record = {'kind': 'note', 'title': title, 'body': body.lstrip('\n')}
            self.writes.append(record)
            return record
        if name == 'addnewevent':
            record = {'kind': 'calendar', 'title': self._value(p['WFCalendarItemTitle']),
                      'start': self._date(self._value(p['WFCalendarItemStartDate'])),
                      'end': self._date(self._value(p['WFCalendarItemEndDate'])),
                      'all_day': p['WFCalendarItemAllDay']}
            self.writes.append(record)
            return record
        if name == 'addnewreminder':
            record = {'kind': 'reminder', 'title': self._value(p['WFCalendarItemTitle']),
                      'alert': p['WFAlertEnabled'], 'due': self._value(p.get('WFAlertCustomTime'))}
            self.writes.append(record)
            return record
        if name.startswith('filter.'):
            return self._filter(name.removeprefix('filter.'), p)
        if name.startswith('properties.'):
            return self._property(self._value(p['WFInput']), p['WFContentItemPropertyName'])
        raise NotImplementedError(f'Unsupported offline action {ident}')
