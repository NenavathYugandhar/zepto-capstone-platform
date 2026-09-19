"""Optional MOCK_LLM=0 extension: real LLM calls via Groq's free-tier API
(OpenAI-compatible endpoint). Not used at all when MOCK_LLM is left at its
default (unset or "1") — the graded baseline never imports or calls this.
"""
import json
import os

from pydantic import ValidationError

from prompts import ANSWER_PROMPT_TEMPLATE, CLASSIFY_PROMPT_TEMPLATE
from schemas import AskResponse

GROQ_MODEL = "llama-3.1-8b-instant"


def _get_client():
    from openai import OpenAI  # Groq exposes an OpenAI-compatible API

    return OpenAI(
        api_key=os.environ["GROQ_API_KEY"],
        base_url="https://api.groq.com/openai/v1",
    )


def llm_classify_intent(question: str) -> str:
    client = _get_client()
    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[{"role": "user", "content": CLASSIFY_PROMPT_TEMPLATE.format(question=question)}],
        temperature=0,
    )
    label = response.choices[0].message.content.strip().lower()
    return "policy_question" if "policy" in label else "general_question"


def llm_answer_with_context(question: str, context: str) -> str:
    client = _get_client()
    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[{"role": "user", "content": ANSWER_PROMPT_TEMPLATE.format(question=question, context=context)}],
        temperature=0.2,
    )
    return response.choices[0].message.content.strip()


def llm_direct_answer(question: str) -> str:
    client = _get_client()
    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[{"role": "user", "content": question}],
        temperature=0.2,
    )
    return response.choices[0].message.content.strip()


def validate_with_retry(raw_json: str, sources: list[str], max_retries: int = 2) -> AskResponse:
    """Validates the LLM's raw JSON output against AskResponse, retrying with
    a corrective instruction up to `max_retries` additional times before
    giving up and returning a clearly marked error response.
    """
    client = _get_client()
    attempt_input = raw_json

    for attempt in range(max_retries + 1):
        try:
            data = json.loads(attempt_input)
            return AskResponse(**data)
        except (json.JSONDecodeError, ValidationError) as exc:
            if attempt == max_retries:
                return AskResponse(
                    answer="[ERROR: LLM output failed schema validation after retries]",
                    sources=sources,
                    confidence=0.0,
                )
            correction_prompt = (
                f"Your previous output was invalid: {exc}\n"
                f"Previous output: {attempt_input}\n"
                f'Return ONLY valid JSON matching this schema: '
                f'{{"answer": string, "sources": list[string], "confidence": float 0-1}}'
            )
            response = client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[{"role": "user", "content": correction_prompt}],
                temperature=0,
            )
            attempt_input = response.choices[0].message.content.strip()

    # Unreachable, but keeps type checkers happy
    return AskResponse(answer="[ERROR]", sources=sources, confidence=0.0)
