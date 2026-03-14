import os
from icecream import ic
ic.configureOutput(prefix=f'Debug | ', includeContext=True)
from langgraph.graph import StateGraph, END
from typing import TypedDict, List, Literal
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_tavily import TavilySearch

# 1. Upgrade the State (Add web_context and qa_status)
class AssessmentState(TypedDict):
    company_name: str
    retrieved_context: str
    web_context: str
    compliance_flags: List[str]
    qa_status: str
    human_override: bool
    final_decision: str
    summary: str

# 2. Initialize Models & Tools
llm = ChatGoogleGenerativeAI(model="gemini-3.1-flash-lite-preview", temperature=0)
embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2", model_kwargs={"device": "cpu"})
vectorstore = Chroma(persist_directory="./chroma_db", embedding_function=embeddings)
web_search_tool = TavilySearch(max_results=2)

# 3. Define the Agents (Nodes)
def retriever_node(state: AssessmentState):
    """Agent 1: Local DB Search"""
    print(f"🕵️ Retriever: Checking local DB for '{state['company_name']}'...")
    retriever = vectorstore.as_retriever(search_kwargs={"k": 3})
    docs = retriever.invoke(state["company_name"])
    context = "\n".join([d.page_content for d in docs]) if docs else "NO_LOCAL_DATA"
    return {"retrieved_context": context}

def web_search_node(state: AssessmentState):
    """Agent 2: Live Web Search (Triggered only if QA fails)"""
    company = state['company_name']
    print(f"\n Web Search Agent: Looking up latest AML news on '{company}'...")

    query = f"{company} money laundering fraud compliance news"

    try:
        # Pass the query purely as a string
        results = web_search_tool.invoke(query)

        if isinstance(results, dict) and "results" in results:
            web_data = "\n\n".join([f"News: {r.get('content', '')}" for r in results["results"]])
        elif isinstance(results, list):
            web_data = "\n\n".join([f"News: {r.get('content', r)}" for r in results])
        else:
            web_data = str(results)

        print("\n" + "="*50)
        print(web_data[:500] + " ...[TRUNCATED]")
        print("="*50 + "\n")

    except Exception as e:
        print(f"Web Search API Error: {e}")
        web_data = "ERROR_FETCHING_WEB_DATA"

    return {"web_context": web_data}

def compliance_node(state: AssessmentState):
    """Agent 3: Analyzes all data"""
    print("⚖️  Compliance Agent: Analyzing risk vectors...")
    full_context = f"LOCAL DB:\n{state.get('retrieved_context', '')}\n\nWEB DATA:\n{state.get('web_context', 'NONE')}"
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are an AML Compliance AI.

        GUARDRAILS:
        1. IDENTITY: If the company name '{company}' is NOT mentioned in the context at all, output ONLY: '- ENTITY_MISMATCH'.
        2. NO RISKS: If the context is a generic policy or if no specific violations are found for '{company}', output NOTHING (an empty response).
        3. RISK EXTRACTION: Only extract risk flags if the context describes an actual investigation, suspicious financial metric, or violation specifically for '{company}'.

        Output format: A bulleted list of risks, or nothing at all."""),
        ("user", "Company: {company}\nContext: {context}")
    ])

    chain = prompt | llm | StrOutputParser()
    response = chain.invoke({"company": state["company_name"], "context": full_context})
    flags =[f.strip("- *") for f in response.split("\n") if f.strip()]
    #ic(response)
    #ic(flags)
    return {"compliance_flags": flags}

def qa_evaluator_node(state: AssessmentState):
    print("🧐 QA Agent: Evaluating compliance findings...")
    flags = state.get("compliance_flags", [])

    # 1. Did the Compliance agent flag a mismatch?
    mismatch = any("ENTITY_MISMATCH" in f.upper() for f in flags)

    # 2. Is the flags list empty? (This happens if the LLM followed Rule #2)
    no_flags_found = len(flags) == 0

    # 3. Did the retriever fail?
    no_local_context = state.get("retrieved_context") == "NO_LOCAL_DATA"

    if mismatch or no_flags_found or no_local_context:
        # Only search if we haven't already
        if not state.get("web_context"):
            print("🌐 -> QA: Local data insufficient. Routing to Web Search.")
            return {"qa_status": "SEARCH_NEEDED"}

    print("   -> QA: Data is sufficient. Proceeding to human review.")
    return {"qa_status": "PASS"}

def synthesizer_node(state: AssessmentState):
    """Agent 5: Final Report Generator (Handles Human Overrides)"""
    print("📝 Synthesizer Agent: Generating final report...")

    company = state["company_name"]
    flags_str = ", ".join(state["compliance_flags"])
    # Combine all evidence so the AI sees the links
    evidence = f"LOCAL DATA:\n{state.get('retrieved_context')}\n\nWEB DATA:\n{state.get('web_context')}"

    if state.get("human_override"):
        system_msg = f"""You are the Head of Compliance.
        A Senior Human Partner has issued a DIRECT OVERRIDE and approved '{company}' despite the AI finding major risk flags.

        YOUR TASK:
        Write a professional Internal Memorandum.
        1. Start with 'DECISION: APPROVED (BY HUMAN OVERRIDE)'.
        2. Specifically list these risks found: {flags_str}.
        3. Reference the specific evidence found in the context provided.
        4. Explicitly state that the final legal and regulatory accountability for onboarding '{company}' rests with the human approver.

        CRITICAL: DO NOT use brackets like [Insert Name]. Use the actual data provided."""
    else:
        system_msg = f"You are the Head of Compliance. Based on the flags ({flags_str}), write a professional determination for '{company}' (APPROVED or REJECTED)."

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_msg),
        ("user", f"Full Evidence Context: {evidence}")
    ])

    chain = prompt | llm | StrOutputParser()
    response_text = chain.invoke({})

    # --- LOGIC FIX: Sync the JSON decision with the Text ---
    if state.get("human_override"):
        decision = "APPROVED (BY HUMAN OVERRIDE)"
    elif "REJECTED" in response_text.upper():
        decision = "REJECTED"
    else:
        decision = "APPROVED"

    return {"final_decision": decision, "summary": response_text}

# 4. The Conditional Router Function
def route_after_qa(state: AssessmentState) -> Literal["web_search", "synthesizer"]:
    if state["qa_status"] == "SEARCH_NEEDED":
        return "web_search"
    return "synthesizer"

# 5. Build the Cyclic Graph
workflow = StateGraph(AssessmentState)

workflow.add_node("retriever", retriever_node)
workflow.add_node("web_search", web_search_node)
workflow.add_node("compliance", compliance_node)
workflow.add_node("qa_evaluator", qa_evaluator_node)
workflow.add_node("synthesizer", synthesizer_node)

workflow.set_entry_point("retriever")

# Linear Edges
workflow.add_edge("retriever", "compliance")
workflow.add_edge("compliance", "qa_evaluator")

# CONDITIONAL EDGE (This is the ONLY way out of the QA Evaluator)
workflow.add_conditional_edges("qa_evaluator", route_after_qa, {
    "web_search": "web_search",
    "synthesizer": "synthesizer"
})

# Loop Back Edge
workflow.add_edge("web_search", "compliance")

# Final Edge
workflow.add_edge("synthesizer", END)

# 6. Compile
from langgraph.checkpoint.memory import MemorySaver
memory = MemorySaver()
app = workflow.compile(
    checkpointer=memory,
    interrupt_before=["synthesizer"]
)
