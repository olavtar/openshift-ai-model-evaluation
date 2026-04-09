import { Link } from '@tanstack/react-router';
import { Logo } from '../logo/logo';
import { ModeToggle } from '../mode-toggle/mode-toggle';

export function Header() {
  return (
    <header className="sticky top-0 z-20 border-b bg-background/80 backdrop-blur">
      <div className="container mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
        <Link to="/" className="flex items-center gap-2">
          <Logo />
          <span className="font-bold">AI Model Evaluation</span>
        </Link>
        <nav className="flex items-center gap-6">
          <Link to="/" className="text-sm font-medium text-muted-foreground transition-colors hover:text-foreground">
            Dashboard
          </Link>
          <Link to="/evaluations" className="text-sm font-medium text-muted-foreground transition-colors hover:text-foreground">
            Evaluations
          </Link>
          <Link to="/evaluations/compare" search={{ run_a: 0, run_b: 0 }} className="text-sm font-medium text-muted-foreground transition-colors hover:text-foreground">
            Comparisons
          </Link>
<Link to="/documents" className="text-sm font-medium text-muted-foreground transition-colors hover:text-foreground">
            Documents
          </Link>
          <ModeToggle />
        </nav>
      </div>
    </header>
  );
}
