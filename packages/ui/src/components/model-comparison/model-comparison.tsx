// This project was developed with assistance from AI tools.

import { useState } from 'react';
import { ModelSelector } from '../model-selector/model-selector';
import { useModelStatus } from '../../hooks/models';
import { GitCompareArrows } from 'lucide-react';
import type { Model } from '../../schemas/models';

const STATUS_COLOR: Record<string, string> = {
    available: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-300',
    unavailable: 'bg-rose-100 text-rose-700 dark:bg-rose-950/40 dark:text-rose-300',
};

function ModelStatusBadge({ modelId }: { modelId: number | null }) {
    const { data: status, isLoading } = useModelStatus(modelId ?? 0);

    if (!modelId) return null;
    if (isLoading) return <span className="text-xs text-muted-foreground">Checking...</span>;

    const color = STATUS_COLOR[status?.status ?? ''] ?? STATUS_COLOR.unavailable;

    return (
        <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-medium ${color}`}>
            {status?.status ?? 'unknown'}
        </span>
    );
}

export function ModelComparison() {
    const [modelA, setModelA] = useState<Model | null>(null);
    const [modelB, setModelB] = useState<Model | null>(null);

    return (
        <div className="rounded-xl border bg-card p-4">
            <div className="mb-4 flex items-center gap-2">
                <GitCompareArrows className="h-5 w-5" />
                <h2 className="text-lg font-semibold">Model Comparison</h2>
            </div>
            <p className="mb-4 text-sm text-muted-foreground">
                Select two models to compare their evaluation results side by side.
            </p>

            <div className="grid gap-4 sm:grid-cols-2">
                <div className="space-y-2">
                    <ModelSelector
                        selectedModelId={modelA?.id ?? null}
                        onSelect={setModelA}
                        label="Model A"
                    />
                    {modelA && (
                        <div className="flex items-center gap-2 rounded-lg bg-muted/50 px-3 py-2">
                            <div className="flex-1">
                                <p className="text-xs font-medium">{modelA.name}</p>
                                <p className="text-[10px] text-muted-foreground">{modelA.deployment_mode}</p>
                            </div>
                            <ModelStatusBadge modelId={modelA.id} />
                        </div>
                    )}
                </div>

                <div className="space-y-2">
                    <ModelSelector
                        selectedModelId={modelB?.id ?? null}
                        onSelect={setModelB}
                        label="Model B"
                    />
                    {modelB && (
                        <div className="flex items-center gap-2 rounded-lg bg-muted/50 px-3 py-2">
                            <div className="flex-1">
                                <p className="text-xs font-medium">{modelB.name}</p>
                                <p className="text-[10px] text-muted-foreground">{modelB.deployment_mode}</p>
                            </div>
                            <ModelStatusBadge modelId={modelB.id} />
                        </div>
                    )}
                </div>
            </div>

            {modelA && modelB && (
                <div className="mt-4 rounded-lg border border-dashed p-4 text-center text-sm text-muted-foreground">
                    Evaluation comparison will appear here once benchmarks are configured.
                </div>
            )}
        </div>
    );
}
