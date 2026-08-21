"""Focused validation helpers used by the evaluation entry point.

The command-line validator remains the compatibility entry point. These small
modules keep protocol, evidence, attestation, and harness-specific routing
concerns separate so the neutral adapter contract does not grow new provider
assumptions.
"""
