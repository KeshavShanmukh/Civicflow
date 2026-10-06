# Security Notes

CivicFlow includes local password hashing, session-token hashing, same-origin write protection, secure response headers, input validation, role checks, audit logging, database transactions and attachment validation.

The local demo server binds to loopback by default. Do not expose the development configuration to an untrusted network or store real sensitive personal data in the demo database.
