// This project was developed with assistance from AI tools.

import { createFileRoute } from '@tanstack/react-router';
import { Hero } from '../components/hero/hero';
import { useHealth } from '../hooks/health';
import { Monitor, Server, Database } from 'lucide-react';
import { ServiceList } from '../components/service-list/service-list';
import { ModelComparison } from '../components/model-comparison/model-comparison';

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export const Route = createFileRoute('/' as any)({
    component: Index,
});

const STATUS_BADGE: Record<string, { label: string; classes: string }> = {
    healthy: { label: 'Healthy', classes: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-300' },
    unhealthy: { label: 'Unhealthy', classes: 'bg-rose-100 text-rose-700 dark:bg-rose-950/40 dark:text-rose-300' },
    unknown: { label: 'Unknown', classes: 'bg-slate-100 text-slate-700 dark:bg-slate-900/60 dark:text-slate-300' },
};

function Index() {
    const { data: readiness, isLoading, error } = useHealth();

    const depStatus = (key: string) => readiness?.dependencies?.[key] ?? 'unknown';

    const overallStatus = readiness?.status ?? 'unknown';
    const overallLabel =
    overallStatus === 'ready' ? 'All Systems Operational'
        : overallStatus === 'degraded' ? 'Degraded'
            : overallStatus === 'not_ready' ? 'Not Ready'
                : 'Checking...';

    const deps = [
        { key: 'database', label: 'Database', icon: <Database className="h-4 w-4" /> },
        { key: 'model_a', label: 'Model A', icon: <Server className="h-4 w-4" /> },
        { key: 'model_b', label: 'Model B', icon: <Server className="h-4 w-4" /> },
    ];

    return (
        <div className="p-4 sm:p-6 lg:p-8">
            <div className="mx-auto max-w-7xl">
                <Hero />

                {/* Overall status */}
                <div className="mt-6 rounded-xl border bg-card p-4">
                    <div className="flex items-center gap-2 mb-4">
                        <Monitor className="h-5 w-5" />
                        <h2 className="text-lg font-semibold">System Health</h2>
                        {!isLoading && (
                            <span className={`ml-auto inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${
                                overallStatus === 'ready' ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-300'
                                    : overallStatus === 'degraded' ? 'bg-amber-100 text-amber-700 dark:bg-amber-950/40 dark:text-amber-300'
                                        : 'bg-rose-100 text-rose-700 dark:bg-rose-950/40 dark:text-rose-300'
                            }`}>
                                {overallLabel}
                            </span>
                        )}
                    </div>

                    {isLoading && <p className="text-sm text-muted-foreground">Checking services...</p>}
                    {error && <p className="text-sm text-destructive">Failed to fetch health: {error.message}</p>}

                    {readiness && (
                        <div className="grid gap-3 sm:grid-cols-3">
                            {deps.map(({ key, label, icon }) => {
                                const st = depStatus(key);
                                const badge = STATUS_BADGE[st] ?? STATUS_BADGE.unknown;
                                return (
                                    <div key={key} className="flex items-center gap-3 rounded-lg border p-3">
                                        <div className="grid h-8 w-8 place-items-center rounded bg-muted">{icon}</div>
                                        <div className="flex flex-col">
                                            <span className="text-sm font-medium">{label}</span>
                                            <span className={`inline-flex w-fit items-center rounded-full px-2 py-0.5 text-[10px] font-medium ${badge.classes}`}>
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

                <div className="mt-6">
                    <ModelComparison />
                </div>

                <div className="mt-6">
                    <div className="mb-4">
                        <h2 className="text-2xl font-semibold tracking-tight">Services</h2>
                        <p className="text-sm text-muted-foreground">Explore each package to get started</p>
                    </div>
                    <ServiceList />
                </div>
            </div>
        </div>
    );
}
