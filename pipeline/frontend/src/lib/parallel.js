/**
 * Run async tasks with limited concurrency, preserving input order in the
 * returned array. `onProgress(i, result|error)` is called after each task
 * completes so the UI can update progressively.
 */
export async function runInParallel(tasks, concurrency = 3, onProgress) {
  const results = new Array(tasks.length);
  let next = 0;
  const worker = async () => {
    while (true) {
      const idx = next++;
      if (idx >= tasks.length) return;
      try {
        const value = await tasks[idx]();
        results[idx] = { status: "done", value };
        onProgress && onProgress(idx, { status: "done", value });
      } catch (error) {
        results[idx] = { status: "error", error };
        onProgress && onProgress(idx, { status: "error", error });
      }
    }
  };
  await Promise.all(
    Array.from({ length: Math.max(1, Math.min(concurrency, tasks.length)) }, worker),
  );
  return results;
}
