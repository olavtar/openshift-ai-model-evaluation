// This project was developed with assistance from AI tools.

export function formatScore(val: number | null | undefined): string {
    if (val == null) return '--';
    return (val * 100).toFixed(0) + '%';
}

export function formatLatency(val: number | null | undefined): string {
    if (val == null) return '--';
    return val.toFixed(0) + 'ms';
}

export function formatMetricValue(metric: string, val: number | null | undefined): string {
    if (val == null) return '--';
    if (metric === 'latency_ms') return val.toFixed(0) + 'ms';
    return (val * 100).toFixed(0) + '%';
}
