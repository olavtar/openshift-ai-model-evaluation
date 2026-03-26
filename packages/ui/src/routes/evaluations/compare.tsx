// This project was developed with assistance from AI tools.

import { useState } from 'react';
import { createFileRoute, useNavigate } from '@tanstack/react-router';
import { useCompareEvalRuns, useEvalRuns } from '../../hooks/evaluation';
import {
    ArrowLeft,
    Loader2,
    Trophy,
    Minus,
    GitCompareArrows,
    BarChart3,
    FileText,
} from 'lucide-react';
import type { ComparisonMetric, EvalResult, EvalRun } from '../../schemas/evaluation';
import { formatScore, formatLatency, formatMetricValue } from '../../lib/format';

interface CompareSearch {
    run_a: number;
    run_b: number;
}

export const Route = createFileRoute('/evaluations/compare')({
    validateSearch: (search: Record<string, unknown>): CompareSearch => ({
        run_a: Number(search.run_a) || 0,
        run_b: Number(search.run_b) || 0,
    }),
    component: ComparePage,
});

const METRIC_LABELS: Record<string, string> = {
    groundedness: 'Faithfulness',
    relevancy: 'Relevancy',
    context_precision: 'Context Precision',
    context_relevancy: 'Context Relevancy',
    hallucination_rate: 'Hallucination Rate',
    latency_ms: 'Avg Latency',
};

function WinnerIcon({ winner }: { winner: string | null | undefined }) {
    if (!winner || winner === 'tie') {
        return <Minus className="h-4 w-4 text-muted-foreground" />;
    }
    return <Trophy className="h-4 w-4 text-amber-500" />;
}

function MetricRow({
    metric,
    modelA,
    modelB,
}: {
    metric: ComparisonMetric;
    modelA: string;
    modelB: string;
}) {
    const aWins = metric.winner === 'run_a';
    const bWins = metric.winner === 'run_b';

    return (
        <div className="flex items-center rounded-lg border p-3">
            <div className="w-40 text-sm font-medium">
                {METRIC_LABELS[metric.metric] ?? metric.metric}
            </div>
            <div className="flex flex-1 items-center justify-center gap-8">
                <div
                    className={`text-center ${aWins ? 'font-bold text-emerald-600 dark:text-emerald-400' : ''}`}
                >
                    <div className="text-xs text-muted-foreground">{modelA}</div>
                    <div className="text-lg">
                        {formatMetricValue(metric.metric, metric.run_a)}
                    </div>
                    {aWins && <WinnerIcon winner={metric.winner} />}
                </div>
                <div className="text-sm text-muted-foreground">
                    {metric.winner === 'tie' ? 'Tie' : 'vs'}
                </div>
                <div
                    className={`text-center ${bWins ? 'font-bold text-emerald-600 dark:text-emerald-400' : ''}`}
                >
                    <div className="text-xs text-muted-foreground">{modelB}</div>
                    <div className="text-lg">
                        {formatMetricValue(metric.metric, metric.run_b)}
                    </div>
                    {bWins && <WinnerIcon winner={metric.winner} />}
                </div>
            </div>
        </div>
    );
}

function QuestionRow({
    question,
    resultA,
    resultB,
}: {
    question: string;
    resultA: EvalResult | null | undefined;
    resultB: EvalResult | null | undefined;
}) {
    return (
        <div className="rounded-lg border bg-card">
            <div className="border-b px-4 py-3">
                <span className="text-sm font-medium">{question}</span>
            </div>
            <div className="grid grid-cols-2 divide-x">
                <div className="p-4">
                    {resultA ? (
                        <>
                            <p className="mb-2 text-sm">{resultA.answer ?? 'No answer'}</p>
                            <div className="flex gap-3 text-xs">
                                <span>
                                    Faith: <strong>{formatScore(resultA.groundedness_score)}</strong>
                                </span>
                                <span>
                                    Relev: <strong>{formatScore(resultA.relevancy_score)}</strong>
                                </span>
                                <span>{formatLatency(resultA.latency_ms)}</span>
                            </div>
                            {resultA.is_hallucination && (
                                <span className="mt-1 inline-block rounded-full bg-rose-100 px-2 py-0.5 text-[10px] font-medium text-rose-700 dark:bg-rose-950/40 dark:text-rose-300">
                                    Hallucination
                                </span>
                            )}
                        </>
                    ) : (
                        <span className="text-sm text-muted-foreground">Not evaluated</span>
                    )}
                </div>
                <div className="p-4">
                    {resultB ? (
                        <>
                            <p className="mb-2 text-sm">{resultB.answer ?? 'No answer'}</p>
                            <div className="flex gap-3 text-xs">
                                <span>
                                    Faith: <strong>{formatScore(resultB.groundedness_score)}</strong>
                                </span>
                                <span>
                                    Relev: <strong>{formatScore(resultB.relevancy_score)}</strong>
                                </span>
                                <span>{formatLatency(resultB.latency_ms)}</span>
                            </div>
                            {resultB.is_hallucination && (
                                <span className="mt-1 inline-block rounded-full bg-rose-100 px-2 py-0.5 text-[10px] font-medium text-rose-700 dark:bg-rose-950/40 dark:text-rose-300">
                                    Hallucination
                                </span>
                            )}
                        </>
                    ) : (
                        <span className="text-sm text-muted-foreground">Not evaluated</span>
                    )}
                </div>
            </div>
        </div>
    );
}

function CompareSelector() {
    const navigate = useNavigate();
    const { data: runs } = useEvalRuns();
    const completedRuns =
        runs?.filter((r: EvalRun) => r.status === 'completed' || r.status === 'complete') ?? [];
    const [runA, setRunA] = useState<number>(0);
    const [runB, setRunB] = useState<number>(0);

    if (completedRuns.length < 2) {
        return (
            <div className="rounded-xl border bg-card p-8 text-center">
                <GitCompareArrows className="mx-auto mb-3 h-8 w-8 text-muted-foreground" />
                <h2 className="mb-1 text-base font-semibold">No comparable runs yet</h2>
                <p className="text-sm text-muted-foreground">
                    You need two completed evaluation runs to compare models side by side.
                </p>
                <div className="mt-4 flex flex-wrap justify-center gap-2">
                    <button
                        onClick={() => navigate({ to: '/evaluations' })}
                        className="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90"
                    >
                        <BarChart3 className="h-4 w-4" />
                        Run New Evaluation
                    </button>
                    <button
                        onClick={() => navigate({ to: '/documents' })}
                        className="inline-flex items-center gap-2 rounded-lg border px-4 py-2 text-sm font-medium transition-colors hover:bg-accent"
                    >
                        <FileText className="h-4 w-4" />
                        Upload Documents
                    </button>
                </div>
            </div>
        );
    }

    return (
        <div className="rounded-xl border bg-card p-4">
            <div className="flex items-end gap-3">
                <div className="flex-1">
                    <label className="mb-1 block text-xs text-muted-foreground">
                        Baseline Run
                    </label>
                    <select
                        value={runA}
                        onChange={(e) => setRunA(Number(e.target.value))}
                        className="w-full rounded-lg border bg-background px-3 py-2 text-sm"
                    >
                        <option value={0}>Select run</option>
                        {completedRuns.map((r: EvalRun) => (
                            <option key={r.id} value={r.id}>
                                #{r.id} - {r.model_name}
                            </option>
                        ))}
                    </select>
                </div>
                <span className="pb-2 text-sm text-muted-foreground">vs</span>
                <div className="flex-1">
                    <label className="mb-1 block text-xs text-muted-foreground">
                        Candidate Run
                    </label>
                    <select
                        value={runB}
                        onChange={(e) => setRunB(Number(e.target.value))}
                        className="w-full rounded-lg border bg-background px-3 py-2 text-sm"
                    >
                        <option value={0}>Select run</option>
                        {completedRuns.map((r: EvalRun) => (
                            <option key={r.id} value={r.id}>
                                #{r.id} - {r.model_name}
                            </option>
                        ))}
                    </select>
                </div>
                <button
                    onClick={() =>
                        navigate({
                            to: '/evaluations/compare',
                            search: { run_a: runA, run_b: runB },
                        })
                    }
                    disabled={!runA || !runB || runA === runB}
                    className="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90 disabled:opacity-50"
                >
                    Compare
                </button>
            </div>
        </div>
    );
}

function ComparePage() {
    const navigate = useNavigate();
    const { run_a, run_b } = Route.useSearch();
    const { data, isLoading, error } = useCompareEvalRuns(run_a, run_b);

    if (!run_a || !run_b) {
        return (
            <div className="p-4 sm:p-6 lg:p-8">
                <div className="mx-auto max-w-5xl">
                    <h1 className="mb-1 text-2xl font-bold tracking-tight">Compare Evaluations</h1>
                    <p className="mb-6 text-sm text-muted-foreground">
                        Compare completed runs across models.
                    </p>
                    <CompareSelector />
                </div>
            </div>
        );
    }

    if (isLoading) {
        return (
            <div className="flex items-center justify-center p-12">
                <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            </div>
        );
    }

    if (error || !data) {
        return (
            <div className="p-8 text-center text-sm text-destructive">
                {error?.message ?? 'Failed to load comparison'}
            </div>
        );
    }

    const modelA = data.run_a.model_name;
    const modelB = data.run_b.model_name;

    return (
        <div className="p-4 sm:p-6 lg:p-8">
            <div className="mx-auto max-w-5xl">
                <button
                    onClick={() => navigate({ to: '/evaluations/compare', search: { run_a: 0, run_b: 0 } })}
                    className="mb-4 flex items-center gap-1 text-sm text-muted-foreground transition-colors hover:text-foreground"
                >
                    <ArrowLeft className="h-4 w-4" />
                    New comparison
                </button>

                <h1 className="mb-1 text-2xl font-bold tracking-tight">Compare Evaluations</h1>
                <p className="mb-6 text-sm text-muted-foreground">
                    Run #{data.run_a.id} ({modelA}) vs Run #{data.run_b.id} ({modelB})
                </p>

                {/* Aggregate metrics */}
                <div className="mb-8">
                    <h2 className="mb-3 text-lg font-semibold">Aggregate Metrics</h2>
                    <div className="space-y-2">
                        {data.metrics.map((metric) => (
                            <MetricRow
                                key={metric.metric}
                                metric={metric}
                                modelA={modelA}
                                modelB={modelB}
                            />
                        ))}
                    </div>
                </div>

                {/* Per-question breakdown */}
                <div>
                    <h2 className="mb-3 text-lg font-semibold">Per-Question Breakdown</h2>
                    <div className="mb-2 grid grid-cols-2 gap-0 px-4 text-xs font-medium text-muted-foreground">
                        <span>{modelA}</span>
                        <span>{modelB}</span>
                    </div>
                    <div className="space-y-3">
                        {data.questions.map((q, i) => (
                            <QuestionRow
                                key={i}
                                question={q.question}
                                resultA={q.run_a}
                                resultB={q.run_b}
                            />
                        ))}
                    </div>
                </div>
            </div>
        </div>
    );
}
