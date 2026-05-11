// This project was developed with assistance from AI tools.

import { createFileRoute, Link, useNavigate } from '@tanstack/react-router';
import { useState, useEffect, useRef, useCallback } from 'react';
import {
    useEvalRuns,
    useCreateEvalRun,
    useCancelEvalRun,
    useDeleteEvalRun,
    useSynthesizeQuestions,
    useProfiles,
} from '../../hooks/evaluation';
import { useModels } from '../../hooks/models';
import { useDocuments } from '../../hooks/documents';
import {
    useQuestionSets,
    useCreateQuestionSet,
    useUpdateQuestionSet,
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
    XCircle,
    FileText,
    CheckCircle2,
    CloudOff,
    Check,
} from 'lucide-react';
import type { EvalRun } from '../../schemas/evaluation';
import type { EvalQuestionInput } from '../../services/evaluation';
import { formatScore, formatLatency, formatUtcDate } from '../../lib/format';
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

function RunRow({
    run,
    onDelete,
    onCancel,
    isCancelling,
}: {
    run: EvalRun;
    onDelete: (id: number) => void;
    onCancel: (id: number) => void;
    isCancelling: boolean;
}) {
    const isActive = run.status === 'pending' || run.status === 'running';

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
                            ` -- ${formatUtcDate(run.created_at, 'date')}`}
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
            <div className="mr-3 flex items-center gap-1">
                {isActive && (
                    isCancelling ? (
                        <span className="flex items-center gap-1 rounded-lg border border-amber-300 bg-amber-50 px-2.5 py-1 text-xs font-medium text-amber-700 dark:border-amber-800 dark:bg-amber-950/30 dark:text-amber-300">
                            <Loader2 className="h-3.5 w-3.5 animate-spin" />
                            Cancelling...
                        </span>
                    ) : (
                        <button
                            onClick={(e) => {
                                e.stopPropagation();
                                if (window.confirm('Cancel this evaluation run?\n\nPartial results will appear once the current question finishes processing.')) {
                                    onCancel(run.id);
                                }
                            }}
                            className="flex items-center gap-1 rounded-lg border border-amber-300 bg-amber-50 px-2.5 py-1 text-xs font-medium text-amber-700 transition-colors hover:bg-amber-100 dark:border-amber-800 dark:bg-amber-950/30 dark:text-amber-300 dark:hover:bg-amber-950/50"
                        >
                            <XCircle className="h-3.5 w-3.5" />
                            Cancel
                        </button>
                    )
                )}
                <button
                    onClick={(e) => {
                        e.stopPropagation();
                        onDelete(run.id);
                    }}
                    className="rounded p-1.5 text-muted-foreground transition-colors hover:bg-destructive/10 hover:text-destructive"
                    title="Delete evaluation run"
                >
                    <Trash2 className="h-4 w-4" />
                </button>
            </div>
        </div>
    );
}

function formatTimeSince(date: Date): string {
    const seconds = Math.floor((Date.now() - date.getTime()) / 1000);
    if (seconds < 10) return 'Saved just now';
    if (seconds < 60) return `Saved ${seconds}s ago`;
    const minutes = Math.floor(seconds / 60);
    if (minutes < 60) return `Saved ${minutes}m ago`;
    return `Saved ${Math.floor(minutes / 60)}h ago`;
}

function SaveIndicator({ lastSavedAt, isSaving, hasError }: {
    lastSavedAt: Date | undefined;
    isSaving: boolean;
    hasError: boolean;
}) {
    if (hasError) {
        return (
            <span className="flex items-center gap-1 text-xs text-destructive">
                <CloudOff className="h-3 w-3" />
                Save failed
            </span>
        );
    }
    if (isSaving) {
        return (
            <span className="flex items-center gap-1 text-xs text-muted-foreground">
                <Loader2 className="h-3 w-3 animate-spin" />
                Saving...
            </span>
        );
    }
    if (lastSavedAt) {
        return (
            <span className="flex items-center gap-1 text-xs text-muted-foreground">
                <Check className="h-3 w-3 text-green-500" />
                {formatTimeSince(lastSavedAt)}
            </span>
        );
    }
    return null;
}

function NewEvalForm({
    onCreated,
    onCancel,
    initialQuestions,
    initialQuestionSetId,
}: {
    onCreated: () => void;
    onCancel: () => void;
    initialQuestions?: EvalQuestionInput[];
    initialQuestionSetId?: number;
}) {
    const { data: models } = useModels();
    const { data: questionSets } = useQuestionSets();
    const { data: profiles } = useProfiles();
    const createMutation = useCreateEvalRun();
    const synthesizeMutation = useSynthesizeQuestions();
    const createSetMutation = useCreateQuestionSet();
    const updateSetMutation = useUpdateQuestionSet();
    const deleteSetMutation = useDeleteQuestionSet();
    const [selectedModel, setSelectedModel] = useState('');
    const [selectedProfile, setSelectedProfile] = useState('');
    const [questions, setQuestions] = useState<EvalQuestionInput[]>(initialQuestions ?? []);
    const [warningMessage, setWarningMessage] = useState('');
    const [activeSetId, setActiveSetId] = useState<number | undefined>(initialQuestionSetId);
    const [activeSetName, setActiveSetName] = useState('');
    const [isEditingName, setIsEditingName] = useState(false);
    const [lastSavedAt, setLastSavedAt] = useState<Date | undefined>();
    const saveTimerRef = useRef<ReturnType<typeof setTimeout>>(undefined);
    const activeSetIdRef = useRef(activeSetId);

    useEffect(() => {
        activeSetIdRef.current = activeSetId;
    }, [activeSetId]);

    useEffect(() => {
        if (profiles && profiles.length > 0 && !selectedProfile) {
            setSelectedProfile(profiles[0].id);
        }
    }, [profiles, selectedProfile]);

    useEffect(() => {
        if (initialQuestionSetId && questionSets) {
            const set = questionSets.find((s) => s.id === initialQuestionSetId);
            if (set) setActiveSetName(set.name);
        }
    }, [initialQuestionSetId, questionSets]);

    useEffect(() => {
        return () => {
            if (saveTimerRef.current) clearTimeout(saveTimerRef.current);
        };
    }, []);

    const scheduleSave = useCallback((questionsToSave: EvalQuestionInput[]) => {
        if (saveTimerRef.current) clearTimeout(saveTimerRef.current);
        const validQuestions = questionsToSave.filter((q) => q.question.trim());
        if (validQuestions.length === 0) return;

        saveTimerRef.current = setTimeout(() => {
            const currentSetId = activeSetIdRef.current;
            if (currentSetId) {
                updateSetMutation.mutate(
                    { id: currentSetId, questions: validQuestions, profileId: selectedProfile || undefined },
                    { onSuccess: () => setLastSavedAt(new Date()) },
                );
            } else {
                const autoName = `Question Set - ${new Date().toLocaleString()}`;
                createSetMutation.mutate(
                    { name: autoName, questions: validQuestions, profileId: selectedProfile || undefined },
                    {
                        onSuccess: (data) => {
                            setActiveSetId(data.id);
                            setActiveSetName(data.name);
                            setLastSavedAt(new Date());
                        },
                    },
                );
            }
        }, 1500);
    }, [selectedProfile, updateSetMutation, createSetMutation]);

    const updateQuestions = useCallback((newQuestions: EvalQuestionInput[]) => {
        setQuestions(newQuestions);
        scheduleSave(newQuestions);
    }, [scheduleSave]);

    const addQuestion = () => {
        setQuestions([...questions, { question: '', expected_answer: '' }]);
    };

    const removeQuestion = (index: number) => {
        const newQuestions = questions.filter((_, i) => i !== index);
        updateQuestions(newQuestions);
    };

    const handleSelectSet = (setId: string) => {
        if (saveTimerRef.current) clearTimeout(saveTimerRef.current);
        if (setId === '') {
            setActiveSetId(undefined);
            setActiveSetName('');
            setQuestions([]);
            setLastSavedAt(undefined);
        } else {
            const set = questionSets?.find((s) => s.id === Number(setId));
            if (set) {
                setQuestions(set.questions.map((q) => ({
                    question: q.question,
                    expected_answer: q.expected_answer,
                    truth: q.truth ?? undefined,
                })));
                setActiveSetId(set.id);
                setActiveSetName(set.name);
                setLastSavedAt(set.updated_at ? new Date(set.updated_at) : undefined);
            }
        }
    };

    const handleRenameSave = () => {
        setIsEditingName(false);
        if (activeSetId && activeSetName.trim()) {
            updateSetMutation.mutate(
                { id: activeSetId, name: activeSetName.trim() },
                { onSuccess: () => setLastSavedAt(new Date()) },
            );
        }
    };

    const handleDeleteActiveSet = () => {
        if (!activeSetId) return;
        if (window.confirm(`Delete question set "${activeSetName}"? This will also delete all evaluation runs linked to this set.`)) {
            deleteSetMutation.mutate(activeSetId, {
                onSuccess: () => {
                    setActiveSetId(undefined);
                    setActiveSetName('');
                    setQuestions([]);
                    setLastSavedAt(undefined);
                },
            });
        }
    };

    const handleSynthesize = () => {
        synthesizeMutation.mutate(
            { maxQuestions: 3 },
            {
                onSuccess: (data) => {
                    const generated: EvalQuestionInput[] = data.questions.map((q) => ({
                        question: q.question,
                        expected_answer: q.expected_answer,
                        truth: q.truth ?? undefined,
                    }));
                    const unique = generated.filter(
                        (g) => !questions.some((q) => q.question === g.question),
                    );
                    if (unique.length > 0) {
                        const merged = [...questions, ...unique];
                        updateQuestions(merged);
                    }
                },
            },
        );
    };

    const handleSubmit = () => {
        if (saveTimerRef.current) clearTimeout(saveTimerRef.current);
        const validQuestions = questions.filter((q) => q.question.trim());
        if (!selectedModel || validQuestions.length === 0) return;

        const doSubmit = (questionSetId: number | undefined) => {
            createMutation.mutate(
                { modelName: selectedModel, questions: validQuestions, questionSetId, profileId: selectedProfile || undefined },
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

        if (activeSetId) {
            updateSetMutation.mutate(
                { id: activeSetId, questions: validQuestions, profileId: selectedProfile || undefined },
                { onSuccess: () => doSubmit(activeSetId) },
            );
        } else if (validQuestions.length > 0) {
            const autoName = `Question Set - ${new Date().toLocaleString()}`;
            createSetMutation.mutate(
                { name: autoName, questions: validQuestions, profileId: selectedProfile || undefined },
                {
                    onSuccess: (data) => {
                        setActiveSetId(data.id);
                        doSubmit(data.id);
                    },
                },
            );
        } else {
            doSubmit(undefined);
        }
    };

    const validQuestionCount = questions.filter((q) => q.question.trim()).length;
    const isSaving = createSetMutation.isPending || updateSetMutation.isPending;
    const saveHasError = createSetMutation.isError || updateSetMutation.isError;

    return (
        <div className="rounded-xl border bg-card p-6">
            <h3 className="mb-6 text-lg font-semibold">Run New Evaluation</h3>

            {/* Step 1 -- Setup */}
            <div className="mb-6">
                <div className="mb-4 flex items-center gap-2">
                    <span className="flex h-6 w-6 items-center justify-center rounded-full bg-blue-600 text-xs font-bold text-white">1</span>
                    <h4 className="text-sm font-semibold">Step 1 -- Setup</h4>
                </div>

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

                {profiles && profiles.length > 0 && (
                    <div>
                        <label className="mb-1.5 block text-xs font-medium text-muted-foreground">
                            Evaluation Profile
                        </label>
                        <select
                            value={selectedProfile}
                            onChange={(e) => setSelectedProfile(e.target.value)}
                            className="w-full rounded-lg border bg-background px-3 py-2 text-sm"
                        >
                            <option value="">No profile (raw metric comparison)</option>
                            {profiles.map((p) => (
                                <option key={p.id} value={p.id}>
                                    {p.id} -- {p.description || p.domain}
                                </option>
                            ))}
                        </select>
                        <p className="mt-1 text-xs text-muted-foreground">
                            Profiles define pass/fail thresholds and disqualification gates for comparison verdicts.
                        </p>
                    </div>
                )}
            </div>

            <div className="mb-6 border-t-2 border-blue-600/20" />

            {/* Step 2 -- Questions */}
            <div className="mb-6">
                <div className="mb-4 flex items-center gap-2">
                    <span className="flex h-6 w-6 items-center justify-center rounded-full bg-blue-600 text-xs font-bold text-white">2</span>
                    <h4 className="text-sm font-semibold">Step 2 -- Questions ({validQuestionCount})</h4>
                </div>

                {/* Question Set Selector */}
                <div className="mb-4 rounded-lg border bg-muted/30 p-4">
                    <label className="mb-1.5 block text-xs font-medium text-muted-foreground">
                        Question Set
                    </label>
                    <select
                        value={activeSetId ?? ''}
                        onChange={(e) => handleSelectSet(e.target.value)}
                        className="w-full rounded-lg border bg-background px-3 py-2 text-sm"
                    >
                        <option value="">New question set</option>
                        {questionSets?.map((s) => (
                            <option key={s.id} value={s.id}>
                                {s.name} ({s.questions.length}q)
                            </option>
                        ))}
                    </select>

                    {activeSetId && (
                        <div className="mt-2 flex items-center gap-2">
                            {isEditingName ? (
                                <input
                                    type="text"
                                    value={activeSetName}
                                    onChange={(e) => setActiveSetName(e.target.value)}
                                    onBlur={handleRenameSave}
                                    onKeyDown={(e) => { if (e.key === 'Enter') handleRenameSave(); }}
                                    className="flex-1 rounded border bg-background px-2 py-1 text-sm outline-none focus:border-primary/50"
                                    autoFocus
                                />
                            ) : (
                                <button
                                    onClick={() => setIsEditingName(true)}
                                    className="flex-1 truncate rounded px-2 py-1 text-left text-sm text-foreground transition-colors hover:bg-accent"
                                    title="Click to rename"
                                >
                                    {activeSetName}
                                </button>
                            )}
                            <SaveIndicator
                                lastSavedAt={lastSavedAt}
                                isSaving={isSaving}
                                hasError={saveHasError}
                            />
                            <button
                                onClick={handleDeleteActiveSet}
                                className="rounded p-1 text-muted-foreground transition-colors hover:bg-destructive/10 hover:text-destructive"
                                title="Delete question set"
                            >
                                <Trash2 className="h-3.5 w-3.5" />
                            </button>
                        </div>
                    )}
                </div>

                <div className="space-y-4">
                    {questions.map((q, i) => (
                        <div key={i} className="rounded-lg border bg-background p-4">
                            <div className="mb-2 flex items-center justify-between">
                                <span className="text-xs font-medium text-muted-foreground">
                                    Question {i + 1}
                                </span>
                                <button
                                    onClick={() => removeQuestion(i)}
                                    className="shrink-0 text-muted-foreground transition-colors hover:text-destructive"
                                    title="Remove question"
                                >
                                    <Trash2 className="h-3.5 w-3.5" />
                                </button>
                            </div>
                            <input
                                type="text"
                                value={q.question}
                                onChange={(e) => {
                                    const updated = [...questions];
                                    updated[i] = { ...updated[i], question: e.target.value };
                                    setQuestions(updated);
                                    scheduleSave(updated);
                                }}
                                className="mb-3 w-full rounded-lg border bg-background px-3 py-2 text-sm outline-none focus:border-primary/50"
                                placeholder="Enter your question"
                            />
                            <div className="flex items-center justify-between">
                                <label className="text-xs font-medium text-muted-foreground">
                                    Expected Answer
                                </label>
                                {q.expected_answer !== undefined && q.expected_answer !== '' && (
                                    <button
                                        onClick={() => {
                                            const updated = [...questions];
                                            updated[i] = { ...updated[i], expected_answer: '' };
                                            updateQuestions(updated);
                                        }}
                                        className="text-xs text-muted-foreground transition-colors hover:text-destructive"
                                    >
                                        Remove
                                    </button>
                                )}
                            </div>
                            <textarea
                                value={q.expected_answer ?? ''}
                                onChange={(e) => {
                                    const updated = [...questions];
                                    updated[i] = { ...updated[i], expected_answer: e.target.value || null };
                                    setQuestions(updated);
                                    scheduleSave(updated);
                                }}
                                placeholder="Used to evaluate correctness and completeness"
                                className="mt-1.5 w-full resize-none rounded-lg border bg-background px-3 py-2 text-sm text-muted-foreground outline-none focus:border-primary/50"
                                rows={2}
                            />
                        </div>
                    ))}
                </div>

                <div className="mt-3 flex items-center gap-3">
                    <button
                        onClick={addQuestion}
                        className="flex items-center gap-1 text-sm text-muted-foreground transition-colors hover:text-foreground"
                    >
                        <Plus className="h-3.5 w-3.5" />
                        Add Question
                    </button>
                    <button
                        onClick={handleSynthesize}
                        disabled={synthesizeMutation.isPending}
                        className="flex items-center gap-1 text-sm text-muted-foreground transition-colors hover:text-foreground disabled:opacity-50"
                    >
                        {synthesizeMutation.isPending ? (
                            <Loader2 className="h-3.5 w-3.5 animate-spin" />
                        ) : (
                            <Sparkles className="h-3.5 w-3.5" />
                        )}
                        Generate Questions
                    </button>
                </div>
            </div>

            <div className="mb-6 border-t-2 border-blue-600/20" />

            {/* Step 3 -- Run */}
            <div>
                <div className="mb-3 flex items-center gap-2">
                    <span className="flex h-6 w-6 items-center justify-center rounded-full bg-blue-600 text-xs font-bold text-white">3</span>
                    <h4 className="text-sm font-semibold">Step 3 -- Run</h4>
                </div>
                <div className="flex items-center gap-2">
                    <button
                        onClick={handleSubmit}
                        disabled={!selectedModel || validQuestionCount === 0 || createMutation.isPending}
                        className="flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2.5 text-sm font-medium text-white transition-colors hover:bg-blue-700 disabled:opacity-50"
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
                        className="rounded-lg border bg-background px-4 py-2.5 text-sm text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
                    >
                        Cancel
                    </button>
                </div>
            </div>

            {synthesizeMutation.error && (
                <p className="mt-4 text-sm text-destructive">{synthesizeMutation.error.message}</p>
            )}

            {createMutation.error && (
                <p className="mt-4 text-sm text-destructive">{createMutation.error.message}</p>
            )}

            {warningMessage && (
                <div className="mt-4 flex items-center gap-2 rounded-lg border border-amber-200 bg-amber-50 p-3 dark:border-amber-900 dark:bg-amber-950/20">
                    <AlertTriangle className="h-4 w-4 shrink-0 text-amber-600 dark:text-amber-400" />
                    <p className="text-xs text-amber-700 dark:text-amber-300">{warningMessage}</p>
                </div>
            )}
        </div>
    );
}

interface WorkflowStep {
    label: string;
    done: boolean;
    action?: { label: string; to: string };
}

function WorkflowBanner({
    steps,
    nextAction,
}: {
    steps: WorkflowStep[];
    nextAction: { label: string; onClick: () => void } | null;
}) {
    return (
        <div className="mb-6 rounded-xl border bg-card p-4">
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-6">
                    {steps.map((step, i) => (
                        <div key={i} className="flex items-center gap-2">
                            {step.done ? (
                                <CheckCircle2 className="h-4 w-4 text-emerald-500" />
                            ) : (
                                <div className="flex h-4 w-4 items-center justify-center rounded-full border-2 border-muted-foreground/30 text-[9px] font-bold text-muted-foreground/50">
                                    {i + 1}
                                </div>
                            )}
                            {step.action && !step.done ? (
                                <Link
                                    to={step.action.to}
                                    className="text-sm font-medium text-primary hover:underline"
                                >
                                    {step.label}
                                </Link>
                            ) : (
                                <span
                                    className={`text-sm ${step.done ? 'text-muted-foreground' : 'font-medium'}`}
                                >
                                    {step.label}
                                </span>
                            )}
                            {i < steps.length - 1 && (
                                <ArrowRight className="ml-4 h-3 w-3 text-muted-foreground/40" />
                            )}
                        </div>
                    ))}
                </div>
                {nextAction && (
                    <button
                        onClick={nextAction.onClick}
                        className="flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90"
                    >
                        {nextAction.label}
                    </button>
                )}
            </div>
        </div>
    );
}

function EvaluationsPage() {
    const navigate = useNavigate();
    const { data: runs, isLoading, error, refetch } = useEvalRuns();
    const { data: documents } = useDocuments();
    const cancelMutation = useCancelEvalRun();
    const deleteMutation = useDeleteEvalRun();
    const [showForm, setShowForm] = useState(false);
    const [preloadedQuestions, setPreloadedQuestions] = useState<EvalQuestionInput[] | undefined>();
    const [preloadedSetId, setPreloadedSetId] = useState<number | undefined>();
    const [cancellingIds, setCancellingIds] = useState<Set<number>>(new Set());

    const readyDocs = documents?.filter((d) => d.status === 'ready') ?? [];
    const hasDocuments = readyDocs.length > 0;
    const completedRuns =
        runs?.filter((r) => r.status === 'completed' || r.status === 'complete') ?? [];
    const hasRuns = (runs?.length ?? 0) > 0;


    // Workflow steps
    const steps: WorkflowStep[] = [
        {
            label: hasDocuments ? `${readyDocs.length} document${readyDocs.length !== 1 ? 's' : ''} indexed` : 'Upload documents',
            done: hasDocuments,
            action: !hasDocuments ? { label: 'Upload documents', to: '/documents' } : undefined,
        },
        {
            label: completedRuns.length >= 1
                ? `${completedRuns.length} evaluation${completedRuns.length !== 1 ? 's' : ''} completed`
                : 'Run evaluations',
            done: completedRuns.length >= 2,
        },
        {
            label: 'Compare models',
            done: false,
        },
    ];

    // Determine the next action based on workflow state
    let nextAction: { label: string; onClick: () => void } | null = null;
    if (!hasDocuments) {
        nextAction = { label: 'Upload Documents', onClick: () => navigate({ to: '/documents' }) };
    } else if (completedRuns.length < 2) {
        nextAction = {
            label: completedRuns.length === 0 ? 'Run First Evaluation' : 'Run Another Model',
            onClick: () => {
                setPreloadedQuestions(undefined);
                setPreloadedSetId(undefined);
                setShowForm(true);
            },
        };
    } else {
        nextAction = {
            label: 'Compare Evaluations',
            onClick: () =>
                navigate({
                    to: '/evaluations/compare',
                    search: { run_a: 0, run_b: 0 },
                }),
        };
    }

    return (
        <div className="p-4 sm:p-6 lg:p-8">
            <div className="mx-auto max-w-5xl">
                <div className="mb-6 flex items-center justify-between">
                    <div>
                        <h1 className="text-2xl font-bold tracking-tight">Evaluations</h1>
                        <p className="text-sm text-muted-foreground">
                            Upload documents, run evaluations on different models, then compare results.
                        </p>
                    </div>
                    {hasDocuments && (
                        <button
                            onClick={() => {
                                setPreloadedQuestions(undefined);
                                setPreloadedSetId(undefined);
                                setShowForm(true);
                            }}
                            className="flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90"
                        >
                            <Plus className="h-4 w-4" />
                            New Evaluation
                        </button>
                    )}
                </div>

                {/* Workflow progress banner */}
                <WorkflowBanner steps={steps} nextAction={!showForm ? nextAction : null} />

                {/* New evaluation form */}
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

                {/* Empty state - no documents */}
                {!hasDocuments && !isLoading && (
                    <div className="rounded-xl border bg-card p-8 text-center">
                        <FileText className="mx-auto mb-3 h-8 w-8 text-muted-foreground" />
                        <h2 className="mb-1 text-base font-semibold">Upload documents first</h2>
                        <p className="text-sm text-muted-foreground">
                            The evaluation pipeline needs documents to retrieve context from.
                            Upload PDFs to build your knowledge base, then come back to run evaluations.
                        </p>
                        <Link
                            to="/documents"
                            className="mt-4 inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90"
                        >
                            <FileText className="h-4 w-4" />
                            Go to Documents
                        </Link>
                    </div>
                )}

                {/* Empty state - has documents but no runs */}
                {hasDocuments && !hasRuns && !showForm && !isLoading && (
                    <div className="rounded-xl border bg-card p-8 text-center">
                        <BarChart3 className="mx-auto mb-3 h-8 w-8 text-muted-foreground" />
                        <h2 className="mb-1 text-base font-semibold">No evaluations yet</h2>
                        <p className="text-sm text-muted-foreground">
                            Run your first evaluation to see how a model performs on your documents.
                            You can generate questions automatically or write your own.
                        </p>
                        <button
                            onClick={() => {
                                setPreloadedQuestions(undefined);
                                setPreloadedSetId(undefined);
                                setShowForm(true);
                            }}
                            className="mt-4 inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90"
                        >
                            <Plus className="h-4 w-4" />
                            Run First Evaluation
                        </button>
                    </div>
                )}

                {/* Run list */}
                {hasRuns && (
                    <div>
                        <div className="mb-3 flex items-center justify-between">
                            <h2 className="text-lg font-semibold">
                                Evaluation Runs ({runs?.length ?? 0})
                            </h2>
                            <div className="flex items-center gap-4 text-xs text-muted-foreground">
                                <span>Faith.</span>
                                <span>Relev.</span>
                                <span>Latency</span>
                            </div>
                        </div>
                        <div className="space-y-2">
                            {runs?.map((run) => (
                                <RunRow
                                    key={run.id}
                                    run={run}
                                    isCancelling={cancellingIds.has(run.id)}
                                    onCancel={(id) => {
                                        setCancellingIds((prev) => new Set(prev).add(id));
                                        cancelMutation.mutate(id);
                                    }}
                                    onDelete={(id) => deleteMutation.mutate(id)}
                                />
                            ))}
                        </div>
                    </div>
                )}

                {isLoading && (
                    <p className="text-sm text-muted-foreground">Loading evaluations...</p>
                )}
                {error && <p className="text-sm text-destructive">{error.message}</p>}

            </div>
        </div>
    );
}
