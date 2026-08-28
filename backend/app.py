import base64
import json
import os
import time
from typing import Any
from urllib.parse import urlparse

import boto3
import requests
from botocore.exceptions import ClientError


BEDROCK_MODEL_ID = os.environ.get(
    "BEDROCK_MODEL_ID",
    "amazon.nova-micro-v1:0",
)

SUPADATA_PARAMETER_NAME = os.environ.get(
    "SUPADATA_PARAMETER_NAME",
    "/youtube-summary/supadata-api-key",
)

MAX_TRANSCRIPT_CHARS = 80_000
POLL_INTERVAL_SECONDS = 2
MAX_POLL_ATTEMPTS = 20

bedrock = boto3.client("bedrock-runtime")
ssm = boto3.client("ssm")

_supadata_api_key: str | None = None


def get_preferred_language(event: dict[str, Any]) -> str:
    """Extract the preferred language from the Accept-Language header."""
    headers = (
        event.get("headers", {})
        or event.get("requestContext", {})
        .get("http", {})
        .get("headers", {})
    )
    
    accept_language = headers.get("accept-language", "")
    
    if accept_language:
        # Extract first language from Accept-Language header
        # e.g., "pt-BR,pt;q=0.9,en;q=0.8" -> "pt"
        first_lang = accept_language.split(",")[0].strip()
        return first_lang.split(";")[0].strip()[:2].lower()
    
    # Default to English
    return "en"


class ValidationError(Exception):
    """Error caused by invalid data sent by the user."""


class TranscriptError(Exception):
    """Error retrieving or processing the transcript."""


def build_response(status_code: int, body: dict[str, Any]) -> dict[str, Any]:
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json; charset=utf-8",
        },
        "body": json.dumps(body, ensure_ascii=False),
        "isBase64Encoded": False,
    }


def get_request_method(event: dict[str, Any]) -> str:
    return (
        event.get("requestContext", {})
        .get("http", {})
        .get("method", "")
        .upper()
    )


def parse_request_body(event: dict[str, Any]) -> dict[str, Any]:
    body = event.get("body")

    if not body:
        raise ValidationError("The request body is empty.")

    if event.get("isBase64Encoded"):
        body = base64.b64decode(body).decode("utf-8")

    try:
        parsed_body = json.loads(body)
    except json.JSONDecodeError as error:
        raise ValidationError("The body must be a valid JSON.") from error

    if not isinstance(parsed_body, dict):
        raise ValidationError("The body must be a JSON object.")

    return parsed_body


def validate_youtube_url(video_url: str) -> str:
    if not isinstance(video_url, str) or not video_url.strip():
        raise ValidationError("Please provide the video URL.")

    video_url = video_url.strip()

    try:
        parsed = urlparse(video_url)
    except ValueError as error:
        raise ValidationError("The provided URL is invalid.") from error

    if parsed.scheme != "https":
        raise ValidationError("The URL must start with https://.")

    hostname = (parsed.hostname or "").lower()

    valid_hostname = (
        hostname == "youtu.be"
        or hostname == "youtube.com"
        or hostname.endswith(".youtube.com")
    )

    if not valid_hostname:
        raise ValidationError("Please provide a valid YouTube URL.")

    return video_url


def get_supadata_api_key() -> str:
    global _supadata_api_key

    if _supadata_api_key:
        return _supadata_api_key

    try:
        response = ssm.get_parameter(
            Name=SUPADATA_PARAMETER_NAME,
            WithDecryption=True,
        )
    except ClientError as error:
        print(
            json.dumps(
                {
                    "event": "parameter_store_error",
                    "error": str(error),
                }
            )
        )
        raise TranscriptError(
            "Could not load the transcript API configuration."
        ) from error

    _supadata_api_key = response["Parameter"]["Value"]
    return _supadata_api_key


def normalize_transcript_content(content: Any) -> str:
    if isinstance(content, str):
        return content.strip()

    if isinstance(content, list):
        texts: list[str] = []

        for item in content:
            if isinstance(item, dict):
                text = item.get("text")

                if isinstance(text, str) and text.strip():
                    texts.append(text.strip())

        return " ".join(texts).strip()

    return ""


def request_supadata(
    endpoint: str,
    *,
    params: dict[str, str] | None = None,
) -> requests.Response:
    api_key = get_supadata_api_key()

    try:
        return requests.get(
            endpoint,
            headers={
                "x-api-key": api_key,
                "Accept": "application/json",
            },
            params=params,
            timeout=30,
        )
    except requests.RequestException as error:
        raise TranscriptError(
            "Could not communicate with the transcript service."
        ) from error


def process_transcript_response(data: dict[str, Any]) -> tuple[str, str]:
    content = normalize_transcript_content(data.get("content"))
    language = str(data.get("lang") or "unknown")

    if not content:
        error_data = data.get("error")

        if isinstance(error_data, dict):
            details = error_data.get("details") or error_data.get("message")

            if details:
                raise TranscriptError(str(details))

        raise TranscriptError(
            "The API did not find a public transcript for this video."
        )

    return content, language


def poll_transcript_job(job_id: str) -> tuple[str, str]:
    endpoint = f"https://api.supadata.ai/v1/transcript/{job_id}"

    for _ in range(MAX_POLL_ATTEMPTS):
        time.sleep(POLL_INTERVAL_SECONDS)

        response = request_supadata(endpoint)

        try:
            data = response.json()
        except ValueError as error:
            raise TranscriptError(
                "The transcript service returned an invalid response."
            ) from error

        status = data.get("status")

        if status == "completed":
            return process_transcript_response(data)

        if status == "failed":
            error_data = data.get("error")

            if isinstance(error_data, dict):
                message = (
                    error_data.get("details")
                    or error_data.get("message")
                    or "Transcript retrieval failed."
                )
            else:
                message = "Transcript retrieval failed."

            raise TranscriptError(str(message))

    raise TranscriptError(
        "The transcript is taking longer than expected to process."
    )


def get_transcript(video_url: str) -> tuple[str, str]:
    response = request_supadata(
        "https://api.supadata.ai/v1/transcript",
        params={
            "url": video_url,
            "text": "true",
            "mode": "native",
        },
    )

    try:
        data = response.json()
    except ValueError as error:
        raise TranscriptError(
            "The transcript service returned an invalid response."
        ) from error

    if response.status_code == 202:
        job_id = data.get("jobId")

        if not isinstance(job_id, str) or not job_id:
            raise TranscriptError(
                "The service started processing but did not return the identifier."
            )

        return poll_transcript_job(job_id)

    if response.status_code == 206:
        raise TranscriptError(
            "The video does not have a public transcript available."
        )

    if not response.ok:
        message = (
            data.get("details")
            or data.get("message")
            or "Could not retrieve the transcript."
        )

        raise TranscriptError(str(message))

    return process_transcript_response(data)


def generate_summary(
    transcript: str,
    transcript_language: str,
    preferred_language: str = "en",
) -> tuple[str, str]:
    # Map preferred language to output language for prompts
    language_map = {
        "pt": "Brazilian Portuguese",
        "en": "English",
    }
    
    if preferred_language in language_map:
        output_language = language_map[preferred_language]
        summary_heading = "Summary" if preferred_language == "en" else "Resumo"
        key_points_heading = "Key points" if preferred_language == "en" else "Principais pontos"
        conclusion_heading = "Conclusion" if preferred_language == "en" else "Conclusão"
        content_map_heading = "Content Map" if preferred_language == "en" else "Mapa de conteúdo"
    else:
        output_language = "English"
        summary_heading = "Summary"
        key_points_heading = "Key points"
        conclusion_heading = "Conclusion"
        content_map_heading = "Content Map"

    prompt = f"""
Create a clear and structured summary of the content below.

Mandatory output language:
{output_language}

Mandatory headings:
## {summary_heading}
## {key_points_heading}
## {conclusion_heading}
## {content_map_heading}

Language requirements:
1. Write every sentence in {output_language}.
2. Use exactly the mandatory headings shown above.
3. Do not mix languages.
4. Do not translate proper nouns, official product names, service names,
   personal names, technical terms, or acronyms.
5. Do not mention the language or the transcript in the answer.

Content requirements:
1. Use only information contained in the supplied content.
2. Do not invent facts, names, numbers, examples, or conclusions.
3. Remove repetitions, filler words, and irrelevant passages.
4. Preserve the original meaning.
5. Explain the topics clearly.

Required structure:

## {summary_heading}

Write two to four paragraphs describing the overall content.

## {key_points_heading}

Present between five and ten bullet points.

## {conclusion_heading}

Present the main conclusion or final message.

## {content_map_heading}

Create a compact ASCII content map that visually organizes the central
topic, main topics, and relevant subtopics from the content.

Content map requirements:
1. Use plain ASCII characters only, such as |, +, -, and >.
2. Use one central topic.
3. Include between three and five main topics when the content supports them.
4. Include no more than three subtopics under each main topic.
5. Use no more than three hierarchy levels.
6. Keep labels short and clear.
7. Represent thematic hierarchy only. Do not invent relationships.
8. Use only information contained in the supplied content.
9. Wrap the complete ASCII map in a fenced text code block.

Content:

<content>
{transcript}
</content>
""".strip()

    try:
        response = bedrock.converse(
            modelId=BEDROCK_MODEL_ID,
            system=[
                {
                    "text": (
                        f"You analyze and summarize video transcript content accurately. "
                        f"You must answer only in {output_language}. "
                        f"Do not mix languages. "
                        f"Follow the requested headings exactly."
                    )
                }
            ],
            messages=[
                {
                    "role": "user",
                    "content": [{"text": prompt}],
                }
            ],
            inferenceConfig={
                "maxTokens": 2_000,
                "temperature": 0.1,
                "topP": 0.9,
            },
        )
    except ClientError as error:
        print(
            json.dumps(
                {
                    "event": "bedrock_error",
                    "error": str(error),
                }
            )
        )
        raise RuntimeError(
            "Could not generate the summary in Amazon Bedrock."
        ) from error

    content_blocks = (
        response.get("output", {})
        .get("message", {})
        .get("content", [])
    )

    summary_parts = []
    content_map_parts = []
    current_section = None

    for block in content_blocks:
        if isinstance(block, dict) and isinstance(block.get("text"), str):
            text = block["text"]
            lines = text.split("\n")
            
            for line in lines:
                if f"## {content_map_heading}" in line:
                    current_section = "content_map"
                elif current_section == "content_map":
                    content_map_parts.append(line)
                elif current_section is None:
                    summary_parts.append(line)

    summary = "\n".join(summary_parts).strip()
    content_map = "\n".join(content_map_parts).strip()

    if not summary:
        raise RuntimeError("Amazon Bedrock did not return a summary.")

    return summary, content_map


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    del context

    method = get_request_method(event)

    if method == "OPTIONS":
        return build_response(204, {})

    if method != "POST":
        return build_response(
            405,
            {
                "error": "method_not_allowed",
                "message": "Use the POST method.",
            },
        )

    preferred_language = get_preferred_language(event)

    try:
        request_body = parse_request_body(event)
        video_url = validate_youtube_url(request_body.get("url", ""))

        transcript, transcript_language = get_transcript(video_url)

        if len(transcript) > MAX_TRANSCRIPT_CHARS:
            raise ValidationError(
                "The transcript is too long for the free tier. "
                "Please use a shorter video."
            )

        summary, content_map = generate_summary(
            transcript=transcript,
            transcript_language=transcript_language,
            preferred_language=preferred_language,
        )

        return build_response(
            200,
            {
                "url": video_url,
                "transcriptLanguage": transcript_language,
                "transcriptCharacters": len(transcript),
                "summary": summary,
                "contentMap": content_map,
                "transcript": transcript,
            },
        )

    except ValidationError as error:
        return build_response(
            400,
            {
                "error": "validation_error",
                "message": str(error),
            },
        )

    except TranscriptError as error:
        return build_response(
            422,
            {
                "error": "transcript_error",
                "message": str(error),
            },
        )

    except RuntimeError as error:
        return build_response(
            502,
            {
                "error": "summary_error",
                "message": str(error),
            },
        )

    except Exception as error:
        print(
            json.dumps(
                {
                    "event": "unexpected_error",
                    "error": str(error),
                }
            )
        )

        return build_response(
            500,
            {
                "error": "internal_error",
                "message": "An unexpected error occurred.",
            },
        )