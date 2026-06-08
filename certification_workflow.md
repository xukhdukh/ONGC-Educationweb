# DIYA LMS — Certification Workflow & Integration Roadmap

> **Document Version**: 1.0  
> **Date**: 6 June 2026  
> **Topic**: Certificate Generation, Evaluation Workflow, and Future Integration

---

## 1. Current Certification Workflow

The current certification workflow in DIYA LMS is highly automated and rule-based, designed to ensure learners actually meet the educational requirements before receiving a credential.

### 1.1 The Policy Engine
Each `Course` has an attached `CourseCompletionPolicy` that dictates the exact rules a learner must satisfy to be eligible for a certificate. The policy enforces:
- **`min_progress_percentage`**: The minimum percentage of lessons the user must watch/complete.
- **`min_quiz_pass_percentage`**: The minimum score required on quizzes.
- **`require_all_quiz_lessons_passed`**: Whether the learner must pass *every* quiz in the course.
- **`require_all_homeworks_submitted`**: Whether all assignments must be turned in.
- **`require_homework_min_percentage` / `require_homework_graded`**: Ensures homeworks are not just submitted, but actually reviewed and passed.
- **`auto_issue_certificate`**: A toggle determining if the certificate is generated immediately upon meeting criteria, or if it requires a manual trigger.

### 1.2 Eligibility & Issuance
1. **Evaluation**: When a learner accesses the course dashboard, the system evaluates their `LessonProgress`, `QuizAttempt`, and `HomeworkSubmission` data against the `CourseCompletionPolicy`.
2. **Eligibility Flag (`certificate_eligible`)**: If all blockers are cleared, the learner becomes eligible.
3. **Generation Trigger**:
   - If `auto_issue_certificate` is **enabled**, the system immediately creates a `Certificate` database record and generates the PDF.
   - If **disabled**, the learner sees an "Issue Digital Certificate" button, which they must click to trigger the `issue_digital_certificate` view.
4. **Enrollment Update**: The learner's `Enrollment` record is updated (`certificate_issued = True`) to lock in the completion status.

### 1.3 PDF Generation (`reportlab`)
The `generate_pdf()` method on the `Certificate` model programmatically creates the PDF document using the `reportlab` library. 
- It generates a unique tracking number (`DIYA-LMS-[YEAR]-[UUID]`).
- It stamps the learner's name, the course name, and the completion date.
- The resulting file is currently saved to local storage at `media/uploads/certificates/`.

### 1.4 Verification System
A public verification endpoint (`/dashboard/certificates/verify/`) allows anyone (e.g., employers, institute admins) to input a certificate tracking number and instantly verify its authenticity against the database.

---

## 2. Integration with Course Modules

Currently, the certification workflow sits at the **Course Level**. Moving forward, we will integrate it deeper into the modular architecture:

### 2.1 Module-Level Micro-Credentials
- **Current State**: Certificates are only issued when the *entire course* is completed.
- **Integration Plan**: Enable "Micro-Credentials" or "Badges" upon the completion of specific *Modules*. If a course has 10 modules, a user might earn a "Data Foundations" badge after Module 3. This ties directly into the existing `Gamification` app (Badges).

### 2.2 Prerequisite Enforcing
- Certificates can act as keys. A user might not be allowed to enroll in an "Advanced" course unless they possess the valid `Certificate` record from the "Beginner" course.

### 2.3 Timeline & Social Feed Broadcasting
- **Integration**: Upon certificate issuance, an automated `TimelinePost` (type: `achievement`) should be generated and broadcast to the user's followers and institute timeline, driving social engagement and gamification loops.

---

## 3. Roadmap & Future Enhancements

Aligning with the recently drafted `Bigdata_Archi.md`, here is the technical and feature roadmap for the certification engine:

### Phase 1: Migration to Object Storage (MinIO)
*Timeline: Short-Term*
- Currently, PDFs are saved to the local disk. As part of the Big Data migration, `certificate.pdf_file_path` will be migrated to the new `MediaAsset` registry.
- Certificates will be generated and uploaded directly to the MinIO `diya-media/certificates/` bucket, ensuring they are accessible across multiple server nodes.

### Phase 2: Customizable Templates
*Timeline: Medium-Term*
- Move away from the hardcoded `reportlab` layout.
- Allow Course Coordinators and Institute Admins to upload custom background images (e.g., Institute-specific branding).
- Store template coordinates (where the name and date go) in a JSON field on the `CourseCompletionPolicy`.

### Phase 3: Verifiable Credentials & Blockchain
*Timeline: Long-Term*
- Instead of just generating a PDF and a tracking number, compute the SHA-256 hash of the generated PDF.
- Implement a decentralized verification layer (e.g., anchoring certificate hashes to a public ledger like Polygon/Ethereum) so that credentials become cryptographically tamper-proof "Verifiable Credentials" (VCs).
- Introduce a "Add to LinkedIn" 1-click button using the LinkedIn Profile API.

### Phase 4: Skill-Graph Integration (AI Layer)
*Timeline: Long-Term*
- When a certificate is issued, the AI layer extracts the `keywords` attached to the Course, Modules, and Lessons (e.g., `['Python', 'Data Science', 'Machine Learning']`).
- These keywords are pushed to the user's `ProfessionalProfile.skills` JSON array, automatically building a dynamic, AI-verified resume for the learner.
