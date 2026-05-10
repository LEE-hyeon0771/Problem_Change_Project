import os


# Keep tests deterministic even when the developer's local .env points at a real LLM provider.
os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("USE_LLM_GENERATION", "false")
os.environ.setdefault("ENABLE_PROBLEM_PERSISTENCE", "false")
