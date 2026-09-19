# Writing workshop

A local web app that helps you edit your own writing. You write in the
browser. An AI agent reads your text and marks problems. You fix each
problem by hand. The agent never writes for you.

The method comes from Thomas Ptacek's post
[How To Write With An LLM](https://sockpuppet.org/blog/2026/09/17/how-to-write-with-an-llm/)
and from the book *Style: Lessons in Clarity and Grace* by Joseph Williams.

## What the app does

- You keep many documents. Each document has a rich text editor.
- You highlight text and attach a note. Notes show in a sidebar next to
  the highlighted text.
- An agent runs an **editing pass** over a document. A pass is one narrow
  check, for example "Sand off filler words". The app ships with 30 passes.
- Each problem the agent finds is a **finding**. A finding has the exact
  words from your text, the paragraph number, and a note. The note names the
  problem. It never gives new wording.
- You accept a finding after you fix the text. You reject a finding when you
  disagree. The agent can see your decisions.
- You save a **revision** at any time. You can mark a revision as major.
  You can view or restore any revision.

## Install

You need Python 3.12 or later, Node.js 22 or later, and `uv`.

```sh
make setup   # installs Python and Node packages
make build   # builds the CSS and the JavaScript
```

## Start the app

```sh
make dev
```

Open http://127.0.0.1:8000 in your browser.

The app stores everything in `data/app.db`. Set the `WORKSHOP_DB` variable
to use another file. The app creates the tables at first start.

## Write

1. Click **New document**.
2. Click the title to rename the document.
3. Write in the editor. The app saves after each pause.
4. Type `/` at the start of a line to open the block menu. Pick a heading,
   a list, a quote, or a code block.
5. Select text to open the format bar. Use it for bold, italic, strike, and
   code.

## Add your own notes

1. Select text.
2. In the format bar, click **Comment**, **Suggest**, or **Question**.
3. Write your note in the card that opens in the sidebar.

Click a highlight to jump to its card. Click a card to jump to its
highlight. Use the arrow buttons in the header, or `Alt+Up` and `Alt+Down`,
to move from one note to the next.

## Run an editing pass with Claude Code

The app serves an MCP server at `http://127.0.0.1:8000/mcp` while it runs.
MCP is the protocol an AI agent uses to call the app.

Do this once:

1. Start the app with `make dev`.
2. Open Claude Code in this repository. The file `.mcp.json` registers the
   server. Claude Code asks you to approve it.

To use the server from any directory, run this instead:

```sh
claude mcp add --transport http --scope user workshop http://127.0.0.1:8000/mcp
```

Then, for each pass:

1. Open the document in your browser.
2. In Claude Code, type:

   ```
   /mcp__workshop__run_pass 0 "My document title"
   ```

   The first value is the pass number. You can also give the pass name.
3. Wait a few seconds. The findings appear in your browser as red underlines.

To run every pass in order, type:

```
/mcp__workshop__review "My document title"
```

Codex and other MCP clients work the same way. Point them at the same URL.

## Review the findings

The **pass bar** sits under the header. It shows the current pass, the
arrows to change the pass, and how many passes have run.

- Click **Passes** in the header to open the panel of passes. A check mark
  shows which passes have run. Each pass shows how many findings are open
  and how many you accepted.
- Click **Only this pass** to hide the findings from other passes.
- Each finding is a card in the sidebar. Read the note. Fix your text.
- Click **Accept** when you fixed the problem. Click **Reject** when you
  disagree. The underline goes away in both cases.

## Save a revision

The revision panel sits below the sidebar.

1. Type a label. Tick **Major** for a big rewrite.
2. Click **Snapshot**.

Each revision has **View**, **Flag major**, and **Restore**. Restore first
saves the current text as a revision named "Before restore".

The check marks in the passes panel reset after a major revision. This shows
which passes the current draft has been through.

## Edit the passes

Click **Edit passes** in the header, or open http://127.0.0.1:8000/passes.

- Click a pass to open its form. Change the title, the group, or the prompt.
- Turn a pass off to hide it from the pass bar.
- Move a pass up or down to change its order.
- Add a new pass with the form at the top.

The agent reads the prompt from the app each time it runs a pass. Your
changes apply to the next run.

## Run the tests

```sh
make test
```

## For coding agents

See `AGENTS.md` for the rules that keep the code correct.

## Layout

| Path | Contents |
| --- | --- |
| `app/main.py` | routes and the MCP endpoint |
| `app/db.py` | database connections and migrations |
| `app/repo.py` | all SQL |
| `app/text.py` | plain text and paragraph numbers |
| `app/coach.py` | the rules the agent receives |
| `app/mcp_server.py` | MCP tools and prompts |
| `app/seed_passes.py` | the 30 seeded passes |
| `app/templates/` | HTML templates |
| `assets/` | CSS and JavaScript sources |
| `app/static/` | built files, not in git |
| `docs/superpowers/specs/` | design documents |
