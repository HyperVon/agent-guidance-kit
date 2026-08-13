# File endpoint contract

- Identity must come from a verified session token, not a caller-controlled
  identity header.
- A user may read only files authorized for that identity.
- The requested name must remain beneath `/srv/files` after normalization and
  symlink resolution.
- Missing or invalid identity returns `401`; unauthorized file access returns
  `403`; malformed names are rejected without opening a file.
