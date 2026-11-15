# Submission release procedure

The submission tag is a record of the exact project reviewed by the judges. Do
not create it while the demo, video, project page, or public links are still
changing.

## Before the tag

1. Confirm the final team and update `CONTRIBUTORS.md` with only merged work.
2. Run the complete test suite and rebuild `dist/`.
3. Review the project page against the live submission form.
4. Verify the public demo, source, and video links in a signed-out browser.
5. Record the final commit identifier in the submission checklist.

## Freeze command

```bash
git tag -a space-apps-2026-submission -m "NASA Space Apps 2026 submission"
git push origin space-apps-2026-submission
```

The tag must point to the exact commit used for the submitted demo and project
page. Do not move or overwrite the tag after submission.

## Development after submission

Continue work in later commits and use normal semantic versions such as
`v0.2.0` or `v0.3.0`. The competition tag remains unchanged so the judged
version can always be reproduced.
