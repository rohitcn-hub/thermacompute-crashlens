# How CrashLens works

1. Read explicitly supplied local text files, bounded to 20 MiB combined.
2. Match case-insensitive, documented regular-expression signatures line by line.
3. Mask selected labelled secrets, bearer values and email addresses.
4. Retain source aliases, line numbers and suggested next checks.
5. Order matches by UTC only when every match has a timezone-aware timestamp.
6. Write JSON, Markdown and escaped static HTML to a new output directory.

There is no model, cloud API, telemetry collector, shell execution, scheduler integration or hardware control. The HTML has no JavaScript or external assets.

Threat boundary: input logs are untrusted. HTML escapes evidence, Markdown indents it as code, and redaction is best effort. Reports still require human review. Filesystem permissions and disk encryption are the operator's responsibility.

The scanner identifies occurrences, not causality. A downstream timeout may follow an upstream memory failure, but the tool does not infer that relationship.
