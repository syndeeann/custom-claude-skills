# Calling the skill from a pipeline

The reels pipeline ends a run when the video is posted and the run log says `Finished with status 'posted'`.
Add one step right after that, before the run is closed:

1. Pull the latest live branch of the portfolio repo.
2. `add --run-dir output/<date>-<topic_id>` (add `--youtube` if the log has no link).
3. `check`, then `publish --message "Add <title>"`.
4. Write one line to the run log: the studio, the published date, and the live URL.

If any command fails, log the error and finish the run anyway. A portfolio problem never blocks posting; the
next run, or the owner, retries it. `add` is idempotent, so running it twice is safe.

For a skill change: run `sync-skills` after pushing the skills repo, then `check` and `publish`.

A run that is only `ready_to_post` (waiting for approval) is not delivered. Run this skill when the owner
approves and the status becomes `posted`.
