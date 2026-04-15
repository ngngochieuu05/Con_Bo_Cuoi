# Con Bò Cưới Documentation

Complete documentation for the AI cattle monitoring system.

## Core Documents

### [Project Overview & PDR](./project-overview-pdr.md) (230 lines)
High-level vision, functional requirements, non-functional requirements, acceptance criteria, and open questions.
- **For:** Stakeholders, product managers, new developers
- **Contains:** Product vision, tech stack, FR/NFR list, data model overview, acceptance criteria

### [Codebase Summary](./codebase-summary.md) (391 lines)
Project structure, module reference, architectural patterns, and data flow examples.
- **For:** Developers, code reviewers, architects
- **Contains:** Directory tree, module reference, design patterns, data model ER diagram, standards applied

### [Code Standards](./code-standards.md) (693 lines)
Naming conventions, file organization, code quality guidelines, and patterns to follow/avoid.
- **For:** All developers (enforcement during code review)
- **Contains:** Naming rules, type hints, error handling, Windows workarounds, common pitfalls, review checklist

### [System Architecture](./system-architecture.md) (787 lines)
3-layer architecture, service layer, data access layer, entity relationships, and design decisions.
- **For:** Architects, tech leads, senior developers
- **Contains:** Layer diagrams, deployment architectures, data flow, integration points, security, testing strategy

### [Project Roadmap](./project-roadmap.md) (458 lines)
6-phase roadmap from MVP to community ecosystem, milestones, risks, and success metrics.
- **For:** Project managers, stakeholders, team planning
- **Contains:** Phases 1-6 breakdown, timelines, dependency graph, quarterly milestones, MoSCoW prioritization

### [Design Guidelines](./design-guidelines.md) (742 lines)
Color system, typography, components, layouts, accessibility, and design patterns.
- **For:** UI developers, designers, frontend engineers
- **Contains:** Color tokens, button styles, component patterns, responsive breakpoints, A11y checklist, microcopy guidelines

---

## Quick Navigation

**Starting Point:**
1. New to project? Start with [Project Overview & PDR](./project-overview-pdr.md)
2. Need to implement code? Read [Code Standards](./code-standards.md) first
3. Want to understand architecture? Study [System Architecture](./system-architecture.md)
4. Building UI? Follow [Design Guidelines](./design-guidelines.md)
5. Understanding codebase structure? Check [Codebase Summary](./codebase-summary.md)
6. Planning next phase? Review [Project Roadmap](./project-roadmap.md)

**By Role:**

| Role | Read | Priority |
|------|------|----------|
| **Developer** | Code Standards, Codebase Summary, Architecture | High |
| **UI/Frontend** | Design Guidelines, Code Standards | High |
| **Architect** | Architecture, Codebase Summary | High |
| **Tech Lead** | Code Standards, Architecture, Roadmap | Medium |
| **Product Manager** | Project Overview, Roadmap | High |
| **DevOps** | Architecture, Project Overview | Medium |
| **QA/Tester** | Project Overview, Code Standards, Roadmap | Medium |

---

## Key Facts At-a-Glance

| Aspect | Detail |
|--------|--------|
| **Language** | Python 3.14 |
| **UI Framework** | Flet 0.82.2 |
| **Architecture** | 3-layer (UI, BLL, DAL) |
| **Data Storage** | JSON (dev), PostgreSQL-ready |
| **Entry Point** | `python webapp_system/src/main.py` |
| **Test Users** | admin/admin123, expert01/expert123, farmer01/farmer123 |
| **File Size Limit** | 200 LOC per file |
| **Design System** | Centralized in `ui/theme.py` |
| **MVP Status** | ~25% complete (Phase 1) |
| **Production Target** | Q3 2026 (Phase 3) |

---

## Development Workflow

```
1. Read Code Standards (naming, patterns, file size)
2. Read relevant architecture section
3. Check Codebase Summary for file locations
4. Review Design Guidelines (if UI work)
5. Implement feature following standards
6. Pass code review checklist
7. Update docs if adding new concepts
```

---

## Documentation Maintenance

**Update triggers:**
- Feature implementation → Update relevant doc section
- Major architectural change → Update System Architecture + Codebase Summary
- New phase starts → Update Project Roadmap
- Design token change → Update Design Guidelines
- Code standard violation → Add to Code Standards section

**Review cycle:**
- Weekly: Spot-check for obvious errors
- Monthly: Full documentation audit
- Quarterly: Update roadmap and architecture diagrams

---

## Standards Compliance

All documentation:
- ✓ Verified against actual codebase
- ✓ Uses exact function/class/variable names from code
- ✓ Includes code examples that compile
- ✓ Links to actual file paths (using relative paths from docs/)
- ✓ Stays under 800 LOC per file
- ✓ Technical terms in English, database fields in Vietnamese

---

## Questions?

- **Architecture question?** → System Architecture
- **How do I code this?** → Code Standards
- **Where is X in the codebase?** → Codebase Summary
- **What phase are we in?** → Project Roadmap
- **How should this look?** → Design Guidelines
- **What's the big picture?** → Project Overview

---

Generated: 2026-04-15  
Last Updated: 2026-04-15
