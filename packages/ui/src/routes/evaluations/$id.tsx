// This project was developed with assistance from AI tools.

import { createFileRoute, useNavigate } from '@tanstack/react-router';
import { useState } from 'react';
import { useEvalRun, useRerunEval } from '../../hooks/evaluation';
import { useModels } from '../../hooks/models';
import {
    ArrowLeft,
    RefreshCw,
    Loader2,
    AlertTriangle,
    CheckCircle2,
    Clock,
} from 'lucide-react';
import type { EvalResult } from '../../schemas/evaluation';
import { formatScore, formatLatency } from '../../lib/format';
import { EVAL_STATUS_COLORS } from '../../lib/status-colors';

export const Route = createFileRoute('/evaluations/$id')({
    component: EvalRunDetailPage,
});

function ScoreColor({ score }: { score: number | null | undefined }) {
    if (score == null) return <span className="text-muted-foreground">--</span>;
    const pct = score * 100;
    const color =
        pct >= 80
            ? 'text-emerald-600 dark:text-emerald-400'
            : pct >= 60
              ? 'text-amber-600 dark:text-amber-400'
              : 'text-rose-600 dark:text-rose-400';
    return <span className={`font-medium ${color}`}>{pct.toFixed(0)}%</span>;
}

function MetricCard({
    label,
    value,
    icon,
}: {
    label: string;
    value: string;
    icon: React.ReactNode;
}) {
    return (
        <div className="rounded-lg border bg-card p-4">
            <div className="mb-1 flex items-center gap-2 text-xs text-muted-foreground">
                {icon}
                {label}
            </div>
            <div className="text-2xl font-bold">{value}</div>
        </div>
    );
}

const VERDICT_STYLES: Record<string, string> = {
    PASS: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-300',
    FAIL: 'bg-rose-100 text-rose-700 dark:bg-rose-950/40 dark:text-rose-300',
    REVIEW_REQUIRED:
        'bg-amber-100 text-amber-700 dark:bg-amber-950/40 dark:text-amber-300',
};

function VerdictBadge({ verdict }: { verdict: string }) {
    const label = verdict === 'REVIEW_REQUIRED' ? 'Review' : verdict;
    return (
        <span
            className={`inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-medium ${VERDICT_STYLES[verdict] ?? VERDICT_STYLES.REVIEW_REQUIRED}`}
        >
            {label}
        </span>
    );
}

interface ParsedChunk {
    document: string;
    page: string | null;
    section: string | null;
    text: string;
}

function parseContextChunks(contexts: string): ParsedChunk[] {
    const raw = contexts.split('\n---\n');
    return raw.map((block) => {
        const lines = block.trim().split('\n');
        let document = '';
        let page: string | null = null;
        let section: string | null = null;
        let textStart = 0;

        // Parse header line like [doc.pdf | p.5 | Section Name]
        if (lines[0]?.startsWith('[') && lines[0]?.includes(']')) {
            const headerEnd = lines[0].indexOf(']');
            const header = lines[0].slice(1, headerEnd);
            const parts = header.split('|').map((p) => p.trim());
            document = parts[0] ?? '';
            for (let i = 1; i < parts.length; i++) {
                if (parts[i].startsWith('p.')) {
                    page = parts[i];
                } else {
                    section = parts[i];
                }
            }
            textStart = 1;
        }

        const text = lines.slice(textStart).join('\n').trim();
        return { document, page, section, text };
    }).filter((c) => c.text.length > 0);
}

function ChunkCard({ chunk, index }: { chunk: ParsedChunk; index: number }) {
    return (
        <div className="rounded-lg border bg-card p-4">
            <div className="mb-2 flex items-start justify-between">
                <div>
                    <div className="flex items-center gap-2">
                        <span className="inline-flex h-6 min-w-6 items-center justify-center rounded-full bg-muted px-1.5 text-xs font-medium">
                            #{index + 1}
                        </span>
                        <span className="text-sm font-semibold">{chunk.document || 'Unknown document'}</span>
                    </div>
                    {(chunk.page || chunk.section) && (
                        <div className="mt-0.5 pl-8 text-xs text-muted-foreground">
                            {[chunk.page, chunk.section].filter(Boolean).join(' \u00b7 ')}
                        </div>
                    )}
                </div>
            </div>
            <p className="pl-8 text-sm">{chunk.text}</p>
        </div>
    );
}

function ResultRow({ result }: { result: EvalResult }) {
    const [expanded, setExpanded] = useState(false);

    return (
        <div className="rounded-lg border bg-card">
            <button
                onClick={() => setExpanded(!expanded)}
                className="flex w-full items-center justify-between p-4 text-left"
            >
                <div className="flex-1">
                    <div className="flex items-center gap-2">
                        <span className="text-sm font-medium">{result.question}</span>
                        {result.verdict && (
                            <VerdictBadge verdict={result.verdict} />
                        )}
                        {result.is_hallucination && (
                            <span className="inline-flex items-center gap-1 rounded-full bg-rose-100 px-2 py-0.5 text-[10px] font-medium text-rose-700 dark:bg-rose-950/40 dark:text-rose-300">
                                <AlertTriangle className="h-3 w-3" />
                                Hallucination
                            </span>
                        )}
                    </div>
                    {result.error_message && (
                        <p className="mt-1 text-xs text-destructive">{result.error_message}</p>
                    )}
                </div>
                <div className="flex items-center gap-4 text-sm">
                    <ScoreColor score={result.groundedness_score} />
                    <ScoreColor score={result.relevancy_score} />
                    <span className="text-xs text-muted-foreground">
                        {formatLatency(result.latency_ms)}
                    </span>
                </div>
            </button>

            {expanded && (
                <div className="border-t px-4 pb-4 pt-3 space-y-4">
                    {result.expected_answer && (
                        <div className="rounded-lg bg-muted/40 p-4">
                            <span className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                                Expected answer
                            </span>
                            <p className="mt-1 text-sm">{result.expected_answer}</p>
                        </div>
                    )}

                    {result.answer && (
                        <div className="rounded-lg bg-muted/40 p-4">
                            <span className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                                Model answer
                            </span>
                            <p className="mt-1 text-sm">{result.answer}</p>
                        </div>
                    )}

                    <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                        <div>
                            <div className="text-xs text-muted-foreground">Faithfulness</div>
                            <ScoreColor score={result.groundedness_score} />
                        </div>
                        <div>
                            <div className="text-xs text-muted-foreground">Relevancy</div>
                            <ScoreColor score={result.relevancy_score} />
                        </div>
                        <div>
                            <div className="text-xs text-muted-foreground">Context Precision</div>
                            <ScoreColor score={result.context_precision_score} />
                        </div>
                        <div>
                            <div className="text-xs text-muted-foreground">Context Relevancy</div>
                            <ScoreColor score={result.context_relevancy_score} />
                        </div>
                        <div>
                            <div className="text-xs text-muted-foreground">Completeness</div>
                            <ScoreColor score={result.completeness_score} />
                        </div>
                        <div>
                            <div className="text-xs text-muted-foreground">Correctness</div>
                            <ScoreColor score={result.correctness_score} />
                        </div>
                        <div>
                            <div className="text-xs text-muted-foreground">
                                Compliance Accuracy
                            </div>
                            <ScoreColor score={result.compliance_accuracy_score} />
                        </div>
                        <div>
                            <div className="text-xs text-muted-foreground">
                                Abstention Quality
                            </div>
                            <ScoreColor score={result.abstention_score} />
                        </div>
                    </div>

                    {result.contexts && (
                        <div>
                            <h3 className="mb-1 text-sm font-semibold">Retrieved chunks</h3>
                            <p className="mb-3 text-xs text-muted-foreground">
                                Document, page, section, and snippet for each retrieved chunk.
                            </p>
                            <div className="space-y-3">
                                {parseContextChunks(result.contexts).map((chunk, i) => (
                                    <ChunkCard key={i} chunk={chunk} index={i} />
                                ))}
                            </div>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}

function EvalRunDetailPage() {
    const { id } = Route.useParams();
    const runId = Number(id);
    const navigate = useNavigate();
    const { data: run, isLoading, error } = useEvalRun(runId);
    const { data: models } = useModels();
    const rerunMutation = useRerunEval();
    const [rerunModel, setRerunModel] = useState('');

    if (isLoading) {
        return (
            <div className="flex items-center justify-center p-12">
                <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            </div>
        );
    }

    if (error || !run) {
        return (
            <div className="p-8 text-center text-sm text-destructive">
                {error?.message ?? 'Evaluation run not found'}
            </div>
        );
    }

    const handleRerun = () => {
        if (!rerunModel) return;
        rerunMutation.mutate(
            { evalRunId: runId, modelName: rerunModel },
            {
                onSuccess: (data) => {
                    navigate({ to: '/evaluations/$id', params: { id: String(data.eval_run_id) } });
                },
            },
        );
    };

    const isRunning = run.status === 'pending' || run.status === 'running';

    return (
        <div className="p-4 sm:p-6 lg:p-8">
            <div className="mx-auto max-w-5xl">
                <button
                    onClick={() => navigate({ to: '/evaluations' })}
                    className="mb-4 flex items-center gap-1 text-sm text-muted-foreground transition-colors hover:text-foreground"
                >
                    <ArrowLeft className="h-4 w-4" />
                    Back to evaluations
                </button>

                <div className="mb-6 flex items-start justify-between">
                    <div>
                        <h1 className="text-2xl font-bold tracking-tight">
                            Run #{run.id} - {run.model_name}
                        </h1>
                        <p className="text-sm text-muted-foreground">
                            {run.created_at && new Date(run.created_at).toLocaleString()}
                        </p>
                    </div>
                    <div className="flex items-center gap-2">
                        {isRunning && (
                            <span className="flex items-center gap-1 text-sm text-blue-600 dark:text-blue-400">
                                <Loader2 className="h-4 w-4 animate-spin" />
                                {run.completed_questions}/{run.total_questions}
                            </span>
                        )}
                        <span
                            className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${EVAL_STATUS_COLORS[run.status] ?? EVAL_STATUS_COLORS.pending}`}
                        >
                            {run.status}
                        </span>
                    </div>
                </div>

                {/* Verdict summary */}
                {run.overall_verdict && (
                    <div className="mb-4 flex items-center gap-3 rounded-lg border bg-card p-3">
                        <VerdictBadge verdict={run.overall_verdict} />
                        <span className="text-sm text-muted-foreground">
                            {run.pass_count}/{run.total_questions} questions passed
                            {run.fail_count ? ` | ${run.fail_count} failed` : ''}
                            {run.review_count ? ` | ${run.review_count} need review` : ''}
                        </span>
                        {run.profile_id && (
                            <span className="ml-auto text-xs text-muted-foreground">
                                Profile: {run.profile_id}
                            </span>
                        )}
                    </div>
                )}

                {/* Summary metrics */}
                <div className="mb-6 grid grid-cols-2 gap-3 sm:grid-cols-4">
                    <MetricCard
                        label="Faithfulness"
                        value={formatScore(run.avg_groundedness)}
                        icon={<CheckCircle2 className="h-3.5 w-3.5" />}
                    />
                    <MetricCard
                        label="Relevancy"
                        value={formatScore(run.avg_relevancy)}
                        icon={<CheckCircle2 className="h-3.5 w-3.5" />}
                    />
                    <MetricCard
                        label="Hallucination Rate"
                        value={
                            run.hallucination_rate != null
                                ? (run.hallucination_rate * 100).toFixed(0) + '%'
                                : '--'
                        }
                        icon={<AlertTriangle className="h-3.5 w-3.5" />}
                    />
                    <MetricCard
                        label="Avg Latency"
                        value={formatLatency(run.avg_latency_ms)}
                        icon={<Clock className="h-3.5 w-3.5" />}
                    />
                    <MetricCard
                        label="Completeness"
                        value={formatScore(run.avg_completeness)}
                        icon={<CheckCircle2 className="h-3.5 w-3.5" />}
                    />
                    <MetricCard
                        label="Correctness"
                        value={formatScore(run.avg_correctness)}
                        icon={<CheckCircle2 className="h-3.5 w-3.5" />}
                    />
                    <MetricCard
                        label="Compliance Accuracy"
                        value={formatScore(run.avg_compliance_accuracy)}
                        icon={<CheckCircle2 className="h-3.5 w-3.5" />}
                    />
                    <MetricCard
                        label="Abstention Quality"
                        value={formatScore(run.avg_abstention)}
                        icon={<CheckCircle2 className="h-3.5 w-3.5" />}
                    />
                </div>

                {/* Rerun */}
                {run.status === 'completed' && (
                    <div className="mb-6 rounded-xl border bg-card p-4">
                        <h3 className="mb-3 text-sm font-semibold">
                            Re-run with a different model
                        </h3>
                        <div className="flex items-end gap-3">
                            <div className="flex-1">
                                <select
                                    value={rerunModel}
                                    onChange={(e) => setRerunModel(e.target.value)}
                                    className="w-full rounded-lg border bg-background px-3 py-2 text-sm"
                                >
                                    <option value="">Select a model</option>
                                    {models?.map((m) => (
                                        <option key={m.id} value={m.name}>
                                            {m.name} ({m.deployment_mode})
                                        </option>
                                    ))}
                                </select>
                            </div>
                            <button
                                onClick={handleRerun}
                                disabled={!rerunModel || rerunMutation.isPending}
                                className="flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90 disabled:opacity-50"
                            >
                                {rerunMutation.isPending ? (
                                    <Loader2 className="h-4 w-4 animate-spin" />
                                ) : (
                                    <RefreshCw className="h-4 w-4" />
                                )}
                                Re-run
                            </button>
                        </div>
                    </div>
                )}

                {/* Results */}
                <div>
                    <div className="mb-3 flex items-center justify-between">
                        <h2 className="text-lg font-semibold">Results</h2>
                        <div className="flex items-center gap-4 text-xs text-muted-foreground">
                            <span>Faith.</span>
                            <span>Relev.</span>
                            <span>Latency</span>
                        </div>
                    </div>
                    <div className="space-y-2">
                        {run.results.map((result) => (
                            <ResultRow key={result.id} result={result} />
                        ))}
                    </div>
                    {run.results.length === 0 && !isRunning && (
                        <p className="text-sm text-muted-foreground">No results yet.</p>
                    )}
                </div>
            </div>
        </div>
    );
}
