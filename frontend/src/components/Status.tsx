import type { AsyncState } from "../useAsync";

interface Props<T> {
  state: AsyncState<T>;
  children: (data: T) => React.ReactNode;
}

/** Renders loading and error states so each view only deals with the happy path. */
export function Status<T>({ state, children }: Props<T>) {
  if (state.status === "loading") return <div className="status" role="status">Loading data...</div>;
  if (state.status === "error") {
    return (
      <div className="status status-error" role="alert">
        Could not load data. {state.message}
      </div>
    );
  }
  return <>{children(state.data)}</>;
}
