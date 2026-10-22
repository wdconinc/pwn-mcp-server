import os
import tempfile

# Unit tests must never touch the network; network tests opt back in explicitly.
os.environ.setdefault("PWN_MCP_OFFLINE", "1")
# Keep caches and rendered figures out of the user's cache directory.
os.environ.setdefault("PWN_MCP_CACHE_DIR", tempfile.mkdtemp(prefix="pwn-mcp-test-"))
