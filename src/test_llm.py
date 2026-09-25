"""Smoke test: confirms your Mistral key works and logging works."""
from llm import call_llm

print(call_llm("Say hello in one sentence.", agent="smoke_test"))
print("\nCheck logs/llm_calls.jsonl for the new log line.")