// This project was developed with assistance from AI tools.

import {
    ComparisonResponseSchema,
    EvalRunCreateResponseSchema,
    EvalRunDetailSchema,
    EvalRunSchema,
    SynthesizeResponseSchema,
    type ComparisonResponse,
    type EvalRun,
    type EvalRunCreateResponse,
    type EvalRunDetail,
    type SynthesizeResponse,
} from '../schemas/evaluation';
import { z } from 'zod';

export async function createEvalRun(
    modelName: string,
    questions: string[],
): Promise<EvalRunCreateResponse> {
    const response = await fetch('/api/evaluations/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ model_name: modelName, questions }),
    });
    if (!response.ok) throw new Error('Failed to create evaluation run');
    const data = await response.json();
    return EvalRunCreateResponseSchema.parse(data);
}

export async function listEvalRuns(): Promise<EvalRun[]> {
    const response = await fetch('/api/evaluations/');
    if (!response.ok) throw new Error('Failed to fetch evaluation runs');
    const data = await response.json();
    return z.array(EvalRunSchema).parse(data);
}

export async function getEvalRun(id: number): Promise<EvalRunDetail> {
    const response = await fetch(`/api/evaluations/${id}`);
    if (!response.ok) throw new Error('Failed to fetch evaluation run');
    const data = await response.json();
    return EvalRunDetailSchema.parse(data);
}

export async function rerunEval(
    evalRunId: number,
    modelName: string,
): Promise<EvalRunCreateResponse> {
    const response = await fetch(`/api/evaluations/${evalRunId}/rerun`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ model_name: modelName }),
    });
    if (!response.ok) throw new Error('Failed to rerun evaluation');
    const data = await response.json();
    return EvalRunCreateResponseSchema.parse(data);
}

export async function compareEvalRuns(
    runAId: number,
    runBId: number,
): Promise<ComparisonResponse> {
    const response = await fetch(
        `/api/evaluations/compare?run_a_id=${runAId}&run_b_id=${runBId}`,
    );
    if (!response.ok) throw new Error('Failed to compare evaluation runs');
    const data = await response.json();
    return ComparisonResponseSchema.parse(data);
}

export async function synthesizeQuestions(
    maxQuestions: number = 10,
    documentIds?: number[],
): Promise<SynthesizeResponse> {
    const response = await fetch('/api/evaluations/synthesize', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            max_questions: maxQuestions,
            document_ids: documentIds ?? null,
        }),
    });
    if (!response.ok) throw new Error('Failed to synthesize questions');
    const data = await response.json();
    return SynthesizeResponseSchema.parse(data);
}
