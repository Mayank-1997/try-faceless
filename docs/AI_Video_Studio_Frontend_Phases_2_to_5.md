# AI Video Studio SaaS - Frontend Roadmap (Phases 2--5)

> This roadmap assumes **Frontend Phase 1 (Platform Foundation)** has
> already been completed.

------------------------------------------------------------------------

# Phase 2 -- Workspace Experience & Project Management

## Objective

Build the primary workspace that hosts every future feature module.

## Scope

-   Dashboard
-   Project Management
-   Project Creation Wizard
-   Workspace Shell
-   Sidebar
-   Top Navigation
-   Right Inspector Panel
-   Bottom Status Bar
-   Workspace Registry
-   Global Search
-   Command Palette Integration
-   Workflow Visualization (UI only)
-   Platform SDK integration for Project CRUD

## Do NOT Implement

-   Research
-   Script
-   Storyboard
-   Assets
-   Timeline
-   Rendering
-   Publishing
-   Analytics

## Deliverables

1.  Dashboard
2.  Project CRUD
3.  Workspace Shell
4.  Navigation
5.  Workspace Registry
6.  Tests
7.  Documentation

**Stop and wait for approval before Phase 3.**

------------------------------------------------------------------------

# Phase 3 -- AI Content Creation Experience

## Objective

Implement the automatic AI content generation workflow.

## Workflow

Topic → Research → Script → Storyboard → Asset Generation

## Modules

-   Research
-   Script Editor
-   Storyboard
-   Asset Studio
-   Generation Dashboard
-   Live Progress
-   Realtime Updates

## Features

### Research

-   Research Summary
-   Keywords
-   Audience
-   Sources
-   Regenerate

### Script

-   Rich Text Viewer/Editor
-   Word Count
-   Estimated Duration
-   Export
-   Regenerate

### Storyboard

-   Scene Cards
-   Narration
-   Camera
-   Animation
-   Asset Type
-   Scene Regeneration

### Asset Studio

-   Images
-   Videos
-   Voice
-   Music
-   Subtitles
-   Thumbnail
-   Preview
-   Download
-   Replace
-   Regenerate

## Deliverables

1.  Research Module
2.  Script Module
3.  Storyboard Module
4.  Asset Studio
5.  Generation Center
6.  Realtime Workflow
7.  Tests
8.  Documentation

**Stop and wait for approval before Phase 4.**

------------------------------------------------------------------------

# Phase 4 -- Video Production Experience

## Objective

Convert generated assets into a final production-ready video.

## Modules

-   Timeline Editor
-   Composition Viewer
-   Rendering
-   Publishing

### Timeline

-   Drag & Drop
-   Trim
-   Split
-   Replace
-   Multi-track Editing

Tracks - Video - Images - Voice - Music - Effects - Subtitles

### Rendering

-   Render Queue
-   Progress
-   Logs
-   Preview
-   Download

### Publishing

-   YouTube Integration
-   Title
-   Description
-   Thumbnail
-   Tags
-   Schedule
-   Publish

## Deliverables

1.  Timeline
2.  Rendering UI
3.  Publishing UI
4.  Progress Monitoring
5.  Tests
6.  Documentation

**Stop and wait for approval before Phase 5.**

------------------------------------------------------------------------

# Phase 5 -- Platform Experience

## Objective

Build operational capabilities for a production SaaS.

## Modules

-   Analytics
-   Billing
-   Settings
-   Admin

### Analytics

-   Usage
-   AI Cost
-   Provider Statistics
-   Rendering Metrics
-   Publishing Metrics

### Billing

-   Subscription
-   Credits
-   Usage
-   Invoices

### Settings

-   Brand Kit
-   AI Providers
-   Voices
-   Models
-   Notifications
-   Storage

### Admin

-   Users
-   Organizations
-   Workers
-   Queues
-   Logs
-   Monitoring
-   Feature Flags

## Deliverables

1.  Analytics
2.  Billing
3.  Settings
4.  Admin
5.  Final Testing
6.  Documentation

------------------------------------------------------------------------

# Development Rules (Apply to Every Phase)

-   Never recreate completed modules.
-   Reuse the Platform Kernel.
-   Reuse the Platform SDK.
-   Reuse the Design System.
-   No direct API calls from pages.
-   No duplicated business logic.
-   Use TanStack Query for server state.
-   Use Zustand for UI state.
-   Maintain feature isolation.
-   Use lazy loading.
-   Keep the workflow fully automatic.
-   Generate production-ready, fully typed code.
-   Generate tests and documentation at the end of each phase.
-   Wait for approval before starting the next phase.
