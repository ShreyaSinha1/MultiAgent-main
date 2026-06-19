import asyncio
import logging
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver
from thenvoi import Agent
from thenvoi.adapters import LangGraphAdapter
from thenvoi.config import load_agent_config
import os
from dotenv import load_dotenv


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    load_dotenv()
    adapter = LangGraphAdapter(
        llm=ChatOpenAI(model="gpt-4o"),
        checkpointer=InMemorySaver(),
        custom_section="You are a routing agent. Reorganize and structure extracted raw text from PDFs before summarizing."
    )
    
    #agent_id, api_key = load_agent_config("router_agent")

    agent_id = os.getenv("THENVOI_ROUTER_AGENT_ID")
    api_key = os.getenv("THENVOI_ROUTER_API_KEY")

    agent = Agent.create(adapter=adapter, agent_id=agent_id, api_key=api_key)
    
    # Mock loop listening for Agent 1's broadcast
    async for message in agent.listen_to_room():
        logger.info(f"Router received raw text: {message.content}")
        
        organized_payload = f"ROUTERED_DATA: \n{message.content.upper()}\nSTATUS: Ready for compliance summary."
        
        # Route to Summarization Agent
        await agent.send_message(recipient_id="summarizer_agent", content=organized_payload)
        logger.info("Routing data to Summarization Agent.")

if __name__ == "__main__":
    asyncio.run(main())
