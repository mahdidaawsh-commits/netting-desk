# StudioNet proofs

Network: **gasless StudioNet**, chain **61999**, not Bradbury.

Contract address: `0xDBf83c382Aae585FB3f79Aa8b770833701C164c2`.

| Operation | Transaction | Verified result |
|---|---|---|
| Deploy | [0x6276c7…](https://explorer-studio.genlayer.com/tx/0x6276c771983cf49f1d0dd52bd7abc09a78fb87939411139f9f294dc1c48817e0) | Successful deployment; source bytes match |
| Unequal ring | [0xc46474…](https://explorer-studio.genlayer.com/tx/0xc4647481ccbd46eb6a1c3ed15504cdcefbd0e1cf896a35c7ff00420443d3762b) | NETTED; 15→3 gross units; 12 canceled |
| Protected position | [0x4f9490…](https://explorer-studio.genlayer.com/tx/0x4f949058066933f5cfb72fed3708e01e8954e9e8a89742e4ca281ea4a3cdec76) | UNCHANGED; DENY position excluded; all quantities retained |
| Competing cycles | [0x35faf5…](https://explorer-studio.genlayer.com/tx/0x35faf53fe72a5cdfceac792c4be45c1c736f187fa2cd786bfa9610570494b074) | NETTED; 16→4 gross units; optimum 12 beats greedy 8 |
| Missing approval | [0x8f4d10…](https://explorer-studio.genlayer.com/tx/0x8f4d1055b89a6b33fac38eeacd5fcebcde546faa41e4b8be67781a03495f231c) | REVIEW; UNKNOWN position excluded; all quantities retained |

**All five receipts are FINALIZED, MAJORITY_AGREE, and execution SUCCESS.** Each scenario preserves all three parties' incoming-minus-outgoing net positions. Gross canceled units count obligation legs; they are not cash released or profit. Full receipts retain disagreeing and idle votes rather than presenting unanimity.

The [successful CLI workflow](https://github.com/mahdidaawsh-commits/netting-desk/actions/runs/37329279583) resumed the existing deployment from an [initial run](https://github.com/mahdidaawsh-commits/netting-desk/actions/runs/37327741329) that stopped before its first scenario submission when `eth_gasPrice` returned HTML. A fresh ephemeral caller completed the permissionless writes against the original contract. No duplicate deployment was sent. The runner compares deployed source before any resumed write; only explicitly identified pre-signing gas-price failures can be retried, and submitted hashes are journaled.

The workflow re-fetched every published fixture, checked exact bytes, used the GenLayer CLI for deployment/receipt/write/read/code operations, and independently enumerated the six reduction variables. Its proof verifier checked maximum gross cancellation, canonical tie order, original and residual quantities, every permission decision, quote membership, exclusions, source hashes, targets, calldata and finalized votes.

Reproduce:

```sh
node scripts/verify-proofs.cjs
```

[Deployment manifest](deployment.json) contains complete transaction hashes and source commitments. Individual `*-receipt.json` files are receipts; `ring.json`, `protected.json`, `competing.json` and `conditional.json` hold progressively accumulated onchain state snapshots.

Source SHA-256: `fdb24f25841a8fad5fc7c831868556bf2878a9ffd336083d4e303648288eb19f`.

Fixture commit: `0f61028320be572b684fccc74d7babef350d4f0a`.

These synthetic publisher-declared snapshots demonstrate permission-gated ledger compression. They do not prove real debts, party assent, legal discharge, service delivery or asset transfers.
