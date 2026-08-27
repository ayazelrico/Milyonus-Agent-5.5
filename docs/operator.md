# Operator authority (T0)

T0 is the highest trust tier — operator authority, not a claim. Treating memory
promotion as a security boundary means **no text the model sees can ever mint
T0**: not a chat message, not a file, not a tool result. A T0 write is bound to a
cryptographic operator identity and happens on a separate surface.

## The boundary (H1)

- **Out-of-band only.** T0 writes go through `milyonus admin`, a surface the
  agent and every messaging channel cannot reach. The agent's `memory_propose`
  tool physically cannot request the operator tier (enforced + tested).
- **Asymmetric signature.** Each T0 write is signed with an **Ed25519 operator
  private key** that lives OFF the agent host. The host holds only the public key
  — it can *verify* a T0 write but can never *forge* one, even under full
  compromise. Missing key or missing `cryptography` → **fail closed** (refused).
- **Two-phase, AND-layered activation.** A staged T0 is passive (never a
  default). Activating it requires **both** a second, distinct signature **and**
  a mandatory review gap (`t0_review_seconds`, default 300s) since staging. A
  time window alone never activates T0; a signature alone doesn't either.
- **Audited.** Every stage/activate is recorded on the hash-chained ledger with
  the key fingerprint; review with `milyonus audit log`.

## Setup

```bash
pip install milyonus-agent[admin]         # brings in cryptography

# on your own trusted device — keep the private key OFF the agent host:
milyonus admin keygen --private ~/operator-key.pem
# the public key is installed at ~/.milyonus/operator.pub for verification
```

## Writing a T0 claim

```bash
# 1. stage (passive)
milyonus admin t0 add "Deploys are allowed only from CI" --key ~/operator-key.pem

# 2. after the review gap, activate with a second signature
milyonus admin t0 activate <id> --key ~/operator-key.pem

milyonus admin t0 list      # staged + active T0, and the operator key fingerprint
```

T0, once active, does not decay (it is authority, not a claim). Every other tier
decays and must be re-earned — see the trust-boundary model in the memory docs.
