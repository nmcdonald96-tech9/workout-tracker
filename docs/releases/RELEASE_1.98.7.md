# IronCycle 1.98.7

## Weight-derived baseline preservation

- Uses the physically verified 1.95.2 workout-interaction runtime as the foundation.
- Removes the mutation that changed the authoritative target rep count after the first weight-derived calculation.
- Keeps each calculated rep result in the pending draft only.
- Every subsequent weight edit now recalculates from the original target weight and reps rather than the prior derived result.
- Retains the immediate mounted reps-field and plate-feedback update path.
- Makes no card-reconciliation, controller, completion, database, or schema changes.
- Removes `.git` before Android packaging.
