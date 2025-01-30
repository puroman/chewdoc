def _format_usage_examples(self, examples: list) -> str:
    """Format usage examples with validation and proper indexing"""
    output = []
    for i, ex in enumerate(examples, 1):
        try:
            if isinstance(ex, (str, dict)):
                code = ex.get("code", ex.get("content", ""))
                if not code.strip():
                    raise ValueError("Empty example content")
                output.append(f"### Example {i}\n```python\n{code}\n```")
            else:
                raise ValueError(f"Invalid type: {type(ex).__name__}")
        except Exception as e:
            logger.warning(f"Skipping example {i}: {str(e)}")
    return "\n\n".join(output) if output else "" 