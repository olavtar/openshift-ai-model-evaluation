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

export function formatUtcDate(val: string | null | undefined, style: 'date' | 'datetime' = 'datetime'): string {
    if (!val) return '';
    // API returns UTC timestamps without timezone suffix; append Z so
    // the browser interprets them correctly in the user's local timezone.
    const iso = val.endsWith('Z') || val.includes('+') ? val : val + 'Z';
    const d = new Date(iso);
    return style === 'date' ? d.toLocaleDateString() : d.toLocaleString();
}
