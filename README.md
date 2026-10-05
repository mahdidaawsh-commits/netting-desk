# NettingDesk

A standalone GenLayer primitive for **maximum balance-neutral obligation cancellation**, with source-derived permission gates.

## Purpose

A three-party ledger can contain mutually offsetting obligations. Greedy pairwise cancellation can leave avoidable gross obligations: in the competing-cycle fixture, canceling alpha→beta against beta→alpha removes 8 units, while a three-party cancellation removes 12. NettingDesk finds the global optimum while preventing a protected obligation from being used in any cancellation.

The source publisher fixes a six-position ledger in shared abstract clearing units. Each position has an amount and a prose operating clause. The contract fetches and hash-checks the complete commit-pinned JSON record; callers cannot submit their own permissions. The leader and validators independently classify each clause as ALLOW, DENY or UNKNOWN. Validators require exact decision agreement and separately verify the source anchors and all conditions.

Only ALLOW amounts become cancellation capacities. The accepted permissions drive an exact integer optimization: maximize the sum of canceled obligations, preserve each party's incoming-minus-outgoing balance, and never reduce an excluded position. Equal objectives prefer the lexicographically larger reduction vector in fixed source order. The result stores actual remaining quantities, reductions, excluded positions and before/after balances.

## State and boundaries

The constructor fixes the publisher repository. `clear(url, sha256)` appends an independent ledger batch; `get_state()` returns the original record, agreed permissions and residual ledger for every accepted batch. No owner can edit or override a result. There are no graph-edit proposals, version approvals, certificates or one-time redemption instruments. The consequential nondeterministic output is the six permission gates, not the deterministic optimizer.

These are **publisher-declared ledger snapshots**, not cryptographically proven debts or verified service deliveries. Each batch is independent; results do not form a cumulative live debt book. Repeating a ledger in differently hashed records does not establish new real obligations. A real settlement integration must authenticate positions and party authority before treating these outputs as binding. The contract neither transfers assets nor establishes legal discharge. The fixtures are synthetic operating instructions, and all quantities share one abstract unit by schema; there is no currency conversion.

## Bounded solver

Exactly three parties, six directed positions, integer amounts 0–8, six clauses of 20–600 characters, 12,000 source bytes, and eight batches per deployment. Permissionless callers can exhaust the batch cap with distinct valid publisher records. No failed evaluation appends a batch.

With reductions `(a,b,c,d,e,f)` in position order, conservation gives `e=a+b-c` and `f=c+d-a`. Exhaustively searching the first four variables needs at most 9⁴=6,561 candidates. UNKNOWN sets that position's capacity to zero; it does not prove approval or prohibition. The gross cancellation objective counts every canceled obligation leg, not cash released or profit.

| Synthetic situation | Expected result |
|---|---|
| Unequal three-party ring | Cancel 12 of 15 gross units; preserve balances |
| Protected ring obligation | No cancellation; original quantities retained |
| Competing two-/three-party cycles | Global optimum 12 exceeds bilateral greedy 8 |
| Missing administrator approval | REVIEW; contingent position excluded |

## Builder resources

- [Pinned GenVM contract](contracts/netting_desk.py)
- [Consensus and algebra](docs/consensus.md)
- [Source records](records)
- [Direct tests](tests/direct/test_clearing.py)
- [CLI deployment](deploy/00_netting_desk.js) and [proof runner](scripts/prove-scenarios.cjs)
- [Independent six-variable proof verifier](scripts/verify-proofs.cjs)
- [Onchain proof receipts](proofs/README.md)

```sh
python -m pip install -r requirements.txt
genvm-lint download --version v0.2.16
genvm-lint check contracts/netting_desk.py --json
pytest tests/direct -q
node scripts/verify-proofs.cjs
```

Direct mocks test parsing, gates and state behavior; explicit validator replay tests exercise the custom validator. Full live consensus uses gasless StudioNet (61999). The workflow journals submitted hashes, retries receipt reads without blind write resubmission, verifies finalized execution and votes, compares deployed source, and checks actual state against independent enumeration.

Model consensus can fail or agree on an incorrect interpretation. The repository does not treat a hash, nonempty text or majority vote as proof that an external obligation was actually incurred. CLI receipt/account scaffolding is reused from earlier projects; the permission-gated clearing mechanism, algebra, fixtures, direct tests and proof verifier are purpose-built. MIT licensed.
