#!/usr/bin/env python3
"""
LiteLLM + Gemini learning script.

Setup:
  1) Install project dependencies: pip install -e .
  2) Export your key: export GEMINI_API_KEY="...your key..."
  3) Run a demo: python litellm_gemini_learning.py basic
"""

import argparse
import asyncio
import json
import os
from typing import Callable

import litellm
from litellm import acompletion, batch_completion, completion, embedding, get_supported_openai_params

# Chunk config: keep models here so you can swap quickly without editing every demo.
# Gemini models should be prefixed with "gemini/" when using the Gemini API key.
CHAT_MODEL = os.getenv("LITELLM_CHAT_MODEL", "gemini/gemini-2.0-flash")
EMBED_MODEL = os.getenv("LITELLM_EMBED_MODEL", "gemini/text-embedding-004")


def ensure_api_key() -> None:
    # Chunk goal: fail fast with a clear error if the Gemini API key is missing.
    # Build steps: read the environment variable and raise a helpful error.
    if not os.getenv("GEMINI_API_KEY"):
        raise RuntimeError(
            "Missing GEMINI_API_KEY. Set it in your shell, e.g. "
            'export GEMINI_API_KEY="your-key-here"'
        )


def demo_basic_completion() -> None:
    # Chunk goal: show the smallest useful chat completion call.
    # Build steps: (1) assemble messages, (2) call completion(), (3) print text + usage.
    messages = [
        {"role": "system", "content": "You are a concise linear algebra tutor."},
        {"role": "user", "content": "Explain eigenvalues in one short paragraph."},
    ]
    response = completion(model=CHAT_MODEL, messages=messages, temperature=0.2)
    print(response.choices[0].message.content)
    print("\nUsage:", response.usage)


def demo_streaming() -> None:
    # Chunk goal: stream tokens as they arrive.
    # Build steps: (1) set stream=True, (2) print delta content, (3) rebuild full message.
    messages = [
        {"role": "user", "content": "Give me 5 short tips for matrix multiplication."}
    ]
    chunks = []
    stream = completion(model=CHAT_MODEL, messages=messages, stream=True)
    print("Streaming output:\n")
    for chunk in stream:
        chunks.append(chunk)
        delta = chunk.choices[0].delta
        if delta and delta.content:
            print(delta.content, end="", flush=True)
    print("\n\nReconstructed output:\n")
    rebuilt = litellm.stream_chunk_builder(chunks, messages=messages)
    print(rebuilt.choices[0].message.content)


async def demo_async_completion() -> None:
    # Chunk goal: use the async API (acompletion) for concurrent workflows.
    # Build steps: (1) define messages, (2) await acompletion(), (3) print content.
    messages = [
        {"role": "user", "content": "Give a 2-sentence summary of SVD."}
    ]
    response = await acompletion(model=CHAT_MODEL, messages=messages)
    print(response.choices[0].message.content)


def demo_function_calling() -> None:
    # Chunk goal: demonstrate tool/function calling with a follow-up call.
    # Build steps: (1) declare a Python function, (2) describe it as a tool,
    # (3) let the model call it, (4) send tool results back for a final reply.
    def area_of_circle(radius: float) -> str:
        return str(3.14159 * radius * radius)

    tools = [
        {
            "type": "function",
            "function": {
                "name": "area_of_circle",
                "description": "Compute the area of a circle.",
                "parameters": {
                    "type": "object",
                    "properties": {"radius": {"type": "number"}},
                    "required": ["radius"],
                },
            },
        }
    ]

    messages = [
        {"role": "user", "content": "What is the area of a circle with radius 3? Use the tool."}
    ]
    response = completion(
        model=CHAT_MODEL,
        messages=messages,
        tools=tools,
        tool_choice="auto",
    )

    response_message = response.choices[0].message
    tool_calls = response_message.tool_calls

    if not tool_calls:
        print(response_message.content or "No tool call returned.")
        return

    messages.append(response_message)
    for call in tool_calls:
        args = json.loads(call.function.arguments)
        result = area_of_circle(radius=float(args["radius"]))
        messages.append(
            {
                "role": "tool",
                "tool_call_id": call.id,
                "name": call.function.name,
                "content": result,
            }
        )

    second = completion(model=CHAT_MODEL, messages=messages)
    print(second.choices[0].message.content)


def demo_embeddings() -> None:
    # Chunk goal: create text embeddings for semantic search or clustering.
    # Build steps: (1) pick an embedding model, (2) pass text inputs, (3) inspect vector.
    response = embedding(
        model=EMBED_MODEL,
        input=["orthogonal matrix properties", "eigenvalues and eigenvectors"],
    )
    vector = response.data[0].embedding
    print(f"Embedding length: {len(vector)}")
    print("First 5 values:", vector[:5])


def demo_json_mode() -> None:
    # Chunk goal: request JSON-only output using response_format.
    # Build steps: (1) set response_format, (2) constrain with a system prompt,
    # (3) parse JSON from the model's reply.
    messages = [
        {"role": "system", "content": "Return ONLY a JSON object."},
        {"role": "user", "content": "Return a JSON object with keys: topic, summary."},
    ]
    response = completion(
        model=CHAT_MODEL,
        messages=messages,
        response_format={"type": "json_object"},
    )
    raw = response.choices[0].message.content
    print("Raw JSON:", raw)
    print("Parsed JSON:", json.loads(raw))


def demo_supported_params() -> None:
    # Chunk goal: introspect which OpenAI-compatible params LiteLLM supports for a model.
    # Build steps: (1) call get_supported_openai_params(), (2) print sorted list.
    params = get_supported_openai_params(model=CHAT_MODEL)
    print("Supported params:")
    for name in sorted(params):
        print("-", name)


def demo_batch_completion() -> None:
    # Chunk goal: send multiple prompts in one batch call.
    # Build steps: (1) create a list of message lists, (2) call batch_completion(),
    # (3) iterate over responses in order.
    messages = [
        [{"role": "user", "content": "Define determinant in one sentence."}],
        [{"role": "user", "content": "Give one practical use of eigenvectors."}],
        [{"role": "user", "content": "Explain what rank means in a matrix."}],
    ]
    responses = batch_completion(model=CHAT_MODEL, messages=messages)
    for i, resp in enumerate(responses, start=1):
        print(f"Response {i}:", resp.choices[0].message.content)


def build_demo_registry() -> dict[str, Callable[[], None]]:
    # Chunk goal: centralize demo names so the CLI can list and run them.
    # Build steps: (1) map names to callables, (2) wrap async demo for sync use.
    return {
        "basic": demo_basic_completion,
        "stream": demo_streaming,
        "async": lambda: asyncio.run(demo_async_completion()),
        "tools": demo_function_calling,
        "embeddings": demo_embeddings,
        "json": demo_json_mode,
        "params": demo_supported_params,
        "batch": demo_batch_completion,
    }


def main() -> None:
    # Chunk goal: small CLI for choosing a demo to run.
    # Build steps: (1) parse args, (2) validate choice, (3) run the demo.
    parser = argparse.ArgumentParser(description="LiteLLM + Gemini learning demos")
    parser.add_argument("demo", nargs="?", help="Demo name (use --list to see options)")
    parser.add_argument("--list", action="store_true", help="List available demos")
    args = parser.parse_args()

    demos = build_demo_registry()
    if args.list or not args.demo:
        print("Available demos:")
        for name in demos:
            print("-", name)
        return

    demo = demos.get(args.demo)
    if not demo:
        raise SystemExit(f"Unknown demo '{args.demo}'. Use --list to see options.")

    ensure_api_key()
    demo()


if __name__ == "__main__":
    main()
