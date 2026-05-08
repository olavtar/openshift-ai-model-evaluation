// This project was developed with assistance from AI tools.

import { Link } from '@tanstack/react-router';
import { useEvalRuns, useCompareEvalRuns } from '../../hooks/evaluation';
import { useDocuments } from '../../hooks/documents';
import {
    ArrowRight,
    BarChart3,
    GitCompareArrows,
    AlertTriangle,
} from 'lucide-react';
import { formatScore, formatLatency } from '../../lib/format';

function MetricCompareRow({
    label,
    valA,
    valB,
    format,
    lowerIsBetter,
}: {
    label: string;
    valA: number | null | undefined;
    valB: number | null | undefined;
    format: (v: number | null | undefined) => string;
    lowerIsBetter?: boolean;
}) {
    const a = valA ?? null;
    const b = valB ?? null;
    let winnerA = false;
    let winnerB = false;
    if (a !== null && b !== null && Math.abs(a - b) >= 0.05) {
        if (lowerIsBetter) {
            winnerA = a < b;
            winnerB = b < a;
        } else {
            winnerA = a > b;
            winnerB = b > a;
        }
    }
    return (
        <div className="grid grid-cols-3 items-center gap-2 rounded-lg border px-3 py-2 text-sm">
            <div className="text-muted-foreground">{label}</div>
            <div className={`text-center font-medium ${winnerA ? 'text-emerald-600 dark:text-emerald-400' : ''}`}>
                {format(a)}
            </div>
            <div className={`text-center font-medium ${winnerB ? 'text-emerald-600 dark:text-emerald-400' : ''}`}>
                {format(b)}
            </div>
        </div>
    );
}

function LatestComparison({ runAId, runBId }: { runAId: number; runBId: number }) {
    const { data: comparison, isLoading } = useCompareEvalRuns(runAId, runBId);

    if (isLoading) {
        return (
            <div className="mt-4 rounded-xl border bg-card p-4">
                <p className="text-sm text-muted-foreground">Loading comparison...</p>
            </div>
        );
    }

    if (!comparison) return null;

    const { run_a, run_b } = comparison;

    return (
        <div className="mt-4 rounded-xl border bg-card p-4">
            <div className="mb-3 flex items-center justify-between">
                <h2 className="text-base font-semibold">Latest Comparison</h2>
                <Link
                    to="/evaluations/compare"
                    search={{ run_a: runAId, run_b: runBId }}
                    className="text-xs text-muted-foreground hover:text-foreground"
                >
                    Full comparison <ArrowRight className="inline h-3 w-3" />
                </Link>
            </div>
            <div className="mb-2 grid grid-cols-3 gap-2 text-xs text-muted-foreground">
                <div>Metric</div>
                <div className="text-center">
                    {run_a.model_name}
                    {run_a.question_set_name && (
                        <span className="ml-1 rounded bg-muted px-1 py-0.5">{run_a.question_set_name}</span>
                    )}
                </div>
                <div className="text-center">
                    {run_b.model_name}
                    {run_b.question_set_name && (
                        <span className="ml-1 rounded bg-muted px-1 py-0.5">{run_b.question_set_name}</span>
                    )}
                </div>
            </div>
            <div className="space-y-1">
                <MetricCompareRow label="Faithfulness" valA={run_a.avg_groundedness} valB={run_b.avg_groundedness} format={formatScore} />
                <MetricCompareRow label="Relevancy" valA={run_a.avg_relevancy} valB={run_b.avg_relevancy} format={formatScore} />
                <MetricCompareRow label="Context Relevancy" valA={run_a.avg_context_relevancy} valB={run_b.avg_context_relevancy} format={formatScore} />
                <MetricCompareRow
                    label="Hallucination Rate"
                    valA={run_a.hallucination_rate}
                    valB={run_b.hallucination_rate}
                    format={(v) => (v != null ? (v * 100).toFixed(0) + '%' : '--')}
                    lowerIsBetter
                />
                <MetricCompareRow
                    label="Avg Latency"
                    valA={run_a.avg_latency_ms}
                    valB={run_b.avg_latency_ms}
                    format={formatLatency}
                    lowerIsBetter
                />
            </div>
        </div>
    );
}

export function OverviewPanel() {
    const { data: runs } = useEvalRuns();
    const { data: documents } = useDocuments();

    const completedRuns =
        runs?.filter((r) => r.status === 'completed' || r.status === 'complete') ?? [];
    const hasDocuments = (documents?.length ?? 0) > 0;
    const hasComparableRuns = completedRuns.length >= 2;
    const comparisonReadinessLabel = hasComparableRuns
        ? 'Ready to compare'
        : hasDocuments
          ? 'Documents ready'
          : 'Setup required';
    const comparisonReadinessIsWarning = !hasComparableRuns && !hasDocuments;
    const latestComparablePair = hasComparableRuns
        ? { runA: completedRuns[0].id, runB: completedRuns[1].id }
        : null;

    return (
        <div className="flex h-full flex-col overflow-y-auto p-4">
            <div>
                <h1 className="text-2xl font-bold tracking-tight">Overview</h1>
                <p className="mt-1 text-sm text-muted-foreground">
                    Evaluate and compare AI models on your compliance documents.
                </p>
            </div>

            <div className="mt-4 flex gap-2">
                <Link
                    to="/evaluations"
                    className="inline-flex items-center gap-1.5 rounded-lg bg-primary px-3 py-2 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90"
                >
                    <BarChart3 className="h-4 w-4" />
                    Run New Evaluation
                </Link>
                <Link
                    to="/evaluations/compare"
                    search={{ run_a: 0, run_b: 0 }}
                    className="inline-flex items-center gap-1.5 rounded-lg border px-3 py-2 text-sm font-medium transition-colors hover:bg-accent"
                >
                    <GitCompareArrows className="h-4 w-4" />
                    Go to Comparisons
                </Link>
            </div>

            <div className="mt-4 rounded-xl border bg-card p-4">
                <div className="mb-3 flex items-center justify-between">
                    <h2 className="text-base font-semibold">Comparison Readiness</h2>
                    <span
                        className={`inline-flex items-center gap-1 text-xs ${
                            comparisonReadinessIsWarning
                                ? 'text-amber-600 dark:text-amber-400'
                                : 'text-muted-foreground'
                        }`}
                    >
                        {comparisonReadinessIsWarning && (
                            <AlertTriangle className="h-3.5 w-3.5" aria-hidden />
                        )}
                        {comparisonReadinessLabel}
                    </span>
                </div>
                <div className="grid gap-3 sm:grid-cols-2">
                    <div className="rounded-lg border p-3">
                        <div className="text-xs text-muted-foreground">Documents uploaded</div>
                        <div className="mt-1 text-sm font-medium">
                            {hasDocuments ? (
                                `${documents?.length ?? 0} ready`
                            ) : (
                                <Link
                                    to="/documents"
                                    className="inline-flex items-center gap-1 text-primary underline underline-offset-4 hover:text-primary/80"
                                >
                                    Upload at least one
                                    <ArrowRight className="h-3.5 w-3.5" />
                                </Link>
                            )}
                        </div>
                    </div>
                    <div className="rounded-lg border p-3">
                        <div className="text-xs text-muted-foreground">Completed evaluations</div>
                        <div className="mt-1 text-sm font-medium">
                            {completedRuns.length >= 2
                                ? `${completedRuns.length} available`
                                : `${completedRuns.length}/2 complete`}
                        </div>
                    </div>
                </div>
            </div>

            {hasComparableRuns && latestComparablePair && (
                <LatestComparison
                    runAId={latestComparablePair.runA}
                    runBId={latestComparablePair.runB}
                />
            )}
        </div>
    );
}
