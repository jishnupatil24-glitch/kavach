import { Link } from 'react-router-dom';

export function NotFound() {
  return (
    <div className="mx-auto max-w-md py-24 text-center">
      <p className="font-display text-4xl font-semibold text-ink">Not found</p>
      <p className="mt-2 text-body">That page doesn't exist.</p>
      <Link
        to="/"
        className="mt-6 inline-flex min-h-[44px] items-center rounded bg-brand-700 px-4 font-sans font-medium text-white"
      >
        Back to runs
      </Link>
    </div>
  );
}
