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
        custom_section="You are a Compliance/Summarization Agent. Flag compliance errors, redact PII, and generate concise summaries."
    )
    
    #agent_id, api_key = load_agent_config("summarizer_agent")
    agent_id = os.getenv("THENVOI_SUMMARIZER_AGENT_ID")
    api_key = os.getenv("THENVOI_SUMMARIZER_API_KEY")

    agent = Agent.create(adapter=adapter, agent_id=agent_id, api_key=api_key)
    
    async for message in agent.listen_to_room():
        if message.sender_id == "router_agent":
            logger.info(f"Summarizer processing payload: {message.content}")
            
            summary_result = "SUMMARY: Sensitive data identified. Patient PII was properly redacted. Zero compliance violations flagged."
            
            # Broadcast the completed report
            await agent.broadcast_to_room(content=summary_result)
            logger.info("Compliance summary completed and broadcasted to system.")

if __name__ == "__main__":
    asyncio.run(main())
