## Temperature policy for deductive coding

This project defaults to a low temperature because its main use case is structured qualitative scoring that is close to deductive coding rather than open-ended idea generation. In annotation and analytical tasks, lower temperatures generally produce more focused and reproducible outputs, whereas higher temperatures increase randomness and response diversity (Anthropic, n.d.-a; OpenAI, n.d.-a; Törnberg, 2024). The qualitative-coding literature points in the same direction: Törnberg (2024) recommends low temperature for annotation, and Wen et al. (2026) used temperature 0 for deductive coding while reserving temperature 0.5 for inductive coding.

For the primary analysis, this software recommends a fixed low temperature and does not treat temperature variation as part of the default scoring workflow. A practical default is `temperature = 0.0` for the main analysis, with `0.1` to `0.2` reserved as documented fallback values when exact zero performs poorly for a specific model or provider. Outputs generated under substantially different temperatures should not be pooled into the default score unless that pooling is itself the object of a separate robustness analysis (Borchers et al., 2025; Wen et al., 2026; Wulcan et al., 2025).

Low temperature does not eliminate all variability. Official guidance and empirical studies both note that temperature 0 is not perfectly deterministic, and LLM-based judgments can still vary across repeated runs, which is why this project supports repeated same-temperature calls and summary statistics over replicates (Anthropic, n.d.-a; Haldar & Hockenmaier, 2025; Ouyang et al., 2025). When additional robustness is needed, prompt-stability checks are preferable to simply adding more sampling randomness (Barrie et al., 2024; Törnberg, 2024).

Some model families require explicit exceptions. For example, Google currently recommends keeping Gemini 3 at its default temperature rather than lowering it, so the software allows provider-specific temperature overrides that are recorded in metadata instead of forcing a single rule onto every model family (Google, n.d.).

### How the scripts should implement this policy

The main analysis should run repeated calls with the same low temperature for each fixed `row_id × model × prompt_version × method` combination. The code should store both the requested temperature and the effective temperature actually used, together with the model identifier, model version, prompt version, schema version, seed if available, a structured `parse_status` for each call, and any validation error message verbatim. If reasoning models are used, the thinking budget should also remain fixed within each replicate set.

Optional temperature sweeps should be implemented as a separate robustness module and written to separate intermediate and output files rather than pooled into the primary score by default. Where the provider supports schema-constrained structured outputs, the scripts should use them so that residual variability reflects substantive judgment differences more than output-format noise (Anthropic, n.d.-b; OpenAI, n.d.-b). The scripts should also avoid jointly tuning `temperature` and `top_p` unless that is part of an explicit experiment, because both OpenAI and Anthropic recommend changing one or the other, not both (Anthropic, n.d.-a; OpenAI, n.d.-a).

## Why the software stores all LLM outputs

This software should automatically store the full LLM output together with the prompt, a structured `parse_status`, any validation error message verbatim, model identifier, model version when available, and other run metadata. That level of logging is necessary because LLM services can change over time in ways that are not visible from the prompt alone. Prior work documents short-horizon service drift in instruction-following and output formatting, ongoing temporal evolution in ChatGPT behavior, nondeterminism and drift in repeated real-world use, and preregistered longitudinal drift even when researchers attempt to hold workflows constant (Aronson et al., 2024; Chen et al., 2024; Tu et al., 2024; Wiese, 2026).

For this project, complete output storage is therefore a scientific and engineering safeguard rather than a convenience feature. Hidden drift can alter scores, break JSON parsing, change category frequencies, or create prompt-specific artifacts without any obvious code change on the user side. Retaining the full outputs and metadata makes it possible to audit failures, detect model drift, re-run analyses under controlled conditions, and distinguish substantive variation from pipeline instability (Brucks & Toubia, 2025; Li et al., 2025; Nicholson, 2026; Payne et al., 2024; Tschisgale & Wulff, 2026).

## References

Aronson, S. J., Machini, K., Shin, J., Sriraman, P., Hamill, S., Henricks, E. R., Mailly, C., Nottage, A. J., Amr, S. S., Oates, M., & Lebo, M. S. (2024). GPT-4 performance, nondeterminism, and drift in genetic literature review. *NEJM AI, 1*(9), AIcs2400245. https://doi.org/10.1056/AIcs2400245

Anthropic. (n.d.-a). *Create a text completion*. Claude API Docs. Retrieved March 11, 2026, from https://platform.claude.com/docs/en/api/completions/create

Anthropic. (n.d.-b). *Increase output consistency*. Claude API Docs. Retrieved March 11, 2026, from https://platform.claude.com/docs/en/test-and-evaluate/strengthen-guardrails/increase-consistency

Barrie, C., Palaiologou, E., & Törnberg, P. (2024). Prompt stability scoring for text annotation with large language models [Preprint]. *arXiv*. https://doi.org/10.48550/arXiv.2407.02039

Borchers, C., Shahrokhian, B., Balzan, F., Tajik, E., Sankaranarayanan, S., & Simon, S. (2025). Temperature and persona shape LLM agent consensus with minimal accuracy gains in qualitative coding [Preprint]. *arXiv*. https://doi.org/10.48550/arXiv.2507.11198

Brucks, M., & Toubia, O. (2025). Prompt architecture induces methodological artifacts in large language models. *PLOS ONE, 20*(4), e0319159. https://doi.org/10.1371/journal.pone.0319159

Chen, L., Zaharia, M., & Zou, J. (2024). How is ChatGPT's behavior changing over time? *Harvard Data Science Review, 6*(2). https://doi.org/10.1162/99608f92.5317da47

Google. (n.d.). *Gemini 3 developer guide*. Gemini API. Retrieved March 11, 2026, from https://ai.google.dev/gemini-api/docs/gemini-3

Haldar, R., & Hockenmaier, J. (2025). Rating roulette: Self-inconsistency in LLM-as-a-judge frameworks. In C. Christodoulopoulos, T. Chakraborty, C. Rose, & V. Peng (Eds.), *Findings of the Association for Computational Linguistics: EMNLP 2025* (pp. 24986–25004). Association for Computational Linguistics. https://doi.org/10.18653/v1/2025.findings-emnlp.1361

Li, X., Kreuzwieser, J., & Peters, A. (2025). When meaning stays the same, but models drift: Evaluating quality of service under token-level behavioral instability in LLMs [Preprint]. *arXiv*. https://doi.org/10.48550/arXiv.2506.10095

Nicholson, C. (2026). Quantifying non-deterministic drift in large language models [Preprint]. *arXiv*. https://doi.org/10.48550/arXiv.2601.19934

OpenAI. (n.d.-a). *Create a model response*. OpenAI API. Retrieved March 11, 2026, from https://developers.openai.com/api/reference/resources/responses/methods/create/

OpenAI. (n.d.-b). *Structured model outputs*. OpenAI API. Retrieved March 11, 2026, from https://developers.openai.com/api/docs/guides/structured-outputs/

Ouyang, S., Zhang, J. M., Harman, M., & Wang, M. (2025). An empirical study of the non-determinism of ChatGPT in code generation. *ACM Transactions on Software Engineering and Methodology, 34*(2), Article 42. https://doi.org/10.1145/3697010

Payne, D. L., Purohit, K., Morales Borrero, W., Chung, K., Hao, M., Mpoy, M., Jin, M., Prasanna, P., & Hill, V. (2024). Performance of GPT-4 on the American College of Radiology In-training Examination: Evaluating accuracy, model drift, and fine-tuning. *Academic Radiology, 31*(7), 3046-3054. https://doi.org/10.1016/j.acra.2024.04.006

Törnberg, P. (2024). Best practices for text annotation with large language models. *Sociologica, 18*(2), 67–85. https://doi.org/10.6092/issn.1971-8853/19461

Tschisgale, P., & Wulff, P. (2026). Evidence for daily and weekly periodic variability in GPT-4o performance [Preprint]. *arXiv*. https://doi.org/10.48550/arXiv.2602.15889

Tu, S., Li, C., Yu, J., Wang, X., Hou, L., & Li, J. (2024). ChatLog: Carefully evaluating the evolution of ChatGPT across time [Preprint]. *arXiv*. https://doi.org/10.48550/arXiv.2304.14106

Wen, C., Clough, P., Paton, R., & Middleton, R. (2026). Leveraging large language models for thematic analysis: A case study in the charity sector. *AI & Society, 41*, 731–748. https://doi.org/10.1007/s00146-025-02487-4

Wiese, T. (2026). Human-anchored longitudinal comparison of generative AI with a bias-calibrated LLM-as-judge. *PLOS ONE, 21*(2), e0339920. https://doi.org/10.1371/journal.pone.0339920

Wulcan, J. M., Jacques, K. L., Lee, M. A., Kovacs, S. L., Dausend, N., Prince, L. E., Wulcan, J., Marsilio, S., & Keller, S. M. (2025). Classification performance and reproducibility of GPT-4 omni for information extraction from veterinary electronic health records. *Frontiers in Veterinary Science, 11*, Article 1490030. https://doi.org/10.3389/fvets.2024.1490030
