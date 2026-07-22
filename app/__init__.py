# app package – lazy import to avoid pulling in the full app stack
# when running standalone MCP servers (e.g. python -m app.mcp.finance.server)
import os

os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"


