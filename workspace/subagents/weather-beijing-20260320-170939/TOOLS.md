# Tools

You have access to the following built-in tools:

## exec
Execute any shell command. This is your primary way of interacting with the system.
- Use it to run programs, scripts, manage files, install software, etc.
- Always check exit_code to verify success.

## read
Read a file's content. Supports optional `offset` (1-based line number) and `limit` (number of lines).

## write
Write content to a file. Creates parent directories automatically. Overwrites existing content.

## Skills (dynamic)
Additional skills may be available. Use `skills list` via exec to discover them.
