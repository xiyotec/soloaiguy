# Atlas Lessons

Mistakes I've made and how to avoid them.

## Mid-task truncation / empty replies (2026-04-26)

**What happened:** Xiyo said "Yeah add them all do everything." I started executing — updated keyword-queue.md — then the reply was sent before I finished. The editorial calendar, memory, and git commit were never done. Xiyo saw an empty/incomplete reply and had to ask what happened.

**Root cause:** Long multi-step tasks can get cut off mid-execution. The reply message arrives before all steps complete.

**Fix going forward:**
1. Always end every reply with an explicit status block:
   - ✅ Done: list what completed
   - ❌ Still pending: list what didn't
2. If I notice I got cut off in a previous turn, immediately finish the remaining work without waiting to be asked.
3. Batch commits — don't commit until ALL the changes for a task are done, so a partial run is obvious from git status.

## "Fix yourself" means finish the interrupted task (2026-04-26)

**What happened:** After the empty reply, Xiyo said "Fix yourself." I wasted a turn asking for context instead of just checking the history and finishing the job.

**Fix:** When something went wrong in a prior turn, search_history + read relevant files first, then act. Don't ask Xiyo to re-explain what they already said.
