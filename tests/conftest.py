import os

# Unit tests must never touch the network; network tests opt back in explicitly.
os.environ.setdefault("PWN_MCP_OFFLINE", "1")
