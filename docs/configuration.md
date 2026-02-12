# Configuration reference

All settings are nested under the Django setting `HONEYWORDS`.

## Amnesia parameters

- `AMNESIA_K` (default `20`): number of candidates per user
- `AMNESIA_P_MARK` (default `0.1`): probability a honeyword is marked at initialization
- `AMNESIA_P_REMARK` (default `0.01`): probability remarking occurs after a successful login

## Policy parameters

- `ON_HONEYWORD` (default `"log"`): action when a honeyword is detected (`"log" | "lock" | "reset"`)
- `LOCK_BASE_SECONDS` (default `60`): base lockout duration
- `LOCK_MAX_SECONDS` (default `3600`): maximum lockout duration

## Logging

- `LOG_REAL_SUCCESS` (default `False`): log successful marked-credential logins.

Note: in Amnesia, a successful login indicates a *marked credential* (real or marked honeyword). It does not prove it was the real password.
