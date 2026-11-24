## Progress bar for long tasks

The status line shows a live progress bar fed by the `claude-eta` command. Use it for any task you expect to take more than about 3 minutes or that has more than 3 distinct steps (renders, builds, test suites, migrations, multi-file refactors, research runs).

- Before starting: `claude-eta start "<short task name>" --eta <honest total estimate, e.g. 20m> --total <number of steps>`. Keep the name under 30 characters.
- After each step: `claude-eta step` (add `--note "<what's next>"` if useful).
- If the estimate changes a lot: `claude-eta set --eta <time remaining>` or `claude-eta set --total <new step count>`.
- When done or abandoned: `claude-eta finish`.

Make the estimate honestly, from the work actually involved; the bar corrects itself from your measured pace as steps finish. These calls are bookkeeping: don't narrate them to the user.
