import { Link } from '@tanstack/react-router';
import { Logo } from '../logo/logo';
import { ModeToggle } from '../mode-toggle/mode-toggle';

const activeProps = {
    className:
        'text-sm font-medium rounded-full bg-blue-100 text-blue-700 px-3 py-1.5 dark:bg-blue-900/40 dark:text-blue-300',
};
const inactiveProps = {
    className:
        'text-sm font-medium text-muted-foreground transition-colors hover:text-foreground px-3 py-1.5',
};

export function Header() {
    return (
        <header className="sticky top-0 z-20 border-b bg-background/80 backdrop-blur">
            <div className="container mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
                <Link to="/" className="flex items-center gap-2">
                    <Logo />
                    <span className="font-bold">AI Model Evaluation</span>
                </Link>
                <nav className="flex items-center gap-1">
                    <Link
                        to="/"
                        activeOptions={{ exact: true }}
                        activeProps={activeProps}
                        inactiveProps={inactiveProps}
                    >
                        Dashboard
                    </Link>
                    <Link
                        to="/evaluations"
                        activeOptions={{ exact: true }}
                        activeProps={activeProps}
                        inactiveProps={inactiveProps}
                    >
                        Evaluations
                    </Link>
                    <Link
                        to="/evaluations/compare"
                        search={{ run_a: 0, run_b: 0 }}
                        activeProps={activeProps}
                        inactiveProps={inactiveProps}
                    >
                        Comparisons
                    </Link>
                    <Link
                        to="/documents"
                        activeProps={activeProps}
                        inactiveProps={inactiveProps}
                    >
                        Documents
                    </Link>
                    <div className="ml-4">
                        <ModeToggle />
                    </div>
                </nav>
            </div>
        </header>
    );
}
