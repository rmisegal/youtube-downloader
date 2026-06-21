"""Multi-vendor LLM auth layer (adapted from C:\\25D\\app\\basic-clis).

Two auth modes per vendor: **CLI login** (shell out to the vendor's own CLI — e.g. the
``claude`` Claude Code CLI — using the subscription, no API key) and **API key**. The
default is Claude via CLI login. In CLI mode the API key is scrubbed from the child
env so the CLI uses the login, not the key. Powers the pipeline's SCRIPT stage.
"""
