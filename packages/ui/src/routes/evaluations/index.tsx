// This project was developed with assistance from AI tools.

import { createFileRoute, Link, useNavigate } from '@tanstack/react-router';
import { useState } from 'react';
import {
    useEvalRuns,
    useCreateEvalRun,
    useDeleteEvalRun,
    useSynthesizeQuestions,
} from '../../hooks/evaluation';
import { useModels } from '../../hooks/models';
import { BarChart3, Plus, Trash2, Sparkles, ArrowRight, Loader2, AlertTriangle } from 'lucide-react';
import type { EvalRun } from '../../schemas/evaluation';
import { formatScore, formatLatency } from '../../lib/format';
import { EVAL_STATUS_COLORS } from '../../lib/status-colors';

export const Route = createFileRoute('/evaluations/')({
    component: EvaluationsPage,
});

function StatusBadge({ status }: { status: string }) {
    return (
        <span
            className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${EVAL_STATUS_COLORS[status] ?? EVAL_STATUS_COLORS.pending}`}
        >
            {status}
        </span>
    );
}

function RunRow({ run, onDelete }: { run: EvalRun; onDelete: (id: number) => void }) {
    return (
        <div className="flex items-center gap-2 rounded-lg border transition-colors hover:bg-accent">
            <Link
                to="/evaluations/$id"
                params={{ id: String(run.id) }}
                className="flex flex-1 items-center justify-between p-4"
            >
                <div className="flex flex-col gap-1">
                    <div className="flex items-center gap-2">
                        <span className="font-medium">{run.model_name}</span>
                        <StatusBadge status={run.status} />
                    </div>
                    <span className="text-xs text-muted-foreground">
                        Run #{run.id} -- {run.completed_questions}/{run.total_questions} questions
                        {run.created_at &&
                            ` -- ${new Date(run.created_at).toLocaleDateString()}`}
                    </span>
                </div>
                <div className="flex items-center gap-6 text-sm">
                    <div className="text-center">
                        <div className="text-xs text-muted-foreground">Faith.</div>
                        <div className="font-medium">{formatScore(run.avg_groundedness)}</div>
                    </div>
                    <div className="text-center">
                        <div className="text-xs text-muted-foreground">Relev.</div>
                        <div className="font-medium">{formatScore(run.avg_relevancy)}</div>
                    </div>
                    <div className="text-center">
                        <div className="text-xs text-muted-foreground">Latency</div>
                        <div className="font-medium">{formatLatency(run.avg_latency_ms)}</div>
                    </div>
                    <ArrowRight className="h-4 w-4 text-muted-foreground" />
                </div>
            </Link>
            <button
                onClick={(e) => {
                    e.stopPropagation();
                    onDelete(run.id);
                }}
                className="mr-3 rounded p-1.5 text-muted-foreground transition-colors hover:bg-destructive/10 hover:text-destructive"
                title="Delete evaluation run"
            >
                <Trash2 className="h-4 w-4" />
            </button>
        </div>
    );
}

function NewEvalForm({ onCreated }: { onCreated: () => void }) {
    const { data: models } = useModels();
    const createMutation = useCreateEvalRun();
    const synthesizeMutation = useSynthesizeQuestions();
    const [selectedModel, setSelectedModel] = useState('');
    const [questions, setQuestions] = useState<string[]>([]);
    const [newQuestion, setNewQuestion] = useState('');
    const [warningMessage, setWarningMessage] = useState('');

    const addQuestion = () => {
        const trimmed = newQuestion.trim();
        if (trimmed && !questions.includes(trimmed)) {
            setQuestions([...questions, trimmed]);
            setNewQuestion('');
        }
    };

    const removeQuestion = (index: number) => {
        setQuestions(questions.filter((_, i) => i !== index));
    };

    const handleSynthesize = () => {
        synthesizeMutation.mutate(
            { maxQuestions: 10 },
            {
                onSuccess: (data) => {
                    const generated = data.questions.map((q) => q.question);
                    const unique = generated.filter((q) => !questions.includes(q));
                    setQuestions([...questions, ...unique]);
                },
            },
        );
    };

    const handleSubmit = () => {
        if (!selectedModel || questions.length === 0) return;
        createMutation.mutate(
            { modelName: selectedModel, questions },
            {
                onSuccess: (data) => {
                    if (data.message.includes('Warning')) {
                        setWarningMessage(data.message);
                    }
                    setQuestions([]);
                    setSelectedModel('');
                    onCreated();
                },
            },
        );
    };

    return (
        <div className="rounded-xl border bg-card p-6">
            <h3 className="mb-4 text-lg font-semibold">Run New Evaluation</h3>

            <div className="mb-4">
                <label className="mb-1.5 block text-xs font-medium text-muted-foreground">
                    Model
                </label>
                <select
                    value={selectedModel}
                    onChange={(e) => setSelectedModel(e.target.value)}
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

            <div className="mb-4">
                <label className="mb-1.5 block text-xs font-medium text-muted-foreground">
                    Questions ({questions.length})
                </label>
                <div className="space-y-2">
                    {questions.map((q, i) => (
                        <div
                            key={i}
                            className="flex items-center gap-2 rounded-lg border bg-background px-3 py-2 text-sm"
                        >
                            <span className="flex-1">{q}</span>
                            <button
                                onClick={() => removeQuestion(i)}
                                className="text-muted-foreground hover:text-destructive"
                            >
                                <Trash2 className="h-3.5 w-3.5" />
                            </button>
                        </div>
                    ))}
                </div>

                <div className="mt-2 flex gap-2">
                    <input
                        type="text"
                        value={newQuestion}
                        onChange={(e) => setNewQuestion(e.target.value)}
                        onKeyDown={(e) => e.key === 'Enter' && addQuestion()}
                        placeholder="Type a question and press Enter"
                        className="flex-1 rounded-lg border bg-background px-3 py-2 text-sm"
                    />
                    <button
                        onClick={addQuestion}
                        disabled={!newQuestion.trim()}
                        className="flex items-center gap-1 rounded-lg border px-3 py-2 text-sm transition-colors hover:bg-accent disabled:opacity-50"
                    >
                        <Plus className="h-3.5 w-3.5" />
                        Add
                    </button>
                </div>

                <button
                    onClick={handleSynthesize}
                    disabled={synthesizeMutation.isPending}
                    className="mt-2 flex items-center gap-1 rounded-lg border px-3 py-2 text-sm transition-colors hover:bg-accent disabled:opacity-50"
                >
                    {synthesizeMutation.isPending ? (
                        <Loader2 className="h-3.5 w-3.5 animate-spin" />
                    ) : (
                        <Sparkles className="h-3.5 w-3.5" />
                    )}
                    Generate from documents
                </button>
            </div>

            <button
                onClick={handleSubmit}
                disabled={!selectedModel || questions.length === 0 || createMutation.isPending}
                className="flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90 disabled:opacity-50"
            >
                {createMutation.isPending ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                    <BarChart3 className="h-4 w-4" />
                )}
                Run Evaluation
            </button>

            {synthesizeMutation.error && (
                <p className="mt-2 text-sm text-destructive">{synthesizeMutation.error.message}</p>
            )}

            {createMutation.error && (
                <p className="mt-2 text-sm text-destructive">{createMutation.error.message}</p>
            )}

            {warningMessage && (
                <div className="mt-2 flex items-center gap-2 rounded-lg border border-amber-200 bg-amber-50 p-3 dark:border-amber-900 dark:bg-amber-950/20">
                    <AlertTriangle className="h-4 w-4 shrink-0 text-amber-600 dark:text-amber-400" />
                    <p className="text-xs text-amber-700 dark:text-amber-300">{warningMessage}</p>
                </div>
            )}
        </div>
    );
}

function CompareSelector({ runs }: { runs: EvalRun[] }) {
    const navigate = useNavigate();
    const completedRuns = runs.filter((r) => r.status === 'completed');
    const [runA, setRunA] = useState<number>(0);
    const [runB, setRunB] = useState<number>(0);

    if (completedRuns.length < 2) return null;

    return (
        <div className="rounded-xl border bg-card p-4">
            <h3 className="mb-3 text-sm font-semibold">Compare Runs</h3>
            <div className="flex items-end gap-3">
                <div className="flex-1">
                    <label className="mb-1 block text-xs text-muted-foreground">Run A</label>
                    <select
                        value={runA}
                        onChange={(e) => setRunA(Number(e.target.value))}
                        className="w-full rounded-lg border bg-background px-3 py-2 text-sm"
                    >
                        <option value={0}>Select run</option>
                        {completedRuns.map((r) => (
                            <option key={r.id} value={r.id}>
                                #{r.id} - {r.model_name}
                            </option>
                        ))}
                    </select>
                </div>
                <span className="pb-2 text-sm text-muted-foreground">vs</span>
                <div className="flex-1">
                    <label className="mb-1 block text-xs text-muted-foreground">Run B</label>
                    <select
                        value={runB}
                        onChange={(e) => setRunB(Number(e.target.value))}
                        className="w-full rounded-lg border bg-background px-3 py-2 text-sm"
                    >
                        <option value={0}>Select run</option>
                        {completedRuns.map((r) => (
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

function EvaluationsPage() {
    const { data: runs, isLoading, error, refetch } = useEvalRuns();
    const deleteMutation = useDeleteEvalRun();
    const [showForm, setShowForm] = useState(false);

    return (
        <div className="p-4 sm:p-6 lg:p-8">
            <div className="mx-auto max-w-5xl">
                <div className="mb-6 flex items-center justify-between">
                    <div>
                        <h1 className="text-2xl font-bold tracking-tight">Evaluation Runs</h1>
                        <p className="text-sm text-muted-foreground">
                            Run evaluations, then compare completed runs side by side.
                        </p>
                    </div>
                    <button
                        onClick={() => setShowForm(!showForm)}
                        className="flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90"
                    >
                        <Plus className="h-4 w-4" />
                        Run New Evaluation
                    </button>
                </div>

                {showForm && (
                    <div className="mb-6">
                        <NewEvalForm
                            onCreated={() => {
                                setShowForm(false);
                                refetch();
                            }}
                        />
                    </div>
                )}

                {runs && runs.length >= 2 && (
                    <div className="mb-6">
                        <CompareSelector runs={runs} />
                    </div>
                )}

                {isLoading && (
                    <p className="text-sm text-muted-foreground">Loading evaluations...</p>
                )}
                {error && <p className="text-sm text-destructive">{error.message}</p>}

                {runs && runs.length === 0 && !showForm && (
                    <div className="rounded-xl border bg-card p-8 text-center">
                        <BarChart3 className="mx-auto mb-3 h-8 w-8 text-muted-foreground" />
                        <p className="text-sm text-muted-foreground">
                            No evaluations yet. Create runs for at least two models, then compare
                            them in the Compare page.
                        </p>
                    </div>
                )}

                {runs && runs.length > 0 && (
                    <div className="space-y-3">
                        {runs.map((run) => (
                            <RunRow
                                key={run.id}
                                run={run}
                                onDelete={(id) => deleteMutation.mutate(id)}
                            />
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
}
