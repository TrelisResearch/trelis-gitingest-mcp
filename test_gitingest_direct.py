import asyncio
from gitingest import ingest

# --- Configuration ---
REPO_URL = "https://github.com/cyclotruc/gitingest"

# --- Test Case 1: Exact File Path ---
# This tests if the library can handle a nested path with no globs.
print("--- Running with exact file path: 'src/gitingest/cli.py' ---")
try:
    pattern1 = {"src/gitingest/cli.py"}
    _, tree1, _ = ingest(source=REPO_URL, include_patterns=pattern1)
    print("Resulting File Tree:")
    print(tree1)
except Exception as e:
    print(f"An error occurred: {e}")

print("\n" + "="*50 + "\n")

# --- Test Case 2: Nested Path with Glob ---
# This tests if the library can handle a glob at the end of a nested path.
print("--- Running with nested glob pattern: 'src/gitingest/cli.p*' ---")
try:
    pattern2 = {"src/gitingest/*"}
    _, tree2, _ = ingest(source=REPO_URL, include_patterns=pattern2)
    print("Resulting File Tree:")
    print(tree2)
except Exception as e:
    print(f"An error occurred: {e}")
