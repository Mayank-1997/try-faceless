# Database Schema Design — AI Video Studio

## Design Principles

- **Normalized** — no duplicated data; foreign keys enforce referential integrity.
- **UUID primary keys** — globally unique, URL-safe, no integer auto-increment.
- **Soft delete** — `is_deleted` boolean on every table; no hard deletes.
- **Timestamps** — `created_at` and `updated_at` on every table (timezone-aware UTC).
- **Indexes** — on all foreign keys, frequently-filtered columns, and timestamp columns.
- **Relationships** — explicit foreign keys with `ON DELETE CASCADE` for child tables.

## Tables

### 1. users
| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| id | UUID | PK | |
| email | VARCHAR(255) | UNIQUE, NOT NULL | |
| username | VARCHAR(100) | UNIQUE, NOT NULL | |
| hashed_password | VARCHAR(255) | NOT NULL | |
| role | VARCHAR(20) | NOT NULL, default 'creator' | Enum: admin, creator, viewer |
| is_active | BOOLEAN | NOT NULL, default true | |
| is_verified | BOOLEAN | NOT NULL, default false | |
| youtube_channel_id | VARCHAR(255) | NULLABLE | Linked YouTube channel |
| youtube_access_token | TEXT | NULLABLE | OAuth token (encrypted at rest) |
| youtube_refresh_token | TEXT | NULLABLE | OAuth refresh token |
| youtube_token_expires_at | TIMESTAMPTZ | NULLABLE | |
| created_at | TIMESTAMPTZ | NOT NULL | |
| updated_at | TIMESTAMPTZ | NOT NULL | |
| is_deleted | BOOLEAN | NOT NULL, default false | |

**Indexes**: `ix_users_email` (unique), `ix_users_username` (unique), `ix_users_created_at`

---

### 2. projects
| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| id | UUID | PK | |
| user_id | UUID | FK → users.id, NOT NULL | |
| name | VARCHAR(255) | NOT NULL | |
| description | TEXT | NULLABLE | |
| input_type | VARCHAR(20) | NOT NULL | Enum: topic, script |
| topic | TEXT | NULLABLE | Required if input_type = topic |
| input_script | TEXT | NULLABLE | Required if input_type = script |
| status | VARCHAR(20) | NOT NULL, default 'draft' | Enum: ProjectStatus |
| target_duration_seconds | INTEGER | NULLABLE | Desired video length |
| target_resolution | VARCHAR(20) | NULLABLE, default '1920x1080' | |
| voice_language | VARCHAR(10) | NULLABLE, default 'en-US' | |
| voice_gender | VARCHAR(10) | NULLABLE | Enum: VoiceGender |
| voice_tone | VARCHAR(20) | NULLABLE | Enum: VoiceTone |
| total_cost_usd | DECIMAL(10,6) | NULLABLE, default 0 | Running cost |
| total_tokens_used | BIGINT | NULLABLE, default 0 | Running token count |
| quality_score | DECIMAL(3,2) | NULLABLE | 0.00–1.00 |
| created_at | TIMESTAMPTZ | NOT NULL | |
| updated_at | TIMESTAMPTZ | NOT NULL | |
| is_deleted | BOOLEAN | NOT NULL, default false | |

**Indexes**: `ix_projects_user_id`, `ix_projects_status`, `ix_projects_created_at`

---

### 3. videos
| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| id | UUID | PK | |
| project_id | UUID | FK → projects.id, NOT NULL, CASCADE | |
| title | VARCHAR(500) | NOT NULL | |
| description | TEXT | NULLABLE | |
| duration_seconds | INTEGER | NULLABLE | Final rendered duration |
| resolution_width | INTEGER | NULLABLE | |
| resolution_height | INTEGER | NULLABLE | |
| fps | INTEGER | NULLABLE | |
| file_path | VARCHAR(1024) | NULLABLE | Path to rendered video |
| file_size_bytes | BIGINT | NULLABLE | |
| thumbnail_path | VARCHAR(1024) | NULLABLE | |
| status | VARCHAR(20) | NOT NULL | Enum: ProjectStatus (rendering stage) |
| created_at | TIMESTAMPTZ | NOT NULL | |
| updated_at | TIMESTAMPTZ | NOT NULL | |
| is_deleted | BOOLEAN | NOT NULL, default false | |

**Indexes**: `ix_videos_project_id`, `ix_videos_status`, `ix_videos_created_at`

---

### 4. research
| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| id | UUID | PK | |
| project_id | UUID | FK → projects.id, NOT NULL, CASCADE | |
| query | TEXT | NOT NULL | Search query used |
| sources | JSONB | NOT NULL, default '[]' | Array of source objects |
| key_facts | JSONB | NOT NULL, default '[]' | Extracted facts |
| summary | TEXT | NULLABLE | AI-generated research summary |
| model_used | VARCHAR(50) | NOT NULL | |
| tokens_used | INTEGER | NOT NULL | |
| cost_usd | DECIMAL(10,6) | NOT NULL | |
| created_at | TIMESTAMPTZ | NOT NULL | |
| updated_at | TIMESTAMPTZ | NOT NULL | |
| is_deleted | BOOLEAN | NOT NULL, default false | |

**Indexes**: `ix_research_project_id`, `ix_research_created_at`

---

### 5. scripts
| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| id | UUID | PK | |
| project_id | UUID | FK → projects.id, NOT NULL, CASCADE | |
| version | INTEGER | NOT NULL, default 1 | Script revision number |
| title | VARCHAR(500) | NOT NULL | |
| content | TEXT | NOT NULL | Full script text |
| hook | TEXT | NULLABLE | Opening hook |
| intro | TEXT | NULLABLE | |
| body | TEXT | NULLABLE | |
| outro | TEXT | NULLABLE | Call to action |
| word_count | INTEGER | NULLABLE | |
| estimated_duration_seconds | INTEGER | NULLABLE | |
| model_used | VARCHAR(50) | NOT NULL | |
| tokens_used | INTEGER | NOT NULL | |
| cost_usd | DECIMAL(10,6) | NOT NULL | |
| quality_score | DECIMAL(3,2) | NULLABLE | |
| created_at | TIMESTAMPTZ | NOT NULL | |
| updated_at | TIMESTAMPTZ | NOT NULL | |
| is_deleted | BOOLEAN | NOT NULL, default false | |

**Indexes**: `ix_scripts_project_id`, `ix_scripts_version`, `ix_scripts_created_at`

---

### 6. scenes
| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| id | UUID | PK | |
| project_id | UUID | FK → projects.id, NOT NULL, CASCADE | |
| script_id | UUID | FK → scripts.id, NOT NULL | |
| scene_number | INTEGER | NOT NULL | Sequential |
| title | VARCHAR(255) | NOT NULL | |
| narration | TEXT | NOT NULL | Voice-over text for this scene |
| start_time | DECIMAL(10,3) | NULLABLE | Seconds from video start |
| end_time | DECIMAL(10,3) | NULLABLE | |
| estimated_duration | DECIMAL(10,3) | NULLABLE | Seconds |
| visual_importance_score | DECIMAL(3,2) | NULLABLE | 0.00–1.00 |
| audience_attention_score | DECIMAL(3,2) | NULLABLE | 0.00–1.00 |
| visual_type | VARCHAR(20) | NULLABLE | Enum: VisualType |
| asset_decision | VARCHAR(20) | NULLABLE | Enum: AssetDecision |
| camera_angle | VARCHAR(20) | NULLABLE | Enum: CameraAngle |
| camera_motion | VARCHAR(20) | NULLABLE | Enum: CameraMotion |
| lens | VARCHAR(100) | NULLABLE | |
| lighting | VARCHAR(100) | NULLABLE | |
| composition | VARCHAR(100) | NULLABLE | |
| emotion | VARCHAR(50) | NULLABLE | |
| color_palette | JSONB | NULLABLE | Array of hex colors |
| transition | VARCHAR(20) | NULLABLE | Enum: TransitionType |
| music_suggestion | VARCHAR(255) | NULLABLE | |
| sound_effects | JSONB | NULLABLE | Array of SFX descriptions |
| image_prompt | TEXT | NULLABLE | |
| video_prompt | TEXT | NULLABLE | |
| negative_prompt | TEXT | NULLABLE | |
| animation_instructions | TEXT | NULLABLE | |
| subtitle_text | TEXT | NULLABLE | |
| voice_timing | JSONB | NULLABLE | Word-level timing data |
| created_at | TIMESTAMPTZ | NOT NULL | |
| updated_at | TIMESTAMPTZ | NOT NULL | |
| is_deleted | BOOLEAN | NOT NULL, default false | |

**Indexes**: `ix_scenes_project_id`, `ix_scenes_script_id`, `ix_scenes_scene_number`, `ix_scenes_created_at`

---

### 7. assets
| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| id | UUID | PK | |
| project_id | UUID | FK → projects.id, NOT NULL, CASCADE | |
| scene_id | UUID | FK → scenes.id, NULLABLE | NULL for project-level assets (thumbnail) |
| asset_type | VARCHAR(20) | NOT NULL | Enum: AssetType |
| status | VARCHAR(20) | NOT NULL, default 'planned' | Enum: AssetStatus |
| provider | VARCHAR(30) | NULLABLE | Enum: AIProvider |
| prompt_used | TEXT | NULLABLE | |
| negative_prompt | TEXT | NULLABLE | |
| metadata | JSONB | NULLABLE | Provider-specific metadata |
| quality_score | DECIMAL(3,2) | NULLABLE | |
| cost_usd | DECIMAL(10,6) | NULLABLE | |
| tokens_used | INTEGER | NULLABLE | |
| created_at | TIMESTAMPTZ | NOT NULL | |
| updated_at | TIMESTAMPTZ | NOT NULL | |
| is_deleted | BOOLEAN | NOT NULL, default false | |

**Indexes**: `ix_assets_project_id`, `ix_assets_scene_id`, `ix_assets_asset_type`, `ix_assets_status`

---

### 8. image_assets
| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| id | UUID | PK | |
| asset_id | UUID | FK → assets.id, NOT NULL, CASCADE | |
| file_path | VARCHAR(1024) | NOT NULL | |
| file_size_bytes | BIGINT | NULLABLE | |
| width | INTEGER | NULLABLE | |
| height | INTEGER | NULLABLE | |
| format | VARCHAR(10) | NULLABLE | png, jpg, webp |
| created_at | TIMESTAMPTZ | NOT NULL | |
| updated_at | TIMESTAMPTZ | NOT NULL | |
| is_deleted | BOOLEAN | NOT NULL, default false | |

**Indexes**: `ix_image_assets_asset_id`

---

### 9. video_assets
| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| id | UUID | PK | |
| asset_id | UUID | FK → assets.id, NOT NULL, CASCADE | |
| file_path | VARCHAR(1024) | NOT NULL | |
| file_size_bytes | BIGINT | NULLABLE | |
| width | INTEGER | NULLABLE | |
| height | INTEGER | NULLABLE | |
| fps | INTEGER | NULLABLE | |
| duration_seconds | DECIMAL(10,3) | NULLABLE | |
| format | VARCHAR(10) | NULLABLE | mp4, webm |
| created_at | TIMESTAMPTZ | NOT NULL | |
| updated_at | TIMESTAMPTZ | NOT NULL | |
| is_deleted | BOOLEAN | NOT NULL, default false | |

**Indexes**: `ix_video_assets_asset_id`

---

### 10. voice_assets
| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| id | UUID | PK | |
| asset_id | UUID | FK → assets.id, NOT NULL, CASCADE | |
| scene_id | UUID | FK → scenes.id, NULLABLE | |
| file_path | VARCHAR(1024) | NOT NULL | |
| file_size_bytes | BIGINT | NULLABLE | |
| duration_seconds | DECIMAL(10,3) | NULLABLE | |
| format | VARCHAR(10) | NULLABLE | mp3, wav |
| voice_name | VARCHAR(100) | NULLABLE | |
| language | VARCHAR(10) | NULLABLE | |
| speaking_rate | DECIMAL(5,2) | NULLABLE | |
| pitch | DECIMAL(5,2) | NULLABLE | |
| created_at | TIMESTAMPTZ | NOT NULL | |
| updated_at | TIMESTAMPTZ | NOT NULL | |
| is_deleted | BOOLEAN | NOT NULL, default false | |

**Indexes**: `ix_voice_assets_asset_id`, `ix_voice_assets_scene_id`

---

### 11. subtitles
| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| id | UUID | PK | |
| project_id | UUID | FK → projects.id, NOT NULL, CASCADE | |
| video_id | UUID | FK → videos.id, NULLABLE | |
| format | VARCHAR(10) | NOT NULL, default 'srt' | srt, vtt |
| language | VARCHAR(10) | NOT NULL, default 'en-US' | |
| file_path | VARCHAR(1024) | NOT NULL | |
| content | TEXT | NULLABLE | Raw subtitle text |
| word_count | INTEGER | NULLABLE | |
| created_at | TIMESTAMPTZ | NOT NULL | |
| updated_at | TIMESTAMPTZ | NOT NULL | |
| is_deleted | BOOLEAN | NOT NULL, default false | |

**Indexes**: `ix_subtitles_project_id`, `ix_subtitles_video_id`

---

### 12. generation_jobs
| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| id | UUID | PK | |
| project_id | UUID | FK → projects.id, NOT NULL, CASCADE | |
| agent_type | VARCHAR(30) | NOT NULL | Enum: AgentType |
| asset_id | UUID | FK → assets.id, NULLABLE | |
| status | VARCHAR(20) | NOT NULL, default 'queued' | Enum: JobStatus |
| priority | VARCHAR(10) | NOT NULL, default 'normal' | Enum: JobPriority |
| input_data | JSONB | NULLABLE | |
| output_data | JSONB | NULLABLE | |
| error_message | TEXT | NULLABLE | |
| retry_count | INTEGER | NOT NULL, default 0 | |
| max_retries | INTEGER | NOT NULL, default 3 | |
| started_at | TIMESTAMPTZ | NULLABLE | |
| completed_at | TIMESTAMPTZ | NULLABLE | |
| execution_time_seconds | DECIMAL(10,3) | NULLABLE | |
| cost_usd | DECIMAL(10,6) | NULLABLE | |
| tokens_used | INTEGER | NULLABLE | |
| celery_task_id | VARCHAR(255) | NULLABLE | |
| created_at | TIMESTAMPTZ | NOT NULL | |
| updated_at | TIMESTAMPTZ | NOT NULL | |
| is_deleted | BOOLEAN | NOT NULL, default false | |

**Indexes**: `ix_generation_jobs_project_id`, `ix_generation_jobs_status`, `ix_generation_jobs_agent_type`, `ix_generation_jobs_priority`, `ix_generation_jobs_created_at`

---

### 13. prompt_templates
| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| id | UUID | PK | |
| agent_type | VARCHAR(30) | NOT NULL | Enum: AgentType |
| prompt_name | VARCHAR(100) | NOT NULL | |
| version | VARCHAR(20) | NOT NULL | Semantic version |
| content | TEXT | NOT NULL | Template with placeholders |
| variables | JSONB | NULLABLE | Expected template variables |
| is_active | BOOLEAN | NOT NULL, default true | |
| created_at | TIMESTAMPTZ | NOT NULL | |
| updated_at | TIMESTAMPTZ | NOT NULL | |
| is_deleted | BOOLEAN | NOT NULL, default false | |

**Indexes**: `ix_prompt_templates_agent_type`, `ix_prompt_templates_prompt_name`, `ix_prompt_templates_version`, unique constraint on (agent_type, prompt_name, version)

---

### 14. api_usage
| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| id | UUID | PK | |
| user_id | UUID | FK → users.id, NOT NULL | |
| project_id | UUID | FK → projects.id, NULLABLE | |
| provider | VARCHAR(30) | NOT NULL | Enum: AIProvider |
| model | VARCHAR(50) | NOT NULL | |
| endpoint | VARCHAR(255) | NULLABLE | |
| input_tokens | INTEGER | NOT NULL, default 0 | |
| output_tokens | INTEGER | NOT NULL, default 0 | |
| total_tokens | INTEGER | NOT NULL, default 0 | |
| cost_usd | DECIMAL(10,6) | NOT NULL, default 0 | |
| latency_ms | INTEGER | NULLABLE | |
| request_id | VARCHAR(255) | NULLABLE | |
| success | BOOLEAN | NOT NULL, default true | |
| error_message | TEXT | NULLABLE | |
| created_at | TIMESTAMPTZ | NOT NULL | |
| updated_at | TIMESTAMPTZ | NOT NULL | |
| is_deleted | BOOLEAN | NOT NULL, default false | |

**Indexes**: `ix_api_usage_user_id`, `ix_api_usage_project_id`, `ix_api_usage_provider`, `ix_api_usage_created_at`

---

### 15. credits
| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| id | UUID | PK | |
| user_id | UUID | FK → users.id, NOT NULL, UNIQUE | One balance per user |
| balance | DECIMAL(10,4) | NOT NULL, default 0 | Current credit balance |
| total_purchased | DECIMAL(10,4) | NOT NULL, default 0 | Lifetime purchases |
| total_used | DECIMAL(10,4) | NOT NULL, default 0 | Lifetime consumption |
| currency | VARCHAR(3) | NOT NULL, default 'USD' | |
| created_at | TIMESTAMPTZ | NOT NULL | |
| updated_at | TIMESTAMPTZ | NOT NULL | |
| is_deleted | BOOLEAN | NOT NULL, default false | |

**Indexes**: `ix_credits_user_id` (unique)

---

### 16. schedules
| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| id | UUID | PK | |
| project_id | UUID | FK → projects.id, NOT NULL, CASCADE | |
| user_id | UUID | FK → users.id, NOT NULL | |
| scheduled_at | TIMESTAMPTZ | NOT NULL | When to publish |
| timezone | VARCHAR(50) | NOT NULL, default 'UTC' | |
| privacy_status | VARCHAR(10) | NOT NULL, default 'public' | Enum: PrivacyStatus |
| is_recurring | BOOLEAN | NOT NULL, default false | |
| recurrence_rule | VARCHAR(255) | NULLABLE | iCal RRULE format |
| created_at | TIMESTAMPTZ | NOT NULL | |
| updated_at | TIMESTAMPTZ | NOT NULL | |
| is_deleted | BOOLEAN | NOT NULL, default false | |

**Indexes**: `ix_schedules_project_id`, `ix_schedules_user_id`, `ix_schedules_scheduled_at`

---

### 17. publish_history
| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| id | UUID | PK | |
| project_id | UUID | FK → projects.id, NOT NULL, CASCADE | |
| video_id | UUID | FK → videos.id, NOT NULL | |
| youtube_video_id | VARCHAR(50) | NULLABLE | YouTube-assigned ID |
| status | VARCHAR(20) | NOT NULL, default 'not_published' | Enum: PublishStatus |
| privacy_status | VARCHAR(10) | NOT NULL, default 'private' | Enum: PrivacyStatus |
| published_at | TIMESTAMPTZ | NULLABLE | |
| error_message | TEXT | NULLABLE | |
| response_data | JSONB | NULLABLE | Full API response |
| created_at | TIMESTAMPTZ | NOT NULL | |
| updated_at | TIMESTAMPTZ | NOT NULL | |
| is_deleted | BOOLEAN | NOT NULL, default false | |

**Indexes**: `ix_publish_history_project_id`, `ix_publish_history_video_id`, `ix_publish_history_status`

---

### 18. analytics
| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| id | UUID | PK | |
| project_id | UUID | FK → projects.id, NOT NULL, CASCADE | |
| youtube_video_id | VARCHAR(50) | NULLABLE | |
| view_count | BIGINT | NULLABLE, default 0 | |
| like_count | BIGINT | NULLABLE, default 0 | |
| comment_count | BIGINT | NULLABLE, default 0 | |
| share_count | BIGINT | NULLABLE, default 0 | |
| subscriber_delta | BIGINT | NULLABLE, default 0 | |
| estimated_revenue_usd | DECIMAL(10,4) | NULLABLE | |
| watch_time_hours | DECIMAL(10,2) | NULLABLE | |
| average_view_duration_seconds | DECIMAL(10,2) | NULLABLE | |
| click_through_rate | DECIMAL(5,2) | NULLABLE | Percentage |
| impressions | BIGINT | NULLABLE, default 0 | |
| recorded_at | TIMESTAMPTZ | NOT NULL | Snapshot timestamp |
| created_at | TIMESTAMPTZ | NOT NULL | |
| updated_at | TIMESTAMPTZ | NOT NULL | |
| is_deleted | BOOLEAN | NOT NULL, default false | |

**Indexes**: `ix_analytics_project_id`, `ix_analytics_youtube_video_id`, `ix_analytics_recorded_at`

---

### 19. activity_logs
| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| id | UUID | PK | |
| user_id | UUID | FK → users.id, NULLABLE | NULL for system events |
| project_id | UUID | FK → projects.id, NULLABLE | |
| activity_type | VARCHAR(20) | NOT NULL | Enum: ActivityType |
| agent_type | VARCHAR(30) | NULLABLE | Enum: AgentType (for agent events) |
| message | TEXT | NOT NULL | |
| details | JSONB | NULLABLE | Structured event data |
| level | VARCHAR(10) | NOT NULL, default 'INFO' | Enum: LogLevel |
| ip_address | VARCHAR(45) | NULLABLE | |
| user_agent | VARCHAR(500) | NULLABLE | |
| created_at | TIMESTAMPTZ | NOT NULL | |
| updated_at | TIMESTAMPTZ | NOT NULL | |
| is_deleted | BOOLEAN | NOT NULL, default false | |

**Indexes**: `ix_activity_logs_user_id`, `ix_activity_logs_project_id`, `ix_activity_logs_activity_type`, `ix_activity_logs_created_at`

---

### 20. settings
| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| id | UUID | PK | |
| user_id | UUID | FK → users.id, NOT NULL, UNIQUE | One settings row per user |
| default_voice_language | VARCHAR(10) | NOT NULL, default 'en-US' | |
| default_voice_gender | VARCHAR(10) | NULLABLE | Enum: VoiceGender |
| default_voice_tone | VARCHAR(20) | NULLABLE | Enum: VoiceTone |
| default_resolution | VARCHAR(20) | NOT NULL, default '1920x1080' | |
| default_fps | INTEGER | NOT NULL, default 30 | |
| default_target_duration | INTEGER | NULLABLE | Seconds |
| default_privacy_status | VARCHAR(10) | NOT NULL, default 'private' | Enum: PrivacyStatus |
| auto_publish | BOOLEAN | NOT NULL, default false | |
| cost_limit_per_video | DECIMAL(10,4) | NULLABLE | Max USD per video |
| monthly_cost_limit | DECIMAL(10,4) | NULLABLE | Max USD per month |
| notify_on_completion | BOOLEAN | NOT NULL, default true | |
| notify_on_failure | BOOLEAN | NOT NULL, default true | |
| preferences | JSONB | NULLABLE | Extensible user preferences |
| created_at | TIMESTAMPTZ | NOT NULL | |
| updated_at | TIMESTAMPTZ | NOT NULL | |
| is_deleted | BOOLEAN | NOT NULL, default false | |

**Indexes**: `ix_settings_user_id` (unique)

---

## Entity Relationships

```
users 1──∞ projects
users 1──1 credits
users 1──1 settings
users 1──∞ activity_logs
users 1──∞ api_usage

projects 1──∞ videos
projects 1──∞ research
projects 1──∞ scripts
projects 1──∞ scenes
projects 1──∞ assets
projects 1──∞ subtitles
projects 1──∞ generation_jobs
projects 1──∞ schedules
projects 1──∞ publish_history
projects 1──∞ analytics
projects 1──∞ activity_logs
projects 1──∞ api_usage

scripts 1──∞ scenes

scenes 1──∞ assets
scenes 1──1 voice_assets (via assets)

assets 1──1 image_assets
assets 1──1 video_assets
assets 1──1 voice_assets

videos 1──∞ subtitles
videos 1──∞ publish_history
```

---

## Phase 3 — Implemented Business Domain Schema

The following tables have been implemented in the persistence layer with SQLAlchemy ORM models, Alembic migration (`0002_business_domain`), and async repository implementations.

### Entity Relationship Diagram

```
users 1──∞ projects
projects 1──∞ workflows
projects 1──∞ research
projects 1──∞ scripts
projects 1──∞ storyboards
projects 1──∞ scenes
projects 1──∞ assets
projects 1──∞ generation_jobs
projects 1──∞ prompt_executions
projects 1──∞ cost_records
projects 1──∞ token_usage_records

workflows 1──∞ research       (workflow_id, nullable)
workflows 1──∞ scripts        (workflow_id, nullable)
workflows 1──∞ storyboards    (workflow_id, nullable)
workflows 1──∞ scenes         (workflow_id, nullable)
workflows 1──∞ generation_jobs (workflow_id, nullable)
workflows 1──∞ prompt_executions (workflow_id, nullable)
workflows 1──∞ cost_records   (workflow_id, nullable)
workflows 1──∞ token_usage_records (workflow_id, nullable)

storyboards 1──∞ scenes       (storyboard_id, nullable)
scenes 1──∞ assets            (scene_id, nullable)
scenes 1──∞ generation_jobs   (scene_id, nullable)
scenes 1──∞ prompt_executions (scene_id, nullable)
scenes 1──∞ cost_records      (scene_id, nullable)

generation_jobs 1──∞ cost_records (job_id, nullable)
assets 1──∞ cost_records      (asset_id, nullable)

users 1──∞ cost_records       (user_id, nullable)
users 1──∞ token_usage_records (user_id, nullable)
users 1──∞ projects           (created_by, updated_by, deleted_by)
users 1──∞ workflows          (created_by, updated_by, deleted_by)
users 1──∞ scenes             (created_by, updated_by, deleted_by)
```

### Implemented Tables

#### projects
| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| id | UUID | PK | |
| owner_id | UUID | FK → users.id (CASCADE), NOT NULL | |
| title | VARCHAR(300) | NOT NULL | |
| description | TEXT | default '' | |
| language | VARCHAR(10) | default 'en' | |
| audience | TEXT | default '' | |
| content_type | VARCHAR(50) | default 'youtube_video' | Enum: ContentType |
| video_style | VARCHAR(50) | default 'mixed' | Enum: VideoStyle |
| target_duration_seconds | INTEGER | NULLABLE | |
| status | VARCHAR(20) | default 'draft' | Enum: ProjectStatus |
| current_step | VARCHAR(50) | default 'initialization' | Enum: WorkflowStep |
| tags | TEXT | default '' | JSON-encoded list |
| metadata | TEXT | default '{}' | JSON-encoded dict |
| deleted_at | TIMESTAMPTZ | NULLABLE | Soft-delete timestamp |
| created_by | UUID | FK → users.id (SET NULL) | Audit |
| updated_by | UUID | FK → users.id (SET NULL) | Audit |
| deleted_by | UUID | FK → users.id (SET NULL) | Audit |
| created_at | TIMESTAMPTZ | NOT NULL | |
| updated_at | TIMESTAMPTZ | NOT NULL | |

**Indexes**: owner_id, status, content_type, current_step, created_at

#### workflows
| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| id | UUID | PK | |
| project_id | UUID | FK → projects.id (CASCADE), NOT NULL | |
| version | INTEGER | default 1 | |
| current_step | VARCHAR(50) | default 'initialization' | Enum: WorkflowStep |
| status | VARCHAR(20) | default 'pending' | Enum: WorkflowStatus |
| started_at | TIMESTAMPTZ | NULLABLE | |
| completed_at | TIMESTAMPTZ | NULLABLE | |
| execution_time_seconds | FLOAT | NULLABLE | |
| failure_reason | TEXT | NULLABLE | |
| retry_count | INTEGER | default 0 | |
| checkpoint_ref | VARCHAR(500) | NULLABLE | LangGraph checkpoint reference |
| created_by/updated_by/deleted_by | UUID | FK → users.id (SET NULL) | Audit |
| created_at/updated_at | TIMESTAMPTZ | NOT NULL | |

**Indexes**: project_id, status, current_step

#### research
| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| id | UUID | PK | |
| project_id | UUID | FK → projects.id (CASCADE), NOT NULL | |
| workflow_id | UUID | FK → workflows.id (SET NULL) | |
| summary | TEXT | default '' | |
| timeline | TEXT | default '' | JSON-encoded list |
| interesting_facts | TEXT | default '' | JSON-encoded list |
| sources | TEXT | default '' | JSON-encoded list |
| keywords | TEXT | default '' | JSON-encoded list |
| references | TEXT | default '' | JSON-encoded list |
| statistics | TEXT | default '{}' | JSON-encoded dict |
| audience_pain_points | TEXT | default '' | JSON-encoded list |
| version | INTEGER | default 1 | |
| status | VARCHAR(20) | default 'draft' | Enum: ResearchStatus |
| created_by | UUID | FK → users.id (SET NULL) | |
| created_at/updated_at | TIMESTAMPTZ | NOT NULL | |

**Indexes**: project_id, version, status

#### scripts
| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| id | UUID | PK | |
| project_id | UUID | FK → projects.id (CASCADE), NOT NULL | |
| workflow_id | UUID | FK → workflows.id (SET NULL) | |
| hook | TEXT | default '' | |
| body | TEXT | default '' | |
| cta | TEXT | default '' | |
| word_count | INTEGER | default 0 | |
| estimated_duration_seconds | INTEGER | default 0 | |
| version | INTEGER | default 1 | |
| language | VARCHAR(10) | default 'en' | |
| status | VARCHAR(20) | default 'draft' | Enum: ScriptStatus |
| created_by | UUID | FK → users.id (SET NULL) | |
| created_at/updated_at | TIMESTAMPTZ | NOT NULL | |

**Indexes**: project_id, version, status

#### storyboards
| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| id | UUID | PK | |
| project_id | UUID | FK → projects.id (CASCADE), NOT NULL | |
| workflow_id | UUID | FK → workflows.id (SET NULL) | |
| version | INTEGER | default 1 | |
| scene_count | INTEGER | default 0 | |
| estimated_duration_seconds | INTEGER | default 0 | |
| style | VARCHAR(50) | default 'mixed' | |
| status | VARCHAR(20) | default 'draft' | Enum: StoryboardStatus |
| narrative_structure | TEXT | default '' | |
| pacing_notes | TEXT | default '' | |
| created_by | UUID | FK → users.id (SET NULL) | |
| created_at/updated_at | TIMESTAMPTZ | NOT NULL | |

**Indexes**: project_id, version, status

#### scenes
| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| id | UUID | PK | |
| project_id | UUID | FK → projects.id (CASCADE), NOT NULL | |
| storyboard_id | UUID | FK → storyboards.id (SET NULL) | |
| workflow_id | UUID | FK → workflows.id (SET NULL) | |
| scene_number | INTEGER | NOT NULL | |
| title | VARCHAR(300) | default '' | |
| duration_seconds | FLOAT | default 0.0 | |
| narration | TEXT | default '' | |
| importance_score | FLOAT | default 0.0 | |
| emotion | VARCHAR(50) | default '' | |
| visual_type | VARCHAR(30) | default 'image' | |
| camera_angle | VARCHAR(30) | NULLABLE | |
| camera_motion | VARCHAR(30) | NULLABLE | |
| lens | VARCHAR(100) | NULLABLE | |
| lighting | VARCHAR(200) | NULLABLE | |
| composition | VARCHAR(200) | NULLABLE | |
| transition | VARCHAR(30) | NULLABLE | |
| subtitle | TEXT | NULLABLE | |
| voice_timing | TEXT | default '{}' | JSON-encoded dict |
| background_music | VARCHAR(200) | NULLABLE | |
| sound_effects | TEXT | default '' | JSON-encoded list |
| generation_status | VARCHAR(30) | default 'pending' | Enum: SceneGenerationStatus |
| review_status | VARCHAR(30) | default 'pending' | Enum: SceneReviewStatus |
| created_by/updated_by/deleted_by | UUID | FK → users.id (SET NULL) | Audit |
| created_at/updated_at | TIMESTAMPTZ | NOT NULL | |

**Indexes**: project_id, storyboard_id, scene_number, generation_status, review_status

#### assets (single-table inheritance)
| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| id | UUID | PK | |
| project_id | UUID | FK → projects.id (CASCADE), NOT NULL | |
| scene_id | UUID | FK → scenes.id (SET NULL) | |
| asset_type | VARCHAR(30) | NOT NULL | Discriminator: image, video, voice, subtitle, thumbnail |
| provider | VARCHAR(50) | default '' | Enum: AIProvider |
| prompt_version | VARCHAR(50) | default '' | |
| generation_cost_usd | FLOAT | default 0.0 | |
| generation_time_seconds | FLOAT | default 0.0 | |
| generation_status | VARCHAR(30) | default 'planned' | Enum: AssetGenerationStatus |
| storage_type | VARCHAR(20) | default 'local' | Enum: StorageType |
| storage_ref | TEXT | default '' | |
| metadata | TEXT | default '{}' | JSON-encoded dict |
| quality_score | FLOAT | NULLABLE | |
| created_by | UUID | FK → users.id (SET NULL) | |
| created_at/updated_at | TIMESTAMPTZ | NOT NULL | |
| **width** | INTEGER | NULLABLE | Image, Video, Thumbnail |
| **height** | INTEGER | NULLABLE | Image, Video, Thumbnail |
| **format** | VARCHAR(10) | NULLABLE | Image, Video, Voice, Subtitle, Thumbnail |
| **prompt** | TEXT | NULLABLE | Image, Video |
| **negative_prompt** | TEXT | NULLABLE | Image |
| **duration_seconds** | FLOAT | NULLABLE | Video, Voice |
| **fps** | INTEGER | NULLABLE | Video |
| **language** | VARCHAR(10) | NULLABLE | Voice, Subtitle |
| **voice_name** | VARCHAR(100) | NULLABLE | Voice |
| **speaking_rate** | FLOAT | NULLABLE | Voice |
| **pitch** | FLOAT | NULLABLE | Voice |
| **word_count** | INTEGER | NULLABLE | Subtitle |
| **is_default** | BOOLEAN | NULLABLE | Thumbnail |

**Indexes**: project_id, scene_id, asset_type, generation_status, created_at

**Inheritance**: Single-table inheritance with `asset_type` as discriminator. Subclasses: `ImageAssetModel`, `VideoAssetModel`, `VoiceAssetModel`, `SubtitleAssetModel`, `ThumbnailAssetModel`.

#### generation_jobs
| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| id | UUID | PK | |
| project_id | UUID | FK → projects.id (CASCADE), NOT NULL | |
| workflow_id | UUID | FK → workflows.id (SET NULL) | |
| scene_id | UUID | FK → scenes.id (SET NULL) | |
| job_type | VARCHAR(30) | NOT NULL | Enum: JobType |
| status | VARCHAR(20) | default 'queued' | Enum: JobStatus |
| priority | VARCHAR(20) | default 'normal' | Enum: JobPriority |
| payload | TEXT | default '{}' | JSON-encoded dict |
| result | TEXT | default '{}' | JSON-encoded dict |
| error_message | TEXT | NULLABLE | |
| retry_count | INTEGER | default 0 | |
| max_retries | INTEGER | default 3 | |
| queued_at | TIMESTAMPTZ | NOT NULL | |
| started_at | TIMESTAMPTZ | NULLABLE | |
| completed_at | TIMESTAMPTZ | NULLABLE | |
| execution_time_seconds | FLOAT | NULLABLE | |
| created_by | UUID | FK → users.id (SET NULL) | |
| created_at/updated_at | TIMESTAMPTZ | NOT NULL | |

**Indexes**: project_id, workflow_id, scene_id, job_type, status, priority, queued_at

#### prompt_executions
| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| id | UUID | PK | |
| project_id | UUID | FK → projects.id (CASCADE) | |
| workflow_id | UUID | FK → workflows.id (SET NULL) | |
| scene_id | UUID | FK → scenes.id (SET NULL) | |
| agent_type | VARCHAR(50) | default '' | |
| prompt_template | VARCHAR(200) | default '' | |
| prompt_variables | TEXT | default '{}' | JSON-encoded dict |
| rendered_prompt | TEXT | default '' | |
| provider | VARCHAR(50) | default '' | Enum: AIProvider |
| model | VARCHAR(100) | default '' | |
| temperature | FLOAT | default 0.7 | |
| response | TEXT | default '' | |
| latency_ms | INTEGER | default 0 | |
| cost_usd | FLOAT | default 0.0 | |
| input_tokens | INTEGER | default 0 | |
| output_tokens | INTEGER | default 0 | |
| cached_tokens | INTEGER | default 0 | |
| status | VARCHAR(20) | default 'pending' | Enum: PromptExecutionStatus |
| error_message | TEXT | NULLABLE | |
| created_at | TIMESTAMPTZ | NOT NULL | |

**Indexes**: project_id, workflow_id, scene_id, provider, status, created_at

#### cost_records
| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| id | UUID | PK | |
| user_id | UUID | FK → users.id (SET NULL) | |
| project_id | UUID | FK → projects.id (CASCADE), NOT NULL | |
| workflow_id | UUID | FK → workflows.id (SET NULL) | |
| job_id | UUID | FK → generation_jobs.id (SET NULL) | |
| scene_id | UUID | FK → scenes.id (SET NULL) | |
| asset_id | UUID | FK → assets.id (SET NULL) | |
| provider | VARCHAR(50) | default '' | |
| cost_usd | FLOAT | default 0.0, NOT NULL | |
| cost_category | VARCHAR(30) | default 'llm' | llm, image, video, voice, rendering |
| period | VARCHAR(20) | default 'daily' | daily, weekly, monthly |
| period_start | TIMESTAMPTZ | NULLABLE | |
| period_end | TIMESTAMPTZ | NULLABLE | |
| metadata | TEXT | default '{}' | JSON-encoded dict |
| created_at | TIMESTAMPTZ | NOT NULL | |

**Indexes**: user_id, project_id, workflow_id, job_id, scene_id, asset_id, provider, cost_category, period, created_at

#### token_usage_records
| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| id | UUID | PK | |
| user_id | UUID | FK → users.id (SET NULL) | |
| project_id | UUID | FK → projects.id (CASCADE), NOT NULL | |
| workflow_id | UUID | FK → workflows.id (SET NULL) | |
| provider | VARCHAR(50) | default '' | |
| agent_type | VARCHAR(50) | default '' | |
| model | VARCHAR(100) | default '' | |
| input_tokens | INTEGER | default 0, NOT NULL | |
| output_tokens | INTEGER | default 0, NOT NULL | |
| cached_tokens | INTEGER | default 0, NOT NULL | |
| metadata | TEXT | default '{}' | JSON-encoded dict |
| created_at | TIMESTAMPTZ | NOT NULL | |

**Indexes**: user_id, project_id, workflow_id, provider, agent_type, created_at

### Design Patterns Implemented

- **Repository Pattern**: Async CRUD + query methods for all aggregates, mapping ORM ↔ domain entities
- **Unit of Work**: Async context manager wrapping `AsyncSession` with nested transaction support
- **Specification Pattern**: Composable query predicates (`AND`, `OR`, `NOT`) for reusable filtering logic
- **Single-Table Inheritance**: Asset hierarchy using `asset_type` discriminator column
- **Audit Mixin**: `created_by`, `updated_by`, `deleted_by` on `Project`, `Workflow`, `Scene` tables
- **JSON Encoding**: Complex fields (tags, metadata, prompts, payload, result) stored as JSON-encoded TEXT
