# FBISE Learning Assistant: Product Requirements & Technical Architecture

**Version:** 1.0  
**Date:** January 2026  
**Status:** Planning & Architecture Phase

---

## Table of Contents

### Part I: Product Requirements Document
1. [Abstract](#abstract)
2. [Business Objectives](#business-objectives)
3. [KPI](#kpi)  
4. [Success Criteria](#success-criteria)
5. [User Journeys](#user-journeys)
6. [Scenarios](#scenarios)
7. [User Flow](#user-flow)
8. [Functional Requirements](#functional-requirements)
9. [Model Requirements](#model-requirements)
10. [Data Requirements](#data-requirements)
11. [Prompt Requirements](#prompt-requirements)
12. [Testing & Measurement](#testing--measurement)
13. [Risks & Mitigations](#risks--mitigations)
14. [Costs](#costs)
15. [Assumptions & Dependencies](#assumptions--dependencies)
16. [Compliance/Privacy/Legal](#complianceprivacylegal)
17. [GTM/Rollout Plan](#gtmrollout-plan)

### Part II: Technical Architecture
18. [Agent Architecture Design](#agent-architecture-design)
19. [Multi-Agent Architecture](#multi-agent-architecture)
20. [Agent Hierarchy](#agent-hierarchy)
21. [Detailed Agent Specifications](#detailed-agent-specifications)
22. [Complete Workflow Diagrams](#complete-workflow-diagrams)
23. [Cost Breakdown](#cost-breakdown-per-question-type)
24. [RAG Integration Points](#rag-integration-points)
25. [Agent State Management](#agent-state-management)
26. [Monitoring & Observability](#monitoring--observability)
27. [Final Architecture Summary](#final-architecture-summary)

---

# Part I: Product Requirements Document

## Abstract

A bilingual (and expandable) learning assistant for **FBISE (Federal Board) Class 9–11** students delivered via **Website + WhatsApp**. It helps students (1) quickly access organized study resources (notes, guess papers, lecture links via Google Drive) and (2) understand concepts and solve questions through clear, step-by-step explanations plus short quizzes—while controlling costs and minimizing wrong/confusing answers through grounded responses and guardrails.

## Business Objectives

- Improve exam readiness for FBISE students by reducing time spent searching for quality materials.
- Increase learning confidence by providing explanations and step-by-step solutions aligned with the curriculum.
- Build a scalable distribution channel (web + WhatsApp) with repeat usage and measurable learning engagement.
- Maintain trust and sustainability via cost controls and accuracy/clarity guardrails.

## KPI

| GOAL                           | METRIC                 | QUESTION                                       |
| ------------------------------ | ---------------------- | ---------------------------------------------- |
| Student reach & adoption       | WAU (# weekly actives) | How many unique students use it weekly?        |
| Early stickiness               | D7 Retention           | Do students return within 7 days?              |
| Resource value realization     | Content Engagement     | Do students open/click Drive resources?        |
| Learning assistance volume     | Questions Solved       | How many questions are handled successfully?   |

## Success Criteria

- Students can reliably find the right material in < 60 seconds (web) or < 2 minutes (WhatsApp).
- Majority of question sessions produce clear step-by-step guidance plus a relevant resource link.
- Low "confusing/wrong answer" complaints relative to total question sessions.
- Stable operating costs per active student (target defined during beta once baselines are known).
- Launch in one board-aligned slice (e.g., Class 10 Science first) then expand across classes/subjects.

## User Journeys

- A Class 10 student opens WhatsApp, selects Urdu, picks Physics, chooses "I need notes," and receives chapter-wise links plus the "top recommended" for the upcoming exam.
- A Class 9 student uses the website, selects English, chooses Math, selects "I have a question," receives a simple explanation, step-by-step solution, a short quiz to confirm understanding, and a link to the most relevant notes/lecture.
- A Class 11 student returns weekly, using the same flow but benefiting from faster navigation (saved preferences) and consistent explanations in their chosen language.

## Scenarios

- "I need guess paper for Class 10 Chemistry (Chapter-wise)."
- "Explain Newton's laws in simple Urdu and give an example."
- "Solve this Math question step-by-step and then give 3 practice questions."
- "I'm confused about a concept—give a simpler explanation and point me to notes/lecture."
- "I opened a Drive link and it says permission denied." (support flow)

## User Flow

**Happy path (both channels)**
- Start
- Select Language
- Select Class → Subject (→ Chapter if applicable)
- Select intent:
  - Notes / Lectures / Guess Paper → show curated links (+ optional "recommended")
  - I have a question → user types question → assistant answers (explain + steps + quiz + resource link)

**Alternatives / edge flows**
- If student doesn't know chapter → offer "search topic keywords" (web) or "choose from top topics" (WhatsApp)
- If assistant confidence is low / content not found → say so, ask 1 clarifying question, and point to closest resource
- If Drive link fails → show fallback link or "report broken link" option
- If misuse detected ("give me exact exam answers only") → refuse/redirect to learning-oriented help + practice

## Functional Requirements

Major flows (auth optional in v1; keep friction low):

| SECTION         | SUB-SECTION | USER STORY & EXPECTED BEHAVIORS | SCREENS      |
| --------------- | ----------- | ------------------------------- | ------------ |
| Signup          | Optional    | As a student, I can use without signup; signup later enables saved prefs and history. | TBD |
| Login           | Optional    | As a student, I can log in if I want my preferences saved across devices. | TBD |
| Onboarding      | Language    | As a student, I choose my language once; system remembers it. | Web: Language screen; WA: menu |
| Navigation      | Class/Subject | As a student, I select class and subject quickly (≤3 taps/clicks). | Web: picker; WA: buttons/lists |
| Resource Access | Notes       | As a student, I can get chapter-wise notes links and open them easily. | Web: list; WA: message + deep links |
| Resource Access | Lectures    | As a student, I can get lecture links (Drive/YouTube if applicable) by chapter/topic. | TBD |
| Resource Access | Guess Papers| As a student, I can access guess papers by class/subject and optionally chapter/topic. | TBD |
| Q&A             | Explain     | As a student, I type a question and get a simple explanation in my selected language. | Chat view |
| Q&A             | Step-by-step| As a student, I get a step-by-step solution when relevant (math/science numericals). | Chat view |
| Q&A             | Mini-quiz   | As a student, I get 3 short practice questions to check understanding (with answers on request). | Chat view |
| Q&A             | Resource link | As a student, I get the most relevant notes/lecture link attached to the answer. | Chat view |
| Feedback        | Helpful?    | As a student, I can thumbs up/down and optionally pick "confusing" or "wrong." | Web UI + WA quick replies |
| Safety/Guardrails | Misuse handling | If a student asks for cheating-only output, assistant redirects to learning + practice. | Built-in |
| Support         | Broken links | As a student, I can report a broken link; admin can fix mapping. | Web form / WA keyword |

**WhatsApp-specific**
- Use interactive menus (quick replies/buttons) for Language/Class/Subject/Intent.
- For longer lists (chapters/resources), send "Top 5 + More" with a web deep-link to browse full library.

**Admin (simple v1)**
- Upload/manage a "content manifest" mapping (Class→Subject→Chapter→Resource Type→Link).
- View broken-link reports and top searched topics.

## Model Requirements

| SPECIFICATION          | REQUIREMENT                          | RATIONALE |
| ---------------------- | ------------------------------------ | --------- |
| Open vs Proprietary    | Proprietary LLM (primary) + fallback | Faster to ship and higher quality for multilingual explanations |
| Context Window         | ≥ 16k (preferred ≥ 32k)              | Handle question + retrieved notes snippets + formatting |
| Modalities             | Text (v1)                            | User confirmed text input only for questions |
| Fine Tuning Capability | Not required initially               | Use RAG + strong prompting; revisit once we have feedback data |
| Latency                | Web P50 ≤ 3s, P95 ≤ 8s; WA P95 ≤ 20s | Keep experience responsive; WA naturally slower |
| Hallucination Tolerance| Low                                 | Wrong/confusing answers are a top risk |
| Safety Controls        | Refusal + redirect patterns          | Reduce misuse and unsafe academic behavior |

## Data Requirements

- **RAG purpose:** Ground explanations in official/curated content and reduce hallucinations.
- **Data preparation plan:**
  - Convert organized content into a structured **content manifest** (metadata + links).
  - For grounding: ingest text from notes where legally and technically feasible (PDF/doc extraction) into a searchable index.
  - If full ingestion is not feasible, store high-quality chapter summaries and key formulas as "approved snippets."
- **Quantity/coverage targets:**
  - 100% coverage for at least one launch slice (e.g., Class 10 Science + Math) in beta.
  - Expand to full Class 9–11 coverage after link stability and Q&A quality meet thresholds.
- **Ongoing collection plan:**
  - Track top queries with "no confident answer" and create approved snippets/FAQs for them.
  - Track broken links and update manifest.
- **Iterative improvement:**
  - Weekly content QA pass on top 50 queries.
  - Add "golden set" questions per subject/chapter for evaluation.

## Prompt Requirements

- **Policy and refusal handling**
  - Detect "cheating-only" requests (e.g., "just give final answers no explanation") and redirect to learning: explanation + steps + practice.
  - If the model is uncertain or content isn't found, it must say so and ask 1 clarifying question or point to the closest resource.
- **Personalization rules**
  - Always respond in the selected language (English/Urdu/Roman Urdu; others in phased rollout).
  - Use age-appropriate, simple language; avoid advanced jargon unless requested.
- **Output format guarantees**
  - Standard answer bundle for Q&A:
    1) Simple explanation  
    2) Step-by-step solution (when applicable)  
    3) 3-question mini-quiz (answers hidden behind "Show answers")  
    4) "Related resource" link (notes/lecture)
- **Accuracy target tied to testing plan**
  - Must meet offline "correctness + clarity" thresholds on the golden set before full rollout.

## Testing & Measurement

- **Offline eval**
  - Build a golden set: ~200 questions across classes/subjects (mix of conceptual + numerical).
  - Rubric (1–5): correctness, clarity, language quality, step ordering, alignment with curated content.
  - Pass thresholds (example): avg ≥ 4.2/5 and "critical incorrect" rate ≤ 2%.
- **Online measurement**
  - Track KPIs: WAU, D7, Content Engagement, Questions Solved.
  - Add quality metrics: thumbs-down rate, "confusing/wrong" tags, "no answer/low confidence" rate.
- **Guardrails & rollback**
  - If thumbs-down spikes or "wrong" tags exceed threshold, automatically:
    - reduce answer length
    - increase grounding requirement
    - route more often to resource links + clarifying questions
- **Cost monitoring**
  - Daily token spend, cost per WAU, cost per question session, WhatsApp conversation fees.

## Risks & Mitigations

| RISK                                  | MITIGATION |
| ------------------------------------- | ---------- |
| Costs grow too fast (LLM + WhatsApp)  | Daily per-user limits; caching; cheaper model for routing; deep-link long browsing to web; rate limits during peaks |
| Wrong/confusing answers reduce trust  | RAG grounding; "confidence + cite the resource" behavior; ask clarifying question when unsure; thumbs down review loop + golden set |
| Misuse for cheating                   | Refusal/redirect to learning format; require explanation + quiz; detect "exam leak" or direct cheating intent |
| Drive links break / permission denied | Permission audit; link health checks; fallback mirrors; "report broken link" workflow |
| Content rights complaints             | Ensure ownership/permission; attribution; takedown process; avoid distributing restricted materials where needed |

## Costs

- **Development**
  - Web app + backend + WhatsApp integration
  - Content manifest tooling + admin panel
  - QA time for core subjects and golden set
- **Operational**
  - LLM inference (per question session)
  - Vector search / storage (if ingesting notes)
  - Hosting + monitoring
  - WhatsApp Business/API provider conversation fees
- **Cost control levers**
  - Limit free daily question sessions per user
  - Cache frequent Q&A and chapter summaries
  - Use lightweight model for classification/routing and heavier model only for final answer generation

## Assumptions & Dependencies

- **Assumptions**
  - v1 languages start with English + Urdu + Roman Urdu; additional languages phased in.
  - Students can open Drive links without permission barriers (or we will fix permissions).
  - Accounts are optional in v1; preferences can be stored locally or via lightweight login.
  - Web and WhatsApp share the same core content and Q&A logic (WhatsApp may deep-link to web for long lists).
- **Dependencies**
  - Google Drive link stability and sharing settings
  - WhatsApp Business/API provider setup and compliance
  - Content ingestion feasibility (PDF extraction) if grounding uses full-text

## Compliance/Privacy/Legal

- Target users include minors; default to **minimal data collection**.
- Avoid collecting sensitive personal info (school name, phone beyond WhatsApp identifier, etc.) unless necessary.
- Data retention: keep chat logs only as needed for QA (e.g., 30 days) with anonymization.
- Provide clear disclaimer: "Learning aid; verify with teacher/textbook; not official board material."
- Content governance: ownership/permission confirmation, attribution where needed, takedown process.
- WhatsApp policies: comply with template rules, opt-out keywords, and message consent.

## GTM/Rollout Plan

- **Milestones**
  - Week 1–2: Content manifest + web MVP navigation + WhatsApp menu flow
  - Week 3: Q&A bundle (explain + steps + quiz + resource link) + feedback capture
  - Week 4: Beta launch with limited group (e.g., 200–500 students)
  - Week 5–8: Improve quality via golden set + fix top content/link issues + add saved preferences
- **Launch strategy**
  - Start with one strong slice (e.g., Class 10 Science/Math) to ensure quality and cost stability.
  - Use existing student communities/channels (e.g., YouTube/WhatsApp groups) to recruit beta testers.
- **Phased rollout**
  - Beta: limited users + strict cost caps + high-touch QA
  - v1 public: expand classes/subjects once thumbs-down rate and cost per active are stable
  - v1.1: add more languages + richer search + optional login/personalization

---

# Part II: Technical Architecture

## Agent Architecture Design

### Architecture Philosophy

**Design Principles:**

1. **Separation of Concerns** - Each agent has ONE clear responsibility
2. **Composability** - Agents can be combined in different workflows
3. **RAG-First** - Ground all outputs in retrieved content
4. **Cost Optimization** - Use cheaper models for routing, expensive for generation
5. **Quality Control** - Multiple validation checkpoints

## Multi-Agent Architecture

### Agent Hierarchy

```
┌─────────────────────────────────────────────────────────────────┐
│                     MASTER ORCHESTRATOR                         │
│  (Routes requests, manages workflow, coordinates sub-agents)    │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                ┌───────────────┼───────────────┐
                │               │               │
                ▼               ▼               ▼
    ┌─────────────────┐ ┌──────────────┐ ┌──────────────┐
    │   INTENT        │ │   RESOURCE   │ │  SAFETY &    │
    │  CLASSIFIER     │ │  ORCHESTRATOR│ │  GUARDRAILS  │
    │   AGENT         │ │    AGENT     │ │    AGENT     │
    └────────┬────────┘ └──────┬───────┘ └──────┬───────┘
             │                 │                 │
             │                 │                 │
    ┌────────▼─────────────────▼─────────────────▼────────┐
    │                                                       │
    │              Q&A ORCHESTRATOR AGENT                   │
    │  (Manages question-answering workflow)                │
    │                                                       │
    └───────────────────────┬───────────────────────────────┘
                            │
            ┌───────────────┼───────────────┐
            │               │               │
            ▼               ▼               ▼
    ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
    │  QUESTION    │ │     RAG      │ │   CONTENT    │
    │  ANALYZER    │ │  RETRIEVAL   │ │   VALIDATOR  │
    │    AGENT     │ │    AGENT     │ │    AGENT     │
    └──────┬───────┘ └──────┬───────┘ └──────────────┘
           │                │
           │    ┌───────────┴────────────┐
           │    │                        │
           ▼    ▼                        ▼
    ┌──────────────────┐         ┌──────────────────┐
    │   EXPLANATION    │         │   STEP-BY-STEP   │
    │    GENERATOR     │         │     SOLVER       │
    │      AGENT       │         │      AGENT       │
    └─────────┬────────┘         └────────┬─────────┘
              │                           │
              │         ┌─────────────────┘
              │         │
              ▼         ▼
       ┌──────────────────────┐
       │   QUIZ GENERATOR     │
       │       AGENT          │
       └──────────┬───────────┘
                  │
                  ▼
       ┌──────────────────────┐
       │   RESPONSE ASSEMBLER │
       │       AGENT          │
       └──────────────────────┘
```

## Detailed Agent Specifications

### TIER 1: MASTER ORCHESTRATOR

**Master Orchestrator Agent**

**Responsibility:** Entry point for all requests, routes to appropriate workflow

**Inputs:**
- User request (text)
- Session context (language, class, subject, chapter)
- Request type (resource access OR question)

**Decision Tree:**
```python
if request_type == "resource_access":
    → Route to RESOURCE ORCHESTRATOR
elif request_type == "question":
    → Route to Q&A ORCHESTRATOR
else:
    → Route to INTENT CLASSIFIER first
```

**Outputs:**
- Workflow selection
- Context enrichment
- Initial validation

**LLM Used:** None (rule-based routing)  
**Cost:** $0

---

### TIER 2: SPECIALIZED ORCHESTRATORS

#### 1. Intent Classifier Agent

**Responsibility:** Determine user intent when ambiguous

**Inputs:**
- Raw user message
- Session context

**Processing:**
```python
# Use lightweight LLM for classification
Classification options:
- "resource_request" (notes/lectures/guess papers)
- "question_conceptual" (explain a concept)
- "question_numerical" (solve a problem)
- "question_mixed" (both explanation + solving)
- "feedback" (student giving feedback)
- "report_issue" (broken link, etc.)
- "off_topic" (not learning-related)
- "cheating_attempt" (just give answers, no explanation)
```

**Outputs:**
- Intent label
- Confidence score (0-1)
- Extracted entities (class, subject, chapter, topic keywords)

**LLM Used:** Groq `llama-3.1-8b-instant` (cheap, fast)  
**Cost:** ~$0.0001 per request  
**RAG Used:** NO

---

#### 2. Resource Orchestrator Agent

**Responsibility:** Handle all resource access requests (notes/lectures/guess papers)

**Sub-Agents:**

1. **Resource Query Builder**
   - Inputs: Class, subject, chapter, resource type
   - Output: Database query parameters
   - LLM: None (rule-based)
   
2. **Resource Ranker**
   - Inputs: Retrieved resources, user context (upcoming exam, weak topics)
   - Output: Ranked list with "recommended" flag
   - LLM: Optional (Groq 8B for personalization)
   - RAG: Uses content manifest metadata

3. **Resource Formatter**
   - Inputs: Ranked resources
   - Output: Formatted response (Drive links + descriptions)
   - LLM: None (template-based)

**Workflow:**
```
User selects "I need notes" → Class 10 → Physics → Chapter 3
    ↓
Resource Query Builder
    ↓
Database query: SELECT * FROM content_manifest 
                WHERE class=10 AND subject='Physics' 
                AND chapter=3 AND type='notes'
    ↓
Resource Ranker (optional: mark "most downloaded" or "recommended for exam")
    ↓
Resource Formatter
    ↓
Return: [
  {title: "Chapter 3 Notes - Reflection of Light", 
   drive_link: "...", 
   recommended: true},
  ...
]
```

**Cost:** ~$0 (mostly database queries)

---

#### 3. Safety & Guardrails Agent

**Responsibility:** Detect misuse, ensure safe responses

**Sub-Agents:**

**3.1 Cheating Detector**

**Inputs:** User question

**Processing:**
```python
Patterns to detect:
- "just give me the answer"
- "don't explain, only final answer"
- "what will come in exam tomorrow"
- "solve all questions from page X"
- Direct exam paper leak requests
```

**Output:** `is_cheating: bool`, `redirect_message: str`  
**LLM:** Groq 8B (pattern matching + intent classification)

**3.2 Content Filter**

**Inputs:** User question

**Processing:**
- Detect inappropriate content
- Detect off-topic requests (non-academic)

**Output:** `is_appropriate: bool`, `reason: str`  
**LLM:** Groq 8B

**3.3 Response Validator**

**Inputs:** Generated answer

**Processing:**
- Check if answer grounds in retrieved content
- Detect hallucinations (claims not in RAG context)
- Ensure answer format matches requirements

**Output:** `is_valid: bool`, `confidence: float`  
**LLM:** Groq 70B (needs reasoning capability)

**RAG Used:** YES (for Response Validator - checks grounding)

---

#### 4. Q&A Orchestrator Agent

**Responsibility:** Manage entire question-answering workflow

**Workflow Phases:**

**Phase 1: Question Analysis**
```
User Question → Question Analyzer Agent
    ↓
Extract:
- Subject area (Physics, Math, etc.)
- Topic/concept (Newton's Laws, Quadratic Equations)
- Question type (conceptual, numerical, mixed)
- Complexity level (basic, intermediate, advanced)
- Language preference
```

**Phase 2: Content Retrieval**
```
Question Analysis → RAG Retrieval Agent
    ↓
Retrieve relevant content chunks from vector DB
    ↓
Rerank and filter by relevance
    ↓
Return top 5 chunks + metadata (chapter, source)
```

**Phase 3: Answer Generation**
```
                    ┌─ Explanation Generator (always)
                    │
Retrieved Content → ├─ Step-by-Step Solver (if numerical)
                    │
                    └─ Quiz Generator (always)
```

**Phase 4: Quality Control**
```
Generated Answers → Content Validator Agent
    ↓
Check grounding, factual accuracy, format compliance
    ↓
If confidence < 0.7 → Trigger fallback (ask clarifying question)
```

**Phase 5: Response Assembly**
```
Validated Components → Response Assembler Agent
    ↓
Bundle: {
  explanation: "...",
  steps: "..." (if applicable),
  quiz: [{q: "...", a: "..."}],
  resource_link: "..."
}
```

---

### TIER 3: SPECIALIZED EXECUTION AGENTS

#### 1. Question Analyzer Agent

**Responsibility:** Deep understanding of the question

**Processing:**
```python
# Use LLM to extract structured info
{
  "subject": "Physics",
  "topic": "Newton's Laws of Motion",
  "subtopic": "Second Law (F=ma)",
  "question_type": "numerical",  # or conceptual, mixed
  "complexity": "intermediate",
  "requires_diagram": false,
  "key_concepts": ["force", "mass", "acceleration"],
  "search_keywords": ["Newton second law", "F=ma", "force calculation"]
}
```

**Inputs:** User question  
**Outputs:** Structured question metadata (JSON)  
**LLM:** Groq llama-3.3-70b-versatile (needs good reasoning)  
**RAG:** NO  
**Cost:** ~$0.0005 per request

---

#### 2. RAG Retrieval Agent

**Responsibility:** Semantic search + reranking for relevant content

**Sub-Components:**

**2.1 Query Expander**
```python
# Expand user question into better search queries
User: "Explain Newton's law"
    ↓
Expanded: [
  "Newton's laws of motion explanation",
  "Newton's first second third law",
  "Force mass acceleration relationship",
  "Inertia action reaction"
]
```
**LLM:** Groq 8B  
**Cost:** ~$0.0001

**2.2 Vector Search**
```python
# Convert expanded queries to embeddings
# Search pgvector for similar chunks
# Filter by metadata (class, subject, chapter)

SELECT content_text, metadata, 
       1 - (embedding <=> query_embedding) AS similarity
FROM content_chunks
WHERE metadata->>'class' = '10'
  AND metadata->>'subject' = 'Physics'
ORDER BY similarity DESC
LIMIT 20;
```
**Cost:** Database query only

**2.3 Reranker**
```python
# Rerank top 20 results using cross-encoder or LLM
# Consider:
- Semantic relevance to original question
- Content quality (from metadata)
- Recency (if applicable)
- Student's complexity level

Return top 5 chunks
```
**LLM:** Optional (Groq 70B for complex reranking)  
**Cost:** ~$0.0003 per request

**Total RAG Retrieval Cost:** ~$0.0005 per question

---

#### 3. Explanation Generator Agent

**Responsibility:** Create simple, clear explanations grounded in RAG content

**Inputs:**
- User question
- Top 5 retrieved chunks
- Question metadata (complexity level, language preference)

**Prompt Structure:**
```python
SYSTEM_PROMPT = """
You are a patient tutor for Class {class} {subject} students.
Create a SIMPLE explanation using the provided content.

RULES:
1. Use language appropriate for {class} students
2. Start with the basic concept before details
3. Use everyday examples and analogies
4. GROUND your explanation in the provided content
5. If content doesn't fully answer, say so and explain what you CAN answer
6. Respond in {language}
7. Maximum 150 words for explanation

PROVIDED CONTENT:
{retrieved_chunks}

QUESTION: {user_question}

Generate a simple explanation following the rules above.
"""
```

**Outputs:**
```json
{
  "explanation": "Newton's Second Law states that...",
  "confidence": 0.92,
  "grounded": true,
  "sources_used": ["chunk_id_123", "chunk_id_456"]
}
```

**LLM:** Groq llama-3.3-70b-versatile  
**RAG:** YES (uses retrieved chunks)  
**Cost:** ~$0.001 per explanation

---

#### 4. Step-by-Step Solver Agent

**Responsibility:** Generate detailed solution steps for numerical problems

**Inputs:**
- User question (numerical problem)
- Retrieved content (formulas, example solutions)
- Question metadata

**Prompt Structure:**
```python
SYSTEM_PROMPT = """
You are a {subject} tutor helping Class {class} students solve problems.

RULES FOR STEP-BY-STEP SOLUTIONS:
1. Identify what is given and what is asked
2. Write the relevant formula/principle
3. Show substitution of values clearly
4. Show ALL calculation steps (don't skip)
5. Include units in every step
6. Box or highlight the final answer
7. Use simple language in {language}

PROVIDED FORMULAS/EXAMPLES:
{retrieved_chunks}

PROBLEM: {user_question}

Generate a complete step-by-step solution.
"""
```

**Outputs:**
```json
{
  "steps": [
    {
      "step_number": 1,
      "description": "Identify given values",
      "content": "Given: mass = 5 kg, acceleration = 2 m/s²"
    },
    {
      "step_number": 2,
      "description": "Write the formula",
      "content": "F = ma (Newton's Second Law)"
    },
    {
      "step_number": 3,
      "description": "Substitute values",
      "content": "F = (5 kg)(2 m/s²)"
    },
    {
      "step_number": 4,
      "description": "Calculate",
      "content": "F = 10 N"
    }
  ],
  "final_answer": "10 N",
  "confidence": 0.95
}
```

**LLM:** Groq llama-3.3-70b-versatile  
**RAG:** YES  
**Cost:** ~$0.0015 per solution

---

#### 5. Quiz Generator Agent

**Responsibility:** Create 3 practice questions to test understanding

**Inputs:**
- Original question
- Generated explanation
- Retrieved content (for question bank)

**Prompt Structure:**
```python
SYSTEM_PROMPT = """
You are creating practice questions for Class {class} {subject} students.

RULES:
1. Generate 3 questions of similar difficulty to the original
2. Mix question types: 1 conceptual, 1 numerical (if applicable), 1 application
3. Questions should test the SAME concept
4. Provide correct answers
5. Questions should be solvable using the explanation given
6. Use {language}

ORIGINAL QUESTION: {user_question}
EXPLANATION PROVIDED: {explanation}
REFERENCE CONTENT: {retrieved_chunks}

Generate 3 practice questions with answers.
"""
```

**Outputs:**
```json
{
  "questions": [
    {
      "question": "What is the SI unit of force?",
      "type": "conceptual",
      "answer": "Newton (N)",
      "explanation": "Force is measured in Newtons, where 1 N = 1 kg⋅m/s²"
    },
    {
      "question": "Calculate force if mass = 10 kg and acceleration = 3 m/s²",
      "type": "numerical",
      "answer": "30 N",
      "explanation": "F = ma = (10)(3) = 30 N"
    },
    {
      "question": "Why does a heavier object require more force to accelerate?",
      "type": "application",
      "answer": "Because F = ma, so greater mass needs proportionally greater force for same acceleration",
      "explanation": "..."
    }
  ]
}
```

**LLM:** Groq llama-3.3-70b-versatile  
**RAG:** YES (can pull from question banks in retrieved content)  
**Cost:** ~$0.0012 per quiz

---

#### 6. Content Validator Agent

**Responsibility:** Verify answer quality and grounding

**Sub-Checks:**

**6.1 Grounding Check**
```python
# Compare generated answer with retrieved chunks
# Detect claims not supported by RAG content
# Use entailment model or LLM

if any_claim_not_in_retrieved_content:
    confidence_penalty = 0.3
```

**6.2 Factual Accuracy Check**
```python
# Use LLM to self-critique
# Ask: "Is this explanation factually correct for Class {class}?"
# Check for common misconceptions
```

**6.3 Format Compliance Check**
```python
# Verify output has required components:
required = {
    "explanation": True,
    "steps": question_type == "numerical",
    "quiz": True,
    "resource_link": True
}

if not all_required_present:
    trigger_regeneration()
```

**Inputs:** Generated answer components  
**Outputs:** `validation_score: float`, `issues: list`, `should_regenerate: bool`  
**LLM:** Groq llama-3.3-70b-versatile  
**Cost:** ~$0.0008 per validation

---

#### 7. Response Assembler Agent

**Responsibility:** Bundle all components into final response

**Processing:**
```python
# Combine components in student-friendly format
# Add resource link from RAG metadata
# Format for web UI consumption

final_response = {
    "explanation": explanation_agent_output,
    "steps": step_solver_output if numerical else None,
    "quiz": {
        "questions": quiz_generator_output,
        "answers_hidden": True  # Show on click
    },
    "resource_link": {
        "title": "Chapter 3 Notes - Newton's Laws",
        "url": drive_link_from_rag_metadata,
        "type": "notes"
    },
    "confidence": min(explanation_conf, solver_conf, validator_score),
    "metadata": {
        "question_id": uuid,
        "timestamp": now(),
        "tokens_used": total_tokens
    }
}
```

**LLM:** None  
**Cost:** $0

---

## Complete Workflow Diagrams

### Workflow 1: Resource Access Request

```
┌─────────────────────────────────────────────────────────────┐
│ USER: "I need notes" → Class 10 → Physics → Chapter 3       │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
            ┌────────────────────────┐
            │ Master Orchestrator    │
            │ Detects: resource_req  │
            └────────┬───────────────┘
                     │
                     ▼
         ┌───────────────────────────┐
         │ Resource Orchestrator     │
         └───────┬───────────────────┘
                 │
      ┌──────────┼──────────┐
      ▼          ▼          ▼
┌──────────┐ ┌──────┐ ┌─────────┐
│ Query    │ │  DB  │ │ Ranker  │
│ Builder  │→│Query │→│(optional│
└──────────┘ └──────┘ └────┬────┘
                            │
                            ▼
                    ┌───────────────┐
                    │   Formatter   │
                    └───────┬───────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ RESPONSE: [                                                  │
│   {title: "Notes - Newton's Laws", link: "...", rec: true}, │
│   {title: "Summary Sheet", link: "...", rec: false}         │
│ ]                                                            │
└─────────────────────────────────────────────────────────────┘

COST: ~$0
TIME: <500ms
```

---

### Workflow 2: Conceptual Question

```
┌─────────────────────────────────────────────────────────────┐
│ USER: "Explain Newton's second law in simple words"         │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
            ┌────────────────────────┐
            │ Master Orchestrator    │
            └────────┬───────────────┘
                     │
                     ▼
         ┌───────────────────────────┐
         │ Safety & Guardrails       │
         │ ✓ Not cheating            │
         │ ✓ Appropriate content     │
         └───────┬───────────────────┘
                 │
                 ▼
         ┌───────────────────────────┐
         │ Q&A Orchestrator          │
         └───────┬───────────────────┘
                 │
      ┌──────────┼──────────┐
      ▼          ▼          ▼
┌──────────┐ ┌──────────┐ ┌──────────┐
│ Question │ │   RAG    │ │ Content  │
│ Analyzer │→│Retrieval │→│Validator │
│          │ │          │ │          │
│ Extract: │ │ Top 5    │ │ Verify   │
│ -Physics │ │ chunks   │ │ coverage │
│ -Newton  │ │ about    │ │          │
│ -Concept │ │ F=ma     │ │          │
└──────────┘ └─────┬────┘ └──────────┘
                   │
                   ▼
         ┌─────────────────────┐
         │ Explanation         │
         │ Generator           │
         │                     │
         │ Uses RAG chunks     │
         │ Creates simple      │
         │ explanation         │
         └──────┬──────────────┘
                │
                ▼
         ┌─────────────────────┐
         │ Quiz Generator      │
         │                     │
         │ Creates 3 practice  │
         │ questions           │
         └──────┬──────────────┘
                │
                ▼
         ┌─────────────────────┐
         │ Content Validator   │
         │                     │
         │ Check grounding     │
         │ Confidence: 0.92    │
         └──────┬──────────────┘
                │
                ▼
         ┌─────────────────────┐
         │ Response Assembler  │
         └──────┬──────────────┘
                │
                ▼
┌─────────────────────────────────────────────────────────────┐
│ RESPONSE: {                                                  │
│   explanation: "Newton's 2nd law states F=ma...",           │
│   quiz: [{q: "...", a: "..."}],                             │
│   resource: {title: "Notes", link: "..."}                   │
│ }                                                            │
└─────────────────────────────────────────────────────────────┘

COST: ~$0.005
TIME: 3-5 seconds
RAG CALLS: 1 (retrieval)
LLM CALLS: 4 (analyzer, explanation, quiz, validator)
```

---

### Workflow 3: Numerical Problem

```
┌─────────────────────────────────────────────────────────────┐
│ USER: "Calculate force if mass=5kg, acceleration=2m/s²"     │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
            ┌────────────────────────┐
            │ Master Orchestrator    │
            └────────┬───────────────┘
                     │
                     ▼
         ┌───────────────────────────┐
         │ Safety & Guardrails       │
         │ ✓ Not cheating            │
         └───────┬───────────────────┘
                 │
                 ▼
         ┌───────────────────────────┐
         │ Q&A Orchestrator          │
         └───────┬───────────────────┘
                 │
      ┌──────────┼──────────┐
      ▼          ▼          ▼
┌──────────┐ ┌──────────┐ ┌──────────┐
│ Question │ │   RAG    │ │          │
│ Analyzer │→│Retrieval │ │          │
│          │ │          │ │          │
│ Detects: │ │ Retrieve:│ │          │
│ numerical│ │ -Formulas│ │          │
│ F=ma     │ │ -Examples│ │          │
└──────────┘ └─────┬────┘ └──────────┘
                   │
         ┌─────────┴─────────┐
         ▼                   ▼
┌──────────────────┐ ┌──────────────────┐
│ Explanation      │ │ Step-by-Step     │
│ Generator        │ │ Solver           │
│                  │ │                  │
│ "F=ma relates    │ │ Step 1: Given... │
│  force, mass..." │ │ Step 2: Formula..│
│                  │ │ Step 3: Calc...  │
│                  │ │ Answer: 10 N     │
└────────┬─────────┘ └────────┬─────────┘
         │                    │
         └─────────┬──────────┘
                   ▼
         ┌─────────────────────┐
         │ Quiz Generator      │
         │ Similar problems    │
         └──────┬──────────────┘
                │
                ▼
         ┌─────────────────────┐
         │ Content Validator   │
         │ Verify steps correct│
         └──────┬──────────────┘
                │
                ▼
         ┌─────────────────────┐
         │ Response Assembler  │
         └──────┬──────────────┘
                │
                ▼
┌─────────────────────────────────────────────────────────────┐
│ RESPONSE: {                                                  │
│   explanation: "Force equals mass times acceleration...",   │
│   steps: [                                                   │
│     {step: 1, desc: "Given", content: "m=5kg, a=2m/s²"},   │
│     {step: 2, desc: "Formula", content: "F=ma"},           │
│     {step: 3, desc: "Substitute", content: "F=(5)(2)"},    │
│     {step: 4, desc: "Calculate", content: "F=10N"}         │
│   ],                                                         │
│   quiz: [...],                                              │
│   resource: {...}                                           │
│ }                                                            │
└─────────────────────────────────────────────────────────────┘

COST: ~$0.006
TIME: 4-6 seconds
RAG CALLS: 1
LLM CALLS: 5 (analyzer, explanation, solver, quiz, validator)
```

---

### Workflow 4: Cheating Detection & Redirect

```
┌─────────────────────────────────────────────────────────────┐
│ USER: "Just give me the answer, don't explain"              │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
            ┌────────────────────────┐
            │ Master Orchestrator    │
            └────────┬───────────────┘
                     │
                     ▼
         ┌───────────────────────────┐
         │ Safety & Guardrails       │
         │                           │
         │ Cheating Detector:        │
         │ ✗ Pattern match: "just"  │
         │   + "answer" + "don't    │
         │   explain"                │
         │                           │
         │ Decision: REDIRECT        │
         └───────┬───────────────────┘
                 │
                 ▼
         ┌───────────────────────────┐
         │ Redirect Message          │
         │ Generator                 │
         └───────┬───────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│ RESPONSE: {                                                  │
│   type: "redirect",                                         │
│   message: "I'm here to help you LEARN, not just get       │
│            answers! Let me explain the concept AND give     │
│            you practice questions so you truly understand.  │
│            What topic would you like to learn about?",      │
│   suggested_action: "Ask a specific concept question"       │
│ }                                                            │
└─────────────────────────────────────────────────────────────┘

COST: ~$0.0001 (only cheating detector)
TIME: <1 second
```

---

### Workflow 5: Low Confidence / Unclear Question

```
┌─────────────────────────────────────────────────────────────┐
│ USER: "Explain that thing about motion"                      │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
         ┌───────────────────────────┐
         │ Q&A Orchestrator          │
         └───────┬───────────────────┘
                 │
      ┌──────────┼──────────┐
      ▼          ▼          ▼
┌──────────┐ ┌──────────┐
│ Question │ │   RAG    │
│ Analyzer │→│Retrieval │
│          │ │          │
│ Extract: │ │ Too many │
│ -Physics │ │ possible │
│ -Motion  │ │ matches  │
│ -VAGUE   │ │          │
└──────────┘ └─────┬────┘
                   │
                   ▼
         ┌─────────────────────┐
         │ Content Validator   │
         │                     │
         │ Confidence: 0.45    │
         │ ✗ Too low!          │
         └──────┬──────────────┘
                │
                ▼
         ┌─────────────────────┐
         │ Clarification       │
         │ Generator           │
         └──────┬──────────────┘
                │
                ▼
┌─────────────────────────────────────────────────────────────┐
│ RESPONSE: {                                                  │
│   type: "clarification_needed",                             │
│   message: "I can help with motion! Are you asking about:", │
│   options: [                                                │
│     "Newton's Laws of Motion",                              │
│     "Equations of motion (v=u+at)",                         │
│     "Circular motion",                                      │
│     "Projectile motion"                                     │
│   ],                                                         │
│   fallback_resources: [                                     │
│     {title: "Chapter 2 - Motion", link: "..."}             │
│   ]                                                          │
│ }                                                            │
└─────────────────────────────────────────────────────────────┘

COST: ~$0.002
TIME: 2-3 seconds
```

---

## Cost Breakdown Per Question Type

### Resource Access Request

| Component | LLM Calls | Cost |
|-----------|-----------|------|
| Intent Classifier | 0 (rule-based) | $0 |
| Database Query | 0 | $0 |
| Resource Ranker | 0 (optional) | $0 |
| **TOTAL** | **0** | **$0** |

### Simple Conceptual Question

| Component | LLM | Tokens (est.) | Cost |
|-----------|-----|---------------|------|
| Question Analyzer | Groq 70B | 500 in + 200 out | $0.0005 |
| RAG Query Expander | Groq 8B | 200 in + 100 out | $0.0001 |
| Explanation Generator | Groq 70B | 1500 in + 300 out | $0.0013 |
| Quiz Generator | Groq 70B | 1000 in + 400 out | $0.0010 |
| Content Validator | Groq 70B | 800 in + 150 out | $0.0007 |
| **TOTAL** | - | **~4000 tokens** | **~$0.0036** |

### Numerical Problem (with steps)

| Component | LLM | Tokens (est.) | Cost |
|-----------|-----|---------------|------|
| Question Analyzer | Groq 70B | 500 in + 200 out | $0.0005 |
| RAG Query Expander | Groq 8B | 200 in + 100 out | $0.0001 |
| Explanation Generator | Groq 70B | 1500 in + 300 out | $0.0013 |
| Step-by-Step Solver | Groq 70B | 1500 in + 500 out | $0.0015 |
| Quiz Generator | Groq 70B | 1000 in + 400 out | $0.0010 |
| Content Validator | Groq 70B | 1000 in + 150 out | $0.0008 |
| **TOTAL** | - | **~6000 tokens** | **~$0.0052** |

**With Caching (30% hit rate):**
- Cached questions: $0.0001 (database lookup only)
- New questions: $0.0052
- Average: ~$0.0037 per question

---

## RAG Integration Points

### Where RAG is Used:

**1. Resource Retrieval (Metadata Only)**
```python
# Query content_manifest table
# No embeddings needed, just structured data
SELECT * FROM content_manifest
WHERE class = ? AND subject = ? AND chapter = ?
```

**2. Question Answering (Full RAG)**
```python
# Step 1: Generate query embedding
query_embedding = embed_model.encode(expanded_query)

# Step 2: Vector similarity search
chunks = vector_db.search(
    embedding=query_embedding,
    filter={
        "class": 10,
        "subject": "Physics"
    },
    top_k=20
)

# Step 3: Rerank
reranked = reranker.rank(
    query=original_question,
    candidates=chunks,
    top_k=5
)

# Step 4: Inject into LLM prompts
context = "\n\n".join([chunk.text for chunk in reranked])
```

**3. Content Validation (Grounding Check)**
```python
# Check if generated answer claims are in retrieved chunks
for claim in extract_claims(generated_answer):
    if not any(claim in chunk.text for chunk in retrieved_chunks):
        flag_hallucination(claim)
```

---

## Agent State Management

### State Schema

```python
class AgentState(TypedDict):
    # User context
    user_id: str
    session_id: str
    language: str  # "en", "ur", "ur-roman"
    class_level: int  # 9, 10, 11
    subject: str
    chapter: Optional[int]
    
    # Request data
    request_type: str  # "resource" | "question"
    user_message: str
    
    # Intermediate results
    intent: Optional[str]
    question_metadata: Optional[Dict]
    retrieved_chunks: Optional[List[Dict]]
    
    # Generated components
    explanation: Optional[str]
    steps: Optional[List[Dict]]
    quiz: Optional[List[Dict]]
    resource_links: Optional[List[Dict]]
    
    # Quality metrics
    confidence: float
    validation_score: float
    
    # Control flow
    current_agent: str
    next_agent: Optional[str]
    should_fallback: bool
    
    # Metadata
    tokens_used: int
    cost_usd: float
    latency_ms: int
```

### State Transitions

```python
# Master Orchestrator decides initial path
state["current_agent"] = "master_orchestrator"
state["next_agent"] = determine_next_agent(state["request_type"])

# Each agent updates state and determines next step
def agent_execute(state: AgentState) -> AgentState:
    # Do work
    result = perform_agent_task(state)
    
    # Update state
    state.update(result)
    
    # Determine next agent
    state["next_agent"] = route_to_next_agent(state)
    
    return state

# Orchestrator runs agent chain
while state["next_agent"] is not None:
    current = state["next_agent"]
    state = agents[current].execute(state)
```

---

## Monitoring & Observability

### Metrics to Track Per Agent

```python
agent_metrics = {
    "agent_name": "explanation_generator",
    "invocations": 1250,
    "avg_latency_ms": 1840,
    "p95_latency_ms": 3200,
    "success_rate": 0.96,
    "avg_tokens_in": 1500,
    "avg_tokens_out": 320,
    "avg_cost_usd": 0.0013,
    "error_rate": 0.04,
    "common_errors": ["timeout", "context_too_long"]
}
```

### Quality Metrics Per Workflow

```python
workflow_quality = {
    "question_type": "numerical",
    "total_sessions": 850,
    "avg_confidence": 0.89,
    "thumbs_up_rate": 0.82,
    "thumbs_down_rate": 0.11,
    "neutral_rate": 0.07,
    "tagged_wrong": 15,  # 1.7%
    "tagged_confusing": 28,  # 3.3%
    "avg_response_time_s": 4.2
}
```

---

## Final Architecture Summary

### Agent Count:
- **Tier 1 (Master):** 1 orchestrator
- **Tier 2 (Specialized Orchestrators):** 4 agents
- **Tier 3 (Execution):** 12 sub-agents
- **Total:** 17 agents

### LLM Usage:
- **Groq llama-3.1-8b-instant:** Intent classification, query expansion, cheating detection
- **Groq llama-3.3-70b-versatile:** Question analysis, content generation, validation

### RAG Calls Per Question:
- 1 retrieval (semantic search + reranking)
- ~5 chunks used in prompts

### Average Costs:
- Resource request: $0
- Conceptual question: $0.0036
- Numerical problem: $0.0052
- With 30% cache hit: $0.0037 average

### Target Latency:
- Resource: <500ms
- Question: 3-5 seconds

---

**END OF COMBINED DOCUMENT**

