// This project was developed with assistance from AI tools.

import { z } from 'zod';

export const EvalRunCreateResponseSchema = z.object({
    eval_run_id: z.number(),
    model_name: z.string(),
    status: z.string(),
    total_questions: z.number(),
    message: z.string(),
});

export const EvalResultSchema = z.object({
    id: z.number(),
    question: z.string(),
    expected_answer: z.string().nullable().optional(),
    answer: z.string().nullable().optional(),
    contexts: z.string().nullable().optional(),
    latency_ms: z.number().nullable().optional(),
    relevancy_score: z.number().nullable().optional(),
    groundedness_score: z.number().nullable().optional(),
    context_precision_score: z.number().nullable().optional(),
    context_relevancy_score: z.number().nullable().optional(),
    completeness_score: z.number().nullable().optional(),
    correctness_score: z.number().nullable().optional(),
    compliance_accuracy_score: z.number().nullable().optional(),
    abstention_score: z.number().nullable().optional(),
    is_hallucination: z.boolean().nullable().optional(),
    verdict: z.string().nullable().optional(),
    fail_reasons: z.array(z.string()).nullable().optional(),
    total_tokens: z.number().nullable().optional(),
    error_message: z.string().nullable().optional(),
});

export const EvalRunSchema = z.object({
    id: z.number(),
    model_name: z.string(),
    question_set_name: z.string().nullable().optional(),
    status: z.string(),
    total_questions: z.number(),
    completed_questions: z.number(),
    avg_latency_ms: z.number().nullable().optional(),
    avg_relevancy: z.number().nullable().optional(),
    avg_groundedness: z.number().nullable().optional(),
    avg_context_precision: z.number().nullable().optional(),
    avg_context_relevancy: z.number().nullable().optional(),
    avg_completeness: z.number().nullable().optional(),
    avg_correctness: z.number().nullable().optional(),
    avg_compliance_accuracy: z.number().nullable().optional(),
    avg_abstention: z.number().nullable().optional(),
    hallucination_rate: z.number().nullable().optional(),
    profile_id: z.string().nullable().optional(),
    overall_verdict: z.string().nullable().optional(),
    pass_count: z.number().nullable().optional(),
    fail_count: z.number().nullable().optional(),
    review_count: z.number().nullable().optional(),
    total_tokens: z.number().nullable().optional(),
    error_message: z.string().nullable().optional(),
    created_at: z.string().nullable().optional(),
    completed_at: z.string().nullable().optional(),
});

export const EvalRunDetailSchema = EvalRunSchema.extend({
    results: z.array(EvalResultSchema),
});

export const ComparisonMetricSchema = z.object({
    metric: z.string(),
    run_a: z.number().nullable().optional(),
    run_b: z.number().nullable().optional(),
    winner: z.string().nullable().optional(),
});

export const QuestionComparisonSchema = z.object({
    question: z.string(),
    expected_answer: z.string().nullable().optional(),
    run_a: EvalResultSchema.nullable().optional(),
    run_b: EvalResultSchema.nullable().optional(),
});

export const ComparisonResponseSchema = z.object({
    run_a: EvalRunSchema,
    run_b: EvalRunSchema,
    metrics: z.array(ComparisonMetricSchema),
    questions: z.array(QuestionComparisonSchema),
});

export const SynthesizedQuestionSchema = z.object({
    question: z.string(),
    expected_answer: z.string().nullable().optional(),
});

export const SynthesizeResponseSchema = z.object({
    questions: z.array(SynthesizedQuestionSchema),
    count: z.number(),
});

export type EvalRunCreateResponse = z.infer<typeof EvalRunCreateResponseSchema>;
export type EvalResult = z.infer<typeof EvalResultSchema>;
export type EvalRun = z.infer<typeof EvalRunSchema>;
export type EvalRunDetail = z.infer<typeof EvalRunDetailSchema>;
export type ComparisonMetric = z.infer<typeof ComparisonMetricSchema>;
export type QuestionComparison = z.infer<typeof QuestionComparisonSchema>;
export type ComparisonResponse = z.infer<typeof ComparisonResponseSchema>;
export type SynthesizedQuestion = z.infer<typeof SynthesizedQuestionSchema>;
export type SynthesizeResponse = z.infer<typeof SynthesizeResponseSchema>;
