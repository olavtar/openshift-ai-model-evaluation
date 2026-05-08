// This project was developed with assistance from AI tools.

import { createFileRoute } from '@tanstack/react-router';
import { OverviewPanel } from '../components/dashboard/overview-panel';
import { ChatPanel } from '../components/chat-panel/chat-panel';

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export const Route = createFileRoute('/' as any)({
    component: Index,
});

function Index() {
    return (
        <div className="grid h-[calc(100vh-128px)] grid-cols-1 lg:grid-cols-2">
            <div className="border-r overflow-y-auto">
                <OverviewPanel />
            </div>
            <div className="min-h-0">
                <ChatPanel />
            </div>
        </div>
    );
}
