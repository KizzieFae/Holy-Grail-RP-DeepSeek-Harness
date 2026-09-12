/**
 * Bounded worker pool for independent async tasks (#165).
 * Preserves result order by logical index regardless of completion order.
 */

/**
 * @template T,R
 * @param {readonly T[]} items
 * @param {number} limit
 * @param {(item: T, index: number) => Promise<R>} worker
 * @returns {Promise<R[]>}
 */
export async function runBoundedConcurrency(items, limit, worker) {
  if (!Array.isArray(items) || items.length === 0) {
    return [];
  }
  const boundedLimit = Math.max(1, Math.min(Math.floor(limit), items.length));
  const results = new Array(items.length);
  const errors = new Array(items.length);
  let nextIndex = 0;

  async function runSlot() {
    while (true) {
      const index = nextIndex;
      nextIndex += 1;
      if (index >= items.length) {
        return;
      }
      try {
        results[index] = await worker(items[index], index);
      } catch (error) {
        errors[index] = error;
      }
    }
  }

  await Promise.all(Array.from({ length: boundedLimit }, () => runSlot()));
  const firstErrorIndex = errors.findIndex((error) => error !== undefined);
  if (firstErrorIndex >= 0) {
    throw errors[firstErrorIndex];
  }
  return results;
}
