# Video projects

One folder per video creation project. Each project has a `script/` folder, and that is where the
`storyteller` skill saves the scripts it writes.

```
video-projects/
  <project>/                       lowercase-with-hyphens, e.g. kwento-kilabot
    script/
      001-<topic-slug>.md              the script: angle, look anchors, clip-by-clip lines and Flow prompts
      001-<topic-slug>.prompts.json    exported from the .md by the storyteller's lint, for the QA skills
```

- Scripts are numbered in the order they were written, per project.
- Only text goes here: no clips, renders or contact sheets (see `.gitignore`).
- To add a project, ask Claude to write a script for it, or run
  `python skills/storyteller/scripts/new_project.py <project> --topic "<working title>"`.
