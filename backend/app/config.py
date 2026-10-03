"""Runtime configuration and layer switches.

Reads GRADER, ENABLE_CTC, ENABLE_RHYTHM and ENABLE_TONE from the environment and
provides layers_for(target, mode), which says which grading layers run for an
attempt.

Owner: B. Spec: docs/contracts/backend-interfaces.md, section 4.
"""
