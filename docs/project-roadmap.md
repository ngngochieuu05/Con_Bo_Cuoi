# Project Roadmap — Con Bò Cưới

## Current Status

**Version:** 0.1.0 (MVP - Minimum Viable Product)  
**Last Updated:** 2026-04-15  
**Overall Progress:** ~25% complete

---

## Phase 1: Core System (MVP) — 25% Complete ✓ Mostly Done

**Timeline:** Weeks 1-8  
**Status:** In Progress (Auth, DAL, Admin basics working)  
**Owner:** Dev Team

### Goals
- [x] 3-layer architecture (UI, BLL, DAL)
- [x] Multi-role authentication (admin, expert, farmer)
- [x] JSON-based data storage with BaseRepo abstraction
- [x] Admin dashboard with basic KPIs
- [x] Alert system (creation, pending/resolved states)
- [x] User management (CRUD)
- [x] Offline-capable with caching
- [ ] Expert dashboard complete (50% done)
- [ ] Farmer live monitoring (camera integration partial)
- [ ] YOLO model management UI (basic interface done)

### Deliverables
- ✓ main.py with role-based routing
- ✓ auth_service.py (login, logout, session)
- ✓ Base repository pattern
- ✓ 3 seeded default users
- ✓ Admin screens (dashboard, user management, settings)
- ⚠ Expert screens (dashboard done, consulting review in progress)
- ⚠ Farmer screens (dashboard cached, live monitoring WIP)
- ✓ Design system (theme.py)

### Success Criteria
- [ ] App launches and loads login screen without errors
- [ ] All 3 roles can log in with test accounts
- [ ] Admin can CRUD users and assign roles
- [ ] Alerts generate and appear in dashboards
- [ ] App works offline (JSON cache fallback)
- [ ] No console errors or warnings

### Known Issues
1. **Camera integration incomplete:** Windows OpenCV setup needed
2. **Live streaming:** MJPG codec handling on Windows requires subprocess workaround
3. **Password hashing:** SHA256 without salt (security debt)
4. **Session persistence:** page.client_storage clears on restart
5. **Email backend:** Forgot password UI only, no email service

### Next Milestone
- Complete expert consulting review workflow
- Complete farmer live monitoring with real camera feed
- Add basic YOLO inference (CPU-based)

---

## Phase 2: Expert & Farmer Features — 15% Complete

**Timeline:** Weeks 9-14  
**Status:** Not Started (Planning phase)  
**Owner:** Feature Team

### Goals
- [ ] Expert consulting review: receive requests → analyze data → send recommendations
- [ ] Expert raw data review: image curation interface for HITL pipeline
- [ ] Farmer live monitoring: real-time camera feed at 30 FPS
- [ ] Farmer health consulting: chat + camera stream context
- [ ] Session history: store and display past consulting interactions
- [ ] Model configuration per user (conf/IOU sliders)
- [ ] Alert details view with image attachments
- [ ] Notification preferences (toast, email, SMS)

### Deliverables
- [ ] expert/dashboard.py (KPI + case table)
- [ ] expert/consulting_review.py (card-based case list)
- [ ] expert/raw_data_review.py (image annotation interface)
- [ ] framer/live_monitoring.py (camera polling + display)
- [ ] framer/health_consulting.py (chat + stream)
- [ ] framer/session_history.py (case outcomes table)
- [ ] model configuration UI (confidence/IOU sliders)
- [ ] Notification service (email/SMS integration)

### Success Criteria
- [ ] Expert receives case requests from farmers
- [ ] Expert can review raw images and add annotations
- [ ] Expert recommendations saved and visible to farmer
- [ ] Farmer sees live camera feed ≥30 FPS
- [ ] Farmer can initiate health consultation (chat + camera)
- [ ] Session history tracks all consulting interactions
- [ ] Model config changes persist per user

### Timeline Estimate
- Weeks 9-10: Expert workflow (case requests, consulting review)
- Weeks 11-12: Expert raw data review (image annotation)
- Weeks 13-14: Farmer live monitoring + session history
- Weeks 15: Integration testing

---

## Phase 3: Production Hardening — 0% Complete

**Timeline:** Weeks 15-20  
**Status:** Planned  
**Owner:** DevOps + Security Team

### Goals
- [ ] Replace SHA256 with bcrypt password hashing
- [ ] Implement persistent session (JWT + HTTP-only cookies)
- [ ] Add role-based access control (RBAC) in DAL layer
- [ ] Switch from JSON to PostgreSQL
- [ ] Add email-based password reset
- [ ] Implement HTTPS enforcement (web mode)
- [ ] Add comprehensive error logging
- [ ] Create user onboarding guide
- [ ] Load testing (simulate 100 concurrent users)

### Deliverables
- [ ] bcrypt integration + password migration script
- [ ] JWT token generation & validation service
- [ ] RBAC middleware (check role before DAL operations)
- [ ] PostgreSQL schema + migration tools
- [ ] Email service integration (SES/SendGrid)
- [ ] Nginx reverse proxy configuration
- [ ] Docker build + deployment scripts
- [ ] Monitoring & alerting setup (Prometheus/Grafana)
- [ ] User documentation + video tutorials

### Success Criteria
- [ ] All passwords bcrypt-hashed
- [ ] Session survives app restart (web mode)
- [ ] Users cannot access unauthorized screens/data
- [ ] PostgreSQL handles >500 users without slowdown
- [ ] Password reset works end-to-end
- [ ] HTTPS enforced in web deployment
- [ ] Zero critical security vulnerabilities (OWASP Top 10)
- [ ] App load time <3 seconds

### Security Checklist
- [ ] No plaintext passwords in logs
- [ ] No hardcoded API keys (use .env)
- [ ] SQL injection protected (ORM usage)
- [ ] CSRF tokens on state-changing requests
- [ ] Rate limiting on login attempts
- [ ] Audit log for sensitive operations
- [ ] Data encryption at rest (if cloud stored)
- [ ] Regular security scanning (SAST/DAST)

---

## Phase 4: Advanced Analytics & ML — 0% Complete

**Timeline:** Weeks 21-30  
**Status:** Planned  
**Owner:** Data Science + Analytics Team

### Goals
- [ ] Herd health trend dashboard (7-day, 30-day, 1-year views)
- [ ] Disease prevalence heatmap (which diseases, which stalls)
- [ ] Model performance metrics (precision, recall, F1 per model)
- [ ] Predictive alerts (ML predicts disease 48h in advance)
- [ ] Behavior pattern recognition (unusual activity flagging)
- [ ] Export functionality (CSV, PDF, Excel)
- [ ] Report generation (automated daily/weekly summaries)
- [ ] Data visualization (charts, graphs, heatmaps)

### Deliverables
- [ ] Analytics dashboard screen (admin + expert only)
- [ ] Trend API endpoint (`GET /api/trends/{period}`)
- [ ] Report generation service
- [ ] Export service (CSV/PDF/Excel)
- [ ] Predictive alert model (trained on historical data)
- [ ] Visualization library integration (Plotly/Matplotlib)
- [ ] Data warehouse schema (for big data)

### Success Criteria
- [ ] Dashboard loads <2 seconds (even with 1yr of data)
- [ ] Trends are accurate ±5%
- [ ] Predictive alerts have >80% precision
- [ ] Reports are exportable in 3+ formats
- [ ] Data retention policy implemented (keep 2 years)

---

## Phase 5: Mobile App — 0% Complete

**Timeline:** Weeks 31-40  
**Status:** Future (depends on web mode stability)  
**Owner:** Mobile Team

### Goals
- [ ] Native iOS app (React Native or Swift)
- [ ] Native Android app (Kotlin or React Native)
- [ ] Push notifications on alert
- [ ] Offline queue (sync when online)
- [ ] Biometric auth (fingerprint/face)
- [ ] QR code scanning for camera setup

### Deliverables
- [ ] iOS app on App Store
- [ ] Android app on Google Play
- [ ] Push notification service (Firebase Cloud Messaging)
- [ ] Mobile-optimized UI
- [ ] Offline data sync mechanism

### Success Criteria
- [ ] 10k+ downloads within 3 months
- [ ] >4.5 star rating on both stores
- [ ] Push notifications delivered <10 seconds
- [ ] Offline mode tested thoroughly

---

## Phase 6: Community & Ecosystem — 0% Complete

**Timeline:** Weeks 41+  
**Status:** Future  
**Owner:** Growth + Community Team

### Goals
- [ ] Public GitHub repository
- [ ] Plugin system for 3rd-party integrations
- [ ] API documentation (OpenAPI/Swagger)
- [ ] SDK for integrating with 3rd-party apps
- [ ] Community forum
- [ ] Bi-weekly webinars
- [ ] User feedback program

### Deliverables
- [ ] Open-source repository (MIT license)
- [ ] Plugin architecture + examples
- [ ] REST API documentation
- [ ] Python SDK + examples
- [ ] Discord/Slack community channel

---

## Dependency Graph

```
Phase 1 (Core)
    ↓
Phase 2 (Expert/Farmer)
    ↓
Phase 3 (Production)
    ├─→ Phase 4 (Analytics)
    │       ↓
    │   Phase 5 (Mobile)
    │
    └─→ Phase 6 (Community)
```

**Critical Path:** Phase 1 → Phase 3 (must complete before production deployment)

**Can run in parallel:** Phase 2 and Phase 4 development

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| **Camera driver issues (Windows)** | High | High | Test on multiple Windows versions early; document workarounds |
| **Performance with large datasets** | Medium | High | Implement PostgreSQL early; load test at 1M records |
| **Security vulnerabilities** | Medium | Critical | Security review at Phase 3; regular penetration testing |
| **User adoption** | Medium | Medium | Early beta testers; gather feedback weekly |
| **Budget overruns** | Low | High | Scope creep control; prioritize features ruthlessly |
| **Key developer turnover** | Low | Medium | Documentation; pair programming; knowledge transfer |

---

## Success Metrics

### User Adoption
- [ ] 50+ beta users by week 10
- [ ] 500+ registered users by end of year
- [ ] 10+ farms using system in production
- [ ] >80% user retention (after 3 months)

### Technical Quality
- [ ] Code coverage >70%
- [ ] Zero critical bugs in production
- [ ] <2% error rate in API calls
- [ ] <1s median response time

### Business Impact
- [ ] Reduce herd illness detection time by 50%
- [ ] Decrease veterinary costs by 30% (per farm)
- [ ] Enable 1 expert to monitor 50+ farms (vs. 5 before)

---

## Quarterly Milestones

### Q1 2026 (Jan-Mar) — CURRENT
- [x] Architecture design
- [x] Auth system
- [x] Admin dashboard (basic)
- [ ] Expert dashboard (in progress)
- [ ] Farmer UI (50% done)

**Target:** App launches and 5 beta users sign up

### Q2 2026 (Apr-Jun)
- [ ] Expert consulting workflow complete
- [ ] Farmer live monitoring complete
- [ ] YOLO model management UI
- [ ] Password reset (email backend)

**Target:** 50 beta users, zero critical bugs

### Q3 2026 (Jul-Sep)
- [ ] PostgreSQL migration
- [ ] Bcrypt + JWT implementation
- [ ] Load testing (100 concurrent users)
- [ ] HTTPS enforcement

**Target:** Production deployment to 5 farms

### Q4 2026 (Oct-Dec)
- [ ] Analytics dashboard
- [ ] Mobile app (iOS/Android)
- [ ] Community forum launch
- [ ] SDK + plugin system

**Target:** 500 users, public beta announcement

---

## Feature Prioritization (MoSCoW)

### Must Have (MVP, Phase 1-2)
- Multi-role authentication
- Alert system
- Admin user management
- Expert consulting workflow
- Farmer live monitoring
- Offline capability

### Should Have (Phase 2-3)
- Email-based password reset
- YOLO model configuration
- Session history
- Notification preferences
- PostgreSQL support

### Could Have (Phase 4-5)
- Analytics dashboard
- Predictive alerts
- Mobile app
- Advanced reporting
- Plugin system

### Won't Have (Out of Scope for 2026)
- AI-powered chatbot (use simple Q&A instead)
- 3D herd visualization (2D dashboard sufficient)
- Blockchain/NFT integration (not needed)
- Multi-language support (Vietnamese + English only)

---

## Budget & Resource Allocation

| Phase | Developers | Duration | Estimated Cost |
|-------|-----------|----------|-----------------|
| Phase 1 | 2 | 8 weeks | $16K |
| Phase 2 | 2 | 6 weeks | $12K |
| Phase 3 | 3 | 6 weeks | $18K |
| Phase 4 | 3 | 10 weeks | $30K |
| Phase 5 | 4 | 10 weeks | $40K |
| **Total** | — | 40 weeks | **$116K** |

(Estimates based on $100/hr dev rate, Vietnam cost of living)

---

## Communication Plan

### Weekly
- [ ] Team standup (15 min): blockers, progress, next steps
- [ ] Code review on all PRs before merge

### Bi-weekly
- [ ] Stakeholder demo (new features)
- [ ] User feedback survey (beta testers)

### Monthly
- [ ] Retrospective: what went well, what didn't
- [ ] Roadmap review: adjust timeline if needed
- [ ] Security/performance audit

### Quarterly
- [ ] Board review: strategic alignment
- [ ] User conference: showcase updates, gather requirements

---

## Graduation Criteria (Phase 1 → Phase 2)

Before moving to Phase 2, Phase 1 must meet:

- [ ] Zero critical bugs (all high-priority bugs fixed)
- [ ] 5+ beta users have tested for >1 week
- [ ] Code review approval from tech lead
- [ ] >70% code coverage in unit tests
- [ ] Performance benchmarks met (dashboard <2s load time)
- [ ] Security audit passed (no OWASP Top 10 vulnerabilities)
- [ ] Documentation complete (README, API docs, architecture)

**Phase 1 → Phase 2 Go/No-Go Decision:** Week 10

---

## Version Numbering

- **0.1.x** — Phase 1 (Alpha): Core system, not production-ready
- **0.2.x** — Phase 2 (Beta): Expert/Farmer features, user feedback
- **1.0.0** — Phase 3 (GA): Production hardening, security audit passed
- **1.1.x** — Phase 4 (Stable): Analytics features
- **2.0.0** — Phase 5+: Mobile apps, ecosystem

---

## Known Debt & Technical Backlog

### Must Fix Before Production
1. [ ] Bcrypt password hashing (SHA256 is weak)
2. [ ] Persistent session (JWT instead of page.client_storage)
3. [ ] Role-based access control in DAL
4. [ ] Email service for password reset

### Should Fix When Time Permits
1. [ ] PostgreSQL migration (currently JSON)
2. [ ] API documentation (OpenAPI spec)
3. [ ] Comprehensive error logging
4. [ ] Performance optimization (caching layer)

### Nice-to-Have
1. [ ] Dark mode UI
2. [ ] Multi-language support
3. [ ] Advanced search/filtering
4. [ ] Data visualization library

---

## Conclusion

Con Bò Cưới is on track for a **Phase 1 completion by week 10** (end of April 2026). The roadmap balances **quick MVP launch** with **long-term production quality**.

Key priorities:
1. **Complete Phase 1 testing** with real users
2. **Fix critical security issues** (Phase 3) before commercial launch
3. **Gather user feedback** continuously; adjust roadmap based on real needs

The 6-phase plan spans 12 months and positions Con Bò Cưới as the **leading AI cattle monitoring platform in Southeast Asia** by Q4 2026.
