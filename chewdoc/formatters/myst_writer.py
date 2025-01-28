def _format_examples(self, examples: list) -> str:
    output = []
    for example in examples:
        if example["type"] == "doctest":
            output.append(f"```python\n{example['content']}\n```")
        elif example["type"] == "pytest":
            output.append(f"**Test Example**: `{example['name']}`\n\n```python\n{example['content']}\n```")
    return "\n\n".join(output) 