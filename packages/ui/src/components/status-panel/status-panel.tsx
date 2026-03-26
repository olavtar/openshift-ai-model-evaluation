import { ServiceList } from "../service-list/service-list";

export function StatusPanel() {
  return (
    <div>
      <div className="mb-4">
        <h2 className="text-2xl font-semibold tracking-tight">Services</h2>
        <p className="text-sm text-muted-foreground">
          Explore each package to get started
        </p>
      </div>
      <ServiceList />
    </div>
  );
}