# CallTrap Artifact

This repository accompanies the paper **"When Scammers Talk Back: Understanding Potentially Unwanted Calls via LLM-Based Interaction"** (CCS 2026).

## Contents

- [`system_implementation.py`](system_implementation.py): the sanitized system implementation used to operate CallTrap. Deployment-specific values remain as placeholders.
- [`coded_dataset/`](coded_dataset/): the redacted coded dataset, divided into five JSON files. Together, the files contain 2,429 call records.
- [`codebook.pdf`](codebook.pdf): the original artifact codebook.
- [`supplementary_material/full_appendix.pdf`](supplementary_material/full_appendix.pdf): the full appendix, including the classification criteria, system prompt, codebook, persuasion-technique definitions, method details, ethical discussion, and representative conversation examples.

## System Implementation

`system_implementation.py` is provided as the sanitized research implementation. API keys, service credentials, public hostnames, routes, prompts, and voice identifiers are represented by placeholder values. The file is provided as-is and requires users to supply their own service configuration before deployment.

## Redacted Coded Dataset

The five files in `coded_dataset/` preserve the JSON organization used in the original artifact. Records are grouped by call-duration bucket. Caller names, organization names, phone numbers, and other sensitive information have been redacted; redacted values are represented as `*****`.

The camera-ready dataset uses the final coding framework. The `persuasion` field contains the original persuasion categories (`auth`, `crc`, `dis`, `lsd`, and `sp`). The `complementary_persuasion` field contains the added categories:

- `nag`: Need and Greed (`NG` in the paper)
- `time`: Time
- `dh`: Dishonesty (`DSH` in the paper)

For compatibility with the original framework, retained `nag` and `time` annotations are also mapped to `dis`, while retained `dh` annotations are mapped to `crc` in the original `persuasion` field.

## Supplementary Material

The [full appendix](supplementary_material/full_appendix.pdf) contains:

1. Open-science and ethical considerations
2. Generative-AI usage disclosure
3. PUC call-classification criteria
4. The complete system prompt with synthetic placeholders
5. The annotation codebook
6. Persuasion-technique definitions
7. Call topics and information-sensitivity tiers
8. The sampling-distribution comparison
9. The campaign-identification algorithm
10. Representative conversation examples


