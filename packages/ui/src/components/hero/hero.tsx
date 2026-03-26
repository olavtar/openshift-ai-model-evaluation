export function Hero() {
  return (
    <section className="relative overflow-hidden rounded-2xl border bg-card p-6 shadow-sm sm:p-8">
      <div
        aria-hidden
        className="pointer-events-none absolute -inset-x-4 -top-16 bottom-0 opacity-60 [mask-image:radial-gradient(60%_60%_at_30%_0%,black,transparent)] dark:opacity-70"
      >
        <div className="mx-auto h-full max-w-6xl bg-gradient-to-tr from-sky-500/10 via-violet-500/10 to-fuchsia-500/10 blur-2xl" />
      </div>
      <div className="relative z-10 flex flex-col gap-3">
        <h1 className="text-3xl font-bold tracking-tight text-foreground sm:text-4xl">
          Welcome to AI Model Evaluation
        </h1>
        <p className="max-w-2xl text-sm leading-6 text-muted-foreground">
          Compare AI model performance using standardized evaluation metrics. Upload your documents, select models, and run evaluations to find the best fit for your use case.
        </p>
      </div>
    </section>
  );
}