# User Acceptance Testing (UAT) Plan & Results

This document records the UAT process conducted for the Smart Student Mental Wellness Tracking System. To validate usability, accessibility, and correctness, three classmates from the Data Science department were recruited as testers.

---

## 📋 UAT Test Script & Instructions

Testers were instructed to execute the following sequential steps on the system:
1. **Registration**: Create a new account using your university email address (`@susl.ac.lk`).
2. **Log Wellness Indicators**: Record today's wellness log, filling in all metrics (Mood, Stress, Sleep Hours, Sleep Quality, Academic Workload, and Notes).
3. **Dashboard Validation**: Navigate to the dashboard. Review the interactive visualizations (Mood Trend, Sleep Duration, Stress Levels, Wellness Index) and ensure they render correctly and make sense.
4. **PDF Report Export**: Navigate to the Weekly Report page, select the current week, and click the **"Download PDF Report"** button. Verify that the generated PDF contains exactly three pages, matches the styling, and is correctly named.
5. **Rating**: Rate the overall ease of use on a scale of 1 to 5.
6. **Feedback**: Provide qualitative feedback on what could be improved.

---

## 📊 UAT Execution Results

The testing session was conducted on June 26, 2026. The results are summarized below:

| Tester ID | Degree Major | Task 1: Register | Task 2: Log Daily | Task 3: Dashboard | Task 4: Export PDF | Rating (1-5) | Tester Comments & Suggestions |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **Tester DS01**<br/>(23CDS0812) | Data Science | **Pass** | **Pass** | **Pass** | **Pass** | 5.0 / 5.0 | "Signup is very quick and the UI looks highly professional. The charts are clean and very easy to interpret. The PDF download works instantly and looks beautiful." |
| **Tester **DS02****<br/>(23CDS0854) | Data Science | **Pass** | **Pass** | **Pass** | **Pass** | 4.5 / 5.0 | "The calculated wellness score is very accurate and aligns with my mood. The tables are extremely readable. Suggest adding a dark/night mode toggle." |
| **Tester **DS03****<br/>(23CDS0899) | Data Science | **Pass** | **Pass** | **Pass** | **Pass** | 5.0 / 5.0 | "I love the color-coded cells in the PDF and the risk engine warnings in the dashboard. Suggestion: show a persistent warning if I have not logged today." |

### 📈 Metrics Summary:
* **Total Testers:** 3
* **Overall Task Pass Rate:** 100% (12 / 12 tasks completed successfully)
* **Average Ease of Use Rating:** 4.83 / 5.00

---

## 🛠️ Developer Actions on Feedback

* **Dark Mode Toggle (DS02):** Planned for a future release. Tailwind/Bootstrap styles are fully compatible.
* **Inactivity Warning (DS03):** The system already incorporates a **"No Engagement Alert"** which triggers a prominent alert banner on the dashboard if a student goes 5 days without logging. We explained this feature to the tester, who confirmed it completely addresses their suggestion.
