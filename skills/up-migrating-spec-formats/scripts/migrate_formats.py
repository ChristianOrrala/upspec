#!/usr/bin/env python3
"""Move earlier upspec formats to the current ones, with git and Python 3.9+ only.

migrate_formats.py plan|apply|verify [--docs DIR] [--format text|json]
Plan writes nothing. Apply performs mechanical changes only. Judgment about
journeys, examples, EARS and unclear types belongs to the agent and owner.
Exit 0 done/nothing to do, 1 verification/read error, 2 usage, 3 git/resume conflict.
The journal lives in git rev-parse --absolute-git-dir, including linked worktrees.
All planned texts and after-fingerprints are journaled before the first write.
Uncertain documents keep their bytes and filenames and are listed for judgment;
dependent overviews and stubs wait. Unmapped diagram lines keep the diagram.
Writes are limited to the recorded Specs folder (else docs/) and tools/specs/,
including resumed targets and rename sources. Other --docs paths are exit 2.
Items run in order: renames, use cases by path, overview/stubs, requirements,
entity model, journeys by path, records by path, installed checks by name.
UPSPEC_MIGRATE_STOP_AFTER=N stops cleanly after N items (test hook).
UPSPEC_MIGRATE_CRASH_AFTER_WRITE=N stops after the Nth write, before its journal
update (test hook). Both leave a resumable journal; neither signals completion.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import spec_model as model
import use_case_map
import installed_copies

HERE = Path(__file__).resolve().parent
JOURNAL = 'upspec-migration.json'
# Exact union of scaffold_docs.CHECK_SCRIPTS and HOOK_SCRIPTS; tested against setup.
INSTALLED_SCRIPTS = ('spec_model.py', 'validate_use_case.py', 'spec_lint.py', 'use_case_map.py',
                     'spec_first_guard.py', 'hook_gate.py', 'workflow_state.py', 'finish_change.py',
                     'scope_audit.py', 'uc_change_list.py', 'unrecorded_changes.py', 'change_view.py', 'hook_profiles.py')
TYPE_MAP = {'String': 'Text', 'Integer': 'Number', 'Boolean': 'Yes/No',
            'Date': 'Date', 'DateTime': 'Date and time'}


class Conflict(Exception):
    pass


class GitUnavailable(Exception):
    pass


def git(root, *args):
    try:
        result = subprocess.run(['git', '-C', str(root), *args], capture_output=True, text=True)
    except OSError as exc:
        raise GitUnavailable(str(exc))
    if result.returncode:
        err = result.stderr.strip()
        if args[:1] == ('rev-parse',) or 'not a git repository' in err or not err:
            raise GitUnavailable(err or 'not a git work tree')
        raise Conflict(err)
    return result.stdout.strip()


def find_root(docs_path):
    """Use apply's worktree root, or repository evidence when git is unavailable."""
    try:
        return Path(git(docs_path, 'rev-parse', '--show-toplevel'))
    except GitUnavailable:
        return Path(model.project_root(str(docs_path))).resolve()


def fingerprint(data):
    return hashlib.sha256(data).hexdigest() if data is not None else None


def installed_source(name):
    """Packaged copies are local; two setup-owned scripts have no shared source."""
    path = HERE / name
    if not path.is_file() and HERE.parent.name == 'shared':
        path = HERE.parent.parent / 'plugins' / 'upspec' / 'skills' / 'up-1-bootstrapping-spec-driven-projects' / 'scripts' / name
    return path


def safe(root, path):
    """Never read or write through a link, or outside this worktree."""
    path = Path(path)
    if not path.is_absolute():
        path = root / path
    try:
        rel = path.relative_to(root)
    except ValueError:
        raise Conflict('%s is outside the git work tree' % path)
    if '..' in rel.parts:
        raise Conflict('%s leaves the git work tree' % path)
    current = root
    for part in rel.parts:
        current /= part
        if current.is_symlink():
            raise Conflict('%s goes through a symbolic link' % path)
    return path


def read(path):
    try:
        return Path(path).read_bytes().decode('utf-8')
    except (OSError, UnicodeError) as exc:
        exc.spec_path = str(path)
        raise


def authorized(root, path):
    """Writes belong to the recorded specification folder and installed checks."""
    path = Path(path)
    if not path.is_absolute():
        path = root / path
    folders = (root / (model.recorded_docs(str(root)) or 'docs'), root / 'tools' / 'specs')
    if '..' in path.parts or not any(path == folder or folder in path.parents for folder in folders):
        raise ValueError('%s is outside authorized specification and installed-check folders' % path)
    return safe(root, path)


def scalar(value, quote=False):
    # The model's YAML subset has no quote escapes; prefer plain text when safe.
    if not value:
        return "''"
    needs_quote = quote or bool(re.search(r':\s|:$|\s#|[\[\]\n\r]|^[!&*|>\'"%@`-]', value))
    if not needs_quote:
        return value
    if '"' not in value:
        return '"' + value + '"'
    if "'" not in value:
        return "'" + value + "'"
    raise ValueError('value cannot be represented in the front matter subset: ' + value)


def front(fields):
    def value(v):
        return '[' + ', '.join(scalar(x) for x in v) + ']' if isinstance(v, list) else scalar(v)
    return '---\n' + ''.join('%s: %s\n' % (k, value(v)) for k, v in fields) + '---\n'


def overview_fields(lines):
    entries = model.sections(lines, 2)
    section = next((s for s in entries if s[0] == 'Overview'), None)
    if section is None or sum(1 for s in entries if s[0] == 'Overview') != 1:
        return None, None
    fields = {}
    for _, line in section[2]:
        match = re.fullmatch(r'\*\*([^*]+):\*\*\s*(.*?)\s*', line)
        if match:
            if match[1] in fields:
                return None, None
            fields[match[1]] = match[2]
        elif line.strip():
            return None, None   # unrecognized content must not disappear
    start = section[1] - 1
    # sections() also ends at a higher-level heading. Searching only for the
    # next ## would swallow such a heading and its unplaced instructions.
    end = section[2][-1][0] if section[2] else section[1]
    return fields, (start, end)


def convert_use_case(lines):
    fields, span = overview_fields(lines)
    keys = [('id', 'Use Case ID'), ('name', 'Use Case Name'), ('primary_actor', 'Primary Actor'),
            ('secondary_actors', 'Secondary Actors'), ('goal', 'Goal'), ('trigger', 'Trigger'),
            ('status', 'Status'), ('requirements', 'Requirements')]
    if fields is None or any(label not in fields for key, label in keys if key != 'secondary_actors'):
        return None
    if set(fields) - {label for _, label in keys}:
        return None
    outside = [(i, line) for i, line in enumerate(lines[:span[0]]) if line.strip()]
    headings = [(i, line) for i, line in outside if line.startswith('# ')]
    if len(headings) != 1 or len(outside) != 1:
        return None
    title_idx = headings[0][0]
    values = []
    for key, label in keys:
        if label not in fields:
            continue
        val = fields[label]
        if key == 'requirements':
            # Validate the entire value before extracting identifiers. Prose is
            # evidence too, and cannot be discarded as a metadata remainder.
            identifier = r'(?:FR|NFR|C)-\d+'
            identifiers = identifier + r'(?:\s*,\s*' + identifier + r')*'
            token = r'(?:' + identifier + r'|\[' + identifiers + r'\]\([^\s()]+\))'
            if val.startswith('[') and val.endswith(']') and '](' not in val:
                val = val[1:-1].strip()
            if val and not re.fullmatch(token + r'(?:\s*,\s*' + token + r')*', val):
                raise ValueError('Requirements contains unrecognized text: ' + fields[label])
            val = re.findall(identifier, re.sub(r'\]\([^)]*\)', ']', val))
        elif key == 'secondary_actors':
            val = [s.strip() for s in val.split(',') if s.strip()]
        values.append((key, val))
    body = lines[:span[0]] + lines[span[1]:]
    if body[title_idx] not in ('# Use Case: ' + fields['Use Case Name'], '# ' + fields['Use Case Name']):
        return None  # a different title contains information not in the metadata
    body[title_idx] = '# ' + fields['Use Case Name']
    return front(values) + '\n'.join(body)


def convert_journey(lines):
    fields, span = overview_fields(lines)
    keys = [('id', 'ID'), ('goal', 'Goal'), ('priority', 'Priority'), ('status', 'Status')]
    if fields is None or any(label not in fields for _, label in keys):
        return None
    if set(fields) - {label for _, label in keys} - {'Process'}:
        return None
    outside = [(i, line) for i, line in enumerate(lines[:span[0]]) if line.strip()]
    headings = [(i, line) for i, line in outside if line.startswith('# ')]
    if len(headings) != 1 or len(outside) != 1:
        return None
    title_idx = headings[0][0]
    ids = []
    for table in model.read_tables(lines):
        for _, row, _ in table['rows']:
            for uid in re.findall(r'UC-\d{3}', row.get('Use Case', '')):
                if uid not in ids:
                    ids.append(uid)
    values = [(key, fields[label]) for key, label in keys] + [('use_cases', ids)]
    if fields.get('Process'):
        proc = fields['Process']
        match = re.fullmatch(r'\[([^]]*)\]\(([^)]+)\)(?:\s*(?:—|--|-)\s*([^→\n]+(?:\s*(?:→|->)\s*[^→\n]+)+))?', proc)
        if not match:
            return None
        values.append(('process', match[2]))
    body = lines[:span[0]] + lines[span[1]:]
    body[title_idx] = re.sub(r'^# Test Case: ', '# ', body[title_idx])
    if fields.get('Process'):
        # The link target becomes metadata, but its label and route remain
        # source evidence. Never throw away the rest of the Process line.
        process_line = next(line for line in lines[span[0]:span[1]] if line.startswith('**Process:**'))
        body += ['\n## Process\n', process_line, '']
    return front(values) + '\n'.join(body)


def table_shape_ok(lines, table):
    """Do not replace a header plus an arbitrary row as if it were a separator."""
    index = table['line']
    separator = model.table_cells(lines[index]) if index < len(lines) else None
    return (separator is not None and len(separator) == len(table['header'])
            and all(re.fullmatch(r':?-{2,}:?', cell) for cell in separator)
            and all(count == len(table['header']) for _, _, count in table['rows']))


def convert_requirements(lines):
    """Off-pattern stories remain intact, for an owner-approved judgment pass."""
    out = list(lines)
    details = []
    for table in model.read_tables(lines):
        header = table['header']
        if not header or header[0] != 'ID':
            continue
        if not table_shape_ok(lines, table):
            return None
        if 'User Story' in header:
            if header != ['ID', 'Title', 'User Story', 'Priority', 'Status']:
                return None
            stories = []
            for number, row, _ in table['rows']:
                match = re.fullmatch(r'As a (.+?), I want (.+?) so that (.+?)\.', row.get('User Story', ''))
                if not match:
                    return None
                stories.append((number, row, match))
            n = table['line'] - 1
            out[n:n + 2] = ['| ID | Role | Need | Priority | Status |', '|----|------|------|----------|--------|']
            for number, row, match in stories:
                need = re.sub(r'^to ', '', match[2])
                out[number - 1] = '| %s | %s | %s | %s | %s |' % (row['ID'], match[1], need, row['Priority'], row['Status'])
                details.append('%s: %s\n\nBenefit: %s.' % (row['ID'], row['Title'], match[3]))
        else:
            out[table['line'] - 1] = out[table['line'] - 1].replace(' Requirement |', ' Statement |').replace(' Constraint |', ' Statement |')
    if details:
        out += ['', '## Requirement context', '', '\n\n'.join(details), '']
    return '\n'.join(out)


def convert_entity_model(lines):
    out = list(lines)
    for table in model.read_tables(lines):
        if 'Length/Precision' not in table['header']:
            continue
        if table['header'] != ['Attribute', 'Description', 'Data Type', 'Length/Precision', 'Validation Rules'] or not table_shape_ok(lines, table):
            return None
        n = table['line'] - 1
        out[n:n + 2] = ['| Attribute | Meaning | Type | Rules |', '|-----------|---------|------|-------|']
        for number, row, _ in table['rows']:
            tokens = [t.strip() for t in row.get('Validation Rules', '').split(',') if t.strip()]
            dtype = TYPE_MAP.get(row.get('Data Type'), row.get('Data Type', ''))
            primary = 'Primary Key' in tokens
            foreign = [re.fullmatch(r'Foreign Key \(([A-Z][A-Z0-9_]*)\.\w+\)', t) for t in tokens]
            foreign = [m for m in foreign if m]
            choices = [i for i, t in enumerate(tokens) if t.startswith('Values:')]
            if sum((primary, bool(foreign), bool(choices))) > 1 or len(foreign) > 1:
                raise ValueError('ambiguous attribute rules: ' + row.get('Validation Rules', ''))
            if primary:
                dtype = 'Identifier'
                tokens = ['Unique', 'never reused'] + [t for t in tokens if t not in ('Primary Key', 'Sequence')]
            elif foreign:
                dtype = 'Reference to ' + foreign[0][1]
                tokens.remove(foreign[0][0])
            elif choices:
                index = choices[0]
                values = [tokens[index][len('Values:'):].strip()] + tokens[index + 1:]
                # Only simple labels with an unambiguous terminal boundary are
                # mechanical. A rule among the values requires owner judgment.
                reserved = {'Required', 'Optional', 'Sequence', 'Unique', 'Null', 'Nullable'}
                if len(choices) != 1 or any(not re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]*', v) or v in reserved for v in values):
                    raise ValueError('ambiguous Values: boundary: ' + row.get('Validation Rules', ''))
                dtype = 'Choice of ' + ', '.join(values)
                tokens = tokens[:index]
            if not model.entity_type_ok(dtype):
                raise ValueError('%s: unclear business type %s' % (row['Attribute'], dtype))
            rules = ', '.join('Required' if t == 'Not Null' else t for t in tokens)
            out[number - 1] = '| %s | %s | %s | %s |' % (row['Attribute'], row.get('Description', ''), dtype, rules)
    return '\n'.join(out)


def convert_record(lines):
    top_headings = [line for _, line in model.outside_fences(lines) if line.startswith(('# ', '## '))]
    if len(top_headings) != 1 or not top_headings[0].startswith(('## Change record:', '# Change record:', '# ')):
        return None
    sec_3 = model.sections(lines, 3)
    titles = [title for title, _, _ in sec_3]
    if len(titles) != len(set(titles)):
        return None
    supported = {'Classification', "Owner's decisions", 'Specification change', 'Differences from today',
                 'Impact', 'Next', *model.RECORD_OPTIONAL_SECTIONS}
    if set(titles) - supported:
        return None
    first_3 = next((i for i, line in enumerate(lines) if line.startswith('### ')), None)
    if first_3 is None:
        return None
    intro = lines[:first_3]
    if any(line.strip() and not line.startswith(('# ', '## ')) and not re.match(r'^\*\*[^*]+:\*\*', line) for line in intro):
        return None
    classification = next((body for title, _, body in sec_3 if title == 'Classification'), [])
    fields = {}
    for line in intro + [line for _, line in classification]:
        if not line.strip() or line == top_headings[0]:
            continue
        match = re.fullmatch(r'\*\*([^*]+):\*\*\s*(.*?)\s*', line)
        if not match or match[1] in fields:
            return None
        fields[match[1]] = match[2]
    if set(fields) - {'Report', 'Element', 'Outcome', 'Sign-off test', 'Decided by'}:
        return None
    outcome = re.match(r'[1-7]\b', fields.get('Outcome', ''))
    if not outcome or not fields.get('Element'):
        return None
    values = [('outcome', outcome[0]), ('element', fields['Element'])]
    if fields.get('Decided by'):
        values.append(('decided_by', fields['Decided by']))
    sections = {title: '\n'.join(t for _, t in body).strip() for title, _, body in sec_3}
    context = fields.get('Report', '')
    if fields.get('Sign-off test'):
        context += '\n\nSign-off test: ' + fields['Sign-off test']
    if fields['Outcome'] != outcome[0]:
        context += '\n\nOutcome: ' + fields['Outcome']
    contents = [('Context', context), ('Decision', sections.get("Owner's decisions", '')),
                ('Specification change', sections.get('Specification change', '')),
                ('Consequences', '\n\n'.join(sections.get(k, '') for k in ('Differences from today', 'Impact')).strip())]
    contents += [(k, sections[k]) for k in model.RECORD_OPTIONAL_SECTIONS if sections.get(k)]
    if sections.get('Next'):
        # Next has no section in the new record; carry its body verbatim as
        # consequences rather than silently discarding an instruction.
        contents[3] = ('Consequences', contents[3][1] + '\n\nNext:\n\n' + sections['Next'])
    title = re.sub(r'^## ', '# ', top_headings[0])
    return front(values) + title + '\n\n' + '\n\n'.join('## %s\n\n%s' % p for p in contents) + '\n'


def convert_diagram(puml_lines, docs, planned_cases=None):
    """Return overview and stubs from the diagram, without writing any file."""
    if planned_cases is None:
        planned_cases = []
        for path in docs.use_case_files():
            value = read(path)
            if not value.startswith('---'):
                value = convert_use_case(value.split('\n'))
                if value is None:
                    return None
            planned_cases.append(model.parse_use_case_lines(value.split('\n'), path))
    planned_cases = list(planned_cases)
    if any(not uc.id for uc in planned_cases):
        return None
    text = '\n'.join(puml_lines)
    declarations = re.findall(r'usecase\s+"(UC-\d{3})\\n([^"]+)"\s+as\s+(\w+)', text)
    system = re.search(r'(?:rectangle|package)\s+"([^"]+)"', text)
    if not system:
        return None
    actor_declarations = re.findall(r'actor\s+"([^"]+)"\s+as\s+(\w+)', text)
    actors = {alias: name for name, alias in actor_declarations}
    links = re.findall(r'^\s*(\w+)\s*[-.]+>\s*(\w+)\s*$', text, re.M)
    unmapped = []
    declaration_aliases = {alias for _, _, alias in declarations}
    supported_links = set(links)
    for number, line in enumerate(puml_lines, 1):
        stripped = line.strip()
        framing = (not stripped or re.fullmatch(r'@startuml(?: [A-Za-z0-9 _-]+)?|@enduml|left to right direction|}', stripped)
                   or re.fullmatch(r'(?:rectangle|package) "[^"\n]+" \{', stripped))
        declaration = re.fullmatch(r'usecase "UC-\d{3}\\n[^"\n]+" as \w+', stripped)
        actor = re.fullmatch(r'actor "[^"\n]+" as \w+', stripped)
        link = re.fullmatch(r'(\w+)\s*[-.]+>\s*(\w+)', stripped)
        mapped_link = (link and (link[1], link[2]) in supported_links
                       and ((link[1] in actors and link[2] in declaration_aliases)
                            or (link[1] in declaration_aliases and link[2] in actors)))
        if not (framing or declaration or actor or mapped_link):
            unmapped.append((number, line))
    # Repeated declarations or nested systems cannot be represented faithfully.
    if (len({uid for uid, _, _ in declarations}) != len(declarations)
            or len(declaration_aliases) != len(declarations)
            or len(actors) != len(actor_declarations)
            or declaration_aliases & set(actors)
            or len(re.findall(r'(?:rectangle|package)\s+"', text)) != 1):
        return None
    existing = {uc.id for uc in planned_cases}
    existing.update(match[0] for path in docs.use_case_files()
                    for match in [re.match(r'UC-\d{3}', Path(path).name)] if match)
    stubs = {}
    for uid, name, alias in declarations:
        if uid in existing:
            continue
        primary = [actors[a] for a, b in links if b == alias and a in actors]
        secondary = [actors[b] for a, b in links if a == alias and b in actors]
        path = Path(docs.use_case_dir or Path(docs.root) / 'use_cases') / (uid + '-' + re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-') + '.md')
        stub = front([('id', uid), ('name', name), ('primary_actor', ', '.join(primary)),
                      ('secondary_actors', secondary), ('goal', ''), ('trigger', ''),
                      ('status', 'Draft'), ('requirements', [])]) + 'Not written yet.\n'
        stubs[path] = stub
        planned_cases.append(model.parse_use_case_lines(stub.split('\n'), str(path)))
    cases = {uc.id: uc for uc in planned_cases}
    aliases = {alias: cases.get(uid) for uid, _, alias in declarations}
    represented_actors = {name for uc in planned_cases for name in uc.primary_actors + uc.secondary_actors}
    for number, line in enumerate(puml_lines, 1):
        stripped = line.strip()
        declaration = re.fullmatch(r'usecase "(UC-\d{3})\\n([^"\n]+)" as \w+', stripped)
        actor = re.fullmatch(r'actor "([^"\n]+)" as \w+', stripped)
        link = re.fullmatch(r'(\w+)\s*([-.]+>)\s*(\w+)', stripped)
        mapped = True
        if declaration:
            uc = cases.get(declaration[1])
            mapped = uc is not None and uc.name == declaration[2]
        elif actor:
            mapped = actor[1] in represented_actors
        elif link:
            primary, secondary = aliases.get(link[3]), aliases.get(link[1])
            mapped = link[2] == '-->' and (
                (primary is not None and actors.get(link[1]) in primary.primary_actors)
                or (secondary is not None and actors.get(link[3]) in secondary.secondary_actors))
        if not mapped and not any(n == number for n, _ in unmapped):
            unmapped.append((number, line))
    unmapped.sort()
    scope = 'In and out: see the vision.\n' if docs.vision and re.search(r'^## (?:.*[Ss]cope)', read(docs.vision), re.M) else ''
    overview = '---\nsystem: %s\n---\n# Use cases\n\n## Scope\n\n%s\n## Delivery order\n\n' % (scalar(system[1], True), scope)
    overview_path = str(Path(docs.root) / 'use_cases.md')
    return overview + use_case_map.overview_block(planned_cases, system[1], overview_path=overview_path) + '\n', stubs, unmapped


def plan(root, docs):
    public = {'mechanical': [], 'judgment': [], 'installed': []}
    authorized(root, Path(docs.root))
    items = []
    rename_items = []
    def note(group, path, what, line=1):
        public[group].append({'path': str(Path(path).relative_to(root)), 'line': line, 'what': what})
    def converted(converter, value, path):
        try:
            return converter(value.split('\n'))
        except (ValueError, KeyError, IndexError) as exc:
            note('judgment', path, 'cannot convert mechanically: ' + str(exc))
            return None
    def item(path, text, what, before_text=None, source=None):
        path = authorized(root, path)
        data = path.read_bytes() if path.exists() else None
        before = fingerprint(before_text.encode('utf-8')) if before_text is not None else fingerprint(data)
        if data == (text.encode('utf-8') if text is not None else None) and source is None:
            return
        entry = {'path': str(path.relative_to(root)), 'what': what, 'before': before,
                 'after': fingerprint(text.encode('utf-8') if text is not None else None), 'text': text, 'done': False}
        if source:
            entry['source'] = str(authorized(root, source).relative_to(root))
            entry['source_before'] = fingerprint(Path(source).read_bytes())
        (rename_items if source else items).append(entry)
        note('mechanical', path, what)
    def content(path):
        path = safe(root, path)
        return read(path)
    renames = {}
    for old, new in [('entity-model.md', 'entity_model.md'), ('requirements_catalog.md', 'requirements.md')]:
        source, target = Path(docs.root) / old, Path(docs.root) / new
        if source.exists():
            if target.exists():
                raise Conflict('%s already exists: cannot rename %s' % (target, source))
            renames[source] = target
    planned_cases = []
    rejected_cases = []
    for given in docs.use_case_files():
        path = Path(given)
        value = content(path)
        if re.search(r'^\*\*Use Case ID:\*\*', value, re.M):
            new_text = converted(convert_use_case, value, path)
            if new_text is None:
                note('judgment', path, 'unrecognized use case Overview')
                rejected_cases.append(path)
            else:
                item(path, new_text, 'Overview fields into front matter')
                value = new_text
        for n, line in enumerate(value.split('\n'), 1):
            if line.lstrip().startswith('Examples:'):
                note('judgment', path, 'rule examples into an Examples table', n)
        uc = model.parse_use_case_lines(value.split('\n'), str(path))
        for rule in uc.rules:
            if not rule.retired and not rule.examples and not any(e['path'] == str(path.relative_to(root)) and 'rule examples' in e['what'] for e in public['judgment']):
                note('judgment', path, 'rule examples into an Examples table: ' + rule.id, rule.line)
        planned_cases.append(uc)
    for name in ('use_cases.puml', 'use-cases.puml'):
        path = Path(docs.root) / name
        if not path.exists():
            continue
        if rejected_cases:
            note('judgment', path, 'overview depends on unconverted use cases: ' + ', '.join(p.name for p in rejected_cases))
            continue
        diagram = converted(lambda lines: convert_diagram(lines, docs, planned_cases), content(path), path)
        if diagram is None:
            note('judgment', path, 'diagram needs an owner-reviewed overview')
            continue
        overview, stubs, unmapped = diagram
        for number, line in unmapped:
            note('judgment', path, 'unmapped diagram line: ' + line, number)
        if docs.overview:
            note('judgment', path, 'diagram needs an owner-reviewed overview')
            continue
        for stub, value in stubs.items():
            item(stub, value, 'use case stub from diagram')
            note('judgment', stub, 'decide goal and trigger and check actor links')
        item(Path(docs.root) / 'use_cases.md', overview, 'generated use case overview')
        if not unmapped:
            item(path, None, 'retire PlantUML diagram')
    for given, converter, label in [(docs.requirements, convert_requirements, 'requirements columns'),
                                    (docs.entity_model, convert_entity_model, 'business types and columns')]:
        if not given:
            continue
        path = Path(given)
        value = content(path)
        if converter is convert_requirements:
            for table in model.read_tables(value.split('\n')):
                for n, row, _ in table['rows']:
                    if 'User Story' in table['header']:
                        story = row.get('User Story', '')
                        match = re.fullmatch(r'As a (.+?), I want (.+?) so that (.+?)\.', story)
                        note('judgment', path, '%s: benefit retained for judgment: %s' % (row.get('ID', ''), match[3]) if match else '%s: off-pattern user story: %s' % (row.get('ID', ''), story), n)
                    if row.get('ID', '').startswith(('NFR-', 'C-')):
                        statement = row.get('Statement', row.get('Requirement', row.get('Constraint', '')))
                        if not model.ears_ok(statement):
                            note('judgment', path, '%s: statement into EARS: %s' % (row['ID'], statement), n)
        else:
            for table in model.read_tables(value.split('\n')):
                if 'Attribute' not in table['header']:
                    continue    # a glossary or a words-to-avoid table holds no business types
                for n, row, _ in table['rows']:
                    dtype = row.get('Data Type', row.get('Type', ''))
                    if not model.entity_type_ok(dtype) and dtype not in TYPE_MAP and not re.search(r'Primary Key|Foreign Key|Values:', row.get('Validation Rules', '')):
                        note('judgment', path, '%s: unclear business type %s' % (row.get('Attribute', ''), dtype), n)
        new_text = converted(converter, value, path)
        if new_text is None:
            note('judgment', path, 'unrecognized ' + label)
        else:
            if path in renames:
                target = renames[path]
                item(target, value, 'rename ' + path.name, source=path)
                path = target
            if new_text != value:
                item(path, new_text, label, before_text=value)
    for given in docs.test_case_files():
        path = Path(given)
        value = content(path)
        if re.search(r'^## Flow\r?$', value, re.M):
            note('judgment', path, 'journey Flow table', next(n for n, line in enumerate(value.split('\n'), 1) if line.strip() == '## Flow'))
        if not value.startswith('---'):
            new_text = converted(convert_journey, value, path)
            if new_text is None:
                note('judgment', path, 'journey Overview or Process field needs judgment')
            else:
                item(path, new_text, 'journey Overview into front matter')
    for given in docs.change_record_files():
        path = Path(given)
        value = content(path)
        if '### Classification' not in value:
            continue
        for title, n, body in model.sections(value.split('\n'), 3):
            if title == 'Next' and any(t.strip() for _, t in body):
                note('judgment', path, 'Next carried into Consequences: ' + ' '.join(t.strip() for _, t in body if t.strip()), n)
        new_text = converted(convert_record, value, path)
        if new_text is None:
            note('judgment', path, 'unrecognized long change record')
        else:
            item(path, new_text, 'short change record')
    folder = safe(root, root / 'tools' / 'specs')
    known = json.loads((HERE / 'known_scripts.json').read_text(encoding='utf-8'))['scripts']
    if folder.exists():
        bundle_path = safe(root, folder / installed_copies.BUNDLE_NAME)
        bundle = installed_copies.read_bundle(folder)
        current = {name: installed_source(name).read_bytes() for name in INSTALLED_SCRIPTS}
        states = {name: installed_copies.classify(safe(root, folder / name), current[name], known, bundle)
                  for name in INSTALLED_SCRIPTS}
        undecided = any(state == 'changed' for state in states.values())
        baselines = bundle.get('scripts', {})
        if not isinstance(baselines, dict):
            baselines = {}
        wrote = False
        for name in sorted(INSTALLED_SCRIPTS):
            path, state = folder / name, states[name]
            if state == 'changed':
                what = ('changed by hand: run scaffold_docs.py --update with --replace %s or --keep %s'
                        % (name, name))
            elif undecided:
                what = state + '; scripts wait for all decisions'
            else:
                what = {'missing': 'add', 'untouched': 'untouched; replace with the current copy'}.get(state, state)
            note('installed', path, what)
            public['installed'][-1]['state'] = state
            if not undecided and state in ('untouched', 'missing'):
                item(path, current[name].decode('utf-8'), what)
                baselines[name] = {'baseline': installed_copies.fingerprint(current[name])}
                wrote = True
        if wrote:
            bundle.update(version=installed_copies.UPSPEC_VERSION, scripts=baselines)
            item(bundle_path, json.dumps(bundle, indent=2, sort_keys=True) + '\n', 'refresh installed script baselines')
    return public, rename_items + items


def atomic(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    mode = stat.S_IMODE(path.stat().st_mode) if path.exists() else None
    fd, temporary = tempfile.mkstemp(prefix='.' + path.name + '.', dir=str(path.parent))
    try:
        with os.fdopen(fd, 'w', encoding='utf-8', newline='') as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        if mode is not None:
            os.chmod(temporary, mode)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def write_journal(path, state):
    atomic(path, json.dumps(state, indent=2, ensure_ascii=False) + '\n')


def dirty_paths(root):
    # -z makes filenames (including spaces and rename arrows) unambiguous.
    result = subprocess.run(['git', '-C', str(root), 'status', '--porcelain', '-z', '--untracked-files=all'], capture_output=True, check=True)
    fields = result.stdout.decode('utf-8').split('\0')
    paths, i = set(), 0
    while i < len(fields) and fields[i]:
        entry = fields[i]
        paths.add(entry[3:])
        if 'R' in entry[:2] or 'C' in entry[:2]:
            i += 1
            paths.add(fields[i])
        i += 1
    return paths


def validate_resume(root, state, docs):
    if not isinstance(state, dict) or not isinstance(state.get('items'), list):
        raise Conflict('invalid migration journal structure')
    for entry in state['items']:
        if (not isinstance(entry, dict) or not isinstance(entry.get('path'), str)
                or not isinstance(entry.get('done'), bool)
                or not isinstance(entry.get('text'), (str, type(None)))
                or 'text' not in entry or 'before' not in entry or 'after' not in entry):
            raise Conflict('invalid migration journal item')
    if state.get('version') != 1 or state.get('head') != git(root, 'rev-parse', 'HEAD') or state.get('docs') != str(Path(docs.root).relative_to(root)):
        raise Conflict('journal version, HEAD or --docs differs from the interrupted apply')
    by_path = {}
    for entry in state['items']:
        authorized(root, entry['path'])
        if fingerprint(entry['text'].encode('utf-8') if entry['text'] is not None else None) != entry['after']:
            raise Conflict('%s: journal text does not match its after-fingerprint' % entry['path'])
        by_path.setdefault(entry['path'], []).append(entry)
        if 'source' in entry:
            authorized(root, entry['source'])
            by_path.setdefault(entry['source'], []).append({'before': entry['source_before'], 'after': None, 'done': entry['done']})
    problems = sorted(dirty_paths(root) - set(by_path))
    for path, entries in by_path.items():
        target = root / path
        if target.exists() and not target.is_file():
            problems.append(path)
            continue
        held = fingerprint(target.read_bytes() if target.exists() else None)
        pending = next((e for e in entries if not e['done']), None)
        acceptable = {pending['before'], pending['after']} if pending else {entries[-1]['after']}
        if held not in acceptable:
            problems.append(path)
    if problems:
        raise Conflict('resume conflict; changed since the journal: ' + ', '.join(sorted(set(problems))))


def apply(root, docs, journal):
    if journal.exists():
        try:
            state = json.loads(journal.read_text(encoding='utf-8'))
            validate_resume(root, state, docs)
        except (KeyError, TypeError, ValueError) as exc:
            raise Conflict('invalid migration journal: %s' % exc)
    else:
        if dirty_paths(root):
            raise Conflict('dirty git work tree without a migration journal')
        _, items = plan(root, docs)
        if not items:
            print('Nothing mechanical to do; plan lists any remaining judgment work.')
            return 0
        state = {'version': 1, 'head': git(root, 'rev-parse', 'HEAD'),
                 'docs': str(Path(docs.root).relative_to(root)), 'items': items}
        write_journal(journal, state)
    stop = int(os.environ.get('UPSPEC_MIGRATE_STOP_AFTER', '0'))
    crash = int(os.environ.get('UPSPEC_MIGRATE_CRASH_AFTER_WRITE', '0'))
    count = 0
    for entry in state['items']:
        if entry['done']:
            continue
        path = authorized(root, entry['path'])
        held = fingerprint(path.read_bytes() if path.exists() else None)
        if 'source' in entry and (root / entry['source']).exists():
            source_path = authorized(root, entry['source'])
            source_held = fingerprint(source_path.read_bytes() if source_path.exists() else None)
            if source_held != entry['source_before']:
                raise Conflict('%s: changed since the journal was written' % entry['source'])
            if held != entry['before']:
                raise Conflict('%s: changed since the journal was written' % entry['path'])
            git(root, 'mv', '--', entry['source'], entry['path'])
            held = source_held
        elif 'source' in entry:
            if held != entry['after']:
                raise Conflict('%s: rename source disappeared since the journal was written' % entry['source'])
        elif held != entry['after']:
            if held != entry['before']:
                raise Conflict('%s: changed since the journal was written' % entry['path'])
            if entry['text'] is None:
                path.unlink()
            elif path == root / 'tools' / 'specs' / installed_copies.BUNDLE_NAME:
                installed_copies.write_bundle(path.parent, json.loads(entry['text']))
            else:
                atomic(path, entry['text'])
        count += 1
        if crash and count == crash:
            print('Test hook: stopped after write, before journal update.')
            return 3
        entry['done'] = True
        write_journal(journal, state)
        if stop and count == stop:
            print('Test hook: stopped with a resumable journal.')
            return 3
    journal.unlink()
    print('Mechanical migration complete. Run plan for judgment work, then verify.')
    return 0


def verify(docs):
    found = [(p, n, 'OLD_FORMAT', w) for p, n, w in model.old_formats(docs)]
    found += model.format_findings(docs)
    if not use_case_map.current(docs):
        found.append((docs.overview or str(Path(docs.root) / 'use_cases.md'), 1, 'STALE_OVERVIEW', 'regenerate the overview'))
    for path, line, code, message in found:
        print('%s:%d: ERROR %s: %s' % (path, line, code, message))
    lint = subprocess.run([sys.executable, str(HERE / 'spec_lint.py'), '--docs', docs.root, '--format', 'json'], capture_output=True, text=True)
    try:
        data = json.loads(lint.stdout)
        if lint.returncode not in (0, 1) or not isinstance(data['findings'], list) or not isinstance(data['summary'], dict):
            raise ValueError('invalid lint result')
        for f in data['findings']:
            if not isinstance(f, dict) or not all(k in f for k in ('path', 'line', 'severity', 'code', 'message')) or not isinstance(f['line'], int):
                raise ValueError('invalid lint finding')
    except (ValueError, KeyError, TypeError):
        print('%s:0: ERROR LINT_RUN: could not run the lint: %s' % (docs.root, lint.stderr.strip() or lint.stdout.strip()))
        return 1
    print('Present before or newly visible: for the owner')
    for f in data['findings']:
        print('%s:%d: %s %s: %s' % (f['path'], f['line'], f['severity'], f['code'], f['message']))
    return 1 if found else 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('mode', choices=('plan', 'apply', 'verify'))
    parser.add_argument('--docs', default=model.docs_default())
    parser.add_argument('--format', choices=('text', 'json'), default='text')
    args = parser.parse_args(argv)
    docs = model.Docs(os.path.abspath(args.docs))
    try:
        if not Path(docs.root).is_dir():
            parser.error('no such docs folder: ' + docs.root)
        if args.mode == 'plan':
            print('warning: apply will need git', file=sys.stderr)
            root = find_root(docs.root)
            given = Path(docs.root)
            alias = next((p for p in given.parents if p.exists() and p.samefile(root)), None)
            if alias is not None:
                docs = model.Docs(str(root / given.relative_to(alias)))
            authorized(root, Path(docs.root))
            public, _ = plan(root, docs)
            if args.format == 'json':
                print(json.dumps(public, indent=2, ensure_ascii=False))
            else:
                for group, entries in public.items():
                    for entry in entries:
                        print('%s:%d: INFO %s: %s' % (entry['path'], entry['line'], group.upper(), entry['what']))
            return 0
        root = Path(git(Path(docs.root), 'rev-parse', '--show-toplevel'))
        # git canonicalizes macOS /var and /tmp aliases; keep links inside the
        # worktree visible to safe() rather than resolving the whole docs path.
        given = Path(docs.root)
        alias = next((p for p in given.parents if p.exists() and p.samefile(root)), None)
        if alias is not None:
            docs = model.Docs(str(root / given.relative_to(alias)))
        authorized(root, Path(docs.root))
        if args.mode == 'verify':
            return verify(docs)
        journal = Path(git(root, 'rev-parse', '--absolute-git-dir')) / JOURNAL
        return apply(root, docs, journal)
    except GitUnavailable as exc:
        print('%s:0: ERROR GIT_UNAVAILABLE: %s' % (docs.root, exc), file=sys.stderr)
        return 3
    except (Conflict, subprocess.CalledProcessError) as exc:
        print('%s:0: ERROR MIGRATION_CONFLICT: %s' % (docs.root, exc), file=sys.stderr)
        return 3
    except (OSError, UnicodeError) as exc:
        print('%s:0: ERROR UNREADABLE: %s' % (getattr(exc, 'spec_path', None) or getattr(exc, 'filename', None) or docs.root, exc), file=sys.stderr)
        return 1
    except ValueError as exc:
        print('%s:0: ERROR MIGRATION_INPUT: %s' % (docs.root, exc), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
