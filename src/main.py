import uuid
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv
#from icecream import ic
#ic.configureOutput(prefix=f'Debug | ', includeContext=True)
load_dotenv()
from src.graph import app as langgraph_app


app = FastAPI(title="CorpRisk-AI Multi-Agent API")

class AssessmentRequest(BaseModel):
    company_name: str
    thread_id: str = None         # Allows us to remember the exact request
    human_approved: bool = False  # The human approval flag

@app.post("/api/v1/assess-company")
async def assess_company(request: AssessmentRequest):
    try:
        # Generate a unique thread ID for this specific assessment
        thread_id = request.thread_id or str(uuid.uuid4())
        config = {"configurable": {"thread_id": thread_id}}

        if not request.human_approved:
            # PHASE 1: Start the graph and run until interrupted
            initial_state = {
                "company_name": request.company_name,
                "retrieved_context": "",
                "web_context": "",
                "compliance_flags":[],
                "qa_status": "",
                "final_decision": "",
                "summary": ""
            }
            
            # Stream the graph. It will automatically STOP before 'synthesizer'
            for event in langgraph_app.stream(initial_state, config=config):
                pass 
            
            # Fetch the state where it paused
            state = langgraph_app.get_state(config)
            flags = state.values.get("compliance_flags",[])
            
            return {
                "status": "PAUSED_FOR_HUMAN_REVIEW",
                "message": "AI has finished data gathering and risk analysis. Waiting for human approval.",
                "thread_id": thread_id,
                "risk_flags_found": flags
            }
        
        else:
            # PHASE 2: Human Overrides the AI findings
            if not request.thread_id:
                raise HTTPException(status_code=400, detail="Must provide thread_id to resume.")

            # CRITICAL: We update the state in memory BEFORE resuming the graph
            # This tells the Synthesizer: "The human has made their choice."
            langgraph_app.update_state(
                config,
                {"human_override": request.human_approved}
            )

            # Resume the graph (it will now run the Synthesizer with the override info)
            for event in langgraph_app.stream(None, config=config):
                pass

            final_state = langgraph_app.get_state(config)
            return {
                "status": "COMPLETED",
                "final_decision": final_state.values.get("final_decision"),
                "ai_found_risks": final_state.values.get("compliance_flags"),
                "summary_report": final_state.values.get("summary")
            }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
