# Video projects

One folder per video creation project. Each project has a `script/` folder, where the
`storyteller` skill saves the scripts it writes, and a `prompts/` folder, where the `ai-prompt-expert` skill
saves the generation prompts for each script (created the first time it runs).

```
video-projects/
  <project>/                       lowercase-with-hyphens, e.g. kwento-kilabot
    script/
      001-<topic-slug>.md              the script: angle, look anchors, clip-by-clip lines and draft visuals
      001-<topic-slug>.prompts.json    exported from the .md by the storyteller's lint, for the QA skills
    prompts/
      001-<topic-slug>.md              final generation prompts for Flow and other generators (ai-prompt-expert)
      001-<topic-slug>.json            exported from the .md by its lint
```

- Scripts are numbered in the order they were written, per project.
- Only text goes here: no clips, renders or contact sheets (see `.gitignore`).
- To add a project, ask Claude to write a script for it, or run
  `python skills/storyteller/scripts/new_project.py <project> --topic "<working title>"`.
