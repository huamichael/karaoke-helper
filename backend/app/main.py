"""FastAPI application and routes.

Serves the song list, a song bundle, and POST /api/v1/attempts, which hands a
recording to the grader and returns an AttemptResult. Also mounts /media and
enables CORS for the frontend dev server. Contains no grading logic.

Owner: B. Spec: docs/contracts/api.md.
"""
