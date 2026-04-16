// This project was developed with assistance from AI tools.

import { createFileRoute, Link } from '@tanstack/react-router';
import { useHealth } from '../hooks/health';
import { useEvalRuns, useCompareEvalRuns } from '../hooks/evaluation';
import { useDocuments } from '../hooks/documents';
import {
    Monitor,
    Server,
    Database,
    ArrowRight,
    BarChart3,
    GitCompareArrows,
    FileText,
    AlertTriangle,
} from 'lucide-react';
import { HEALTH_STATUS_COLORS } from '../lib/status-colors';
import { formatScore, formatLatency } from '../lib/format';

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export const Route = createFileRoute('/' as any)({
    component: Index,
});

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
            <div className="mt-6 rounded-xl border bg-card p-4">
                <p className="text-sm text-muted-foreground">Loading comparison...</p>
            </div>
        );
    }

    if (!comparison) return null;

    const { run_a, run_b } = comparison;

    return (
        <div className="mt-6 rounded-xl border bg-card p-4">
            <div className="mb-3 flex items-center justify-between">
                <h2 className="text-lg font-semibold">Latest Comparison</h2>
                <Link
                    to="/evaluations/compare"
                    search={{ run_a: runAId, run_b: runBId }}
                    className="text-sm text-muted-foreground hover:text-foreground"
                >
                    Full comparison <ArrowRight className="inline h-3.5 w-3.5" />
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
                    format={(v) => v != null ? (v * 100).toFixed(0) + '%' : '--'}
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

function Index() {
    const { data: readiness, isPending: healthPending, error: healthError } = useHealth();
    const { data: runs } = useEvalRuns();
    const { data: documents } = useDocuments();

    const depStatus = (key: string) => readiness?.dependencies?.[key] ?? 'unknown';

    const overallStatus = readiness?.status ?? 'unknown';
    const overallLabel =
        overallStatus === 'ready'
            ? 'All Systems Operational'
            : overallStatus === 'degraded'
              ? 'Degraded'
              : overallStatus === 'not_ready'
                ? 'Not Ready'
                : 'Checking...';

    const deps = [
        { key: 'database', label: 'Database', icon: <Database className="h-4 w-4" /> },
        { key: 'model_a', label: 'Model A', icon: <Server className="h-4 w-4" /> },
        { key: 'model_b', label: 'Model B', icon: <Server className="h-4 w-4" /> },
    ];

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
        <div className="p-4 sm:p-6 lg:p-8">
            <div className="mx-auto max-w-7xl">
                {/* Hero */}
                <section className="relative overflow-hidden rounded-2xl border bg-card p-6 shadow-sm sm:p-8">
                    <div
                        aria-hidden
                        className="pointer-events-none absolute -inset-x-4 -top-16 bottom-0 opacity-60 [mask-image:radial-gradient(60%_60%_at_30%_0%,black,transparent)] dark:opacity-70"
                    >
                        <div className="mx-auto h-full max-w-6xl bg-gradient-to-tr from-sky-500/10 via-violet-500/10 to-fuchsia-500/10 blur-2xl" />
                    </div>
                    <div className="relative z-10 flex flex-col gap-3">
                        <h1 className="text-3xl font-bold tracking-tight text-foreground sm:text-4xl">
                            Compare Models
                        </h1>
                        <p className="max-w-2xl text-sm leading-6 text-muted-foreground">
                            The core workflow is evaluation comparison: run model evaluations on
                            the same task, then compare quality, hallucination risk, and latency
                            side by side.
                        </p>
                        <div className="mt-2 flex gap-3">
                            {hasComparableRuns ? (
                                <Link
                                    to="/evaluations/compare"
                                    search={{ run_a: 0, run_b: 0 }}
                                    className="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90"
                                >
                                    <GitCompareArrows className="h-4 w-4" />
                                    Compare Evaluations
                                </Link>
                            ) : hasDocuments ? (
                                <Link
                                    to="/evaluations"
                                    className="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90"
                                >
                                    <BarChart3 className="h-4 w-4" />
                                    Start Comparison Setup
                                </Link>
                            ) : (
                                <Link
                                    to="/documents"
                                    className="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90"
                                >
                                    <FileText className="h-4 w-4" />
                                    Start Comparison Setup
                                </Link>
                            )}
                            <Link
                                to="/evaluations"
                                className="inline-flex items-center gap-2 rounded-lg border px-4 py-2 text-sm font-medium transition-colors hover:bg-accent"
                            >
                                <BarChart3 className="h-4 w-4" />
                                Run New Evaluation
                            </Link>
                        </div>
                    </div>
                </section>

                {/* Comparison readiness */}
                <section className="mt-6 rounded-xl border bg-card p-4">
                    <div className="mb-3 flex items-center justify-between">
                        <h2 className="text-lg font-semibold">Comparison Readiness</h2>
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
                            <div className="text-xs text-muted-foreground">
                                1. Documents uploaded
                            </div>
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
                            <div className="text-xs text-muted-foreground">
                                2. Completed evaluation runs
                            </div>
                            <div className="mt-1 text-sm font-medium">
                                {completedRuns.length >= 2
                                    ? `${completedRuns.length} available`
                                    : `${completedRuns.length}/2 complete`}
                            </div>
                        </div>
                    </div>
                </section>

                {/* Latest Comparison */}
                {hasComparableRuns && latestComparablePair && (
                    <LatestComparison
                        runAId={latestComparablePair.runA}
                        runBId={latestComparablePair.runB}
                    />
                )}

                {/* Empty state */}
                {completedRuns.length === 0 && !healthPending && (
                    <div className="mt-6 rounded-xl border bg-card p-8 text-center">
                        <BarChart3 className="mx-auto mb-3 h-8 w-8 text-muted-foreground" />
                        <p className="text-sm text-muted-foreground">
                            No completed evaluations yet. Run evaluations for two models, then
                            compare them side by side.
                        </p>
                        <div className="mt-3 flex justify-center gap-2">
                            <Link
                                to="/evaluations"
                                className="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90"
                            >
                                <BarChart3 className="h-4 w-4" />
                                Run New Evaluation
                            </Link>
                            <Link
                                to="/evaluations/compare"
                                search={{ run_a: 0, run_b: 0 }}
                                className="inline-flex items-center gap-2 rounded-lg border px-4 py-2 text-sm font-medium transition-colors hover:bg-accent"
                            >
                                <GitCompareArrows className="h-4 w-4" />
                                Open Compare
                            </Link>
                        </div>
                    </div>
                )}

                {/* System Health */}
                <div className="mt-6 rounded-xl border bg-card p-4">
                    <div className="mb-4 flex items-center gap-2">
                        <Monitor className="h-5 w-5" />
                        <h2 className="text-lg font-semibold">System Health</h2>
                        {!healthPending && (
                            <span
                                className={`ml-auto inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${
                                    overallStatus === 'ready'
                                        ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-300'
                                        : overallStatus === 'degraded'
                                          ? 'bg-amber-100 text-amber-700 dark:bg-amber-950/40 dark:text-amber-300'
                                          : 'bg-rose-100 text-rose-700 dark:bg-rose-950/40 dark:text-rose-300'
                                }`}
                            >
                                {overallLabel}
                            </span>
                        )}
                    </div>

                    {healthPending && (
                        <p className="text-sm text-muted-foreground">Checking services...</p>
                    )}
                    {healthError && (
                        <p className="text-sm text-destructive">
                            Failed to fetch health: {healthError.message}
                        </p>
                    )}

                    {readiness && (
                        <div className="grid gap-3 sm:grid-cols-3">
                            {deps.map(({ key, label, icon }) => {
                                const st = depStatus(key);
                                const badge =
                                    HEALTH_STATUS_COLORS[st] ?? HEALTH_STATUS_COLORS.unknown;
                                return (
                                    <div
                                        key={key}
                                        className="flex items-center gap-3 rounded-lg border p-3"
                                    >
                                        <div className="grid h-8 w-8 place-items-center rounded bg-muted">
                                            {icon}
                                        </div>
                                        <div className="flex flex-col">
                                            <span className="text-sm font-medium">{label}</span>
                                            <span
                                                className={`inline-flex w-fit items-center rounded-full px-2 py-0.5 text-[10px] font-medium ${badge.classes}`}
                                            >
                                                {badge.label}
                                            </span>
                                        </div>
                                    </div>
                                );
                            })}
                        </div>
                    )}

                    {readiness?.message && (
                        <p className="mt-3 text-xs text-muted-foreground">{readiness.message}</p>
                    )}
                </div>
            </div>
        </div>
    );
}
