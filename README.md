# Arabic Business Agent Evaluation Framework (`ar-biz-agent-eval`)

A production-grade, offline-executable benchmark framework specifically designed to evaluate autonomous AI agents operating in Arabic business environments across the MENA region.

## Key Features

- **Multi-Dialect Coverage**: Rigorous test suites across Modern Standard Arabic (MSA / الفصحى), Gulf/Khaleeji (الخليجية - Saudi/UAE/Kuwaiti), Egyptian (المصرية), Levantine (الشامية), Maghrebi (المغاربية), and Anglo-Arabic Code-Switching (Arabizi & tech jargon).
- **Core Business Domains**:
  - **B2B Sales & CRM**: Lead qualification, enterprise deal pipeline, pricing negotiations, proposal generation.
  - **Billing & Invoicing**: ZATCA phase-2 electronic invoicing, GCC VAT rates (15% KSA, 5% UAE, 14% Egypt), credit notes, multi-currency conversions (SAR, AED, EGP, USD, KWD).
  - **Customer Support & Disputes**: SLA tracking, multi-tier escalation, courteous resolution, Arabic customer sentiments.
  - **Procurement & ERP**: Request for Quotation (RFQ), supplier vetting, purchase orders, inventory checks across regional warehouses.
- **Mock Business Environment Suite**: Complete in-memory simulation of CRM, ERP, Billing, and Support systems with multi-tool execution dispatch, deterministic state transitions, and snapshotting.
- **Multidimensional Evaluation**:
  - `ToolCallEvaluator`: Precision, recall, schema compliance, required/optional parameter accuracy, sequence order, hallucination detection.
  - `BusinessGoalEvaluator`: Environmental state validation, domain compliance (tax rates, currency alignment), end-state criteria.
  - `ArabicCulturalSafetyEvaluator`: Business register, honorifics (طال عمرك، حضرتك، سعادة), religious and cultural etiquette, vulgarity/insult avoidance.
  - `EfficiencyEvaluator`: Turn efficiency, execution latency, redundant tool calls, infinite loop detection.
- **Agent Interoperability**:
  - Built-in deterministic `MockAgent` for offline CI/CD benchmarking (zero API keys required).
  - Production adapters for OpenAI, Google Gemini, Anthropic Claude, and custom HTTP / Agent-to-Agent (A2A) endpoints.
- **CLI & Rich Reporting**:
  - `ar-eval run`: Execute evaluations with custom filters (domain, dialect, agent).
  - `ar-eval scenarios`: List and inspect benchmark scenarios.
  - `ar-eval inspect`: Detailed examination of scenario steps, context, and criteria.
  - `ar-eval report`: Re-render or export reports in Terminal, Markdown, JSON, and HTML formats.

## Installation

```bash
pip install -e .
```

## Quick Start

Run the benchmark using the deterministic offline MockAgent:

```bash
# Run all scenarios with terminal summary
ar-eval run --agent mock --mode perfect

# Run specific dialect (e.g. Gulf) or domain (e.g. Billing)
ar-eval run --agent mock --dialect gulf
ar-eval run --agent mock --domain billing

# Output markdown report and JSON export
ar-eval run --agent mock --output-md benchmark_report.md --output-json results.json
```

## Scenario Example

```yaml
id: "billing_saudi_zatca_vat"
title: "Saudi Enterprise ZATCA E-Invoicing & 15% VAT Verification"
dialect: "gulf"
domain: "billing"
difficulty: "intermediate"
description: "Process a B2B service invoice for a Riyadh client, verify tax number, apply 15% VAT, and record payment."
```

## Architecture

- `ar_biz_agent_eval/core`: Pydantic data schemas, turn models, evaluation results, session state.
- `ar_biz_agent_eval/environments`: Mock CRM, ERP, Billing (ZATCA/VAT), Support desk.
- `ar_biz_agent_eval/scenarios`: Curated benchmark scenarios with dialectal context and criteria.
- `ar_biz_agent_eval/agents`: Base agent contract, MockAgent, OpenAI, Gemini, Claude, HTTP/A2A.
- `ar_biz_agent_eval/evaluators`: Tool calling, business goal, cultural safety, and efficiency evaluators.
- `ar_biz_agent_eval/reporting`: Rich CLI UI, Markdown generator, JSON/HTML exports.
- `ar_biz_agent_eval/cli`: Typer CLI entrypoint.
