# UNIVERSAL OUTPUT RULES

These rules apply to ALL AI generation in this framework. No exceptions.

## Anti-Truncation (ABSOLUTE RULE)
- Output the COMPLETE code from first character to last
- NEVER use: `/* rest of code */`, `<!-- more here -->`, `// ...`, `[continues]`, or any placeholder
- NEVER stop mid-function, mid-tag, or mid-block
- If output would be long, that is expected — write it all anyway

## Format Rules
- Output ONLY the raw content requested (HTML, CSS, JS, or Python)
- Do NOT wrap output in markdown backticks (no ```html, ```css, ```js, ```python blocks)
- Do NOT add preamble ("Here is the code..."), postamble ("I hope this helps!"), or any explanation
- Do NOT add comments explaining what you did unless comments are part of the code logic

## Quality Rules
- Write production-quality code — no "TODO:", no placeholder values like "your-api-key-here"
- Use real, specific values: real CSS measurements, real function names, real data structures
- Every interactive element MUST have hover/focus/active states
- Every user-facing state MUST be handled: empty, loading, error, success
