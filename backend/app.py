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


class ValidationError(Exception):
    """Erro causado por dados inválidos enviados pelo usuário."""


class TranscriptError(Exception):
    """Erro ao recuperar ou processar a legenda."""


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
        raise ValidationError("O corpo da solicitação está vazio.")

    if event.get("isBase64Encoded"):
        body = base64.b64decode(body).decode("utf-8")

    try:
        parsed_body = json.loads(body)
    except json.JSONDecodeError as error:
        raise ValidationError("O corpo precisa ser um JSON válido.") from error

    if not isinstance(parsed_body, dict):
        raise ValidationError("O corpo precisa ser um objeto JSON.")

    return parsed_body


def validate_youtube_url(video_url: str) -> str:
    if not isinstance(video_url, str) or not video_url.strip():
        raise ValidationError("Informe a URL do vídeo.")

    video_url = video_url.strip()

    try:
        parsed = urlparse(video_url)
    except ValueError as error:
        raise ValidationError("A URL informada é inválida.") from error

    if parsed.scheme not in {"http", "https"}:
        raise ValidationError("A URL deve começar com http:// ou https://.")

    hostname = (parsed.hostname or "").lower()

    valid_hostname = (
        hostname == "youtu.be"
        or hostname == "youtube.com"
        or hostname.endswith(".youtube.com")
    )

    if not valid_hostname:
        raise ValidationError("Informe uma URL válida do YouTube.")

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
            "Não foi possível carregar a configuração da API de legendas."
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
            "Não foi possível se comunicar com o serviço de legendas."
        ) from error


def process_transcript_response(data: dict[str, Any]) -> tuple[str, str]:
    content = normalize_transcript_content(data.get("content"))
    language = str(data.get("lang") or "desconhecido")

    if not content:
        error_data = data.get("error")

        if isinstance(error_data, dict):
            details = error_data.get("details") or error_data.get("message")

            if details:
                raise TranscriptError(str(details))

        raise TranscriptError(
            "A API não encontrou uma legenda pública para esse vídeo."
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
                "O serviço de legendas retornou uma resposta inválida."
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
                    or "A obtenção da legenda falhou."
                )
            else:
                message = "A obtenção da legenda falhou."

            raise TranscriptError(str(message))

    raise TranscriptError(
        "A legenda está demorando mais do que o esperado para ser processada."
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
            "O serviço de legendas retornou uma resposta inválida."
        ) from error

    if response.status_code == 202:
        job_id = data.get("jobId")

        if not isinstance(job_id, str) or not job_id:
            raise TranscriptError(
                "O serviço iniciou o processamento, mas não retornou o identificador."
            )

        return poll_transcript_job(job_id)

    if response.status_code == 206:
        raise TranscriptError(
            "O vídeo não possui uma legenda pública disponível."
        )

    if not response.ok:
        message = (
            data.get("details")
            or data.get("message")
            or "Não foi possível obter a legenda."
        )

        raise TranscriptError(str(message))

    return process_transcript_response(data)


def generate_summary(transcript: str, transcript_language: str) -> str:
    language_code = transcript_language.lower().strip()

    if language_code.startswith("pt"):
        output_language = "Brazilian Portuguese"
        summary_heading = "Resumo"
        key_points_heading = "Principais pontos"
        conclusion_heading = "Conclusão"
    elif language_code.startswith("en"):
        output_language = "English"
        summary_heading = "Summary"
        key_points_heading = "Key points"
        conclusion_heading = "Conclusion"
    else:
        output_language = (
            "the predominant language used in the transcript"
        )
        summary_heading = "Summary translated into the transcript language"
        key_points_heading = (
            "Key points translated into the transcript language"
        )
        conclusion_heading = (
            "Conclusion translated into the transcript language"
        )

    prompt = f"""
Create a clear and structured summary of the content below.

Mandatory output language:
{output_language}

Mandatory headings:
## {summary_heading}
## {key_points_heading}
## {conclusion_heading}

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
                        f"You summarize educational content accurately. "
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
                "maxTokens": 1_500,
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
            "Não foi possível gerar o resumo no Amazon Bedrock."
        ) from error

    content_blocks = (
        response.get("output", {})
        .get("message", {})
        .get("content", [])
    )

    summary_parts = [
        block["text"]
        for block in content_blocks
        if isinstance(block, dict) and isinstance(block.get("text"), str)
    ]

    summary = "\n".join(summary_parts).strip()

    if not summary:
        raise RuntimeError("O Amazon Bedrock não retornou um resumo.")

    return summary


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
                "message": "Utilize o método POST.",
            },
        )

    try:
        request_body = parse_request_body(event)
        video_url = validate_youtube_url(request_body.get("url", ""))

        transcript, transcript_language = get_transcript(video_url)

        if len(transcript) > MAX_TRANSCRIPT_CHARS:
            raise ValidationError(
                "A legenda é muito longa para a versão mínima. "
                "Utilize um vídeo mais curto."
            )

        summary = generate_summary(
            transcript=transcript,
            transcript_language=transcript_language,
        )

        return build_response(
            200,
            {
                "url": video_url,
                "transcriptLanguage": transcript_language,
                "transcriptCharacters": len(transcript),
                "summary": summary,
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
                "message": "Ocorreu um erro inesperado.",
            },
        )