# Transformer Community Assistant

## Project Overview

This project is a Transformer-based community assistant designed to help members access community information through a Gradio interface.

The assistant:

- Pulls data from an existing CMS
- Stores processed knowledge in Chroma
- Uses Retrieval-Augmented Generation (RAG) to answer user questions
- Supports tool calling for community operations such as event registration and event lookup
- Includes an evaluation layer to measure retrieval quality, response relevance, and tool-call reliability

Optional fine-tuning can also be added depending on the chosen LLM and project needs.

## Core Purpose

The main goal of the project is to allow community members to easily get information about their community through a Gradio application.

This assistant is intended for communities such as:

- Churches
- Associations
- Similar organizations that need a central assistant for information access and lightweight operational support

## Key Components

### 1. Data Ingestion From CMS

The system pulls community data from an existing CMS platform.

### 2. Vector Storage

The extracted content is processed and stored in Chroma for retrieval.

### 3. LLM Layer

A Transformer-based LLM is used for question answering, with optional fine-tuning if required.

### 4. RAG Pipeline

The assistant retrieves relevant information from the community knowledge base before generating a response.

## Chroma + RAG Pipeline (Local)

The repository now includes small utilities to build a Chroma store and query it locally.

### Build the vector store

```bash
python scripts/build_chroma.py \
  --input data/community.json \
  --persist-dir vector_db \
  --reset

# Uses rag_config.json by default. Override with:
python scripts/build_chroma.py \
  --input data/community.json \
  --config rag_config.json \
  --reset

# To use raw text instead of PR-2 event formatting
python scripts/build_chroma.py \
  --input data/community.json \
  --persist-dir vector_db \
  --format raw \
  --project-types "" \
  --reset
```

### Query the vector store

```bash
python scripts/query_rag.py \
  --query "What events are coming up this month?" \
  --persist-dir vector_db \
  --k 4
```

These scripts expect `OPENAI_API_KEY` to be set for embeddings.

### 5. Gradio Interface

Community members interact with the assistant through Gradio to ask questions and get answers.

### 6. Tool Calling Layer

The assistant can call external tools for structured actions that go beyond knowledge retrieval.

### 7. Evaluation Layer

The project includes evals to assess:

- Retrieval quality
- Answer relevance
- Faithfulness to source content
- Correctness of tool-based actions such as registration and event lookup

## Supported Tool Calls

### Event Registration

This tool allows a user to register for an event using their email address.

When a registration is made:

- The user’s email and selected event are stored in Firebase
- A confirmation email is sent to the user with the event details

This makes registration both actionable and traceable.

### Check Events Registered by a User

This tool allows the assistant to fetch all events a user has registered for using their email address.

The assistant queries Firebase and returns the relevant event records associated with that email.

## Scope of Community Use

The assistant is intended for communities that need:

- A conversational way for members to access information
- A basic system for handling community event interactions

## Technical Flow

### Knowledge and Response Flow

```text
CMS -> Data extraction -> Storage in Chroma -> RAG retrieval -> LLM response through Gradio
```

### Tool-Based Action Flow

```text
User request -> LLM decides tool call -> Firebase storage or retrieval -> Optional email notification -> Response returned in Gradio
```

### Evaluation Flow

```text
User query or test case -> Retrieval and/or tool execution -> Response generation -> Evaluation against expected relevance, accuracy, and tool correctness
```

## Project Tickets

### Ticket 1: CMS Data Extraction and Ingestion Pipeline

**Owner focus**  
Build the pipeline that pulls community data from the existing CMS and prepares it for downstream use.

**Scope**  
Connect to the CMS, fetch the required community content, clean and normalize the data, and define the ingestion flow into the knowledge base pipeline.

**Deliverables**  
A working CMS extraction module, a data cleaning and transformation layer, and a repeatable ingestion process that prepares content for storage in Chroma.

**Acceptance criteria**  
The system can successfully pull data from the CMS, transform it into a usable format, and pass it into the vector storage pipeline without manual intervention.

### Ticket 2: Chroma Storage and RAG Pipeline

**Owner focus**  
Set up the retrieval layer that stores the CMS content in Chroma and makes it searchable for the LLM.

**Scope**  
Chunk the content, generate embeddings, store the data in Chroma, and implement retrieval logic for relevant context during question answering.

**Deliverables**  
A working Chroma setup, document chunking logic, embedding pipeline, and retrieval module integrated into the assistant workflow.

**Acceptance criteria**  
Community data is stored in Chroma correctly, relevant results are retrieved for user questions, and the RAG pipeline returns usable context to the LLM.

### Ticket 3: LLM Integration and Assistant Orchestration

**Owner focus**  
Build the core assistant logic that connects the LLM to the RAG pipeline and handles response generation.

**Scope**  
Integrate the Transformer-based model, add optional fine-tuning support as a future-ready path, and implement orchestration logic for deciding when to answer from RAG and when to call tools.

**Deliverables**  
An assistant service that accepts user queries, retrieves context from the RAG layer, invokes the LLM, and supports tool-calling hooks.

**Acceptance criteria**  
The assistant can answer community-related questions using retrieved CMS knowledge and can trigger tool calls when the request matches a supported action.

### Ticket 4: Tool Calling, Firebase, and Email Flow

**Assigned contributor**  
Damola

**Owner focus**  
Implement the structured action layer for event registration and event lookup.

**Scope**  
Build the event registration tool, store email and event records in Firebase, implement the tool to fetch registered events by email, and add email confirmation for successful registrations.

**Deliverables**  
A Firebase data model for registrations, registration and lookup tool functions, and email-sending integration for event confirmations.

**Acceptance criteria**  
A user can register for an event with an email, the registration is stored in Firebase, a confirmation email is sent, and the assistant can fetch all registered events using the user’s email.

### Ticket 5: Gradio Interface, End-to-End Integration, and Evals

**Owner focus**  
Build the user-facing Gradio application, connect all components into one working flow, and define the evaluation approach for the assistant.

**Scope**  
Create the Gradio interface for question answering and tool-driven actions, connect it to the assistant backend, and test the full system from CMS retrieval to final response. Also define and implement evals for retrieval relevance, answer quality, hallucination checks, and tool-call correctness.

**Deliverables**  
A functional Gradio app with input and response flow, support for community questions, support for registration-related interactions, and an evaluation suite with baseline test cases and measurable metrics.

**Acceptance criteria**  
A user can use the Gradio interface to ask community questions, receive RAG-based answers, register for events, and check registered events in one integrated experience. In addition, the eval suite can run against sample queries and tool-based scenarios to measure system quality.

## Suggested Ownership Summary

| Area | Contributors | Reviewer |
| --- | --- |
| CMS extraction and ingestion | Joshua | Michael |
| Chroma and RAG | Michael, Adetayo |
| LLM integration and orchestration | Adetayo | Damola |
| Tool calling, Firebase, and email | Damola | Tobe |
| Gradio UI, end-to-end integration, and evals | Tobe | Joshua |

## Recommended Dependency Order

1. Ticket 1 and Ticket 4
2. Ticket 2
3. Ticket 3
4. Ticket 5

## Timeline

All contributors are expected to complete their assigned parts by **11:00 AM WAT**.
