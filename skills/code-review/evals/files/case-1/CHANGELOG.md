# Changelog

## Unreleased

- Session-context endpoint reports whether a profile row was present
- Page-size clamping helper for the upcoming directory paging work

## 2024.5.2

- Added `GET /internal/export` for the nightly directory job
- Login rate-limit keys are now hashed before they reach the cache
- Bumped Flask to 3.0.3

## 2024.4.1

- MFA challenge gate applied to the legacy desktop login continuation
- `user_profiles` backfill batches 1–7 completed; batches 8+ pending
- Removed the deprecated `GET /whoami` endpoint

## 2024.3.0

- Introduced `user_profiles` table and `Profile` dataclass
- Password hashing moved to `pbkdf2_sha256` with 60000 iterations
