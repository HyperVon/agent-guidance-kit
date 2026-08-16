# Review conventions

- Reviews are scoped to a named target: a branch, a diff range against `main`,
  a single subsystem directory, or a specific pull request. State the target
  and the review question before starting.
- The default comparison base is `origin/main` unless the requester names a
  different base.
- Uncommitted working-tree edits are called out separately from committed
  branch work, because they are not part of any pull request yet.
- `spike/*` branches are exploratory and are not reviewed for merge.
- A dependency bump branch is reviewed by running the full suite against it,
  not by reading the diff alone.

## Release notes

### 2024.6.1
- Fix dunning retry cap
- Add tenant timezone column to accounts

### 2024.6.0
- Invoice assembly refactor
- Admin console invoice table
