#set page(
  paper: "a4",
  margin: (x: 1.5cm, y: 1.5cm),
  header: align(right)[#text(size: 8pt, fill: gray)[Technical Case Study | Neel More]],
  // The 'context' keyword is required here in Typst 0.11+
  footer: context align(center)[#text(size: 8pt, fill: gray)[Page #counter(page).display()]]
)

#set text(font: ("Lato", "sans-serif"), size: 11pt)
#show heading: it => [
  #v(1em)
  #text(weight: "bold", size: 14pt, it.body)
  #v(0.5em)
]

// ==========================================
// TITLE PAGE
// ==========================================
#align(center)[
  #text(size: 26pt, weight: "bold")[CorpRisk-AI] \
  #text(size: 16pt, weight: "medium", fill: rgb("#444444"))[Autonomous Multi-Agent Systems for Banking Compliance] \
  #v(1em)
  #line(length: 100%, stroke: 1pt + black)
  #v(1em)
  #grid(
    columns: (1fr, 1fr),
    align: (left, right),
    [
      *Author:* Neel Shirish More \
      *Role:* Python AI Engineer \
      *Domain:* Financial Services / AML
    ],
    [
      *Stack:* LangGraph, Gemini, RAG \
      *Tools:* LangSmith, Tavily, Docker \
      #link("https://github.com/NeelM47/CorpRisk-AI")[GitHub Repository]
    ]
  )
]

#v(2em)

= Executive Summary
Financial institutions face a critical challenge: manual due diligence is slow, and standard AI "chatbots" hallucinate when local data is missing. *CorpRisk-AI* addresses this by implementing a **cyclic, self-correcting agentic workflow**. 

The system autonomously detects data gaps, fallbacks to live OSINT (Open Source Intelligence) web-searching, and enforces a strict "Human-in-the-Loop" governance model required for regulatory compliance in the UK banking sector.

// ==========================================
// PAGE 2: ARCHITECTURE & TRACING
// ==========================================
#pagebreak()

= 🏗️ Agentic Orchestration & Logic Flow
Unlike linear RAG pipelines, this system uses **LangGraph** to manage a stateful conversation between specialized agents.

#figure(
  image("terminal_trace.png", width: 90%),
  caption: [Fig 1: Terminal Trace showing the Retriever failing locally and autonomously routing to Web Search (OSINT) via Tavily.]
)

*Key Logic Trigger:*
As shown in the logs above, when the Retriever node returns `NO_LOCAL_DATA`, the **QA Supervisor Agent** intercepts the state. Instead of terminating, it triggers a recursive loop to gather live intelligence on entities like "Wirecard" that do not exist in the bank's static database.

// ==========================================
// PAGE 3: OBSERVABILITY
// ==========================================
#pagebreak()

= 📊 Production-Grade Observability
In Banking, "Black Box" AI is a liability. I integrated **LangSmith** to provide full-lifecycle monitoring of the agentic loops.

#figure(
  image("langsmith_monitoring.png", width: 95%),
  caption: [Fig 2: LangSmith Dashboard monitoring P99 Latency, Error Rates, and Token Consumption in real-time.]
)

#v(1em)

*Strategic Engineering Insights:*
- **Tracing:** Every "thought" and web search result is indexed and auditable.
- **Cost Control:** By monitoring token usage per node, I optimized the synthesizer to use `Gemini-1.5-Flash` for heavy reasoning while maintaining low operational costs.
- **Latency Benchmarking:** The dashboard allows us to identify bottlenecks in the OSINT retrieval phase, essential for scaling microservices on **Azure AKS**.

// ==========================================
// PAGE 4: GOVERNANCE & OUTPUT
// ==========================================
#pagebreak()

= ⚖️ Governance: Human-in-the-Loop (HITL)
The final determination is never made by the AI alone. The system utilizes **Checkpointer Memory** to pause execution right before the final synthesis.

#figure(
  image("final_memo.png", width: 85%),
  caption: [Fig 3: Final Compliance Memorandum generated after a Human Partner issued an Override.]
)

#v(1em)

*Decision Provenance:*
As demonstrated in the report above, if a human partner chooses to approve a high-risk entity (like Wirecard), the AI does not hide the risks. It generates an **Audit Trail** that acknowledges the specific fraud flags found on the web while documenting that legal accountability rests with the human approver. 

This architecture directly satisfies **Responsible AI Governance** and **GDPR/AML** audit requirements.

// ==========================================
// CONCLUSION
// ==========================================
#v(2em)
= Technical Capabilities Demonstrated
- **Self-Correction:** Agents that detect entity mismatches and re-route logic.
- **Advanced RAG:** Moving beyond vector search into dynamic OSINT integration.
- **Cloud-Native Dev:** Multi-stage Docker builds for CPU-optimized inference.
- **Observability:** Implementing enterprise-standard tracing for regulated sectors.
