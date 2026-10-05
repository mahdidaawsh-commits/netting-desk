import ast
import hashlib
import itertools
import json
import re
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[2]
REPO = 'mahdidaawsh-commits/netting-desk'
DOCS = {name: (ROOT / 'records' / f'{name}.json').read_bytes() for name in ['ring', 'protected', 'competing', 'conditional']}

def source(name):
    return f"https://raw.githubusercontent.com/{REPO}/{'a' * 40}/records/{name}.json", hashlib.sha256(DOCS[name]).hexdigest()

def report(name):
    rows = json.loads(DOCS[name])['positions']
    return {'permissions': [{'id': row['id'], 'decision': 'DENY' if i == 4 and name == 'protected' else 'UNKNOWN' if i == 4 and name == 'conditional' else 'ALLOW', 'quote': row['clause']} for i, row in enumerate(rows)]}

def mock(vm, name, leader=None, independent=None, anchors=None, changed=None):
    vm.clear_mocks()
    vm.mock_web(re.escape(source(name)[0]), {'status': 200, 'body': DOCS[name] if changed is None else changed})
    vm.mock_llm(r'.*NETTINGDESK-LEADER.*', json.dumps(report(name) if leader is None else leader))
    vm.mock_llm(r'.*NETTINGDESK-VALIDATOR.*', json.dumps(report(name) if independent is None else independent))
    vm.mock_llm(r'.*NETTINGDESK-ANCHORS.*', json.dumps({'valid': [True] * 6 if anchors is None else anchors}))

@pytest.fixture
def desk(direct_deploy):
    return direct_deploy(str(ROOT / 'contracts/netting_desk.py'), REPO)

def run(c, vm, name):
    mock(vm, name)
    c.clear(*source(name))
    return c.get_state()['batches'][-1]['result']

def test_ring_reduces_amounts_and_preserves_net_positions(desk, direct_vm):
    r = run(desk, direct_vm, 'ring')
    assert r['reductions'] == [4, 0, 0, 4, 4, 0]
    assert r['remaining'] == [2, 0, 0, 0, 1, 0]
    assert r['gross_before'] == 15 and r['gross_after'] == 3 and r['canceled_gross'] == 12
    assert r['net_before'] == r['net_after'] == {'alpha': -1, 'beta': 2, 'gamma': -1}

def test_protected_position_cannot_be_routed_through(desk, direct_vm):
    r = run(desk, direct_vm, 'protected')
    assert r['status'] == 'UNCHANGED' and r['canceled_gross'] == 0
    assert r['remaining'] == [6, 0, 0, 4, 5, 0]
    assert r['excluded'] == [{'id': 'gamma-alpha', 'reason': 'DENY'}]

def test_global_optimum_beats_bilateral_greedy(desk, direct_vm):
    r = run(desk, direct_vm, 'competing')
    assert r['canceled_gross'] == 12 and r['remaining'] == [0, 0, 4, 0, 0, 0]
    # Greedy alpha-beta / beta-alpha cancellation removes only 8 units.
    assert r['canceled_gross'] > 8

def test_missing_approval_blocks_cancellation(desk, direct_vm):
    r = run(desk, direct_vm, 'conditional')
    assert r['status'] == 'REVIEW' and r['canceled_gross'] == 0
    assert r['excluded'] == [{'id': 'gamma-alpha', 'reason': 'UNKNOWN'}]

def test_validator_agrees(desk, direct_vm):
    run(desk, direct_vm, 'ring')
    assert direct_vm.run_validator() is True

@pytest.mark.parametrize('decision', ['ALLOW', 'UNKNOWN'])
def test_validator_rejects_exact_permission_change(desk, direct_vm, decision):
    run(desk, direct_vm, 'protected')
    independent = report('protected')
    independent['permissions'][4]['decision'] = decision
    mock(direct_vm, 'protected', independent=independent)
    assert direct_vm.run_validator() is False

def test_validator_rejects_unknown_promotion(desk, direct_vm):
    run(desk, direct_vm, 'conditional')
    independent = report('conditional')
    independent['permissions'][4]['decision'] = 'ALLOW'
    mock(direct_vm, 'conditional', independent=independent)
    assert direct_vm.run_validator() is False

def test_validator_requires_source_relevant_quotes(desk, direct_vm):
    run(desk, direct_vm, 'protected')
    mock(direct_vm, 'protected', anchors=[True] * 4 + [False, True])
    assert direct_vm.run_validator() is False

def test_validator_refetch_hash_binding(desk, direct_vm):
    run(desk, direct_vm, 'ring')
    mock(direct_vm, 'ring', changed=DOCS['ring'] + b' ')
    assert direct_vm.run_validator() is False

@pytest.mark.parametrize('kind', ['omission', 'enum', 'foreign-quote', 'order'])
def test_malformed_report(desk, direct_vm, kind):
    bad = report('protected')
    if kind == 'omission': bad['permissions'].pop()
    if kind == 'enum': bad['permissions'][0]['decision'] = 'YES'
    if kind == 'foreign-quote': bad['permissions'][4]['quote'] = bad['permissions'][0]['quote']
    if kind == 'order': bad['permissions'].reverse()
    mock(direct_vm, 'protected', leader=bad)
    with direct_vm.expect_revert(): desk.clear(*source('protected'))

def test_duplicate_record_does_not_append(desk, direct_vm):
    run(desk, direct_vm, 'ring')
    with direct_vm.expect_revert('Duplicate record'): desk.clear(*source('ring'))
    assert len(desk.get_state()['batches']) == 1

def test_append_only_independent_batches(desk, direct_vm):
    for name in DOCS: run(desk, direct_vm, name)
    assert len(desk.get_state()['batches']) == 4

@pytest.mark.parametrize('url', ['https://example.com/ledger.json', f"https://raw.githubusercontent.com/other/netting-desk/{'a' * 40}/records/ring.json"])
def test_publisher_binding(desk, direct_vm, url):
    with direct_vm.expect_revert('pinned publisher'): desk.clear(url, 'a' * 64)

@pytest.mark.parametrize('amount', [-1, 9, 1.5, True])
def test_source_amount_bounds(desk, direct_vm, amount):
    record = json.loads(DOCS['ring'])
    record['positions'][0]['amount'] = amount
    body = json.dumps(record).encode()
    mock(direct_vm, 'ring', changed=body)
    with direct_vm.expect_revert('amount'): desk.clear(source('ring')[0], hashlib.sha256(body).hexdigest())

def test_duplicate_json_field_rejected(desk, direct_vm):
    body = DOCS['ring'].replace(b'"amount": 6', b'"amount": 6, "amount": 1')
    mock(direct_vm, 'ring', changed=body)
    with direct_vm.expect_revert('Duplicate JSON'): desk.clear(source('ring')[0], hashlib.sha256(body).hexdigest())

def solver():
    tree = ast.parse((ROOT / 'contracts/netting_desk.py').read_text())
    selected = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in ['net_positions', 'clear_ledger']]
    def failure(message): raise AssertionError(message)
    ns = {'itertools': itertools, 'IDS': ('ab', 'ac', 'ba', 'bc', 'ca', 'cb'), 'fail': failure}
    exec(compile(ast.Module(body=selected, type_ignores=[]), 'solver', 'exec'), ns)
    return ns['clear_ledger']

def test_exhaustive_binary_capacity_optimality_and_tie_break():
    clear = solver()
    # Independent six-dimensional enumeration; do not derive the last two flows.
    for caps in itertools.product([0, 1], repeat=6):
        record = {'positions': [{'amount': value} for value in caps]}
        report_ = {'permissions': [{'decision': 'ALLOW'}] * 6}
        valid = []
        for r in itertools.product(*(range(cap + 1) for cap in caps)):
            incoming = [r[2] + r[4], r[0] + r[5], r[1] + r[3]]
            outgoing = [r[0] + r[1], r[2] + r[3], r[4] + r[5]]
            if incoming == outgoing: valid.append(r)
        expected = max(valid, key=lambda r: (sum(r), r))
        result = clear(record, report_)
        assert result['reductions'] == list(expected)
        assert result['net_before'] == result['net_after']

def test_maximum_bound_and_complete_closure():
    r = solver()({'positions': [{'amount': 8}] * 6}, {'permissions': [{'decision': 'ALLOW'}] * 6})
    assert r['status'] == 'CLOSED' and r['canceled_gross'] == 48 and r['remaining'] == [0] * 6
