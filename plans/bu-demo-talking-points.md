# BU Demo Talking Points: RAG Evaluation for FSI Compliance

## 1. The Problem

Financial services firms are adopting AI assistants to help compliance officers navigate SEC and FINRA regulations. But before deploying one, they need to answer a critical question: **can I trust this model to give correct, grounded answers about regulations -- and how do I prove it?**

Today, teams evaluate models by hand: reading answers, spot-checking sources, hoping they catch hallucinations. That does not scale when you are comparing multiple models across dozens of compliance scenarios. Getting it wrong means regulatory risk -- a model that confidently invents a filing deadline or omits a disclosure requirement is worse than no model at all.

This system gives compliance teams a repeatable, auditable way to evaluate any model against their own regulatory documents and get a clear PASS/FAIL/REVIEW verdict with a full evidence trail.


## 2. The Flow (What Happens When You Run an Evaluation)

Here is the end-to-end sequence in plain language:

1. **Upload documents** -- The user uploads SEC/FINRA regulatory PDFs (public filings, rule books, compliance manuals). The system chunks them, indexes them, and makes them searchable.

2. **Get evaluation questions** -- Two options:
   - **Auto-generate**: The system reads the uploaded documents and generates compliance-focused questions with expected answers. ("What are the filing requirements for Form N-1A?")
   - **Bring your own**: The user provides a question set with expected answers from their compliance team.

3. **Build structured truth** -- For each question, the system creates a "truth payload":
   - Extracts the key concepts from the expected answer (e.g., "must file Form N-1A", "publish daily NAV")
   - Classifies which uploaded documents are *required* vs *supporting* for that question
   - Maps specific document chunks to each question

4. **Run the model** -- The system sends each question through the full RAG pipeline: retrieval (find relevant chunks from the uploaded docs) then generation (ask the model to answer using those chunks).

5. **Check the retrieval first** -- Before even looking at the answer, the system runs deterministic checks:
   - Did the retrieval pull back the required documents? (Document presence)
   - Did it find the right chunks within those documents? (Chunk alignment)
   - These are hard gates -- if retrieval fails, the question gets a FAIL verdict attributed to retrieval, not the model.

6. **Score the answer** -- An LLM judge scores the answer on eight dimensions: faithfulness, relevancy, completeness, correctness, compliance accuracy, context precision, context relevancy, and abstention quality.

7. **Detect coverage gaps** -- The system checks which concepts from the expected answer are missing from the model's response, and classifies each gap: was the concept missing from the retrieved context (retrieval problem) or present in the context but omitted by the model (generation problem)?

8. **Produce a verdict** -- Each question gets a PASS, FAIL, or REVIEW verdict based on the evaluation profile's thresholds. The run gets an aggregate verdict.

9. **Compare models** -- Run the same questions against a different model and get a head-to-head comparison with a winner declaration, disqualification gates, and risk flags.


## 3. What Makes It Smart

### Question-Aware Document Classification

Not all documents matter equally for every question. The system uses the judge model to classify each document as "required" (the answer depends on it) or "supporting" (background context). This means a missing supporting document does not trigger a false failure, but a missing required document does.

**Why this matters to customers:** Generic RAG evaluations treat all documents the same. A compliance team cares whether the model found *the right regulation*, not just *some document*.

### Structured Truth with Concept Extraction

Instead of comparing raw text, the system breaks the expected answer into discrete concepts -- specific facts, obligations, thresholds, and requirements. For example: "must file Form N-1A", "publish daily NAV", "SAI provides tax information." Each concept can be independently checked for coverage.

**Why this matters:** A model might answer correctly but miss one critical compliance requirement. Concept-level tracking catches that.

### Deterministic Checks as Hard Gates

Before any LLM judge scores run, the system applies fast, rule-based checks:
- **Document presence**: Were the required regulatory documents retrieved?
- **Chunk alignment**: Were the right sections within those documents found?
- **Abstention validation**: Did the model correctly refuse to answer when it lacked context?
- **Source reference**: Did the model cite only documents that were actually retrieved?

The retrieval checks (document presence, chunk alignment) act as hard gates. If retrieval fails, the question is marked FAIL immediately with a retrieval-specific reason code. This prevents blaming the model for problems in the retrieval pipeline.

**Why this matters:** Compliance officers need to trust the evaluation itself. Deterministic checks are explainable, reproducible, and not subject to LLM judgment variability.

### Verdict Attribution (Retrieval vs Generation Failures)

When something goes wrong, the system tells you *where* it went wrong:
- **Retrieval failure**: The relevant information was not retrieved from the documents. Fix the chunking, embeddings, or retrieval configuration.
- **Generation failure**: The information was in the retrieved context, but the model ignored or misrepresented it. This is a model quality issue.

**Why this matters:** A compliance team that sees a FAIL needs to know whether to change models or fix their document processing pipeline. This system tells them which.

### LLM-as-Judge Scoring (Eight Dimensions)

The system uses a separate judge model to score answers on dimensions specifically chosen for compliance use cases:
- **Faithfulness**: Is every claim grounded in the retrieved documents? (Below 70% is flagged as hallucination.)
- **Relevancy**: Does the answer address the question?
- **Completeness**: Are all key points from the expected answer covered?
- **Correctness**: Are the facts consistent with the expected answer?
- **Compliance Accuracy**: Are regulatory obligations, thresholds, disclosures, and cited authorities correct?
- **Context Precision / Relevancy**: Did the retrieval pipeline deliver useful context?
- **Abstention Quality**: When context is insufficient, does the model say so instead of fabricating?

### Coverage Gap Detection

For every question with an expected answer, the system identifies exactly which concepts were covered and which were missed. Each missed concept is classified as a retrieval gap (not in the context) or a generation gap (in the context but the model skipped it).

**Why this matters:** Instead of just seeing a completeness score of 60%, the compliance team sees: "The model missed 'must disclose beneficial ownership above 5%' -- and that concept was present in the retrieved context, so this is a generation failure."

### Head-to-Head Comparison with Disqualification Gates

When comparing two models, the system applies a structured decision framework:
1. **Disqualification gates**: If a model's average completeness, correctness, or compliance accuracy falls below the profile threshold, it is disqualified -- it cannot win regardless of other metrics.
2. **Verdict comparison**: PASS beats REVIEW beats FAIL.
3. **Failure counts**: Fewer critical failures wins.
4. **Business-priority metrics**: Groundedness and completeness are weighted higher than latency.

The result is a clear "Model A wins because..." with supporting evidence, risk flags, and disqualification details.

**Why this matters:** A stakeholder should not have to study a spreadsheet of metric scores. The system produces a business decision with justification.

### Profile-Driven Evaluation

Everything -- thresholds, retrieval configuration, system prompts, scoring criteria -- is controlled by a YAML profile. The FSI compliance profile includes:
- Pass/fail thresholds for each metric (e.g., faithfulness must be above 70%)
- Critical thresholds that trigger immediate failure (e.g., faithfulness below 50%)
- Retrieval parameters tuned for regulatory document corpora (15 chunks, 6-document diversity minimum, hybrid search enabled)
- A compliance-specific system prompt that instructs the model to cite sources and never invent regulatory references

**Why this matters:** Different customers, different risk tolerance. A profile can be tuned per use case -- stricter for client-facing advisory, more permissive for internal research.


## 4. Demo Walkthrough

### Screen 1: Document Upload

**Show:** Upload 3-5 SEC/FINRA PDFs (Form N-1A, FINRA Rule 2111, a supervisory procedures manual).

**Say:** "First, you upload the regulatory documents your compliance team works with. These are public SEC and FINRA documents. The system automatically chunks and indexes them for both the chat assistant and the evaluation engine."

### Screen 2: Question Set (Auto-Generated)

**Show:** Click "Generate Questions" and wait for the system to produce 10 compliance questions with expected answers.

**Say:** "The system reads your documents and generates compliance-focused evaluation questions -- things like 'What are the suitability obligations under FINRA Rule 2111?' Each question comes with an expected answer derived directly from the document text, plus a structured truth payload that maps concepts to source documents and chunks."

**Point out:** The expected answers include specific regulatory details -- filing requirements, thresholds, deadlines -- all traceable back to the uploaded documents.

### Screen 3: Run Evaluation

**Show:** Select Model A (e.g., granite-3.1-8b) and start the evaluation. Show the progress indicator as questions complete.

**Say:** "Now we run the evaluation. For each question, the system retrieves relevant document chunks, generates an answer using the selected model, runs deterministic checks on the retrieval quality, then scores the answer on eight quality dimensions using a separate judge model."

### Screen 4: Evaluation Detail View

**Show:** Click into a completed run. Walk through the summary metrics at the top, then expand 2-3 individual questions.

**Say at the summary level:** "At the top you see the aggregate picture: overall verdict (PASS, FAIL, or REVIEW), average faithfulness, hallucination rate, completeness, compliance accuracy. This run shows [X]% faithfulness and [Y]% compliance accuracy."

**Expand a passing question. Say:** "Here is a question that passed. You can see the model's answer, the expected answer, all eight metric scores, and the deterministic checks -- both document presence and chunk alignment passed. The truth panel shows which concepts were covered and which documents were required."

**Expand a failing question. Say:** "This one failed. Look at the fail reasons -- FAIL_RETRIEVAL_INCOMPLETE. The deterministic checks show that a required document was not retrieved. This is not the model's fault; it is a retrieval pipeline issue. The coverage gaps show exactly which concepts were missed and whether they are retrieval failures or generation failures."

**Point out the hallucination flag if present:** "This answer was flagged as a potential hallucination -- faithfulness scored below 70%, meaning the model made claims not supported by the retrieved context. In compliance, that is a dealbreaker."

### Screen 5: Re-run with a Different Model

**Show:** On the completed run, use the "Re-run with a different model" selector. Pick Model B (e.g., llama-3.3-70b) and start.

**Say:** "Same documents, same questions, different model. The system runs the identical evaluation pipeline so the comparison is apples-to-apples."

### Screen 6: Comparison View

**Show:** Navigate to the comparison screen and select both runs.

**Walk through three sections:**

**Executive verdict:** "The system produces a business-level decision: which model wins and why. Here it says '[Model B] wins: has a better overall verdict, has fewer critical failures.' If either model falls below the compliance accuracy threshold, it gets disqualified -- it cannot win the comparison regardless of other metrics."

**Aggregate metrics:** "The side-by-side metric comparison shows where each model is stronger. Note the compliance accuracy and faithfulness rows -- these are weighted highest because they matter most for compliance use cases."

**Per-question breakdown:** "At the bottom, you can see each question with both models' answers side by side, their verdicts, deterministic check results, and coverage gaps. This is where a compliance officer can drill into specific scenarios -- 'Did Model A or Model B handle suitability obligations better?'"


## 5. Customer Value Proposition

### For Compliance Teams

- **Auditable model evaluation**: Every verdict comes with a full evidence trail -- which documents were retrieved, which concepts were covered, where failures occurred, and why. This is what regulators expect.
- **Quantified regulatory risk**: Instead of "we think the model is good enough," you get "the model correctly handles 92% of compliance concepts with 85% faithfulness and zero hallucinations on our 10 critical scenarios."
- **Repeatable benchmarking**: When a new model is released, re-run the same question set and compare. No manual review required.

### For AI Platform Teams

- **Model selection with evidence**: Choose between models based on objective compliance performance, not vendor claims.
- **Pipeline diagnostics**: Distinguish retrieval problems from model problems. Know whether to improve your chunking strategy or switch models.
- **Profile-driven flexibility**: Tune evaluation strictness per use case. Different profiles for advisory vs research vs internal tools.

### For the Business

- **Faster time to deployment**: Automated evaluation replaces weeks of manual review with hours of systematic testing.
- **Reduced regulatory risk**: Catch hallucinations and coverage gaps before they reach compliance officers.
- **Cost/quality tradeoff visibility**: Compare a smaller, cheaper model against a larger one on the metrics that actually matter for your use case.

### The Pitch in One Sentence

"This is a compliance-grade evaluation framework that tells you exactly which model to deploy, exactly where it fails, and exactly whether the failure is a retrieval problem you can fix or a model problem you need to switch away from -- with a full audit trail."
