import Link from "next/link";

function NotFound() {
  return (
    <div
      className="mx-auto max-w-lg rounded-lg border border-border bg-bg-panel p-8 text-center"
      role="alert"
    >
      <p className="text-sm font-medium text-accent">404</p>

      <h2 className="mt-2 text-2xl font-semibold text-zinc-100">
        Page not found
      </h2>

      <p className="mt-2 text-sm text-muted">
        The page you were looking for doesn't exist or may have been moved.
      </p>

      <nav
        className="mt-6 flex flex-wrap justify-center gap-3"
        aria-label="Helpful navigation"
      >
        <Link
          href="/"
          className="rounded bg-accent px-4 py-2 text-sm font-medium text-white hover:opacity-90"
        >
          Back to Overview
        </Link>

        <Link
          href="/candidates"
          className="rounded border border-border px-4 py-2 text-sm font-medium text-zinc-100 hover:bg-bg-panel"
        >
          Candidates
        </Link>

        <Link
          href="/interview"
          className="rounded border border-border px-4 py-2 text-sm font-medium text-zinc-100 hover:bg-bg-panel"
        >
          Interview
        </Link>

        <Link
          href="/analytics"
          className="rounded border border-border px-4 py-2 text-sm font-medium text-zinc-100 hover:bg-bg-panel"
        >
          Analytics
        </Link>
      </nav>
    </div>
  );
}

export default NotFound;
