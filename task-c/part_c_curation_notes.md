# Part C curation notes

- **Data-quality issue fixed**
  - **Issue:** Five usable responses were relevant to HR queries but ignored explicit output-format instructions: IDs 15, 16, 19, 32, and 40.
  - **Fix:** Rewrote those responses to preserve helpful HR content and Singlish/local tone while meeting the requested limits: under 10 words, three bullets, under 5 words, one word, and yes/no respectively.
  - **Why it matters:** Fine-tuning on format-breaking examples teaches the assistant to disregard user constraints. Corrected examples teach natural Singlish HR phrasing and reliable instruction following without removing relevant training data.

- **Five new examples**
  - **ID 51**
    - **Gap:** Maternity/parental leave.
    - **Why it matters:** The dataset has a maternity-leave query, but its response is mismatched; a natural Singlish example helps an internal HR assistant support a common employee life event.
    - **Query:** Eh I’m expecting soon, how do I apply for maternity leave ah?
    - **Response:** Can submit your maternity-leave request through the HR portal, then HR will confirm the eligibility and documents needed lah.
  - **ID 52**
    - **Gap:** Sick-leave and medical-certificate workflow.
    - **Why it matters:** Existing medical coverage is about reimbursement claims, not absence reporting; a Malay query and Malay response add language-matched coverage for practical internal HR support.
    - **Query:** Kalau saya sakit hari ini, macam mana nak hantar sijil cuti sakit ah?
    - **Response:** Muat naik sijil cuti sakit ke portal HR dan maklumkan pengurus ikut proses pelaporan lor.
  - **ID 53**
    - **Gap:** Flexible work and caregiving requests.
    - **Why it matters:** Current examples do not cover workplace arrangements; a Mandarin query and Mandarin response help a Singlish HR assistant handle employee needs beyond leave balances and claims while respecting the user's language.
    - **Query:** 我需要照顾家人，可以申请灵活工作时间吗？
    - **Response:** 可以向经理和 HR 提交弹性工作申请，说明照顾家人的需要，再按照现行政策审核 lor。
  - **ID 54**
    - **Gap:** Payroll self-service.
    - **Why it matters:** The dataset has no usable payroll or payslip example; this adds a frequent internal HR portal task in the target Singlish style.
    - **Query:** Where can I download my payslip ah?
    - **Response:** You can download your payslip from the HR portal under Payroll or Payslips; if cannot find it, you try contact HR support.
  - **ID 55**
    - **Gap:** Confidential grievance reporting.
    - **Why it matters:** No usable example covers inappropriate workplace conduct; this adds a safety-sensitive internal HR pathway while demonstrating respectful Singlish phrasing without personal data.
    - **Query:** My colleague keeps making inappropriate comments, how report confidentially ah?
    - **Response:** You can report it through HR’s confidential grievance channel; keep relevant details then ask HR about the next steps.

- **Multilingual coverage:** IDs 52 and 53 intentionally pair non-English inputs with responses in the same language. This addresses a gap where the assistant might default to English instead of responding in Malay or Mandarin.
