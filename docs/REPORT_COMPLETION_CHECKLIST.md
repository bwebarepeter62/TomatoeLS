# Tomato Leaf Scan: Academic Report Completion Checklist

---

**Project Title:** AI-Based Image Processing System for Early Tomato Leaf Disease Detection  
**Target File to Finalize:** `PROJECT_REPORT_DRAFT.md` & `TECHNICAL_DOCUMENTATION.md`  
**Purpose:** This actionable checklist identifies all personal details, screenshots, empirical tests, supervisor confirmations, and institutional formatting requirements needed before submitting your final-year university project report.

---

## 1. Personal & Institutional Information Checklist

In `PROJECT_REPORT_DRAFT.md`, find and replace the following placeholder tags:

- [ ] **Candidate Full Name:** Replace `[Insert Student Full Name Here]` on Title Page, Declaration, and Approval pages.
- [ ] **Registration / Student ID Number:** Replace `[Insert Student Registration / ID Number Here]`.
- [ ] **Department & Faculty:** Verify `Department of Computer Science` and `Faculty of Computing and Information Technology` match your university's exact faculty/school names.
- [ ] **University Name:** Replace `[Insert University / College Name Here]`.
- [ ] **Supervisor Details:** Replace `[Insert Supervisor Name and Academic Title Here]` (e.g., *Dr. John Doe, Senior Lecturer*).
- [ ] **Head of Department:** Replace `[Insert Head of Department Name Here]` on the Approval page.
- [ ] **Submission Month & Year:** Update `[Insert Month and Year, e.g., October 2026]`.
- [ ] **Dedication:** Adapt the text in the Dedication section according to your personal preference.
- [ ] **Acknowledgements:** Personalize the names and acknowledgements for family, friends, laboratory staff, and lecturers who assisted you.

---

## 2. Screenshot Capture Checklist (Figure Placeholders)

Start the local server (`python app.py` or double-click `start_app.bat`), open your browser to `http://127.0.0.1:5000`, and capture the following screenshots:

- [ ] **Figure 4.1: Landing Page (`home.html`)**
  - *Location in Report:* Chapter 4, Section 4.7.1 (`[Insert Figure 4.1: ...]`).
  - *How to Capture:* Open `http://127.0.0.1:5000/`. Capture the full hero section showing the title, call-to-action button, feature list, and floating preview card.
- [ ] **Figure 4.2: AI Leaf Scanner Page (`scan.html`)**
  - *Location in Report:* Chapter 4, Section 4.7.2 (`[Insert Figure 4.2: ...]`).
  - *How to Capture:* Navigate to `http://127.0.0.1:5000/scan`. Select a leaf image from your computer to show the upload box, farm plot selector, and the live image preview.
- [ ] **Figure 4.3: Diagnostic Results Display (`scan.html`)**
  - *Location in Report:* Chapter 4, Section 4.7.3 (`[Insert Figure 4.3: ...]`).
  - *How to Capture:* Click "Scan leaf". Once the diagnosis renders, capture the diagnosis title, confidence percentage badge, pathogen cause, immediate action cards, and treatment recommendations.
- [ ] **Figure 4.4: Tomato Farm Management (`farms.html`)**
  - *Location in Report:* Chapter 4, Section 4.7.4 (`[Insert Figure 4.4: ...]`).
  - *How to Capture:* Navigate to `http://127.0.0.1:5000/farms`. Show your registered farm cards with acreage, plant count, and varieties, or open the "Add New Farm" modal dialog.
- [ ] **Figure 4.5: Crop Monitoring Dashboard (`monitoring.html`)**
  - *Location in Report:* Chapter 4, Section 4.7.5 (`[Insert Figure 4.5: ...]`).
  - *How to Capture:* Navigate to `http://127.0.0.1:5000/monitoring`. Capture the four KPI cards, any active outbreak alerts, the Doughnut health distribution chart, and the pathogen frequency bar chart.
- [ ] **Figure 4.6: Scan Diagnostic History Archive (`history.html`)**
  - *Location in Report:* Chapter 4, Section 4.7.6 (`[Insert Figure 4.6: ...]`).
  - *How to Capture:* Navigate to `http://127.0.0.1:5000/history`. Show the filter toolbar (search field, status dropdown, farm filter) and the grid of past scan cards with thumbnails and dates.
- [ ] **Optional Figure 4.7: Scan Detail Modal**
  - *How to Capture:* On the History page, click "View Full Report" on any scan card to display the diagnostic modal overlay.

---

## 3. Empirical Model Evaluation & Field Testing Checklist

> **Crucial Academic Integrity Note:**
> The project codebase contains the pre-compiled, quantized model weights (`assets/models/best_int8.tflite`) and runs inference locally on CPU. The repository does not contain raw training datasets or training logs. Do not fabricate accuracy metrics. Instead, execute the following evaluation procedures:

- [ ] **Automated Regression Suite:**
  - Run the automated test suite in terminal:
    ```powershell
    python test_app.py
    ```
  - Verify that all **54 tests pass** and record the timestamp and execution duration for your Chapter 4 discussion.
- [ ] **Collect a Small Local Test Sample (Optional but Highly Recommended):**
  - Collect 20 to 50 real tomato leaf photographs (or use sample leaves from open benchmarks such as PlantVillage).
  - Categorize them into known ground-truth classes (e.g., 10 Healthy, 10 Early Blight, 10 Septoria, 10 Late Blight).
  - Upload each leaf through the `/scan` interface and record whether the predicted class matches the ground truth.
  - Compute your own empirical test accuracy:
    $$\text{Empirical Accuracy} = \frac{\text{Correct Predictions}}{\text{Total Test Images}} \times 100\%$$
  - Insert this empirical table into Chapter 4, Section 4.9.
- [ ] **Inference Latency Measurement:**
  - Note the time elapsed (in seconds) between clicking "Scan leaf" and the results appearing on screen. Typical CPU inference latency ranges from **0.8s to 2.5s** depending on workstation processor specifications. Document your hardware CPU model and measured latency in Chapter 4.

---

## 4. Agronomic & Supervisor Consultations Checklist

Consult with your academic supervisor and an agricultural officer/agronomist on the following:

- [ ] **University Title Approval:** Confirm whether your university department requires the exact wording:
  - *AI-Based Image Processing System for Early Tomato Leaf Disease Detection*, or
  - *Tomato Leaf Scan: An Intelligent Crop Health Platform for Tomato Growers*.
- [ ] **Referencing Style Confirmation:** The draft uses **APA 7th Edition**. Confirm whether your faculty specifies IEEE, Harvard, or APA.
- [ ] **Local Chemical Trade Names:** Review the chemical treatments in `DAMAGE_DB` (e.g., Mancozeb, Copper Oxychloride, Chlorothalonil) with a local agronomist to confirm they match authorized agricultural products in your region.
- [ ] **Local Extension Contacts:** If your department requires a real local stakeholder contact, add the phone number or office details of your local agricultural extension service in Chapter 1.

---

## 5. University Formatting & Dissertation Standards

Before converting `PROJECT_REPORT_DRAFT.md` into Word or PDF, format according to your university's guidelines:

- [ ] **Typography:** Standard university fonts: Times New Roman (12 pt) or Arial / Calibri (11 pt).
- [ ] **Line Spacing:** 1.5 or 2.0 (Double) line spacing, with 1.0 (Single) line spacing for indented code excerpts and block quotes.
- [ ] **Margins:** 1.5 inches (38 mm) left margin (for binding), 1.0 inch (25 mm) top, bottom, and right margins.
- [ ] **Pagination:**
  - Roman numerals (`i, ii, iii, iv...`) for Preliminary pages (starting after the Title Page).
  - Arabic numerals (`1, 2, 3, 4...`) starting from Chapter One, Page 1 through to the end of Appendices.
- [ ] **Headings Hierarchy:**
  - Heading 1: Chapter Titles (e.g., `CHAPTER ONE: INTRODUCTION`) — Centered, Bold, Uppercase.
  - Heading 2: Main Sections (e.g., `1.1 Background of the Study`) — Left-aligned, Bold.
  - Heading 3: Subsections (e.g., `1.3.1 Functional Requirements`) — Left-aligned, Bold.
- [ ] **Table & Figure Captions:**
  - Figure captions placed **below** the figure (e.g., *Figure 4.1: Tomato Leaf Scan Landing Page*).
  - Table captions placed **above** the table (e.g., *Table 4.1: Automated Software Test Case Results*).

---

## 6. Document File Verification

Ensure the following documentation files exist in your project root:

1. `TECHNICAL_DOCUMENTATION.md` — Complete engineering reference manual (13 chapters + 4 appendices).
2. `PROJECT_REPORT_DRAFT.md` — Formal university academic dissertation draft (5 academic chapters + preliminary pages + APA 7th references).
3. `REPORT_COMPLETION_CHECKLIST.md` — This actionable checklist.

---

*Checklist generated for the Tomato Leaf Scan project. Keep this document updated as you complete each task prior to final submission.*
