import asyncio
import logging
from pathlib import Path
from dotenv import load_dotenv

dotenv_path = Path("/Users/carlosmoncada/Documents/code/master/tfm/travel-assitant/.env")
load_dotenv(dotenv_path=dotenv_path, override=True)

async def main():
    from app.agents.orchestrator import TravelAgentOrchestrator
    router = TravelAgentOrchestrator()
    
    # Run a message on a thread
    thread_id = "test_inspect_checkpointer"
    res = await router.handle_message("Gastos", thread_id=thread_id)
    
    # Now retrieve the state using a temp agent
    from langchain.agents import create_agent
    from langchain_openai import ChatOpenAI
    from app.services.llm import get_openai_model
    
    llm = ChatOpenAI(model_name=get_openai_model(), temperature=0.0)
    temp_agent = create_agent(llm, [], system_prompt="", checkpointer=router.memory)
    
    config = {"configurable": {"thread_id": thread_id}}
    state = await temp_agent.aget_state(config)
    print("\n--- STATE VALUES KEYS ---")
    if state and state.values:
        print("Keys in state.values:", state.values.keys())
        messages = state.values.get("messages", [])
        print(f"\n--- TOTAL MESSAGES IN CHECKPOINTER: {len(messages)} ---")
        for i, msg in enumerate(messages):
            print(f"Message [{i}]: Class={msg.__class__.__name__}, Type={getattr(msg, 'type', None)}, ID={getattr(msg, 'id', None)}")
            print(f"Content: '{msg.content[:150]}'")
            if hasattr(msg, 'tool_calls') and msg.tool_calls:
                print(f"Tool Calls: {msg.tool_calls}")
    else:
        print("No state found in memory for this thread.")
        
    await router.stop()

if __name__ == "__main__":
    asyncio.run(main())
