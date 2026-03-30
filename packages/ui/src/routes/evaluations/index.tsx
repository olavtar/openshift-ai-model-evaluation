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
import {
    useQuestionSets,
    useCreateQuestionSet,
    useDeleteQuestionSet,
} from '../../hooks/question-sets';
import {
    BarChart3,
    Plus,
    Trash2,
    Sparkles,
    ArrowRight,
    Loader2,
    AlertTriangle,
    Save,
    FolderOpen,
} from 'lucide-react';
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
                        {run.question_set_name && (
                            <span className="rounded bg-muted px-1.5 py-0.5 text-xs font-medium text-muted-foreground">
                                {run.question_set_name}
                            </span>
                        )}
                        <StatusBadge status={run.status} />
                    </div>
                    <span className="text-xs text-muted-foreground">
                        Run #{run.id}
                        {' -- '}
                        {run.completed_questions}/{run.total_questions} questions
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

function NewEvalForm({
    onCreated,
    onCancel,
    initialQuestions,
    initialQuestionSetId,
}: {
    onCreated: () => void;
    onCancel: () => void;
    initialQuestions?: string[];
    initialQuestionSetId?: number;
}) {
    const { data: models } = useModels();
    const { data: questionSets } = useQuestionSets();
    const createMutation = useCreateEvalRun();
    const synthesizeMutation = useSynthesizeQuestions();
    const saveSetMutation = useCreateQuestionSet();
    const deleteSetMutation = useDeleteQuestionSet();
    const [selectedModel, setSelectedModel] = useState('');
    const [questions, setQuestions] = useState<string[]>(initialQuestions ?? []);
    const [newQuestion, setNewQuestion] = useState('');
    const [warningMessage, setWarningMessage] = useState('');
    const [loadedSetId, setLoadedSetId] = useState<number | undefined>(initialQuestionSetId);
    const [saveSetName, setSaveSetName] = useState('');
    const [showSaveSet, setShowSaveSet] = useState(false);

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
            { modelName: selectedModel, questions, questionSetId: loadedSetId },
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
                <div className="mb-1.5 flex items-center justify-between">
                    <label className="text-xs font-medium text-muted-foreground">
                        Questions ({questions.length})
                    </label>
                    <div className="flex items-center gap-2">
                        {questionSets && questionSets.length > 0 && (
                            <select
                                onChange={(e) => {
                                    const set = questionSets.find(
                                        (s) => s.id === Number(e.target.value),
                                    );
                                    if (set) {
                                        setQuestions(set.questions);
                                        setLoadedSetId(set.id);
                                    }
                                    e.target.value = '';
                                }}
                                className="rounded-lg border bg-background px-2 py-1 text-xs"
                                defaultValue=""
                            >
                                <option value="" disabled>
                                    Load question set...
                                </option>
                                {questionSets.map((s) => (
                                    <option key={s.id} value={s.id}>
                                        {s.name} ({s.questions.length}q)
                                    </option>
                                ))}
                            </select>
                        )}
                    </div>
                </div>
                <div className="space-y-2">
                    {questions.map((q, i) => (
                        <div
                            key={i}
                            className="flex items-center gap-2 rounded-lg border bg-background px-3 py-2 text-sm"
                        >
                            <input
                                type="text"
                                value={q}
                                onChange={(e) => {
                                    const updated = [...questions];
                                    updated[i] = e.target.value;
                                    setQuestions(updated);
                                }}
                                className="flex-1 bg-transparent outline-none"
                            />
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

                <div className="mt-2 flex gap-2">
                    <button
                        onClick={handleSynthesize}
                        disabled={synthesizeMutation.isPending}
                        className="flex items-center gap-1 rounded-lg border px-3 py-2 text-sm transition-colors hover:bg-accent disabled:opacity-50"
                    >
                        {synthesizeMutation.isPending ? (
                            <Loader2 className="h-3.5 w-3.5 animate-spin" />
                        ) : (
                            <Sparkles className="h-3.5 w-3.5" />
                        )}
                        Generate from documents
                    </button>
                    {questions.length > 0 && !showSaveSet && (
                        <button
                            onClick={() => setShowSaveSet(true)}
                            className="flex items-center gap-1 rounded-lg border px-3 py-2 text-sm transition-colors hover:bg-accent"
                        >
                            <Save className="h-3.5 w-3.5" />
                            Save as question set
                        </button>
                    )}
                </div>

                {showSaveSet && (
                    <div className="mt-2 flex gap-2">
                        <input
                            type="text"
                            value={saveSetName}
                            onChange={(e) => setSaveSetName(e.target.value)}
                            onKeyDown={(e) => {
                                if (e.key === 'Enter' && saveSetName.trim()) {
                                    saveSetMutation.mutate(
                                        { name: saveSetName.trim(), questions },
                                        {
                                            onSuccess: () => {
                                                setSaveSetName('');
                                                setShowSaveSet(false);
                                            },
                                        },
                                    );
                                }
                            }}
                            placeholder="Name for this question set"
                            className="flex-1 rounded-lg border bg-background px-3 py-2 text-sm"
                            autoFocus
                        />
                        <button
                            onClick={() => {
                                if (!saveSetName.trim()) return;
                                saveSetMutation.mutate(
                                    { name: saveSetName.trim(), questions },
                                    {
                                        onSuccess: () => {
                                            setSaveSetName('');
                                            setShowSaveSet(false);
                                        },
                                    },
                                );
                            }}
                            disabled={!saveSetName.trim() || saveSetMutation.isPending}
                            className="flex items-center gap-1 rounded-lg bg-primary px-3 py-2 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90 disabled:opacity-50"
                        >
                            {saveSetMutation.isPending ? (
                                <Loader2 className="h-3.5 w-3.5 animate-spin" />
                            ) : (
                                <Save className="h-3.5 w-3.5" />
                            )}
                            Save
                        </button>
                        <button
                            onClick={() => {
                                setShowSaveSet(false);
                                setSaveSetName('');
                            }}
                            className="rounded-lg border px-3 py-2 text-sm transition-colors hover:bg-accent"
                        >
                            Cancel
                        </button>
                    </div>
                )}
            </div>

            <div className="flex gap-2">
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
                <button
                    onClick={onCancel}
                    className="rounded-lg border px-4 py-2 text-sm font-medium transition-colors hover:bg-accent"
                >
                    Cancel
                </button>
            </div>

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

function QuestionSetsPanel({
    onLoad,
}: {
    onLoad: (questions: string[], setId: number) => void;
}) {
    const { data: sets } = useQuestionSets();
    const deleteMutation = useDeleteQuestionSet();

    if (!sets || sets.length === 0) return null;

    return (
        <div className="rounded-xl border bg-card p-4">
            <h3 className="mb-3 text-sm font-semibold">Saved Question Sets</h3>
            <p className="mb-3 text-xs text-muted-foreground">
                Click a set to load its questions into a new evaluation.
            </p>
            <div className="space-y-2">
                {sets.map((s) => (
                    <div
                        key={s.id}
                        className="flex items-center justify-between rounded-lg border bg-background px-3 py-2 transition-colors hover:bg-accent"
                    >
                        <button
                            onClick={() => onLoad(s.questions, s.id)}
                            className="flex flex-1 flex-col text-left"
                        >
                            <span className="text-sm font-medium">{s.name}</span>
                            <span className="text-xs text-muted-foreground">
                                {s.questions.length} questions
                                {s.created_at &&
                                    ` -- ${new Date(s.created_at).toLocaleDateString()}`}
                            </span>
                        </button>
                        <button
                            onClick={(e) => {
                                e.stopPropagation();
                                deleteMutation.mutate(s.id);
                            }}
                            className="rounded p-1.5 text-muted-foreground transition-colors hover:bg-destructive/10 hover:text-destructive"
                            title="Delete question set"
                        >
                            <Trash2 className="h-3.5 w-3.5" />
                        </button>
                    </div>
                ))}
            </div>
        </div>
    );
}

function EvaluationsPage() {
    const { data: runs, isLoading, error, refetch } = useEvalRuns();
    const deleteMutation = useDeleteEvalRun();
    const [showForm, setShowForm] = useState(false);
    const [preloadedQuestions, setPreloadedQuestions] = useState<string[] | undefined>();
    const [preloadedSetId, setPreloadedSetId] = useState<number | undefined>();

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
                        onClick={() => {
                            setPreloadedQuestions(undefined);
                            setPreloadedSetId(undefined);
                            setShowForm(true);
                        }}
                        className="flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90"
                    >
                        <Plus className="h-4 w-4" />
                        Run New Evaluation
                    </button>
                </div>

                {runs && runs.length >= 2 && (
                    <div className="mb-6">
                        <CompareSelector runs={runs} />
                    </div>
                )}

                {showForm && (
                    <div className="mb-6">
                        <NewEvalForm
                            key={JSON.stringify(preloadedQuestions)}
                            initialQuestions={preloadedQuestions}
                            initialQuestionSetId={preloadedSetId}
                            onCreated={() => {
                                setShowForm(false);
                                setPreloadedQuestions(undefined);
                                setPreloadedSetId(undefined);
                                refetch();
                            }}
                            onCancel={() => {
                                setShowForm(false);
                                setPreloadedQuestions(undefined);
                                setPreloadedSetId(undefined);
                            }}
                        />
                    </div>
                )}

                <div className="mb-6">
                    <QuestionSetsPanel
                        onLoad={(questions, setId) => {
                            setPreloadedQuestions(questions);
                            setPreloadedSetId(setId);
                            setShowForm(true);
                        }}
                    />
                </div>

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
