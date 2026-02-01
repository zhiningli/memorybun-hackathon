# MemoryBun Database Schema Hardening

> **Version**: 1.1  
> **Last Updated**: January 2026  
> **Status**: Phase 1 Complete

---

## Overview

This document tracks schema changes to prepare data models for production database storage.

| Phase | Service | Status |
|-------|---------|--------|
| Phase 1 | Question Service | ✅ **Complete** |
| Phase 2 | Transcription Service | ⏸️ Deferred (post-MVP) |
| Phase 3 | Grading Service | ⏸️ Deferred (post-MVP) |

---

## Phase 1: Question Service ✅

### Changes Implemented

All schemas updated with snake_case naming, field constraints, and multi-value support.

#### Question Table
| Field | Change |
|-------|--------|
| `think_time_limit_seconds` | ✅ Renamed from camelCase |
| `record_time_limit_seconds` | ✅ Renamed from camelCase |
| `question_image_url` | ✅ Renamed from `questionImage` |
| `hints: List[Hint]` | ✅ Multi-hint support (was single `hint`) |
| `subjects: List[SubjectEnum]` | ✅ New required field |
| `topics: List[QuestionTopicEnum]` | ✅ Multi-value (was `category`) |
| `difficulty` | ✅ Now required |
| `rubric_id` | ✅ Now required (FK) |
| `isPlottingQuestion` | ❌ Removed (use `topics`) |
| `dependency_ids` | ❌ Removed (deprecated) |

#### Hint Schema
| Field | Change |
|-------|--------|
| `text` | ✅ Optional, max 1000 chars |
| `image_url` | ✅ New (renamed from `graph_tip`) |
| Validation | ✅ At least one field required |

#### Answer Table
| Field | Change |
|-------|--------|
| `graph_answer_url` | ✅ Renamed from `graph_answer` |
| `text_answer` | ✅ max_length=5000 added |

#### QuestionListMetadata Table
| Field | Change |
|-------|--------|
| `categories: List[Enum]` | ✅ Multi-value (was single `category`) |
| `subjects: List[SubjectEnum]` | ✅ New required field |
| `duration_seconds` | ✅ Renamed from `duration` |
| `access_status: AccessStatusEnum` | ✅ Replaces `is_public` boolean |
| `updated_at` | ✅ New audit field |

#### QuestionListItem Table (Join Table)
| Field | Change |
|-------|--------|
| `weightage: float` | ✅ New (0.0-1.0, must sum to 1.0) |
| `created_at`, `updated_at` | ✅ New audit fields |

#### Rubric Table
| Field | Change |
|-------|--------|
| `name` | ✅ Renamed from `category` |
| `description` | ✅ New optional field |
| `version` | ✅ New optional field |
| `created_at`, `updated_at` | ✅ New audit fields |

### New Enums Added
- `SubjectEnum`: Engineering, Mathematics, Physics
- `QuestionTopicEnum`: Mathematics, Energy, Electricity, Graph Plotting, Fluid Dynamics
- `AccessStatusEnum`: public, private, premium
- `QuestionListCategoryEnum`: Added GUIDED, FULL_RUN

---

## Phase 2: Transcription Service ⏸️

*Deferred to post-MVP. Will address session/audio metadata schemas.*

---

## Phase 3: Grading Service ⏸️

*Deferred to post-MVP. Will address result storage and user history schemas.*

---

## Database Considerations (Future)

When migrating to a database:

| Pydantic Type | PostgreSQL / DynamoDB |
|---------------|----------------------|
| `str` with `max_length` | `VARCHAR(n)` / String attribute |
| `str` unlimited | `TEXT` / String attribute |
| `List[Enum]` | `JSONB` array / List attribute |
| `datetime` | `TIMESTAMPTZ` / ISO string |
| LaTeX content | Store as text, render client-side |

> [!NOTE]
> Current Pydantic schemas are database-ready. No additional changes needed for LaTeX/math content—databases store it as plain text.
