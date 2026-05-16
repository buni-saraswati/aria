# ARIA — AI Reliability & Integrity Architecture

## The Problem
88% of enterprise AI pilots never reach production (IDC).
Not because the model failed — because the system around it did.

## What ARIA Does
ARIA is the missing accountability layer between AI agents
and enterprise systems. Every action an AI wants to take
gets classified, routed, approved, executed, and logged.

## Architecture
[diagram]

## Decision Lifecycle
submitted → validating → classified → pending_approval
         → approved → executing → completed → rolled_back

## Key Features
- Data freshness validation before any action runs
- AI classification (reversible/irreversible, low/critical)
- Business rules engine that overrides AI when needed
- Human-in-the-loop approval workflow with TTL
- Pre-action snapshots + rollback
- Immutable audit trail — every decision, every actor
- Full observability via Azure Monitor

## Tech Stack
FastAPI · Azure Cosmos DB · Azure Event Hub
Azure OpenAI (GPT-4.1 mini) · Azure Blob Storage
Azure Container Apps · Azure Application Insights
Docker · Python 3.11

## Live Demo
https://ca-aria-dev.purpleisland-b4cd0839.centralus.azurecontainerapps.io/docs