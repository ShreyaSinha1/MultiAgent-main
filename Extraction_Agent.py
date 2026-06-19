import asyncio
import logging
import re
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver
from thenvoi import Agent
from thenvoi.adapters import LangGraphAdapter
from thenvoi.config import load_agent_config
import os
from dotenv import load_dotenv
from thenvoi import ExecutionContext, AgentTools
import requests
from thenvoi import ThenvoiLink
#AlphaAgents

# my_rest_client = requests.Session()
# my_rest_client.headers.update({
#     "Authorization": "Bearer YOUR_API_SECRET_TOKEN",
#     "Content-Type": "application/json"
# })
link = ThenvoiLink(agent_id="sender_agent",api_key="OPENAI_API_KEY")


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class HybridExtractor:
    def extract_text(self, document_path: str) -> str:
        # Hybrid Pipeline: CPU-based regex / OCR placeholder
        raw_text = "CONFIDENTIAL: Patient ID 998-A. Treatment administered on 12/04/2026. Drug X-44 applied."
        return raw_text

async def main():
    load_dotenv()
    extractor = HybridExtractor()
    
    adapter = LangGraphAdapter(
        llm=ChatOpenAI(model="gpt-4o"),
        checkpointer=InMemorySaver(),
        custom_section="You are a CPU-level data extractor. Isolate raw PII and compliance-related strings from incoming files."
    )
    
    #agent_id, api_key = load_agent_config("extractor_agent")
    agent_id = os.getenv("THENVOI_EXTRACTOR_AGENT_ID")
    api_key = os.getenv("THENVOI_EXTRACTOR_API_KEY")

    agent = Agent.create(adapter=adapter, agent_id=agent_id, api_key=api_key)
    
    # Simulate extraction before passing to router
    raw_data = extractor.extract_text("dummy_medical_record.pdf")
    logger.info(f"Extracted Text via CPU Pipeline: {raw_data}")
    
    # Send data onto the Band SDK network to communicate with next agent
    tools=AgentTools(room_id="12345", rest=link.rest)
    await tools.add_participant("router_agent")

    await tools.send_message(content=f'@router_agent{raw_data}')#f"@router_agent {raw_data}")
    logger.info("Sent extracted data to Router.")

if __name__ == "__main__":
    asyncio.run(main())
