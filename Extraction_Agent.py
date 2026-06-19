import logging
from typing import TypedDict, List
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import StateGraph, END
from band import Agent
#from band.client import BandClient
from band.adapters import LangGraphAdapter
from band.config import load_agent_config
import asyncio  # <-- Add this line here
from langchain_groq import ChatGroq
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ExtractorState(TypedDict):
    raw_text: str
    extracted_data: List[str]
    route_decision: str
    final_summary: str


async def main():
    load_dotenv()
    
    # 1. Load agent credentials from agent_config.yaml
    agent_id, api_key = load_agent_config("extractor_agent")
      # 6. Initialize and run the Band Remote Agent listener
    global agent
    agent = Agent.create(
         adapter=adapter,
         agent_id=agent_id,
         api_key=api_key,
     )

    logger.info("Extractor Agent is running! Press Ctrl+C to stop.")
    await agent.run()

    # Initialize Band Client to interact with other agents
    #band_client = BandClient()

    # 2. Define the extraction node logic
def extract_information(state: ExtractorState):
        logger.info("Extractor processing data...")
        
        # Pull custom prompt configuration from the Band Portal
        # portal_config = await agent.get_config()
        # system_prompt = portal_config.get("prompt", "Extract all key entities, metrics, and facts from the following text.")
        
        incoming_text = ""
        
        if "raw_text" in state and state["raw_text"]:
            incoming_text = state["raw_text"]
        elif "messages" in state and state["messages"]:
            # If triggered via the Band Portal, read the content of the last chat message
            last_msg = state["messages"][-1]
            if isinstance(last_msg, dict):
                incoming_text = last_msg.get("content", "")
            elif hasattr(last_msg, "content"):
                incoming_text = last_msg.content
        else:
            # Absolute fallback to avoid crash if payload shape is completely blank
            incoming_text = str(state)

        system_prompt = "Extract all key entities, metrics, and facts from the following text."
        groq_api_key = os.getenv("GROQ_API_KEY")
    
        if not groq_api_key:
             logger.error("CRITICAL: GROQ_API_KEY environment variable is missing!")

        # Safe fallback block to check if portal properties exist
        if hasattr(agent, "config") and agent.config:
            if isinstance(agent.config, dict):
                system_prompt = agent.config.get("prompt", system_prompt)

        llm =ChatGroq(model="llama-3.3-70b-versatile", temperature=0.2,groq_api_key=groq_api_key)# ChatOpenAI(model="gpt-4o", temperature=0.2)
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content":incoming_text}# state["raw_text"]}
        ]
        
        response = llm.invoke(messages)
        extracted_facts = [line.strip("- ") for line in response.content.split("\n") if line.strip()]
        
        return {"extracted_data": extracted_facts}


def route_to_router(state: ExtractorState):
        logger.info("Forwarding extracted data to Router agent via active workspace room...")
        
        try:
            # Dynamically extract the room ID injected by the platform listener loop
            active_room = "389c6085-eae7-4860-9a7d-b3392b5117c5"
            # if hasattr(agent, "rooms"):
            #     active_room = agent.rooms.get("389c6085-eae7-4860-9a7d-b3392b5117c5") or agent.rooms.get("6f8a1d36-e70b-461b-9f0f-b894ec6c8b3b")
            if  hasattr(agent, "chats") and "389c6085-eae7-4860-9a7d-b3392b5117c5" in agent.chats:
                logger.info("Active chat ! The agent might not be a member of this chat room yet.")
                #await agent.chats["389c6085-eae7-4860-9a7d-b3392b5117c5"].send_message(content=text)

            # if active_room is None:
            #      logger.info("Active room is None! The agent might not be a member of this chat room yet.")
            # else:
            #      logger.info(f"Successfully joined Room ID: {active_room.id}")
            #active_room_id = getattr(agent, "389c6085-eae7-4860-9a7d-b3392b5117c5", None) or getattr(agent, "6f8a1d36-e70b-461b-9f0f-b894ec6c8b3b", None)
            logger.info(f'Active room{active_room}')
            if active_room:
                # Initialize the Room Tool workspace context natively
                room_tools = agent.tools(room_id=active_room)
                
                # Format a targeted agent prompt mention string
                payload_msg = f"@sinhashreya707/router-agent Process the newly extracted dataset. Payload: {state['extracted_data']}"
                
                # Broadcast back to the room workspace channel
                room_tools.send_message(content=payload_msg)
                logger.info(f"Successfully broadcasted to Router inside room: {active_room}")
            else:
                 if hasattr(agent, "room") and agent.room:
                    agent.room.send_message(content=f"@sinhashreya707/router-agent Payload: {state['extracted_data']}")
                 else:
        # Fallback tracking if running in a localized test harness environment
                        logger.warning("No dynamic room context found. Sending text event to global scope.")

                        logger.info(f"[Room Simulation Broadcast] @sinhashreya707/router-agent  Payload: {state['extracted_data']}")
    

                # Safe fallback option if the runner operates out of an isolated scope
           # await agent.send(content=f"@router_agent Payload: {state['extracted_data']}")
                
        except Exception as e:
            logger.error(f"Failed to communicate through room session tools: {e}")
            
        return state
    # 3. Define peer-to-peer communication node logic
    # async def route_to_router(state: ExtractorState):
    #     logger.info("Forwarding extracted data to Router agent...")
        
    #     # Load Router credentials to send a remote trigger
    #     router_cfg = load_agent_config("router_agent")
        
    #     # Trigger the remote Router agent asynchronously using BandClient
    #     await band_client.agents.trigger(
    #         agent_id=router_cfg[0],
    #         payload={"extracted_data": state["extracted_data"]}
    #     )
    #     return state
# 2. Add the Summarizer node function
def summarize_information(state: ExtractorState):
    print("Step 3: Creating execution summary...")
    # Your summary logic here
    summary_text = f"Successfully processed items: {', '.join(state['extracted_data'])}"
    return {"final_summary": summary_text}

# --- CONDITIONAL ROUTING ROUTER ---

# 3. Decision function to check if we should summarize or end early
def check_route_decision(state: ExtractorState):
    if state.get("route_decision")  == "SUMMARIZE":
        return "summarize"
    return END

workflow = StateGraph(ExtractorState)
workflow.add_node("extract", extract_information)
workflow.add_node("forward", route_to_router)
workflow.add_node("summarize", summarize_information)
workflow.set_entry_point("extract")
workflow.add_edge("extract", "forward")
workflow.add_conditional_edges(
    "forward",
    check_route_decision,
    {
        "summarize": "summarize",
        END: END
    }
)

    #workflow.add_edge("forward", END)
    
    # 5. Create adapter with the LangGraph compiled graph
adapter = LangGraphAdapter(
        graph=workflow.compile(),
        checkpointer=InMemorySaver(),
    )

  
if __name__ == "__main__":
    asyncio.run(main())













    # 4. Construct the LangGraph workflow

    




















# import asyncio
# import logging
# import os
# from dotenv import load_dotenv
# from langchain_openai import ChatOpenAI
# from langgraph.checkpoint.memory import InMemorySaver

# # 1. Swapped all thenvoi imports to the targeted band library wrappers
# from band import Agent
# from band.adapters import LangGraphAdapter
# from band.config import load_agent_config

# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)

# class HybridExtractor:
#     def extract_text(self, document_path: str) -> str:
#         # Hybrid Pipeline: CPU-based regex / OCR placeholder
#         raw_text = "CONFIDENTIAL: Patient ID 998-A. Treatment administered on 12/04/2026. Drug X-44 applied."
#         return raw_text

# async def main():
#     load_dotenv()
    
#     # 2. Extract text locally using your custom pipeline logic
#     extractor = HybridExtractor()
#     raw_data = extractor.extract_text("C:/Users/sinha/OneDrive/Desktop/Band-of-Agents/MultiAgent-main/dummy_medical_record.pdf")
#     logger.info(f"Extracted Text via CPU Pipeline: {raw_data}")

#     # 3. Load agent credentials from agent_config.yaml matching targeted structure
#     #agent_id, api_key = load_agent_config("extractor_agent")
#     agent_id = os.getenv("THENVOI_EXTRACTOR_AGENT_ID")
#     api_key = os.getenv("THENVOI_EXTRACTOR_API_KEY")
#     openai_key = os.getenv("AGENT_OPEN_API")



#     # 4. Create your LangGraph adapter with model definitions and system guidelines
#     adapter = LangGraphAdapter(
#         llm=ChatOpenAI(model="gpt-4o",api_key=openai_key ),
#         checkpointer=InMemorySaver(),
#         # Retained custom extraction guidelines within the adapter framework
#         custom_section="You are a CPU-level data extractor. Isolate raw PII and compliance-related strings from incoming files."
#     )

#     # 5. Initialize the core running agent using the band framework
#     agent = Agent.create(
#         adapter=adapter,
#         agent_id=agent_id,
#         api_key=api_key,
#     )
    
#     # 6. Execute network orchestration steps using the active agent instance tools
#     try:
#         room_id = "12345"
#         # Accessing network communication primitives exposed through agent state
#         room_tools = agent.tools(room_id=room_id) 
        
#         await room_tools.add_participant("router_agent")
#         await room_tools.send_message(content=f'@router_agent {raw_data}')
#         logger.info("Sent extracted data to Router.")
#     except Exception as e:
#         logger.error(f"Failed to transmit pipeline data prior to loop start: {e}")

#     # 7. Start the continuous listening thread
#     logger.info("Agent is running! Press Ctrl+C to stop.")
#     await agent.run()

# if __name__ == "__main__":
#     asyncio.run(main())
