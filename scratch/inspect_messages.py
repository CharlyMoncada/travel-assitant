import asyncio
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, SystemMessage

print("HumanMessage type:", HumanMessage(content="hi").type)
print("AIMessage type:", AIMessage(content="hi").type)
print("ToolMessage type:", ToolMessage(content="hi", tool_call_id="1").type)
print("SystemMessage type:", SystemMessage(content="hi").type)
