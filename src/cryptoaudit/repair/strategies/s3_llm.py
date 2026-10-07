"""S3: single-shot local LLM repair strategy."""

from cryptoaudit.core.errors import CryptoAuditError
from cryptoaudit.core.identity import finding_id
from cryptoaudit.llm.client import DEFAULT_MODEL, LLMClient, LLMRequest
from cryptoaudit.repair.base import RepairStrategy
from cryptoaudit.repair.models import GenerationMetadata, RepairRequest, RepairResult, RepairStatus, StrategyId
from cryptoaudit.repair.prompting import DEFAULT_MAX_CODE_CHARS, OutputParseError, parse_llm_output, render_prompt


class LLMRepairStrategy(RepairStrategy):
    """
    One prompt, one generation, one strict parse. There is no retry and no feedback
    from validation: the LLM's output is recorded as-is and judged elsewhere.
    """

    strategy_id = StrategyId.S3
    template_name = "s3_v1"

    def __init__(
        self,
        client: LLMClient,
        model: str = DEFAULT_MODEL,
        temperature: float = 0.0,
        seed: int = 0,
        max_tokens: int = 4096,
        max_code_chars: int = DEFAULT_MAX_CODE_CHARS,
    ) -> None:
        self.client = client
        self.model = model
        self.temperature = temperature
        self.seed = seed
        self.max_tokens = max_tokens
        self.max_code_chars = max_code_chars

    def _repair(self, request: RepairRequest) -> RepairResult:
        prompt = render_prompt(request, self.template_name)
        metadata = GenerationMetadata(
            model=self.model,
            prompt_version=prompt.version,
            prompt_hash=prompt.prompt_hash,
            temperature=self.temperature,
            seed=self.seed,
            max_tokens=self.max_tokens,
        )
        llm_request = LLMRequest(
            model=self.model,
            system=prompt.system,
            prompt=prompt.user,
            temperature=self.temperature,
            seed=self.seed,
            max_tokens=self.max_tokens,
        )
        try:
            response = self.client.generate(llm_request)
        except CryptoAuditError as exc:
            return self.failure(RepairStatus.NO_REPAIR, exc.message, exc.code, generation=metadata)

        metadata = metadata.model_copy(update={"raw_output": response.text, "model_digest": response.model_digest})
        all_ids = [finding_id(f) for f in request.findings]
        try:
            code = parse_llm_output(response.text, self.max_code_chars)
        except OutputParseError as exc:
            return self.failure(
                RepairStatus.PARSE_ERROR, str(exc), unrepaired_finding_ids=all_ids, generation=metadata
            )

        return RepairResult(
            strategy_id=self.strategy_id,
            status=RepairStatus.PRODUCED,
            candidate_code=code,
            repaired_finding_ids=all_ids,
            notes=["LLM output is an unvalidated candidate; repaired_finding_ids are the targeted findings"],
            generation=metadata,
        )
