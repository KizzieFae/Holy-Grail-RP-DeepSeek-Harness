/**
 * Issue #201 LH-0 — two-clock contract (fixture vs runtime/continuity).
 *
 * Fixture clock: authored LH-0 predicates, deferral, projection eligibility, lifecycle.
 * Runtime clock: authoritative round/continuity identity for domain manifest binding.
 */
export const LH0_CLOCK_SCHEMA = 'issue201_lh0_two_clock_v1';

export function resolveLh0TransportClocks({
  fixtureTurnIndex = null,
  bindingTurnIndex = null,
  turnIndex = null,
}) {
  const fixtureClock = Number(fixtureTurnIndex ?? turnIndex ?? 0);
  const runtimeBindingClock = Number(bindingTurnIndex ?? fixtureClock);
  return {
    schema: LH0_CLOCK_SCHEMA,
    fixture_turn_index: fixtureClock,
    runtime_binding_turn_index: runtimeBindingClock,
  };
}

export function attachLh0ClockForensics(target, clocks) {
  return {
    ...target,
    lh0_clocks: clocks,
    fixture_turn_index: clocks.fixture_turn_index,
    runtime_binding_turn_index: clocks.runtime_binding_turn_index,
  };
}
