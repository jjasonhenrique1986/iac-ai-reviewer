"""Testes sem acesso à AWS: um servidor HTTP local faz o papel do Bedrock."""

import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest
from anthropic import AnthropicBedrockMantle, BetaRefusalFallbackMiddleware

sys.path.insert(0, str(Path(__file__).parent.parent / "reviewer"))
import review  # noqa: E402

REVIEW_JSON = {
    "summary": "O Security Group libera SSH para a internet.",
    "risk": "alto",
    "findings": [
        {
            "file": "examples/terraform/main.tf",
            "severity": "alta",
            "title": "SSH aberto para 0.0.0.0/0",
            "explanation": "Qualquer IP da internet pode tentar acessar a porta 22.",
            "suggestion": "Restrinja o cidr_blocks ou use o Session Manager.",
        }
    ],
}


def message(model: str, stop_reason: str, text: str) -> dict:
    content = [{"type": "text", "text": text}] if text else []
    return {
        "id": "msg_test",
        "type": "message",
        "role": "assistant",
        "model": model,
        "content": content,
        "stop_reason": stop_reason,
        "stop_sequence": None,
        "stop_details": {"type": "refusal", "category": None, "explanation": None} if stop_reason == "refusal" else None,
        "usage": {"input_tokens": 10, "output_tokens": 10},
    }


@pytest.fixture
def fake_bedrock():
    """Responde com recusa para os modelos em `refuse`, com erro se `status` não for 200
    e com a revisão para os demais."""
    state = {"requests": [], "refuse": set(), "status": 200}

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            state["requests"].append(body)
            if state["status"] != 200:
                error_type = {403: "permission_error", 404: "not_found_error"}[state["status"]]
                data = {"type": "error", "error": {"type": error_type, "message": "erro simulado"}}
            elif body["model"] in state["refuse"]:
                data = message(body["model"], "refusal", "")
            else:
                data = message(body["model"], "end_turn", json.dumps(REVIEW_JSON))
            payload = json.dumps(data).encode()
            self.send_response(state["status"])
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, *args):
            pass

    server = HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    client = AnthropicBedrockMantle(
        aws_region="us-east-1",
        base_url=f"http://127.0.0.1:{server.server_port}",
        skip_auth=True,
        max_retries=0,
        middleware=[BetaRefusalFallbackMiddleware([{"model": review.DEFAULT_FALLBACK_MODEL}])],
    )
    yield client, state
    server.shutdown()


def test_review_is_parsed(fake_bedrock):
    client, state = fake_bedrock
    result = review.ask_claude(client, review.DEFAULT_MODEL, review.build_prompt("diff", ""))

    assert isinstance(result, review.Review)
    assert result.risk == "alto"
    request = state["requests"][0]
    assert request["model"] == review.DEFAULT_MODEL
    assert request["output_config"]["effort"] == "medium"
    assert request["output_config"]["format"]["type"] == "json_schema"


def test_refusal_falls_back_to_other_model(fake_bedrock):
    client, state = fake_bedrock
    state["refuse"].add(review.DEFAULT_MODEL)
    result = review.ask_claude(client, review.DEFAULT_MODEL, review.build_prompt("diff", ""))

    assert isinstance(result, review.Review)
    assert [r["model"] for r in state["requests"]] == [review.DEFAULT_MODEL, review.DEFAULT_FALLBACK_MODEL]


def test_refusal_on_every_model(fake_bedrock):
    client, state = fake_bedrock
    state["refuse"].update({review.DEFAULT_MODEL, review.DEFAULT_FALLBACK_MODEL})
    result = review.ask_claude(client, review.DEFAULT_MODEL, review.build_prompt("diff", ""))

    assert result == "O modelo recusou a revisão deste Pull Request."


def test_prompt_wraps_untrusted_content():
    prompt = review.build_prompt("+ resource {}", "Check: CKV_AWS_24")
    assert "<diff>\n+ resource {}\n</diff>" in prompt
    assert "<checkov>\nCheck: CKV_AWS_24\n</checkov>" in prompt
    assert "<checkov>" not in review.build_prompt("+ resource {}", "")


def test_render():
    text = review.render(review.Review.model_validate(REVIEW_JSON), "anthropic.claude-opus-5-5")
    assert "🔴 alto" in text
    assert "### 🔴 SSH aberto para 0.0.0.0/0" in text
    assert "`examples/terraform/main.tf`" in text
    assert "⚠️ algo deu errado\n\n---" in review.render("algo deu errado", "m")


# --- Seleção do modelo (specs/001-selecao-de-modelo) ---

import anthropic  # noqa: E402
import boto3  # noqa: E402
from botocore.stub import Stubber  # noqa: E402

GPT_OSS = "openai.gpt-oss-120b-1:0"


def aws_client(service: str):
    # Credenciais fictícias: o Stubber intercepta as chamadas antes de qualquer acesso à rede
    return boto3.client(service, region_name="us-east-1", aws_access_key_id="teste", aws_secret_access_key="teste")


def converse_response(content: list, stop_reason: str = "tool_use") -> dict:
    return {
        "output": {"message": {"role": "assistant", "content": content}},
        "stopReason": stop_reason,
        "usage": {"inputTokens": 10, "outputTokens": 10, "totalTokens": 20},
        "metrics": {"latencyMs": 1},
    }


def tool_use(data: dict) -> dict:
    return {"toolUse": {"toolUseId": "t1", "name": review.TOOL_NAME, "input": data}}


def test_supported_models_list():
    assert review.DEFAULT_MODEL in review.SUPPORTED_MODELS
    assert review.SUPPORTED_MODELS[review.DEFAULT_FALLBACK_MODEL].api == "mantle"
    assert review.SUPPORTED_MODELS[GPT_OSS].api == "converse"
    assert "não é suportado" in review.unsupported_message("modelo.qualquer")
    assert f"`{GPT_OSS}`" in review.unsupported_message("modelo.qualquer")


def test_review_schema_has_no_refs_and_keeps_title_field():
    schema = review.review_schema()
    text = json.dumps(schema)
    assert "$ref" not in text and "$defs" not in text
    finding = schema["properties"]["findings"]["items"]
    assert "title" in finding["properties"]
    assert set(finding["required"]) == {"file", "severity", "title", "explanation", "suggestion"}
    assert finding["additionalProperties"] is False


def test_converse_forced_tool_returns_review():
    client = aws_client("bedrock-runtime")
    with Stubber(client) as stub:
        stub.add_response("converse", converse_response([tool_use(REVIEW_JSON)]))
        result = review.ask_converse(client, GPT_OSS, review.build_prompt("diff", ""))
    assert isinstance(result, review.Review)
    assert result.findings[0].title == "SSH aberto para 0.0.0.0/0"


def test_converse_sends_forced_tool_with_schema():
    client = aws_client("bedrock-runtime")
    with Stubber(client) as stub:
        stub.add_response(
            "converse",
            converse_response([tool_use(REVIEW_JSON)]),
            expected_params={
                "modelId": GPT_OSS,
                "system": [{"text": review.SYSTEM_PROMPT}],
                "messages": [{"role": "user", "content": [{"text": "p"}]}],
                "toolConfig": {
                    "tools": [
                        {
                            "toolSpec": {
                                "name": review.TOOL_NAME,
                                "description": "Registra a revisão do Pull Request.",
                                "inputSchema": {"json": review.review_schema()},
                            }
                        }
                    ],
                    "toolChoice": {"tool": {"name": review.TOOL_NAME}},
                },
                "inferenceConfig": {"maxTokens": 8000},
            },
        )
        review.ask_converse(client, GPT_OSS, "p")


def test_converse_retries_once_on_invalid_answer():
    client = aws_client("bedrock-runtime")
    with Stubber(client) as stub:
        stub.add_response("converse", converse_response([{"text": "sem ferramenta"}], "end_turn"))
        stub.add_response("converse", converse_response([tool_use(REVIEW_JSON)]))
        result = review.ask_converse(client, GPT_OSS, "p")
    assert isinstance(result, review.Review)


def test_converse_gives_up_after_two_invalid_answers():
    client = aws_client("bedrock-runtime")
    invalid = {**REVIEW_JSON, "findings": [{"resource": "aws_security_group.web"}]}
    with Stubber(client) as stub:
        stub.add_response("converse", converse_response([tool_use(invalid)]))
        stub.add_response("converse", converse_response([tool_use(invalid)]))
        result = review.ask_converse(client, GPT_OSS, "p")
        stub.assert_no_pending_responses()
    assert result == "Não foi possível interpretar a resposta do modelo."


def test_converse_max_tokens():
    client = aws_client("bedrock-runtime")
    with Stubber(client) as stub:
        stub.add_response("converse", converse_response([{"text": "..."}], "max_tokens"))
        result = review.ask_converse(client, GPT_OSS, "p")
    assert "limite de tokens" in result


@pytest.mark.parametrize(
    ("code", "expected"),
    [
        ("AccessDeniedException", "não está disponível para esta conta"),
        ("ResourceNotFoundException", "não existe nesta região"),
        ("ThrottlingException", "limite de uso"),
        ("InternalServerException", "Veja o log do job"),
    ],
)
def test_converse_errors_are_explained(code, expected):
    client = aws_client("bedrock-runtime")
    with Stubber(client) as stub:
        stub.add_client_error("converse", service_error_code=code, service_message="arn:aws:iam::111122223333:x")
        with pytest.raises(review.ClientError) as exc:
            review.ask_converse(client, GPT_OSS, "p")
    message = review.explain_error(exc.value, GPT_OSS)
    assert expected in message
    assert "111122223333" not in message  # o erro original não vai para o comentário


@pytest.mark.parametrize(("status", "expected"), [(403, "não está disponível para esta conta"), (404, "não existe")])
def test_mantle_errors_are_explained(fake_bedrock, status, expected):
    client, state = fake_bedrock
    state["status"] = status
    with pytest.raises(anthropic.APIStatusError) as exc:
        review.ask_claude(client, review.DEFAULT_MODEL, "p")
    assert expected in review.explain_error(exc.value, review.DEFAULT_MODEL)


def availability(model_id: str, status: str) -> dict:
    return {
        "modelId": model_id,
        "agreementAvailability": {"status": status},
        "authorizationStatus": "AUTHORIZED",
        "entitlementAvailability": "AVAILABLE",
        "regionAvailability": "AVAILABLE",
    }


def test_list_models_shows_agreement_and_probe():
    client = aws_client("bedrock")
    with Stubber(client) as stub:
        for model_id in review.SUPPORTED_MODELS:
            status = "AVAILABLE" if model_id.startswith("openai.") else "NOT_AVAILABLE"
            stub.add_response("get_foundation_model_availability", availability(model_id, status), {"modelId": model_id})
        text = review.list_models(client, tester=lambda m: "ok" if m.api == "converse" else "acesso negado")
    assert f"| `{GPT_OSS}` | openai | gpt-oss-120b | AVAILABLE | ok |" in text
    assert f"| `{review.DEFAULT_MODEL}` | anthropic | Claude Opus 5.5 | NOT_AVAILABLE | acesso negado |" in text
    assert "Chamada" in text


def test_list_models_without_permission():
    client = aws_client("bedrock")
    with Stubber(client) as stub:
        for _ in review.SUPPORTED_MODELS:
            stub.add_client_error("get_foundation_model_availability", service_error_code="AccessDeniedException")
        text = review.list_models(client)
    assert text.count("| desconhecido |") == len(review.SUPPORTED_MODELS)
    assert "bedrock:GetFoundationModelAvailability" in text
    assert "--test" in text


def run_main(monkeypatch, tmp_path, env: dict, diff: str = "+ resource {}") -> str:
    monkeypatch.setattr(review, "get_diff", lambda base: diff)
    calls = []
    monkeypatch.setattr(review, "run_review", lambda *a: calls.append(a) or review.Review.model_validate(REVIEW_JSON))
    for key in ("MODEL_ID", "FALLBACK_MODEL_ID"):
        monkeypatch.delenv(key, raising=False)
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    output = tmp_path / "review.md"
    monkeypatch.setattr(sys, "argv", ["review.py", "--base", "main", "--output", str(output)])
    assert review.main() == 0
    return output.read_text(), calls


def test_main_uses_default_model(monkeypatch, tmp_path):
    text, calls = run_main(monkeypatch, tmp_path, {"MODEL_ID": ""})
    assert calls[0][0].model_id == review.DEFAULT_MODEL
    assert f"Gerado por `{review.DEFAULT_MODEL}`" in text


def test_main_uses_chosen_model(monkeypatch, tmp_path):
    text, calls = run_main(monkeypatch, tmp_path, {"MODEL_ID": GPT_OSS})
    assert calls[0][0].model_id == GPT_OSS
    assert f"Gerado por `{GPT_OSS}`" in text


def test_main_rejects_unsupported_model(monkeypatch, tmp_path):
    text, calls = run_main(monkeypatch, tmp_path, {"MODEL_ID": "modelo.qualquer"})
    assert calls == []
    assert "não é suportado" in text


def test_main_rejects_invalid_fallback(monkeypatch, tmp_path):
    text, calls = run_main(monkeypatch, tmp_path, {"FALLBACK_MODEL_ID": GPT_OSS})
    assert calls == []
    assert "FALLBACK_MODEL_ID" in text


def test_main_requires_base_unless_listing(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["review.py"])
    with pytest.raises(SystemExit):
        review.main()
