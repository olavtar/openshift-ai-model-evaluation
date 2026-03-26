// This project was developed with assistance from AI tools.

import { createFileRoute, Link } from '@tanstack/react-router';
import { useHealth } from '../hooks/health';
import { useEvalRuns } from '../hooks/evaluation';
import { useDocuments } from '../hooks/documents';
import {
    Monitor,
    Server,
    Database,
    CheckCircle2,
    AlertTriangle,
    Clock,
    Target,
    ArrowRight,
    BarChart3,
    GitCompareArrows,
    FileText,
} from 'lucide-react';
import { HEALTH_STATUS_COLORS } from '../lib/status-colors';
import { formatScore, formatLatency } from '../lib/format';

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export const Route = createFileRoute('/' as any)({
    component: Index,
});

function KpiCard({
    label,
    value,
    icon,
    color,
}: {
    label: string;
    value: string;
    icon: React.ReactNode;
    color?: string;
}) {
    return (
        <div className="rounded-lg border bg-card p-4">
            <div className="mb-1 flex items-center gap-2 text-xs text-muted-foreground">
                {icon}
                {label}
            </div>
            <div className={`text-2xl font-bold ${color ?? ''}`}>{value}</div>
        </div>
    );
}

function Index() {
    const { data: readiness, isLoading: healthLoading, error: healthError } = useHealth();
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
    const latestRun = completedRuns.length > 0 ? completedRuns[0] : null;
    const hasDocuments = (documents?.length ?? 0) > 0;
    const hasComparableRuns = completedRuns.length >= 2;
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
                            {hasComparableRuns && latestComparablePair ? (
                                <Link
                                    to="/evaluations/compare"
                                    search={{
                                        run_a: latestComparablePair.runA,
                                        run_b: latestComparablePair.runB,
                                    }}
                                    className="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90"
                                >
                                    <GitCompareArrows className="h-4 w-4" />
                                    Compare Latest Runs
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
                        <span className="text-xs text-muted-foreground">
                            {hasComparableRuns ? 'Ready to compare' : 'Setup required'}
                        </span>
                    </div>
                    <div className="grid gap-3 sm:grid-cols-3">
                        <div className="rounded-lg border p-3">
                            <div className="text-xs text-muted-foreground">
                                1. Documents uploaded
                            </div>
                            <div className="mt-1 text-sm font-medium">
                                {hasDocuments
                                    ? `${documents?.length ?? 0} ready`
                                    : 'Upload at least one'}
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
                        <div className="rounded-lg border p-3">
                            <div className="text-xs text-muted-foreground">3. Compare models</div>
                            <div className="mt-1 text-sm font-medium">
                                {hasComparableRuns
                                    ? 'Open comparison now'
                                    : 'Needs two completed runs'}
                            </div>
                        </div>
                    </div>
                </section>

                {/* KPI Cards */}
                {latestRun && (
                    <div className="mt-6">
                        <h2 className="mb-3 text-sm font-medium text-muted-foreground">
                            Latest Evaluation: {latestRun.model_name} (Run #{latestRun.id})
                        </h2>
                        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 lg:grid-cols-5">
                            <KpiCard
                                label="Faithfulness"
                                value={formatScore(latestRun.avg_groundedness)}
                                icon={<CheckCircle2 className="h-3.5 w-3.5" />}
                            />
                            <KpiCard
                                label="Relevancy"
                                value={formatScore(latestRun.avg_relevancy)}
                                icon={<Target className="h-3.5 w-3.5" />}
                            />
                            <KpiCard
                                label="Hallucination Rate"
                                value={
                                    latestRun.hallucination_rate != null
                                        ? (latestRun.hallucination_rate * 100).toFixed(0) + '%'
                                        : '--'
                                }
                                icon={<AlertTriangle className="h-3.5 w-3.5" />}
                                color={
                                    latestRun.hallucination_rate != null &&
                                    latestRun.hallucination_rate > 0.3
                                        ? 'text-rose-600 dark:text-rose-400'
                                        : undefined
                                }
                            />
                            <KpiCard
                                label="Context Precision"
                                value={formatScore(latestRun.avg_context_precision)}
                                icon={<CheckCircle2 className="h-3.5 w-3.5" />}
                            />
                            <KpiCard
                                label="Avg Latency"
                                value={formatLatency(latestRun.avg_latency_ms)}
                                icon={<Clock className="h-3.5 w-3.5" />}
                            />
                        </div>
                    </div>
                )}

                {/* Latest Evaluation Runs */}
                {completedRuns.length > 0 && (
                    <div className="mt-6 rounded-xl border bg-card p-4">
                        <div className="mb-3 flex items-center justify-between">
                            <h2 className="text-lg font-semibold">Recent Evaluations</h2>
                            <Link
                                to="/evaluations"
                                className="text-sm text-muted-foreground hover:text-foreground"
                            >
                                View all
                            </Link>
                        </div>
                        <div className="space-y-2">
                            {completedRuns.slice(0, 3).map((run) => (
                                <Link
                                    key={run.id}
                                    to="/evaluations/$id"
                                    params={{ id: String(run.id) }}
                                    className="flex items-center justify-between rounded-lg border p-3 transition-colors hover:bg-accent"
                                >
                                    <div>
                                        <span className="text-sm font-medium">
                                            {run.model_name}
                                        </span>
                                        <span className="ml-2 text-xs text-muted-foreground">
                                            Run #{run.id}
                                            {run.created_at &&
                                                ` -- ${new Date(run.created_at).toLocaleDateString()}`}
                                        </span>
                                    </div>
                                    <div className="flex items-center gap-4 text-xs">
                                        <div className="text-center">
                                            <div className="text-muted-foreground">Faith.</div>
                                            <div className="font-medium">
                                                {formatScore(run.avg_groundedness)}
                                            </div>
                                        </div>
                                        <div className="text-center">
                                            <div className="text-muted-foreground">Relev.</div>
                                            <div className="font-medium">
                                                {formatScore(run.avg_relevancy)}
                                            </div>
                                        </div>
                                        <div className="text-center">
                                            <div className="text-muted-foreground">Latency</div>
                                            <div className="font-medium">
                                                {formatLatency(run.avg_latency_ms)}
                                            </div>
                                        </div>
                                        <ArrowRight className="h-3.5 w-3.5 text-muted-foreground" />
                                    </div>
                                </Link>
                            ))}
                        </div>
                    </div>
                )}

                {/* Empty state */}
                {completedRuns.length === 0 && !healthLoading && (
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
                        {!healthLoading && (
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

                    {healthLoading && (
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
